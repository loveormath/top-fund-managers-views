#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
语料检索工具 — 在五位基金经理的语料中搜索关键词，返回命中段落+出处。

用法：
  python search_corpus.py "关键词"                    # 跨五位经理搜索
  python search_corpus.py "关键词" --manager 张坤       # 仅在张坤语料中搜索
  python search_corpus.py "关键词" --manager 谢治宇    # 仅在谢治宇语料中搜索
  python search_corpus.py "关键词" --manager 刘旭      # 仅在刘旭语料中搜索
  python search_corpus.py "关键词1" "关键词2" --any    # 命中任一关键词
  python search_corpus.py "关键词" --type 定期报告      # 限类型
  python search_corpus.py "关键词" --context 2          # 带上下文行
"""

import argparse
from pathlib import Path

from manager_registry import manager_names

# 定位 skill 根目录
SKILL_DIR = Path(__file__).resolve().parent.parent
CORPUS_DIR = SKILL_DIR / "references" / "managers"

MANAGERS = manager_names()

def search_corpus(keywords, manager=None, match_any=False, doc_type=None, context_lines=0):
    """在语料中搜索关键词"""
    results = []
    
    # 确定搜索范围
    if manager:
        managers_to_search = [manager] if manager in MANAGERS else []
        if not managers_to_search:
            print(f"错误：未知基金经理 '{manager}'，可选：{', '.join(MANAGERS)}")
            return results
    else:
        managers_to_search = MANAGERS
    
    for mgr in managers_to_search:
        mgr_corpus = CORPUS_DIR / mgr / "corpus"
        if not mgr_corpus.exists():
            continue
        
        # 遍历所有 .md 文件
        for md_file in sorted(mgr_corpus.rglob("*.md")):
            rel_path = md_file.relative_to(mgr_corpus)
            
            # 按类型筛选
            if doc_type:
                if doc_type not in str(rel_path):
                    continue
            
            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                continue
            
            lines = content.split("\n")
            for i, line in enumerate(lines):
                # 检查是否匹配
                if match_any:
                    matched = any(kw.lower() in line.lower() for kw in keywords)
                else:
                    matched = all(kw.lower() in line.lower() for kw in keywords)
                
                if matched and line.strip():
                    # 构建出处
                    source_parts = [mgr, str(rel_path)]
                    source = " / ".join(source_parts)
                    
                    # 带上下文
                    context = ""
                    if context_lines > 0:
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)
                        context = "\n".join(lines[start:end])
                    
                    results.append({
                        "manager": mgr,
                        "source": source,
                        "line": line.strip(),
                        "context": context if context else None,
                        "file": str(rel_path),
                    })
    
    return results

def main():
    parser = argparse.ArgumentParser(description="在基金经理语料中搜索关键词")
    parser.add_argument("keywords", nargs="+", help="搜索关键词（可多个）")
    parser.add_argument("--manager", "-m", choices=MANAGERS, help="指定基金经理")
    parser.add_argument("--any", action="store_true", help="命中任一关键词即可")
    parser.add_argument("--type", dest="doc_type", help="限定文档类型（如：定期报告、媒体报道）")
    parser.add_argument("--context", "-c", type=int, default=0, help="上下文行数")
    
    args = parser.parse_args()
    
    results = search_corpus(
        args.keywords,
        manager=args.manager,
        match_any=args.any,
        doc_type=args.doc_type,
        context_lines=args.context,
    )
    
    if not results:
        print("未找到匹配结果。")
        print("提示：尝试换近义词，或用 --any 命中任一关键词，或用 --manager 指定经理。")
        return
    
    print(f"找到 {len(results)} 条匹配结果：\n")
    
    # 限制输出
    max_results = 50
    for i, r in enumerate(results[:max_results]):
        print(f"--- [{i+1}] ---")
        print(f"基金经理：{r['manager']}")
        print(f"出处：{r['source']}")
        if r["context"]:
            print(f"内容：")
            print(r["context"])
        else:
            print(f"内容：{r['line']}")
        print()
    
    if len(results) > max_results:
        print(f"... 还有 {len(results) - max_results} 条结果未显示。")

if __name__ == "__main__":
    main()
