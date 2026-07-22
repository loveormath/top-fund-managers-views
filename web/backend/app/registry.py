from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schemas import FundRef, ManagerPublic


class ManagerRegistry:
    def __init__(self, registry_path: Path, root_dir: Path):
        self.registry_path = registry_path
        self.root_dir = root_dir
        self._raw: dict[str, dict[str, Any]] = {}
        self.reload()

    def reload(self) -> None:
        payload = yaml.safe_load(self.registry_path.read_text(encoding="utf-8")) or {}
        managers = payload.get("managers", {})
        if len(managers) != 5:
            raise ValueError(f"经理注册表必须包含 5 位经理，当前为 {len(managers)} 位")
        self._raw = managers
        for manager_id, item in self._raw.items():
            for key in ("profile_file", "method_file", "scorecard_file", "corpus_dir", "fund_data_dir"):
                path = self.root_dir / item[key]
                if not path.exists():
                    raise FileNotFoundError(f"{manager_id} 的 {key} 不存在：{path}")

    def ids(self) -> list[str]:
        return list(self._raw)

    def get_raw(self, manager_id: str) -> dict[str, Any]:
        try:
            return self._raw[manager_id]
        except KeyError as exc:
            raise KeyError(f"未知基金经理：{manager_id}") from exc

    def resolve(self, manager_id: str, key: str) -> Path:
        return (self.root_dir / self.get_raw(manager_id)[key]).resolve()

    def public(self, manager_id: str, include_detail: bool = False) -> ManagerPublic:
        item = self.get_raw(manager_id)
        corpus_dir = self.resolve(manager_id, "corpus_dir")
        fund_dir = self.resolve(manager_id, "fund_data_dir")
        profile = self.resolve(manager_id, "profile_file").read_text(encoding="utf-8")
        method = self.resolve(manager_id, "method_file").read_text(encoding="utf-8")
        return ManagerPublic(
            id=manager_id,
            name=item["name"],
            institution=item["institution"],
            role=item["role"],
            color=item["color"],
            avatar=item["avatar"],
            tags=item.get("tags", []),
            representative_funds=[FundRef(**fund) for fund in item.get("representative_funds", [])],
            corpus_files=sum(1 for p in corpus_dir.rglob("*") if p.is_file()),
            fund_files=sum(1 for p in fund_dir.rglob("*") if p.is_file()),
            profile_excerpt=profile[:5000] if include_detail else self._excerpt(profile),
            method_excerpt=method[:10000] if include_detail else self._excerpt(method),
        )

    def list_public(self) -> list[ManagerPublic]:
        return [self.public(manager_id) for manager_id in self.ids()]

    @staticmethod
    def _excerpt(content: str, limit: int = 260) -> str:
        compact = " ".join(line.strip("# ") for line in content.splitlines() if line.strip())
        return compact[:limit]
