#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""compare_managers —— 兼容旧命令：委托给 top_fund_managers_mcp 包。

用法等价旧版：
  python scripts/compare_managers.py topic 白酒
  python scripts/compare_managers.py method
  python scripts/compare_managers.py fund
"""
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from top_fund_managers_mcp.cli import run_compare

if __name__ == "__main__":
    run_compare(sys.argv[1:])
