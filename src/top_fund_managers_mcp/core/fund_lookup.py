# -*- coding: utf-8 -*-
"""基金代码查询工具 — 在全市场约2.7万只基金中按名称/拼音/代码/类型查找。"""

import json

from ..config import FUND_LIST_FILE


def load_fund_list():
    """加载基金列表。"""
    if not FUND_LIST_FILE.exists():
        return None
    try:
        with open(FUND_LIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"加载基金列表失败：{e}")
        return None


def search_funds(funds, keyword, fund_type=None, limit=20):
    """搜索基金。"""
    results = []
    keyword_lower = keyword.lower()

    for fund in funds:
        code = fund.get("code", "")
        name = fund.get("name", "")
        pinyin = fund.get("pinyin", "")
        ftype = fund.get("type", "")

        matched = (
            keyword_lower in code.lower()
            or keyword_lower in name.lower()
            or keyword_lower in pinyin.lower()
        )
        if not matched:
            continue

        if fund_type and fund_type.lower() not in ftype.lower():
            continue

        results.append(fund)
        if len(results) >= limit:
            break

    return results


def fund_lookup(keyword, fund_type=None, limit=20):
    """按关键词查基金，返回格式化结果字符串。"""
    funds = load_fund_list()
    if funds is None:
        return (f"错误：基金列表文件不存在：{FUND_LIST_FILE}\n"
                "请先运行 `python -m top_fund_managers_mcp index-funds` 生成。")

    results = search_funds(funds, keyword, fund_type, limit)
    if not results:
        return f"未找到匹配 '{keyword}' 的基金。"

    out = [f"找到 {len(results)} 只匹配基金：\n",
            f"{'代码':<10} {'名称':<30} {'类型':<15}",
            "-" * 60]
    for fund in results:
        out.append(f"{fund.get('code', ''):<10} {fund.get('name', ''):<30} {fund.get('type', ''):<15}")
    return "\n".join(out)
