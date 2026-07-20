#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""score_fund —— 兼容旧命令：委托给 top_fund_managers_mcp 包。

用法等价旧版：
  python scripts/score_fund.py 163406 --manager 谢治宇
"""
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from top_fund_managers_mcp.cli import run_score

if __name__ == "__main__":
    run_score(sys.argv[1:])
