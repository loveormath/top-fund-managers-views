from __future__ import annotations

import pytest

from backend.app.registry import ManagerRegistry
from backend.app.workflow import build_workflow


class FakeIndex:
    def search(self, manager_id, query, limit=8):
        return [{
            "id": f"{manager_id}-chunk", "file_path": f"references/{manager_id}.md",
            "title": "测试资料", "document_type": "corpus", "content": "长期研究与安全边际同样重要。",
            "excerpt": "长期研究与安全边际同样重要。", "date": "2026",
        }]

    def quote_is_exact(self, chunk_id, quote):
        return quote == "安全边际"


class FakeGateway:
    def __init__(self):
        self.json_calls = 0
        self.report_calls = 0

    async def generate_json(self, system_prompt, user_prompt):
        self.json_calls += 1
        return {
            "position": "重视长期研究。", "direct_evidence": [],
            "method_inference": ["关注证据与估值"], "holdings_evidence": [],
            "missing_information": [], "confidence": "medium",
        }

    async def generate_text_stream(self, system_prompt, user_prompt, on_delta=None):
        self.report_calls += 1
        if on_delta:
            await on_delta("综合")
            await on_delta("报告")
        return "综合报告"


async def run_mode(project_root, mode, manager_ids):
    registry = ManagerRegistry(project_root / "config" / "managers.yaml", project_root)
    gateway = FakeGateway()
    events = []

    async def emit(run_id, event_type, data):
        events.append((event_type, data))

    graph = build_workflow(registry, FakeIndex(), gateway, emit)
    result = await graph.ainvoke({
        "run_id": "run-1", "thread_id": "thread-1", "question": "怎么看制造业？",
        "mode": mode, "manager_ids": manager_ids, "history_context": "", "output_language": "zh-CN",
        "manager_results": [], "errors": [],
    })
    return gateway, events, result


@pytest.mark.asyncio
async def test_single_uses_one_model_call(project_root):
    gateway, events, result = await run_mode(project_root, "single", ["liu-xu"])
    assert gateway.json_calls == 1 and gateway.report_calls == 0
    assert result["final_report"]
    assert len([event for event in events if event[0] == "manager.completed"]) == 1


@pytest.mark.asyncio
async def test_summary_parallel_then_one_synthesis(project_root):
    gateway, _, result = await run_mode(project_root, "summary", ["liu-xu", "zhang-kun"])
    assert gateway.json_calls == 2 and gateway.report_calls == 1
    assert result["final_report"] == "综合报告"


@pytest.mark.asyncio
async def test_meeting_is_two_rounds_plus_moderator(project_root):
    gateway, events, result = await run_mode(project_root, "meeting", ["liu-xu", "zhang-kun", "zhao-yi"])
    assert gateway.json_calls == 6 and gateway.report_calls == 1
    assert len(result["manager_results"]) == 6
    assert any(event[0] == "round.started" and event[1]["round"] == 2 for event in events)
