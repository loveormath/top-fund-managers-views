"""Shared access to the single Fund Insight manager registry."""

from pathlib import Path

import yaml


ROOT_DIR = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT_DIR / "config" / "managers.yaml"


def registry_items():
    payload = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    return payload.get("managers", {})


def managers_by_name():
    return {item["name"]: {"id": manager_id, **item} for manager_id, item in registry_items().items()}


def manager_names():
    return list(managers_by_name())
