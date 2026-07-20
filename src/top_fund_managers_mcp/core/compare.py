# -*- coding: utf-8 -*-
"""多经理横向对比（Track B：整合 Agent 核心能力）。

对同一主题/标的，跨多位基金经理检索观点并列呈现；也可对比方法框架与业绩。
只做检索与并列，不杜撰；引用忠于原文，标注出处。
"""

import re
from pathlib import Path

from ..config import REPO_ROOT
from .managers import list_managers, corpus_dir, fund_data_dir, representative_fund


def _resolve_managers(managers):
    """校验并返回有效经理列表；默认全部（动态发现）。"""
    valid = list_managers()
    if not managers:
        return valid
    out = []
    for m in managers:
        if m in valid:
            out.append(m)
        else:
            print(f"[跳过] 未找到经理目录：{m}")
    return out


def compare_topic(keyword, managers, context_lines=1, per_manager_limit=8):
    out = [f"# 横向对比：各经理对「{keyword}」的公开观点\n",
            f"> 对比范围：{', '.join(managers)}｜引用忠于原文，出处见每条末尾\n"]
    any_hit = False
    for mgr in managers:
        c_dir = corpus_dir(mgr)
        hits = []
        if c_dir and c_dir.exists():
            for md in sorted(c_dir.rglob("*.md")):
                rel = md.relative_to(c_dir)
                try:
                    lines = md.read_text(encoding="utf-8").split("\n")
                except Exception:
                    continue
                for i, line in enumerate(lines):
                    if keyword.lower() in line.lower() and line.strip():
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)
                        frag = " ".join(l.strip() for l in lines[start:end] if l.strip())
                        hits.append((frag, str(rel)))
                        if len(hits) >= per_manager_limit:
                            break
                if len(hits) >= per_manager_limit:
                    break
        out.append(f"## {mgr}")
        if hits:
            any_hit = True
            for frag, src in hits:
                if len(frag) > 200:
                    frag = frag[:200] + "…"
                out.append(f"- {frag}")
                out.append(f"  （出处：{mgr} / {src}）")
        else:
            out.append(f"- 语料中未检索到「{keyword}」的直接表态。")
            out.append(f"  可读取 `references/managers/{mgr}/method.md` 用其方法框架推演（需声明非本人原话）。")
        out.append("")
    if not any_hit:
        out.append("> 提示：各经理语料均未直接谈及该主题，建议用各自 method.md 框架推演对比。")
    return "\n".join(out)


def _extract_method_summary(method_path, max_points=6):
    if not method_path or not method_path.exists():
        return []
    points = []
    try:
        for line in method_path.read_text(encoding="utf-8").split("\n"):
            m = re.match(r"^#{2,3}\s+(.*)", line.strip())
            if m:
                title = m.group(1).strip()
                if title and not title.startswith(("引用", "边界", "免责", "来源", "说明")):
                    points.append(title)
            if len(points) >= max_points:
                break
    except Exception:
        pass
    return points


def compare_method(managers):
    out = ["# 横向对比：投资方法框架\n",
            f"> 对比范围：{', '.join(managers)}｜摘要取自各经理 method.md 的方法要点标题\n"]
    for mgr in managers:
        method_path = REPO_ROOT / "references" / "managers" / mgr / "method.md"
        points = _extract_method_summary(method_path)
        out.append(f"## {mgr}")
        if points:
            for p in points:
                out.append(f"- {p}")
        else:
            out.append(f"- 未能解析方法要点，请直接查看 `references/managers/{mgr}/method.md`。")
        out.append(f"  （完整框架：references/managers/{mgr}/method.md）")
        out.append("")
    out.append("> 对比维度建议：选股逻辑、行业偏好、仓位/集中度、换手率、回撤控制、估值方法。")
    return "\n".join(out)


def compare_fund(managers):
    out = ["# 横向对比：代表基金业绩\n",
            f"> 对比范围：{', '.join(managers)}｜数据取自各经理 fund_data/ 快照\n"]
    for mgr in managers:
        fd = fund_data_dir(mgr)
        rep = representative_fund(mgr)
        out.append(f"## {mgr}（代表基金：{rep or '未知'}）")
        if not fd or not fd.exists():
            out.append(f"- 无 fund_data 目录。\n")
            continue
        found = False
        if rep:
            target = fd / rep
            perf = target / "净值业绩规模.md" if target.exists() else None
            if perf and perf.exists():
                found = True
                lines = [
                    l.strip() for l in perf.read_text(encoding="utf-8").split("\n")
                    if l.strip() and not l.startswith(">")
                ]
                for l in lines[:14]:
                    out.append(l)
        if not found:
            out.append(f"- 未找到代表基金业绩数据（{rep or '无代表基金'}）。")
        out.append("")
    return "\n".join(out)


def compare_managers(mode, keyword=None, managers=None):
    """横向对比总入口。mode ∈ {topic, method, fund}。"""
    mgrs = _resolve_managers(managers)
    if not mgrs:
        return "错误：没有可用的经理目录。"
    if mode == "topic":
        if not keyword:
            return "错误：topic 模式需要 keyword。"
        return compare_topic(keyword, mgrs)
    elif mode == "method":
        return compare_method(mgrs)
    elif mode == "fund":
        return compare_fund(mgrs)
    return "错误：mode 必须是 topic / method / fund。"
