from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any

from .database import Database
from .schemas import RunStatus


TERMINAL_EVENTS = {"run.completed", "run.failed"}


class EventHub:
    def __init__(self, db: Database):
        self.db = db
        self.listeners: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)

    async def emit(self, run_id: str, event_type: str, data: dict[str, Any]) -> None:
        event_id = self.db.add_event(run_id, event_type, data)
        event = {"id": event_id, "event_type": event_type, "data": data}
        for queue in list(self.listeners.get(run_id, set())):
            await queue.put(event)

    async def stream(self, run_id: str, after_id: int = 0) -> AsyncIterator[str]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.listeners[run_id].add(queue)
        cursor = after_id
        try:
            for event in self.db.list_events(run_id, after_id):
                cursor = max(cursor, event["id"])
                yield self._format(event)
                if event["event_type"] in TERMINAL_EVENTS:
                    return
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    run = self.db.get_run(run_id)
                    if run["status"] in {
                        RunStatus.COMPLETED.value,
                        RunStatus.FAILED.value,
                        RunStatus.CANCELLED.value,
                    }:
                        return
                    continue
                if event["id"] <= cursor:
                    continue
                cursor = event["id"]
                yield self._format(event)
                if event["event_type"] in TERMINAL_EVENTS:
                    return
        finally:
            self.listeners[run_id].discard(queue)
            if not self.listeners[run_id]:
                self.listeners.pop(run_id, None)

    @staticmethod
    def _format(event: dict[str, Any]) -> str:
        data = json.dumps(event["data"], ensure_ascii=False, separators=(",", ":"))
        return f"id: {event['id']}\nevent: {event['event_type']}\ndata: {data}\n\n"


class RunService:
    def __init__(self, db: Database, graph: Any, events: EventHub):
        self.db = db
        self.graph = graph
        self.events = events
        self.tasks: dict[str, asyncio.Task[None]] = {}

    def create(self, thread_id: str, question: str, output_language: str) -> dict[str, Any]:
        thread = self.db.get_thread(thread_id)
        run = self.db.create_run(thread_id, question)
        task = asyncio.create_task(self._execute(run, thread, output_language), name=f"run-{run['id']}")
        self.tasks[run["id"]] = task
        task.add_done_callback(lambda _task: self.tasks.pop(run["id"], None))
        return run

    async def _execute(
        self, run: dict[str, Any], thread: dict[str, Any], output_language: str
    ) -> None:
        run_id = run["id"]
        thread_id = thread["id"]
        try:
            self.db.update_run(run_id, RunStatus.RUNNING)
            self.db.add_message(thread_id, run_id, "user", run["question"])
            await self.events.emit(
                run_id,
                "run.started",
                {
                    "run_id": run_id,
                    "thread_id": thread_id,
                    "mode": thread["mode"],
                    "manager_ids": thread["manager_ids"],
                },
            )
            if thread["mode"] == "meeting":
                await self.events.emit(run_id, "round.started", {"round": 1, "name": "独立开场"})
            state = await self.graph.ainvoke(
                {
                    "run_id": run_id,
                    "thread_id": thread_id,
                    "question": run["question"],
                    "mode": thread["mode"],
                    "manager_ids": thread["manager_ids"],
                    "history_context": self.db.previous_context(thread_id),
                    "output_language": output_language,
                    "manager_results": [],
                    "errors": [],
                },
                config={"configurable": {"thread_id": run_id}},
            )
            for view in state.get("manager_results", []):
                citations = [
                    item
                    for key in ("direct_evidence", "holdings_evidence")
                    for item in view.get(key, [])
                ]
                self.db.add_message(
                    thread_id,
                    run_id,
                    "manager",
                    json.dumps(view, ensure_ascii=False),
                    manager_id=view.get("manager_id"),
                    round_no=2 if view.get("stage") == "response" else 1,
                    citations=citations,
                )
            report = state.get("final_report", "")
            self.db.add_message(thread_id, run_id, "assistant", report)
            self.db.update_run(run_id, RunStatus.COMPLETED, final_report=report)
            await self.events.emit(
                run_id,
                "run.completed",
                {"run_id": run_id, "final_report": report, "errors": state.get("errors", [])},
            )
        except asyncio.CancelledError:
            self.db.update_run(run_id, RunStatus.CANCELLED, error="用户已取消")
            await self.events.emit(run_id, "run.failed", {"run_id": run_id, "cancelled": True})
        except Exception as exc:
            self.db.update_run(run_id, RunStatus.FAILED, error=str(exc))
            await self.events.emit(run_id, "run.failed", {"run_id": run_id, "error": str(exc)})

    async def cancel(self, run_id: str) -> bool:
        task = self.tasks.get(run_id)
        if not task or task.done():
            return False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return True

    async def shutdown(self) -> None:
        tasks = [task for task in self.tasks.values() if not task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
