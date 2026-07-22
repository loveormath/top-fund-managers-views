#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
任意基金数据抓取工具 — 从天天基金网抓取指定基金的持仓/净值/业绩数据到缓存。

用法：
  python fetch_any_fund.py 003095                    # 抓取单只基金
  python fetch_any_fund.py 003095 163406             # 抓取多只基金
  python fetch_any_fund.py 003095 --force             # 强制刷新缓存
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("错误：缺少依赖库。请运行 pip install requests beautifulsoup4 lxml")
    sys.exit(1)

SKILL_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = SKILL_DIR / "references" / "fund_data_cache"
CACHE_EXPIRE_DAYS = 7

# 天天基金 API 端点
FUND_DETAIL_URL = "https://fund.eastmoney.com/{code}.html"
FUND_HOLDINGS_URL = "https://fundf10.eastmoney.com/ccmx_{code}.html"
FUND_NET_VALUE_URL = "https://fundf10.eastmoney.com/jjjz_{code}.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://fund.eastmoney.com/",
}

def get_fund_name(code):
    """获取基金名称"""
    url = FUND_DETAIL_URL.format(code=code)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")
        title = soup.find("title")
        if title:
            name = title.text.split("(")[0].strip()
            return name
    except Exception as e:
        print(f"获取基金名称失败：{e}")
    return "未知基金"

def fetch_fund_data(code, force=False):
    """抓取基金数据"""
    fund_name = get_fund_name(code)
    cache_dir = CACHE_DIR / f"{code}_{fund_name}"
    
    # 检查缓存
    if not force and cache_dir.exists():
        # 检查缓存是否过期
        cache_age = time.time() - cache_dir.stat().st_mtime
        if cache_age < CACHE_EXPIRE_DAYS * 86400:
            print(f"使用缓存：{cache_dir}（{cache_age/86400:.1f}天前更新）")
            return cache_dir
    
    cache_dir.mkdir(parents=True, exist_ok=True)
    print(f"正在抓取基金 {code}（{fund_name}）的数据...")
    
    # 抓取持仓数据
    try:
        url = FUND_HOLDINGS_URL.format(code=code)
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")
        
        # 解析持仓表格
        holdings = []
        table = soup.find("table", class_="tzms")
        if not table:
            # 尝试其他表格
            table = soup.find("table", {"id": "ccmx_table"})
        
        if table:
            rows = table.find_all("tr")
            for row in rows[1:]:  # 跳过表头
                cols = row.find_all("td")
                if len(cols) >= 4:
                    holdings.append({
                        "rank": cols[0].text.strip(),
                        "code": cols[1].text.strip(),
                        "name": cols[2].text.strip(),
                        "ratio": cols[3].text.strip(),
                    })
        
        holdings_file = cache_dir / "季度持仓.md"
        with open(holdings_file, "w", encoding="utf-8") as f:
            f.write(f"# {fund_name}（{code}）· 季度持仓\n\n")
            f.write(f"> 数据来源：天天基金网\n")
            f.write(f"> 抓取时间：{time.strftime('%Y-%m-%d %H:%M')}\n\n")
            if holdings:
                f.write(f"| 排名 | 股票代码 | 股票名称 | 占净值比(%) |\n")
                f.write(f"|---|---|---|---|\n")
                for h in holdings[:10]:
                    f.write(f"| {h['rank']} | {h['code']} | {h['name']} | {h['ratio']} |\n")
            else:
                f.write("暂未获取到持仓数据，请手动查看。\n")
        
        print(f"  持仓数据已保存到 {holdings_file}")
    except Exception as e:
        print(f"  抓取持仓数据失败：{e}")
    
    # 抓取净值/业绩数据
    try:
        url = FUND_NET_VALUE_URL.format(code=code)
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")
        
        # 提取基本信息
        info = {}
        info_div = soup.find("div", class_="bs_jz")
        if info_div:
            info["raw"] = info_div.get_text(strip=True)
        
        perf_file = cache_dir / "净值业绩规模.md"
        with open(perf_file, "w", encoding="utf-8") as f:
            f.write(f"# {fund_name}（{code}）· 净值业绩规模\n\n")
            f.write(f"> 数据来源：天天基金网\n")
            f.write(f"> 抓取时间：{time.strftime('%Y-%m-%d %H:%M')}\n\n")
            if info.get("raw"):
                f.write(f"## 基本信息\n\n{info['raw']}\n\n")
            else:
                f.write("暂未获取到详细数据，请手动查看。\n")
        
        print(f"  净值数据已保存到 {perf_file}")
    except Exception as e:
        print(f"  抓取净值数据失败：{e}")
    
    return cache_dir

def main():
    parser = argparse.ArgumentParser(description="抓取任意基金的持仓/净值/业绩数据")
    parser.add_argument("codes", nargs="+", help="基金代码（可多个）")
    parser.add_argument("--force", "-f", action="store_true", help="强制刷新缓存")
    
    args = parser.parse_args()
    
    for code in args.codes:
        fetch_fund_data(code, force=args.force)
        print()

if __name__ == "__main__":
    main()
