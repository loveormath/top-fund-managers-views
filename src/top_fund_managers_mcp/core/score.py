# -*- coding: utf-8 -*-
"""基金评分一键入口 — 自动找代码+备数据+算机械指标，配合 scorecard.md 打分。"""

import json
import re
from pathlib import Path

from ..config import FUND_LIST_FILE
from .managers import list_managers, fund_data_dir, representative_fund


def find_fund_code(keyword):
    """从全市场基金列表中查找代码。"""
    if not FUND_LIST_FILE.exists():
        return None
    try:
        with open(FUND_LIST_FILE, "r", encoding="utf-8") as f:
            funds = json.load(f)
    except Exception:
        return None

    keyword_lower = keyword.lower()
    for fund in funds:
        if (keyword_lower in fund.get("code", "").lower()
                or keyword_lower in fund.get("name", "").lower()
                or keyword_lower in fund.get("pinyin", "").lower()):
            return fund
    return None


def load_fund_data(fund_dir):
    """加载基金数据。"""
    holdings_file = fund_dir / "季度持仓.md"
    perf_file = fund_dir / "净值业绩规模.md"
    data = {}
    if holdings_file.exists():
        data["holdings"] = holdings_file.read_text(encoding="utf-8")
    if perf_file.exists():
        data["performance"] = perf_file.read_text(encoding="utf-8")
    return data


def analyze_concentration(holdings_text):
    """分析持仓集中度（前十大占比合计）。"""
    ratio_pattern = re.findall(r'\|\s*\d+\s*\|\s*\S+\s*\|\s*\S+\s*\|\s*([\d.]+)\s*\|', holdings_text)
    if ratio_pattern:
        return sum(float(r) for r in ratio_pattern[:10])
    return None


def score_fund(fund, manager):
    """框架评分一键入口，返回格式化结果字符串。"""
    if manager not in list_managers():
        return f"错误：未知基金经理 '{manager}'，可选：{', '.join(list_managers())}"

    mgr_fund_dir = fund_data_dir(manager)
    representative = representative_fund(manager) or "（未知，请在 fund_data 目录补充代表基金快照）"

    fund_input = fund
    if fund_input.isdigit() and len(fund_input) == 6:
        fund_code = fund_input
        fund_name = "待查"
    else:
        fund_info = find_fund_code(fund_input)
        if fund_info:
            fund_code = fund_info["code"]
            fund_name = fund_info["name"]
        else:
            return (f"未找到匹配 '{fund_input}' 的基金。\n"
                    f"请尝试使用6位基金代码，或运行 fund_lookup.py 搜索。")

    out = [f"基金代码：{fund_code}",
            f"基金名称：{fund_name}",
            f"评分框架：{manager}", ""]

    target_fund_dir = None
    if mgr_fund_dir and mgr_fund_dir.exists():
        for d in mgr_fund_dir.iterdir():
            if d.is_dir() and fund_code in d.name:
                target_fund_dir = d
                break

    if target_fund_dir:
        out.append(f"数据来源：经理基金快照 ({target_fund_dir.name})")
        fund_data = load_fund_data(target_fund_dir)
    else:
        out.append(f"数据来源：需运行 fetch_any_fund.py {fund_code} 抓取")
        cache_dir = Path(__file__).resolve().parent.parent.parent / "references" / "fund_data_cache"
        if cache_dir.exists():
            for d in cache_dir.iterdir():
                if fund_code in d.name:
                    target_fund_dir = d
                    break
        fund_data = load_fund_data(target_fund_dir) if target_fund_dir else {}

    out.append("")
    out.append("=== 机械指标 ===")
    if fund_data.get("holdings"):
        concentration = analyze_concentration(fund_data["holdings"])
        if concentration:
            out.append(f"前十大集中度：{concentration:.2f}%")
    if fund_data.get("performance"):
        for line in fund_data["performance"].split("\n")[:20]:
            if line.strip():
                out.append(line)

    scorecard_file = (Path(__file__).resolve().parent.parent.parent
                      / "references" / "managers" / manager / "scorecard.md")
    out.append("")
    out.append("=== 评分指引 ===")
    out.append(f"请读取 {scorecard_file} 按六维评分卡逐项打分。")
    out.append(f"参考基金：{manager}的代表基金 {representative}")
    out.append(f"\n注意：这套分衡量的是'与{manager}投资风格的契合度'，不是基金好坏的绝对评判。")
    return "\n".join(out)
