from __future__ import annotations

import json
import operator
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .deepseek import DeepSeekGateway
from .registry import ManagerRegistry
from .retrieval import CorpusIndex
from .schemas import Evidence, ManagerView


Emit = Callable[[str, str, dict[str, Any]], Awaitable[None]]


class DiscussionState(TypedDict, total=False):
    run_id: str
    thread_id: str
    question: str
    mode: Literal["single", "summary", "meeting"]
    manager_ids: list[str]
    manager_id: str
    manager_name: str
    stage: Literal["analysis", "opening", "response"]
    history_context: str
    output_language: str
    manager_results: Annotated[list[dict[str, Any]], operator.add]
    final_report: str
    errors: Annotated[list[dict[str, str]], operator.add]


MANAGER_SYSTEM = """你是 Fund Insight 的研究模拟节点。你必须只基于提供的指定基金经理资料回答，不能补充外部事实。
你不是经理本人，凡非资料原话的判断必须以“基于方法论模拟：”开头。直接引语必须逐字来自证据片段。
输出严格 JSON 对象，字段为：position（字符串）、direct_evidence（数组，每项含 quote、chunk_id）、
method_inference（字符串数组）、holdings_evidence（数组，每项含 quote、chunk_id）、
missing_information（字符串数组）、confidence（high/medium/low）。不要输出 Markdown 代码围栏。"""


def _evidence_payload(chunks: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        f"[{item['id']}] 文件={item['file_path']}；标题={item['title']}；类型={item['document_type']}\n{item['content']}"
        for item in chunks
    )


def _view_dict(
    payload: dict[str, Any],
    manager_id: str,
    manager_name: str,
    stage: str,
    chunks: list[dict[str, Any]],
    index: CorpusIndex,
) -> dict[str, Any]:
    by_id = {item["id"]: item for item in chunks}

    def evidence_list(values: Any) -> list[Evidence]:
        valid: list[Evidence] = []
        for raw in values if isinstance(values, list) else []:
            if not isinstance(raw, dict):
                continue
            chunk_id = str(raw.get("chunk_id", ""))
            quote = str(raw.get("quote", "")).strip()
            source = by_id.get(chunk_id)
            if not source or not index.quote_is_exact(chunk_id, quote):
                continue
            valid.append(
                Evidence(
                    quote=quote,
                    chunk_id=chunk_id,
                    source_file=source["file_path"],
                    title=source["title"],
                    date=source.get("date"),
                    excerpt=source["excerpt"],
                )
            )
        return valid

    inferences = []
    for value in payload.get("method_inference", []):
        text = str(value).strip()
        if text:
            inferences.append(text if text.startswith("基于方法论模拟：") else f"基于方法论模拟：{text}")
    view = ManagerView(
        manager_id=manager_id,
        manager_name=manager_name,
        position=str(payload.get("position") or "资料不足，暂时无法形成可靠立场。"),
        direct_evidence=evidence_list(payload.get("direct_evidence")),
        method_inference=inferences,
        holdings_evidence=evidence_list(payload.get("holdings_evidence")),
        missing_information=[str(item) for item in payload.get("missing_information", []) if str(item).strip()],
        confidence=payload.get("confidence") if payload.get("confidence") in {"high", "medium", "low"} else "low",
        stage=stage,
    )
    return view.model_dump()


def build_workflow(
    registry: ManagerRegistry,
    index: CorpusIndex,
    gateway: DeepSeekGateway,
    emit: Emit,
    checkpointer: Any | None = None,
):
    async def validate(state: DiscussionState) -> dict[str, Any]:
        manager_ids = list(dict.fromkeys(state["manager_ids"]))
        invalid = [item for item in manager_ids if item not in registry.ids()]
        if invalid:
            raise ValueError(f"未知基金经理：{', '.join(invalid)}")
        if state["mode"] == "single" and len(manager_ids) != 1:
            raise ValueError("单人总结模式必须选择 1 位基金经理")
        if state["mode"] in {"summary", "meeting"} and not 2 <= len(manager_ids) <= 5:
            raise ValueError("多人总结和会议讨论模式必须选择 2–5 位基金经理")
        return {"manager_ids": manager_ids, "manager_results": [], "errors": []}

    def dispatch_managers(state: DiscussionState) -> list[Send]:
        stage = "opening" if state["mode"] == "meeting" else "analysis"
        return [
            Send(
                "manager_analyze",
                {
                    "run_id": state["run_id"],
                    "thread_id": state["thread_id"],
                    "question": state["question"],
                    "mode": state["mode"],
                    "manager_ids": state["manager_ids"],
                    "manager_id": manager_id,
                    "manager_name": registry.get_raw(manager_id)["name"],
                    "stage": stage,
                    "history_context": state.get("history_context", ""),
                    "output_language": state.get("output_language", "zh-CN"),
                },
            )
            for manager_id in state["manager_ids"]
        ]

    async def manager_analyze(state: DiscussionState) -> dict[str, Any]:
        manager_id = state["manager_id"]
        manager_name = state["manager_name"]
        stage = state["stage"]
        await emit(state["run_id"], "manager.started", {"manager_id": manager_id, "stage": stage})
        chunks = index.search(manager_id, state["question"], limit=8)
        stage_instruction = {
            "analysis": "独立分析问题并给出结构化观点。",
            "opening": "这是会议第一轮。独立发表开场观点，不要假设其他经理的意见。",
            "response": "这是会议第二轮。回应其他人的第一轮观点，指出认同、分歧和补充；引用仍只能来自你自己的资料。",
        }[stage]
        prompt = f"""经理：{manager_name}
讨论问题：{state['question']}
任务：{stage_instruction}
此前同一线程摘要（可为空）：{state.get('history_context', '')}

证据片段：
{_evidence_payload(chunks)}"""
        try:
            raw = await gateway.generate_json(MANAGER_SYSTEM, prompt)
            result = _view_dict(raw, manager_id, manager_name, stage, chunks, index)
            text = result["position"]
            for start in range(0, len(text), 28):
                await emit(
                    state["run_id"], "manager.delta",
                    {"manager_id": manager_id, "stage": stage, "delta": text[start : start + 28]},
                )
            await emit(
                state["run_id"], "manager.completed",
                {"manager_id": manager_id, "stage": stage, "view": result},
            )
            return {"manager_results": [result]}
        except Exception as exc:
            error = {"manager_id": manager_id, "stage": stage, "error": str(exc)}
            await emit(state["run_id"], "manager.completed", {**error, "failed": True})
            return {"errors": [error]}

    def after_analysis(state: DiscussionState) -> str | list[Send]:
        if state["mode"] == "single":
            return "render_single"
        if state["mode"] == "summary":
            return "synthesize"
        openings = [item for item in state.get("manager_results", []) if item.get("stage") == "opening"]
        transcript = json.dumps(openings, ensure_ascii=False)
        return [
            Send(
                "manager_respond",
                {
                    "run_id": state["run_id"], "thread_id": state["thread_id"],
                    "question": state["question"], "mode": state["mode"],
                    "manager_ids": state["manager_ids"], "manager_id": manager_id,
                    "manager_name": registry.get_raw(manager_id)["name"], "stage": "response",
                    "history_context": f"上一周期：{state.get('history_context', '')}\n本轮开场：{transcript}",
                    "output_language": state.get("output_language", "zh-CN"),
                },
            )
            for manager_id in state["manager_ids"]
        ]

    async def round_two_marker(state: DiscussionState) -> dict[str, Any]:
        if state["mode"] == "meeting":
            await emit(state["run_id"], "round.started", {"round": 2, "name": "交叉回应"})
        return {}

    async def manager_respond(state: DiscussionState) -> dict[str, Any]:
        return await manager_analyze(state)

    async def render_single(state: DiscussionState) -> dict[str, Any]:
        results = state.get("manager_results", [])
        if not results:
            raise RuntimeError("所选基金经理分析失败")
        view = results[0]
        report = (
            f"## {view['manager_name']}的观点\n\n{view['position']}\n\n"
            + "\n".join(f"- {item}" for item in view.get("method_inference", []))
        ).strip()
        return {"final_report": report}

    async def synthesize(state: DiscussionState) -> dict[str, Any]:
        results = state.get("manager_results", [])
        if not results:
            raise RuntimeError("所有基金经理分析均失败")
        system = """你是中立的基金研究主持人。只总结提供的结构化观点，生成中文 Markdown 报告。
必须包含：核心结论、逐位经理观点、共识、分歧、证据边界。不要添加外部事实；失败经理应标记缺席。"""
        prompt = f"问题：{state['question']}\n观点：{json.dumps(results, ensure_ascii=False)}\n失败：{json.dumps(state.get('errors', []), ensure_ascii=False)}"

        async def on_delta(delta: str) -> None:
            await emit(state["run_id"], "moderator.delta", {"delta": delta})

        report = await gateway.generate_text_stream(system, prompt, on_delta)
        return {"final_report": report}

    async def moderate(state: DiscussionState) -> dict[str, Any]:
        results = state.get("manager_results", [])
        if not results:
            raise RuntimeError("会议中所有基金经理均失败")
        system = """你是投资圆桌会议主持人。根据两轮结构化发言生成中文 Markdown 主持报告。
必须包含：议题结论、第一轮立场、第二轮交锋、共识、关键分歧、待验证问题、缺席说明。
不能增加发言之外的事实，区分资料原话与方法论模拟。"""
        prompt = f"议题：{state['question']}\n两轮发言：{json.dumps(results, ensure_ascii=False)}\n失败：{json.dumps(state.get('errors', []), ensure_ascii=False)}"

        async def on_delta(delta: str) -> None:
            await emit(state["run_id"], "moderator.delta", {"delta": delta})

        report = await gateway.generate_text_stream(system, prompt, on_delta)
        return {"final_report": report}

    graph = StateGraph(DiscussionState)
    graph.add_node("validate", validate)
    graph.add_node("manager_analyze", manager_analyze)
    graph.add_node("render_single", render_single)
    graph.add_node("synthesize", synthesize)
    graph.add_node("round_two_marker", round_two_marker)
    graph.add_node("manager_respond", manager_respond)
    graph.add_node("moderate", moderate)
    graph.add_edge(START, "validate")
    graph.add_conditional_edges("validate", dispatch_managers, ["manager_analyze"])
    graph.add_edge("manager_analyze", "round_two_marker")
    graph.add_conditional_edges(
        "round_two_marker", after_analysis,
        ["render_single", "synthesize", "manager_respond"],
    )
    graph.add_edge("manager_respond", "moderate")
    graph.add_edge("render_single", END)
    graph.add_edge("synthesize", END)
    graph.add_edge("moderate", END)
    return graph.compile(checkpointer=checkpointer)
