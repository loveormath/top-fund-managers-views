#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金评分一键入口 — 自动找代码+备数据+算机械指标，配合scorecard.md打分。

用法：
  python score_fund.py 招商中证白酒 --manager 张坤
  python score_fund.py 005827 --manager 谢治宇
  python score_fund.py 000628 --manager 刘旭
"""

import argparse
import json
from pathlib import Path

from manager_registry import managers_by_name

SKILL_DIR = Path(__file__).resolve().parent.parent

MANAGER_REGISTRY = managers_by_name()
MANAGERS = list(MANAGER_REGISTRY)
MANAGER_FUNDS = {
    name: {
        "fund_data_dir": SKILL_DIR / item["fund_data_dir"],
        "representative": (
            f"{item['representative_funds'][0]['code']}_{item['representative_funds'][0]['name']}"
            if item.get("representative_funds") else "未配置"
        ),
    }
    for name, item in MANAGER_REGISTRY.items()
}

def find_fund_code(keyword):
    """从全市场基金列表中查找代码"""
    fund_list_file = SKILL_DIR / "references" / "all_funds" / "fund_list.json"
    if not fund_list_file.exists():
        return None
    
    with open(fund_list_file, "r", encoding="utf-8") as f:
        funds = json.load(f)
    
    keyword_lower = keyword.lower()
    for fund in funds:
        if (keyword_lower in fund.get("code", "").lower()
            or keyword_lower in fund.get("name", "").lower()
            or keyword_lower in fund.get("pinyin", "").lower()):
            return fund
    
    return None

def load_fund_data(fund_dir):
    """加载基金数据"""
    holdings_file = fund_dir / "季度持仓.md"
    perf_file = fund_dir / "净值业绩规模.md"
    
    data = {}
    if holdings_file.exists():
        data["holdings"] = holdings_file.read_text(encoding="utf-8")
    if perf_file.exists():
        data["performance"] = perf_file.read_text(encoding="utf-8")
    
    return data

def analyze_concentration(holdings_text):
    """分析持仓集中度"""
    import re
    # 提取前十大占比
    ratio_pattern = re.findall(r'\|\s*\d+\s*\|\s*\S+\s*\|\s*\S+\s*\|\s*([\d.]+)\s*\|', holdings_text)
    if ratio_pattern:
        top10 = sum(float(r) for r in ratio_pattern[:10])
        return top10
    return None

def main():
    parser = argparse.ArgumentParser(description="基金经理框架评分一键入口")
    parser.add_argument("fund", help="基金代码或名称")
    parser.add_argument("--manager", "-m", required=True, choices=MANAGERS, help="评分框架（基金经理）")
    
    args = parser.parse_args()
    
    manager = args.manager
    mgr_info = MANAGER_FUNDS[manager]
    
    # 1. 找代码
    fund_input = args.fund
    if fund_input.isdigit() and len(fund_input) == 6:
        fund_code = fund_input
        fund_name = "待查"
    else:
        fund_info = find_fund_code(fund_input)
        if fund_info:
            fund_code = fund_info["code"]
            fund_name = fund_info["name"]
        else:
            print(f"未找到匹配 '{fund_input}' 的基金。")
            print("请尝试使用6位基金代码，或运行 fund_lookup.py 搜索。")
            return
    
    print(f"基金代码：{fund_code}")
    print(f"基金名称：{fund_name}")
    print(f"评分框架：{manager}")
    print()
    
    # 2. 备数据
    # 先看是不是经理自己的基金
    mgr_fund_dir = mgr_info["fund_data_dir"]
    target_fund_dir = None
    
    for d in mgr_fund_dir.iterdir() if mgr_fund_dir.exists() else []:
        if d.is_dir() and fund_code in d.name:
            target_fund_dir = d
            break
    
    if target_fund_dir:
        print(f"数据来源：经理基金快照 ({target_fund_dir.name})")
        fund_data = load_fund_data(target_fund_dir)
    else:
        print(f"数据来源：需运行 fetch_any_fund.py {fund_code} 抓取")
        cache_dir = SKILL_DIR / "references" / "fund_data_cache"
        for d in cache_dir.iterdir() if cache_dir.exists() else []:
            if fund_code in d.name:
                target_fund_dir = d
                break
        if target_fund_dir:
            fund_data = load_fund_data(target_fund_dir)
        else:
            fund_data = {}
    
    # 3. 算机械指标
    print("\n=== 机械指标 ===")
    
    if fund_data.get("holdings"):
        concentration = analyze_concentration(fund_data["holdings"])
        if concentration:
            print(f"前十大集中度：{concentration:.2f}%")
    
    if fund_data.get("performance"):
        # 简单展示业绩数据
        perf_lines = fund_data["performance"].split("\n")
        for line in perf_lines[:20]:
            if line.strip():
                print(line)
    
    # 4. 提示按评分卡打分
    scorecard_file = SKILL_DIR / "references" / "managers" / manager / "scorecard.md"
    print(f"\n=== 评分指引 ===")
    print(f"请读取 {scorecard_file} 按六维评分卡逐项打分。")
    print(f"参考基金：{manager}的代表基金 {mgr_info['representative']}")
    print(f"\n注意：这套分衡量的是'与{manager}投资风格的契合度'，不是基金好坏的绝对评判。")

if __name__ == "__main__":
    main()
