#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""search_corpus —— 兼容旧命令：委托给 top_fund_managers_mcp 包。

用法等价旧版：
  python scripts/search_corpus.py "白酒" --manager 谢治宇
"""
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from top_fund_managers_mcp.cli import run_search

if __name__ == "__main__":
    run_search(sys.argv[1:])
