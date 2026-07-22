from __future__ import annotations

from cryptography.fernet import Fernet

from backend.app.database import Database
from backend.app.registry import ManagerRegistry
from backend.app.runs import EventHub
from backend.app.schemas import DiscussionMode
from backend.app.security import SecretBox


def test_registry_has_exact_five_standardized_managers(project_root):
    registry = ManagerRegistry(project_root / "config" / "managers.yaml", project_root)
    assert registry.ids() == ["liu-xu", "zhang-kun", "zhang-lu", "xie-zhi-yu", "zhao-yi"]
    assert all(registry.resolve(manager_id, "profile_file").exists() for manager_id in registry.ids())
    assert "gao-nan" not in registry.ids()


def test_database_persists_thread_run_events(tmp_path):
    db = Database(tmp_path / "app.sqlite3")
    thread = db.create_thread(DiscussionMode.SUMMARY, ["liu-xu", "zhang-kun"])
    run = db.create_run(thread["id"], "如何看制造业的长期机会？")
    db.add_message(thread["id"], run["id"], "user", run["question"])
    event_id = db.add_event(run["id"], "run.started", {"ok": True})
    assert db.get_thread(thread["id"])["manager_ids"] == ["liu-xu", "zhang-kun"]
    assert db.list_events(run["id"], event_id - 1)[0]["data"] == {"ok": True}
    db.close()


def test_secret_box_encrypts_and_masks(tmp_path):
    box = SecretBox(tmp_path / "secret.key", Fernet.generate_key().decode())
    token = box.encrypt("sk-test-secret-value")
    assert "sk-test-secret-value" not in token
    assert box.decrypt(token) == "sk-test-secret-value"
    assert box.mask("sk-test-secret-value").startswith("sk-")


async def test_sse_event_log_resumes_after_id(tmp_path):
    db = Database(tmp_path / "events.sqlite3")
    thread = db.create_thread(DiscussionMode.SINGLE, ["liu-xu"])
    run = db.create_run(thread["id"], "测试断线续传")
    hub = EventHub(db)
    await hub.emit(run["id"], "run.started", {"step": 1})
    first_id = db.list_events(run["id"])[0]["id"]
    await hub.emit(run["id"], "manager.completed", {"step": 2})
    await hub.emit(run["id"], "run.completed", {"step": 3})
    resumed = [event async for event in hub.stream(run["id"], after_id=first_id)]
    assert "event: run.started" not in "".join(resumed)
    assert "event: manager.completed" in resumed[0]
    assert "event: run.completed" in resumed[1]
    db.close()
