from __future__ import annotations

import asyncio
import json
import operator
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .deepseek import DeepSeekGateway
from .registry import ManagerRegistry
from .retrieval import CorpusIndex


Emit = Callable[[str, str, dict[str, Any]], Awaitable[None]]
MAX_AGENT_STEPS = 4
TOOL_TIMEOUT_SECONDS = 180


class SupervisorState(TypedDict, total=False):
    run_id: str
    thread_id: str
    question: str
    history_context: str
    output_language: str
    step: int
    decision: dict[str, Any]
    observations: Annotated[list[dict[str, Any]], operator.add]
    manager_results: Annotated[list[dict[str, Any]], operator.add]
    errors: Annotated[list[dict[str, str]], operator.add]
    critique: dict[str, Any]
    final_report: str


PLANNER_SYSTEM = """你是 Fund Insight 的 Supervisor Agent。你的任务是决定下一步调用哪个工具，而不是直接回答。
可用工具只有：
1. search_corpus：检索一至五位经理的原始资料，适合补证据、核对原话。
2. run_discussion：调用现有专家讨论工作流，模式可为 single、summary 或 meeting。
3. finish：证据和观点已足够，进入最终整理。
必须输出 JSON，字段：action、reason、manager_ids、query、discussion_mode。
每次只选一个动作；不得使用列表外的经理或工具。"""


def _compact(value: Any, limit: int = 12000) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else f"{text[:limit]}...<truncated>"


def _clean_ids(raw: Any, allowed: list[str]) -> list[str]:
    values = raw if isinstance(raw, list) else []
    return list(dict.fromkeys(str(item) for item in values if str(item) in allowed))[:5]


def build_supervisor_workflow(
    registry: ManagerRegistry,
    index: CorpusIndex,
    gateway: DeepSeekGateway,
    emit: Emit,
    discussion_graph: Any,
    checkpointer: Any | None = None,
):
    allowed_ids = registry.ids()
    catalog = [
        {
            "id": manager_id,
            "name": registry.get_raw(manager_id)["name"],
            "institution": registry.get_raw(manager_id)["institution"],
            "tags": registry.get_raw(manager_id).get("tags", []),
        }
        for manager_id in allowed_ids
    ]

    async def plan(state: SupervisorState) -> dict[str, Any]:
        step = state.get("step", 0) + 1
        prompt = f"""用户问题：{state['question']}
可用经理：{_compact(catalog)}
历史摘要：{state.get('history_context', '')}
已有观察：{_compact(state.get('observations', []))}
上轮评审：{_compact(state.get('critique', {}))}
当前步数：{step}/{MAX_AGENT_STEPS}
请选择下一步。"""
        raw = await gateway.generate_json(PLANNER_SYSTEM, prompt)
        action = raw.get("action") if raw.get("action") in {
            "search_corpus", "run_discussion", "finish"
        } else "run_discussion"
        manager_ids = _clean_ids(raw.get("manager_ids"), allowed_ids)
        if action != "finish" and not manager_ids:
            manager_ids = allowed_ids[:3]
        if action == "finish" and not state.get("observations"):
            action = "run_discussion"
            manager_ids = allowed_ids[:3]
        mode = raw.get("discussion_mode")
        if mode not in {"single", "summary", "meeting"}:
            mode = "single" if len(manager_ids) == 1 else "summary"
        if action == "run_discussion":
            if mode == "single":
                manager_ids = manager_ids[:1]
            elif len(manager_ids) < 2:
                manager_ids = (
                    manager_ids + [item for item in allowed_ids if item not in manager_ids]
                )[:2]
        elif action == "finish":
            manager_ids = []
        decision = {
            "action": action,
            "reason": str(raw.get("reason") or "根据当前证据选择下一步"),
            "manager_ids": manager_ids,
            "query": str(raw.get("query") or state["question"])[:2000],
            "discussion_mode": mode,
            "step": step,
        }
        await emit(state["run_id"], "agent.plan.created", decision)
        return {"step": step, "decision": decision}

    def route_action(state: SupervisorState) -> str:
        return {
            "search_corpus": "search_corpus",
            "run_discussion": "run_discussion",
            "finish": "finalize",
        }[state["decision"]["action"]]

    async def search_corpus(state: SupervisorState) -> dict[str, Any]:
        decision = state["decision"]
        payload = {
            "tool": "search_corpus",
            "manager_ids": decision["manager_ids"],
            "query": decision["query"],
            "step": state["step"],
        }
        await emit(state["run_id"], "agent.tool.started", payload)

        async def search_one(manager_id: str) -> dict[str, Any]:
            chunks = await asyncio.to_thread(index.search, manager_id, decision["query"], 6)
            return {
                "manager_id": manager_id,
                "manager_name": registry.get_raw(manager_id)["name"],
                "chunks": [
                    {
                        "id": item["id"],
                        "title": item["title"],
                        "source_file": item["file_path"],
                        "excerpt": item["content"][:1000],
                    }
                    for item in chunks
                ],
            }

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*(search_one(item) for item in decision["manager_ids"])),
                timeout=TOOL_TIMEOUT_SECONDS,
            )
            observation = {"tool": "search_corpus", "step": state["step"], "results": results}
            await emit(
                state["run_id"], "agent.tool.completed",
                {**payload, "result_count": sum(len(item["chunks"]) for item in results)},
            )
            return {"observations": [observation]}
        except Exception as exc:
            error = {"tool": "search_corpus", "error": str(exc)}
            await emit(state["run_id"], "agent.tool.completed", {**payload, **error, "failed": True})
            return {"observations": [{**error, "step": state["step"]}], "errors": [error]}

    async def run_discussion(state: SupervisorState) -> dict[str, Any]:
        decision = state["decision"]
        payload = {
            "tool": "run_discussion",
            "mode": decision["discussion_mode"],
            "manager_ids": decision["manager_ids"],
            "step": state["step"],
        }
        await emit(state["run_id"], "agent.tool.started", payload)
        try:
            result = await asyncio.wait_for(
                discussion_graph.ainvoke(
                    {
                        "run_id": state["run_id"],
                        "thread_id": state["thread_id"],
                        "question": decision["query"],
                        "mode": decision["discussion_mode"],
                        "manager_ids": decision["manager_ids"],
                        "history_context": state.get("history_context", ""),
                        "output_language": state.get("output_language", "zh-CN"),
                        "manager_results": [],
                        "errors": [],
                    },
                    config={
                        "configurable": {
                            "thread_id": f"{state['run_id']}:agent:{state['step']}"
                        }
                    },
                ),
                timeout=TOOL_TIMEOUT_SECONDS,
            )
            manager_results = result.get("manager_results", [])
            observation = {
                "tool": "run_discussion",
                "step": state["step"],
                "mode": decision["discussion_mode"],
                "manager_ids": decision["manager_ids"],
                "report": result.get("final_report", ""),
                "manager_results": manager_results,
            }
            await emit(
                state["run_id"], "agent.tool.completed",
                {**payload, "view_count": len(manager_results)},
            )
            return {
                "observations": [observation],
                "manager_results": manager_results,
                "errors": result.get("errors", []),
            }
        except Exception as exc:
            error = {"tool": "run_discussion", "error": str(exc)}
            await emit(state["run_id"], "agent.tool.completed", {**payload, **error, "failed": True})
            return {"observations": [{**error, "step": state["step"]}], "errors": [error]}

    async def critique(state: SupervisorState) -> dict[str, Any]:
        system = """你是研究质检员。判断已有观察是否足以回答用户问题。
输出严格 JSON：{"sufficient": true/false, "reason": "...", "gaps": ["..."], "next_action_hint": "..."}。
若只有工具错误或缺少可核验的观点，sufficient 必须为 false。"""
        raw = await gateway.generate_json(
            system,
            f"问题：{state['question']}\n观察：{_compact(state.get('observations', []))}",
        )
        sufficient_value = raw.get("sufficient")
        sufficient = sufficient_value is True or str(sufficient_value).lower() == "true"
        critique_result = {
            "sufficient": sufficient,
            "reason": str(raw.get("reason") or ""),
            "gaps": [str(item) for item in raw.get("gaps", []) if str(item).strip()],
            "next_action_hint": str(raw.get("next_action_hint") or ""),
            "step": state["step"],
        }
        await emit(state["run_id"], "agent.critique.completed", critique_result)
        return {"critique": critique_result}

    def after_critique(state: SupervisorState) -> str:
        if state.get("critique", {}).get("sufficient") or state.get("step", 0) >= MAX_AGENT_STEPS:
            return "finalize"
        return "plan"

    async def finalize(state: SupervisorState) -> dict[str, Any]:
        if not state.get("observations"):
            raise RuntimeError("Supervisor Agent 未获得可用的工具观察")
        system = """你是 Fund Insight 研究主编。仅基于 Supervisor Agent 收集的观察生成 Markdown 报告。
必须包含：核心结论、专家观点、证据与方法边界、分歧或不确定性。
不得补充观察之外的事实；明确区分资料证据和方法论模拟。"""
        prompt = f"用户问题：{state['question']}\n观察：{_compact(state.get('observations', []), 30000)}"

        async def on_delta(delta: str) -> None:
            await emit(state["run_id"], "moderator.delta", {"delta": delta})

        report = await gateway.generate_text_stream(system, prompt, on_delta)
        return {"final_report": report}

    graph = StateGraph(SupervisorState)
    graph.add_node("plan", plan)
    graph.add_node("search_corpus", search_corpus)
    graph.add_node("run_discussion", run_discussion)
    graph.add_node("critique", critique)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "plan")
    graph.add_conditional_edges(
        "plan", route_action, ["search_corpus", "run_discussion", "finalize"]
    )
    graph.add_edge("search_corpus", "critique")
    graph.add_edge("run_discussion", "critique")
    graph.add_conditional_edges("critique", after_critique, ["plan", "finalize"])
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=checkpointer)
