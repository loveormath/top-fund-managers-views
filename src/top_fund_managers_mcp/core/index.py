# -*- coding: utf-8 -*-
"""语料索引重建工具 — 扫描全部语料文件，生成/更新 corpus_index.json。"""

import json
from datetime import datetime
from pathlib import Path

from ..config import MANAGERS_DIR
from .managers import list_managers, corpus_dir

DOC_TYPES = {
    "定期报告": "定期报告",
    "媒体报道": "媒体报道",
}


def build_index():
    """扫描全部语料，构建索引（写入每位经理目录的 corpus_index.json）。"""
    index = {
        "managers": {},
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    for mgr in list_managers():
        mgr_corpus = corpus_dir(mgr)
        if not mgr_corpus:
            continue

        mgr_index = {"documents": []}

        for md_file in sorted(mgr_corpus.rglob("*.md")):
            rel_path = md_file.relative_to(mgr_corpus)

            doc_type = "其他"
            for type_key, type_val in DOC_TYPES.items():
                if type_key in str(rel_path):
                    doc_type = type_val
                    break

            title = md_file.stem
            try:
                content = md_file.read_text(encoding="utf-8")
                for line in content.split("\n")[:5]:
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break
            except Exception:
                pass

            mgr_index["documents"].append({
                "type": doc_type,
                "title": title,
                "path": str(rel_path),
                "file": str(md_file),
            })

        index["managers"][mgr] = mgr_index
        print(f"{mgr}：{len(mgr_index['documents'])} 篇文档")

    out = ["正在扫描语料并构建索引...\n"]
    for mgr in list_managers():
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
        out.append(f"索引已保存到 {index_file}")
    out.append("\n索引构建完成。")
    return "\n".join(out)
