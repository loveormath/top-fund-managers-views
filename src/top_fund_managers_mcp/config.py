# -*- coding: utf-8 -*-
"""路径与数据目录解析。

单一事实来源：references/（经理语料 + 基金快照 + 全市场基金列表）。
解析顺序：
  1. 环境变量 TFM_DATA_DIR（显式覆盖，便于把数据放到别处）
  2. 从本文件向上回溯，找到含 references/ 的目录
  3. 回退到仓库根 references/（src 布局下为 package 的祖父目录）
"""

import os
from pathlib import Path

# src/top_fund_managers_mcp/config.py -> parent=包目录, parent.parent=src, parent.parent.parent=仓库根
PKG_DIR = Path(__file__).resolve().parent
SRC_DIR = PKG_DIR.parent
REPO_ROOT = SRC_DIR.parent


def _find_references(start: Path) -> Path | None:
    for p in [start, *start.parents]:
        cand = p / "references"
        if cand.is_dir():
            return cand
    return None


def _resolve_data_dir() -> Path:
    env = os.environ.get("TFM_DATA_DIR")
    if env:
        return Path(env)
    found = _find_references(REPO_ROOT) or _find_references(Path.cwd())
    if found:
        return found
    return REPO_ROOT / "references"


DATA_DIR = _resolve_data_dir()
MANAGERS_DIR = DATA_DIR / "managers"
ALL_FUNDS_DIR = DATA_DIR / "all_funds"
FUND_LIST_FILE = ALL_FUNDS_DIR / "fund_list.json"

# 兼容旧脚本里对 SKILL_DIR 的引用（部分遗留脚本会 import 它）
SKILL_DIR = REPO_ROOT
