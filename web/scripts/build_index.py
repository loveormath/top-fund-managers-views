#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
语料索引重建工具 — 扫描全部语料文件，生成/更新 corpus_index.json。

用法：
  python build_index.py
"""

import json
from datetime import datetime
from pathlib import Path

from manager_registry import manager_names

SKILL_DIR = Path(__file__).resolve().parent.parent
MANAGERS_DIR = SKILL_DIR / "references" / "managers"

MANAGERS = manager_names()

DOC_TYPES = {
    "定期报告": "定期报告",
    "媒体报道": "媒体报道",
}

def build_index():
    """扫描全部语料，构建索引"""
    index = {
        "managers": {},
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    
    for mgr in MANAGERS:
        mgr_corpus = MANAGERS_DIR / mgr / "corpus"
        if not mgr_corpus.exists():
            continue
        
        mgr_index = {"documents": []}
        
        for md_file in sorted(mgr_corpus.rglob("*.md")):
            rel_path = md_file.relative_to(mgr_corpus)
            
            # 确定类型
            doc_type = "其他"
            for type_key, type_val in DOC_TYPES.items():
                if type_key in str(rel_path):
                    doc_type = type_val
                    break
            
            # 确定标题
            title = md_file.stem
            
            # 读取前几行获取标题
            try:
                content = md_file.read_text(encoding="utf-8")
                lines = content.split("\n")
                for line in lines[:5]:
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break
            except Exception:
                pass
            
            mgr_index["documents"].append({
                "type": doc_type,
                "title": title,
                "path": str(rel_path),
                "file": md_file.relative_to(SKILL_DIR).as_posix(),
            })
        
        index["managers"][mgr] = mgr_index
        print(f"{mgr}：{len(mgr_index['documents'])} 篇文档")
    
    return index

def main():
    print("正在扫描语料并构建索引...\n")
    
    index = build_index()
    
    # 保存到每位经理目录
    for mgr in MANAGERS:
        mgr_dir = MANAGERS_DIR / mgr
        if not mgr_dir.exists():
            continue
        
        index_file = mgr_dir / "corpus_index.json"
        mgr_index = {
            "manager": mgr,
            "documents": index["managers"].get(mgr, {}).get("documents", []),
            "updated": index["updated"],
        }
        
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(mgr_index, f, ensure_ascii=False, indent=2)
        
        print(f"索引已保存到 {index_file}")
    
    print("\n索引构建完成。")

if __name__ == "__main__":
    main()
