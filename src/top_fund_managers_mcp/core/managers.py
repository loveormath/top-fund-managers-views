# -*- coding: utf-8 -*-
"""经理动态发现器（零代码扩展基础）。

运行时扫描 references/managers/，并容忍目录名变体；新增一位经理
只需往 references/managers/ 放好目录，所有工具即自动识别。
"""

from ..config import MANAGERS_DIR


def list_managers():
    """返回 references/managers/ 下全部经理名（动态发现，按名排序）。"""
    if not MANAGERS_DIR.exists():
        return []
    return sorted(
        d.name for d in MANAGERS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


def corpus_dir(manager):
    """返回该经理的语料目录。优先级：corpus → media → copus → None。"""
    base = MANAGERS_DIR / manager
    for name in ("corpus", "media", "copus"):
        d = base / name
        if d.is_dir():
            return d
    return None


def fund_data_dir(manager):
    """返回该经理的基金快照目录。优先级：funds_data → fund_data → None。"""
    base = MANAGERS_DIR / manager
    for name in ("funds_data", "fund_data"):
        d = base / name
        if d.is_dir():
            return d
    return None


def representative_fund(manager):
    """返回代表基金子目录名（快照目录下首个含「净值业绩规模」的子目录）。

    找不到时回退到第一个子目录；都没有返回 None。
    """
    fd = fund_data_dir(manager)
    if not fd:
        return None
    for d in sorted(fd.iterdir()):
        if d.is_dir() and any(d.glob("净值业绩规模*")):
            return d.name
    for d in sorted(fd.iterdir()):
        if d.is_dir():
            return d.name
    return None
