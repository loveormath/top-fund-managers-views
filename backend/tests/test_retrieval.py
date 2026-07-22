from __future__ import annotations

from dataclasses import replace

from backend.app.config import AppConfig
from backend.app.registry import ManagerRegistry
from backend.app.retrieval import CorpusIndex


class UnavailableEncoder:
    def encode(self, *args, **kwargs):
        raise RuntimeError("offline model")


def test_incremental_index_and_keyword_retrieval(project_root, tmp_path):
    base = AppConfig.from_env()
    config = replace(
        base,
        root_dir=project_root,
        data_dir=tmp_path,
        registry_path=project_root / "config" / "managers.yaml",
        references_dir=project_root / "references",
        index_path=tmp_path / "index.sqlite3",
    )
    registry = ManagerRegistry(config.registry_path, project_root)
    index = CorpusIndex(config, registry)
    index._encoder = UnavailableEncoder()
    first = index.rebuild()
    second = index.rebuild()
    assert first["state"] == "degraded"
    assert first["files"] > 0 and first["chunks"] > 0
    assert second["files"] == first["files"]
    results = index.search("liu-xu", "安全边际", 8)
    assert results and all(item["manager_id"] == "liu-xu" for item in results)
    sample = results[0]
    assert index.quote_is_exact(sample["id"], sample["content"][:20])
    assert not index.quote_is_exact(sample["id"], "这句不存在于原文")
    index.close()
