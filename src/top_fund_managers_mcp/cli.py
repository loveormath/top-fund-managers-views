# -*- coding: utf-8 -*-
"""命令行入口（子命令与 MCP 工具名一一对应，便于本地与 SKILL.md 兼容）。

子命令（= MCP 工具名，旧短名 search/compare/score/generate/lookup/index/managers 仍可作别名）：
  list_managers   列出全部基金经理
  search_corpus   在基金经理语料中搜索关键词
  compare_managers 多经理横向对比（topic/method/fund）
  score_fund      用某经理框架给基金打分
  generate_skill  复用性引擎，生成 Skill 骨架
  fund_lookup     按名称/代码/拼音查全市场基金
  build_index     重建语料索引
用法示例：
  python -m top_fund_managers_mcp search_corpus "白酒" --manager 谢治宇
  python -m top_fund_managers_mcp compare_managers method
  python -m top_fund_managers_mcp score_fund 163406 --manager 谢治宇
  python -m top_fund_managers_mcp generate_skill --name 朱少醒 --dry-run
  python -m top_fund_managers_mcp fund_lookup 中欧医疗
  python -m top_fund_managers_mcp build_index
"""

import argparse
import sys

from . import core

# CLI 子命令（与 MCP 工具名一一对应）
CLI_SUBCOMMANDS = {
    "list_managers", "search_corpus", "compare_managers",
    "score_fund", "generate_skill", "fund_lookup", "build_index",
}
# 旧短名别名（向后兼容，仍可使用）
CLI_ALIASES = {
    "managers": "list_managers",
    "search": "search_corpus",
    "compare": "compare_managers",
    "score": "score_fund",
    "generate": "generate_skill",
    "lookup": "fund_lookup",
    "index": "build_index",
}


def run_search(argv):
    p = argparse.ArgumentParser(prog="search", description="在基金经理语料中搜索关键词")
    p.add_argument("keywords", nargs="+", help="搜索关键词（可多个）")
    p.add_argument("--manager", "-m", help="指定基金经理")
    p.add_argument("--any", action="store_true", help="命中任一关键词即可")
    p.add_argument("--type", dest="doc_type", help="限定文档类型")
    p.add_argument("--context", "-c", type=int, default=0, help="上下文行数")
    a = p.parse_args(argv)
    print(core.search.search_corpus(
        a.keywords, manager=a.manager, match_any=a.any,
        doc_type=a.doc_type, context_lines=a.context))


def run_compare(argv):
    p = argparse.ArgumentParser(prog="compare", description="多经理横向对比")
    sub = p.add_subparsers(dest="mode", required=True)
    pt = sub.add_parser("topic"); pt.add_argument("keyword")
    pt.add_argument("--managers", "-m", nargs="+")
    pt.add_argument("--context", "-c", type=int, default=1)
    pm = sub.add_parser("method"); pm.add_argument("--managers", "-m", nargs="+")
    pf = sub.add_parser("fund"); pf.add_argument("--managers", "-m", nargs="+")
    a = p.parse_args(argv)
    if a.mode == "topic":
        print(core.compare.compare_managers("topic", keyword=a.keyword, managers=a.managers))
    elif a.mode == "method":
        print(core.compare.compare_managers("method", managers=a.managers))
    else:
        print(core.compare.compare_managers("fund", managers=a.managers))


def run_score(argv):
    p = argparse.ArgumentParser(prog="score", description="框架评分一键入口")
    p.add_argument("fund", help="基金代码或名称")
    p.add_argument("--manager", "-m", required=True, help="评分框架（基金经理）")
    a = p.parse_args(argv)
    print(core.score.score_fund(a.fund, a.manager))


def run_generate(argv):
    p = argparse.ArgumentParser(prog="generate", description="复用性引擎：生成 Skill 骨架")
    p.add_argument("--name", "-n", required=True, help="经理/大V 姓名")
    p.add_argument("--company", "-c", help="所在公司")
    p.add_argument("--style", "-s", help="投资风格标签")
    p.add_argument("--representative", "-r", help="代表基金（code_名称）")
    p.add_argument("--source", help="本地语料素材目录")
    p.add_argument("--dry-run", action="store_true", help="只预览、不落盘")
    a = p.parse_args(argv)
    msg = core.generate.build_skeleton(
        a.name, company=a.company, style=a.style,
        representative=a.representative, source=a.source, dry_run=a.dry_run)
    print(msg)
    if not a.dry_run:
        print(core.generate.research_checklist(a.name, a.source))


def run_index(argv):
    print(core.index.build_index())


def run_lookup(argv):
    p = argparse.ArgumentParser(prog="fund_lookup", description="按名称/代码/拼音查基金")
    p.add_argument("keyword", help="搜索关键词（名称/代码/拼音）")
    p.add_argument("--type", dest="fund_type", help="按类型筛选")
    p.add_argument("--limit", "-l", type=int, default=20, help="最大返回数量")
    a = p.parse_args(argv)
    print(core.fund_lookup.fund_lookup(a.keyword, fund_type=a.fund_type, limit=a.limit))


def run_list_managers(argv):
    names = core.managers.list_managers()
    if not names:
        print("未找到任何经理目录（references/managers/ 为空）")
        return
    print(f"共发现 {len(names)} 位基金经理：")
    for n in names:
        print(f"  - {n}")


_DISPATCH = {
    "list_managers": run_list_managers,
    "search_corpus": run_search,
    "compare_managers": run_compare,
    "score_fund": run_score,
    "generate_skill": run_generate,
    "fund_lookup": run_lookup,
    "build_index": run_index,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        names = " | ".join(sorted(CLI_SUBCOMMANDS))
        print("用法：python -m top_fund_managers_mcp <子命令> ...")
        print(f"子命令（= MCP 工具名）：{names}")
        print("旧短名 managers/search/compare/score/generate/lookup/index 仍可作别名。")
        print("或留空直接启动 MCP stdio server。")
        return
    raw, rest = sys.argv[1], sys.argv[2:]
    cmd = CLI_ALIASES.get(raw, raw)
    if cmd not in _DISPATCH:
        print(f"未知子命令：{raw}")
        return
    _DISPATCH[cmd](rest)


if __name__ == "__main__":
    main()
