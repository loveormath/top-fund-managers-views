from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    root_dir: Path
    data_dir: Path
    registry_path: Path
    references_dir: Path
    database_path: Path
    index_path: Path
    checkpoint_path: Path
    secret_key_path: Path
    embedding_model: str
    deepseek_base_url: str
    app_encryption_key: str | None

    @classmethod
    def from_env(cls) -> "AppConfig":
        default_root = Path(__file__).resolve().parents[2]
        root = Path(os.getenv("FUND_INSIGHT_ROOT", default_root)).resolve()
        data_dir = Path(os.getenv("FUND_INSIGHT_DATA_DIR", root / "data")).resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            root_dir=root,
            data_dir=data_dir,
            registry_path=Path(
                os.getenv("FUND_INSIGHT_MANAGER_REGISTRY", root / "config" / "managers.yaml")
            ).resolve(),
            references_dir=(root / "references").resolve(),
            database_path=(data_dir / "fund_insight.sqlite3").resolve(),
            index_path=(data_dir / "corpus_index.sqlite3").resolve(),
            checkpoint_path=(data_dir / "checkpoints.sqlite3").resolve(),
            secret_key_path=(data_dir / "secret.key").resolve(),
            embedding_model=os.getenv("FUND_INSIGHT_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"),
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            app_encryption_key=os.getenv("APP_ENCRYPTION_KEY"),
        )
