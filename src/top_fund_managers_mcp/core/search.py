# -*- coding: utf-8 -*-
"""语料检索工具 — 在全部基金经理的语料中搜索关键词，返回命中段落+出处。"""

from .managers import list_managers, corpus_dir


def search_corpus(keywords, manager=None, match_any=False, doc_type=None, context_lines=0):
    """在语料中搜索关键词，返回格式化的命中结果字符串。"""
    results = []

    if manager:
        if manager not in list_managers():
            return f"错误：未知基金经理 '{manager}'，可选：{', '.join(list_managers())}"
        managers_to_search = [manager]
    else:
        managers_to_search = list_managers()

    for mgr in managers_to_search:
        mgr_corpus = corpus_dir(mgr)
        if not mgr_corpus:
            continue

        for md_file in sorted(mgr_corpus.rglob("*.md")):
            rel_path = md_file.relative_to(mgr_corpus)

            if doc_type and doc_type not in str(rel_path):
                continue

            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                continue

            lines = content.split("\n")
            for i, line in enumerate(lines):
                if match_any:
                    matched = any(kw.lower() in line.lower() for kw in keywords)
                else:
                    matched = all(kw.lower() in line.lower() for kw in keywords)

                if matched and line.strip():
                    context = ""
                    if context_lines > 0:
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)
                        context = "\n".join(lines[start:end])

                    results.append({
                        "manager": mgr,
                        "source": f"{mgr} / {rel_path}",
                        "line": line.strip(),
                        "context": context if context else None,
                    })

    if not results:
        return "未找到匹配结果。"

    out = [f"找到 {len(results)} 条匹配结果：\n"]
    for i, r in enumerate(results[:50]):
        out.append(f"--- [{i+1}] ---")
        out.append(f"基金经理：{r['manager']}")
        out.append(f"出处：{r['source']}")
        if r["context"]:
            out.append("内容：")
            out.append(r["context"])
        else:
            out.append(f"内容：{r['line']}")
        out.append("")

    if len(results) > 50:
        out.append(f"... 还有 {len(results) - 50} 条结果未显示。")

    return "\n".join(out)
