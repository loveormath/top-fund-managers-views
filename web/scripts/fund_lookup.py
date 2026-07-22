#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金代码查询工具 — 在全市场约2.7万只基金中按名称/拼音/代码/类型查找。

用法：
  python fund_lookup.py 中欧医疗                    # 按名称搜索
  python fund_lookup.py 005827                       # 按代码搜索
  python fund_lookup.py 蓝筹 --type 混合型-偏股       # 按类型筛选
"""

import argparse
import json
import os
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
FUND_LIST_FILE = SKILL_DIR / "references" / "all_funds" / "fund_list.json"

def load_fund_list():
    """加载基金列表"""
    if not FUND_LIST_FILE.exists():
        print(f"错误：基金列表文件不存在：{FUND_LIST_FILE}")
        print("请先运行 python scripts/build_fund_list.py 生成。")
        return []
    
    try:
        with open(FUND_LIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"加载基金列表失败：{e}")
        return []

def search_funds(funds, keyword, fund_type=None, limit=20):
    """搜索基金"""
    results = []
    keyword_lower = keyword.lower()
    
    for fund in funds:
        code = fund.get("code", "")
        name = fund.get("name", "")
        pinyin = fund.get("pinyin", "")
        ftype = fund.get("type", "")
        
        # 匹配关键词
        matched = (
            keyword_lower in code.lower()
            or keyword_lower in name.lower()
            or keyword_lower in pinyin.lower()
        )
        
        if not matched:
            continue
        
        # 按类型筛选
        if fund_type and fund_type.lower() not in ftype.lower():
            continue
        
        results.append(fund)
        
        if len(results) >= limit:
            break
    
    return results

def main():
    parser = argparse.ArgumentParser(description="在全市场基金列表中查找基金代码")
    parser.add_argument("keyword", help="搜索关键词（基金名称/代码/拼音）")
    parser.add_argument("--type", dest="fund_type", help="按类型筛选（如：混合型-偏股、债券型）")
    parser.add_argument("--limit", "-l", type=int, default=20, help="最大返回数量")
    
    args = parser.parse_args()
    
    funds = load_fund_list()
    if not funds:
        return
    
    results = search_funds(funds, args.keyword, args.fund_type, args.limit)
    
    if not results:
        print(f"未找到匹配 '{args.keyword}' 的基金。")
        return
    
    print(f"找到 {len(results)} 只匹配基金：\n")
    print(f"{'代码':<10} {'名称':<30} {'类型':<15}")
    print("-" * 60)
    for fund in results:
        print(f"{fund.get('code', ''):<10} {fund.get('name', ''):<30} {fund.get('type', ''):<15}")

if __name__ == "__main__":
    main()
