#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金经理基金数据刷新工具 — 从天天基金网抓取/刷新基金经理的基金数据。

用法：
  python fetch_fund_data.py                        # 刷新全部五位经理的全部基金
  python fetch_fund_data.py --manager 张坤          # 仅刷新张坤的基金
  python fetch_fund_data.py 005827                  # 仅刷新指定基金
"""

import argparse
import sys
import time
from pathlib import Path

from manager_registry import manager_names

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("错误：缺少依赖库。请运行 pip install requests beautifulsoup4 lxml")
    sys.exit(1)

SKILL_DIR = Path(__file__).resolve().parent.parent
MANAGERS_DIR = SKILL_DIR / "references" / "managers"

MANAGERS = manager_names()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://fund.eastmoney.com/",
}

FUND_HOLDINGS_URL = "https://fundf10.eastmoney.com/ccmx_{code}.html"
FUND_DETAIL_URL = "https://fundf10.eastmoney.com/jbgk_{code}.html"

def fetch_fund_holdings(code, fund_name, output_dir):
    """抓取基金持仓数据"""
    try:
        url = FUND_HOLDINGS_URL.format(code=code)
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")
        
        # 解析持仓表格
        holdings = []
        table = soup.find("table", {"id": "ccmx_table"})
        if not table:
            table = soup.find("table", class_="tzms")
        
        if table:
            rows = table.find_all("tr")
            for row in rows[1:]:
                cols = row.find_all("td")
                if len(cols) >= 4:
                    holdings.append({
                        "rank": cols[0].text.strip(),
                        "code": cols[1].text.strip(),
                        "name": cols[2].text.strip(),
                        "ratio": cols[3].text.strip(),
                    })
        
        holdings_file = output_dir / "季度持仓.md"
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
                f.write("暂未获取到持仓数据。\n")
        
        return True
    except Exception as e:
        print(f"  抓取持仓失败：{e}")
        return False

def fetch_fund_detail(code, fund_name, output_dir):
    """抓取基金净值/业绩/规模数据"""
    try:
        url = FUND_DETAIL_URL.format(code=code)
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")
        
        # 提取基本信息表格
        info = {}
        table = soup.find("table", class_="w782 comm cfxq")
        if table:
            rows = table.find_all("tr")
            for row in rows:
                th = row.find("th")
                td = row.find("td")
                if th and td:
                    info[th.text.strip()] = td.text.strip()
        
        perf_file = output_dir / "净值业绩规模.md"
        with open(perf_file, "w", encoding="utf-8") as f:
            f.write(f"# {fund_name}（{code}）· 净值业绩规模\n\n")
            f.write(f"> 数据来源：天天基金网\n")
            f.write(f"> 抓取时间：{time.strftime('%Y-%m-%d %H:%M')}\n\n")
            if info:
                f.write("## 基本信息\n\n")
                f.write("| 项目 | 内容 |\n|---|---|\n")
                for k, v in info.items():
                    f.write(f"| {k} | {v} |\n")
            else:
                f.write("暂未获取到详细数据。\n")
        
        return True
    except Exception as e:
        print(f"  抓取净值数据失败：{e}")
        return False

def refresh_manager_funds(manager, fund_code=None):
    """刷新指定经理的基金数据"""
    mgr_fund_dir = MANAGERS_DIR / manager / "fund_data"
    if not mgr_fund_dir.exists():
        print(f"  {manager} 的基金数据目录不存在")
        return
    
    # 遍历基金目录
    for fund_dir in sorted(mgr_fund_dir.iterdir()):
        if not fund_dir.is_dir():
            continue
        if fund_dir.name.startswith("_"):
            continue
        
        # 从目录名提取代码
        code = fund_dir.name.split("_")[0]
        
        if fund_code and code != fund_code:
            continue
        
        fund_name = fund_dir.name.split("_", 1)[1] if "_" in fund_dir.name else code
        print(f"  刷新 {code}（{fund_name}）...")
        
        fetch_fund_holdings(code, fund_name, fund_dir)
        fetch_fund_detail(code, fund_name, fund_dir)
        
        time.sleep(0.5)

def main():
    parser = argparse.ArgumentParser(description="刷新基金经理的基金数据")
    parser.add_argument("fund_code", nargs="?", help="指定基金代码（可选）")
    parser.add_argument("--manager", "-m", choices=MANAGERS, help="指定基金经理")
    
    args = parser.parse_args()
    
    if args.manager:
        managers_to_refresh = [args.manager]
    else:
        managers_to_refresh = MANAGERS
    
    for mgr in managers_to_refresh:
        print(f"\n正在刷新 {mgr} 的基金数据...")
        refresh_manager_funds(mgr, args.fund_code)
    
    print("\n刷新完成。")

if __name__ == "__main__":
    main()
