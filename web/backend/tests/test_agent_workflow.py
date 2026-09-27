from __future__ import annotations

import pytest

from backend.app.agent_workflow import build_supervisor_workflow
from backend.app.registry import ManagerRegistry
from backend.app.workflow import build_workflow


class FakeIndex:
    def search(self, manager_id, query, limit=8):
        return [{
            "id": f"{manager_id}-chunk",
            "file_path": f"references/{manager_id}.md",
            "title": "测试资料",
            "document_type": "corpus",
            "content": "长期研究与安全边际同样重要。",
            "excerpt": "长期研究与安全边际同样重要。",
            "date": "2026",
        }]

    def quote_is_exact(self, chunk_id, quote):
        return quote == "安全边际"


class AgentGateway:
    async def generate_json(self, system_prompt, user_prompt):
        if "Supervisor Agent" in system_prompt:
            return {
                "action": "run_discussion",
                "reason": "需要两位经理独立分析",
                "manager_ids": ["liu-xu", "zhang-kun"],
                "query": "如何看制造业？",
                "discussion_mode": "summary",
            }
        if "研究质检员" in system_prompt:
            return {
                "sufficient": True,
                "reason": "已有多视角观点",
                "gaps": [],
                "next_action_hint": "",
            }
        return {
            "position": "重视长期研究。",
            "direct_evidence": [],
            "method_inference": ["关注证据与估值"],
            "holdings_evidence": [],
            "missing_information": [],
            "confidence": "medium",
        }

    async def generate_text_stream(self, system_prompt, user_prompt, on_delta=None):
        report = "Supervisor 综合报告"
        if on_delta:
            await on_delta(report)
        return report


@pytest.mark.asyncio
async def test_supervisor_plans_calls_tool_critiques_and_finishes(project_root):
    registry = ManagerRegistry(project_root / "config" / "managers.yaml", project_root)
    gateway = AgentGateway()
    events = []

    async def emit(run_id, event_type, data):
        events.append((event_type, data))

    discussion = build_workflow(registry, FakeIndex(), gateway, emit)
    agent = build_supervisor_workflow(registry, FakeIndex(), gateway, emit, discussion)
    result = await agent.ainvoke({
        "run_id": "run-agent",
        "thread_id": "thread-agent",
        "question": "如何看制造业？",
        "history_context": "",
        "output_language": "zh-CN",
        "step": 0,
        "observations": [],
        "manager_results": [],
        "errors": [],
    })

    assert result["final_report"] == "Supervisor 综合报告"
    assert len(result["manager_results"]) == 2
    event_names = [item[0] for item in events]
    assert "agent.plan.created" in event_names
    assert "agent.tool.started" in event_names
    assert "agent.tool.completed" in event_names
    assert "agent.critique.completed" in event_names


class IteratingGateway(AgentGateway):
    def __init__(self):
        self.plan_calls = 0
        self.critique_calls = 0

    async def generate_json(self, system_prompt, user_prompt):
        if "Supervisor Agent" in system_prompt:
            self.plan_calls += 1
            if self.plan_calls == 1:
                return {
                    "action": "search_corpus",
                    "reason": "先核对原始资料",
                    "manager_ids": ["liu-xu"],
                    "query": "制造业安全边际",
                    "discussion_mode": "single",
                }
            return {
                "action": "run_discussion",
                "reason": "证据后需要形成结构化观点",
                "manager_ids": ["liu-xu"],
                "query": "制造业安全边际",
                "discussion_mode": "single",
            }
        if "研究质检员" in system_prompt:
            self.critique_calls += 1
            return {
                "sufficient": self.critique_calls > 1,
                "reason": "已有证据但还需要专家观点" if self.critique_calls == 1 else "证据与观点已齐备",
                "gaps": ["缺少结构化观点"] if self.critique_calls == 1 else [],
                "next_action_hint": "run_discussion",
            }
        return await super().generate_json(system_prompt, user_prompt)


@pytest.mark.asyncio
async def test_supervisor_replans_when_critic_finds_a_gap(project_root):
    registry = ManagerRegistry(project_root / "config" / "managers.yaml", project_root)
    gateway = IteratingGateway()
    events = []

    async def emit(run_id, event_type, data):
        events.append((event_type, data))

    discussion = build_workflow(registry, FakeIndex(), gateway, emit)
    agent = build_supervisor_workflow(registry, FakeIndex(), gateway, emit, discussion)
    result = await agent.ainvoke({
        "run_id": "run-loop",
        "thread_id": "thread-loop",
        "question": "如何看制造业？",
        "history_context": "",
        "output_language": "zh-CN",
        "step": 0,
        "observations": [],
        "manager_results": [],
        "errors": [],
    })

    assert result["step"] == 2
    assert [item["tool"] for item in result["observations"]] == [
        "search_corpus",
        "run_discussion",
    ]
    assert gateway.plan_calls == 2
    assert gateway.critique_calls == 2
