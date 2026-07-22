#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全市场基金列表重建工具 — 从天天基金网抓取全市场基金列表。

用法：
  python build_fund_list.py
"""

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
OUTPUT_FILE = SKILL_DIR / "references" / "all_funds" / "fund_list.json"

# 天天基金基金列表 API
# 每页20条，通过页码翻页
FUND_LIST_API = "https://fundapi.eastmoney.com/fundtradenew.aspx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://fund.eastmoney.com/",
}

def fetch_fund_list():
    """从天天基金网抓取全市场基金列表"""
    funds = []
    page = 1
    total = 0
    
    print("开始抓取全市场基金列表...")
    
    while True:
        params = {
            "ft": "all",
            "sc": "1nzf",
            "sd": "",
            "ed": "",
            "pi": str(page),
            "pn": "20",
            "zf": "diy",
            "sh": "rst",
        }
        
        try:
            resp = requests.get(FUND_LIST_API, params=params, headers=HEADERS, timeout=15)
            resp.encoding = "utf-8"
            data = resp.json()
            
            if not data.get("Data"):
                break
            
            page_funds = data["Data"]
            if not page_funds:
                break
            
            for f in page_funds:
                funds.append({
                    "code": f.get("FCODE", ""),
                    "name": f.get("SHORTNAME", ""),
                    "type": f.get("FTYPE", ""),
                    "pinyin": f.get("PYABBR", ""),
                })
            
            total = int(data.get("TotalNum", 0))
            
            if page % 50 == 0:
                print(f"  已抓取 {len(funds)}/{total} ...")
            
            if len(funds) >= total:
                break
            
            page += 1
            time.sleep(0.3)  # 避免过快
            
        except Exception as e:
            print(f"  第 {page} 页抓取失败：{e}")
            break
    
    return funds

def main():
    funds = fetch_fund_list()
    
    if not funds:
        print("抓取失败，未获取到数据。")
        return
    
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(funds, f, ensure_ascii=False, indent=2)
    
    print(f"\n完成！共抓取 {len(funds)} 只基金。")
    print(f"已保存到 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
