#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""managers_list —— 向后兼容：委托给 top_fund_managers_mcp.core.managers。

原 scripts/managers_list.py 的能力（list_managers / corpus_dir /
fund_data_dir / representative_fund）现已位于包内 core.managers，
本文件仅作薄再导出，供旧脚本 import 使用。
"""
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from top_fund_managers_mcp.core.managers import (
    list_managers,
    corpus_dir,
    fund_data_dir,
    representative_fund,
)

__all__ = ["list_managers", "corpus_dir", "fund_data_dir", "representative_fund"]
