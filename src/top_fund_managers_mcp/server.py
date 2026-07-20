# -*- coding: utf-8 -*-
"""MCP server：把整个基金经理观点库封装为 MCP 工具。

工具列表（对应 PPT 四大 Track）：
  - list_managers    动态发现全部经理
  - search_corpus    语料检索（返回命中段落+出处）
  - compare_managers 横向对比（topic/method/fund）
  - score_fund       框架评分一键入口
  - generate_skill   复用性引擎（传入大V生成骨架）
  - fund_lookup      全市场基金代码查询
  - build_index      语料索引重建
"""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import core

mcp = FastMCP("top-fund-managers-views")


@mcp.tool()
def list_managers() -> str:
    """列出全部基金经理（运行时动态发现）。返回经理名与代表基金。"""
    mgrs = core.managers.list_managers()
    if not mgrs:
        return "当前未收录任何基金经理目录（references/managers/ 为空）。"
    lines = [f"共 {len(mgrs)} 位基金经理：", ""]
    for m in mgrs:
        rep = core.managers.representative_fund(m)
        lines.append(f"- {m}（代表基金：{rep or '未知'}）")
    return "\n".join(lines)


@mcp.tool()
def search_corpus(keywords: list[str], manager: Optional[str] = None,
                 match_any: bool = False, doc_type: Optional[str] = None,
                 context: int = 0) -> str:
    """在基金经理语料中搜索关键词，返回命中段落与出处。

    keywords: 一个或多个关键词；manager: 限定经理（留空则跨全部）；
    match_any: 命中任一关键词即可（默认需全部命中）；
    doc_type: 限定文档类型（如「定期报告」「媒体报道」）；
    context: 命中行上下文字数。
    """
    return core.search.search_corpus(
        keywords, manager=manager, match_any=match_any,
        doc_type=doc_type, context_lines=context)


@mcp.tool()
def compare_managers(mode: str, keyword: Optional[str] = None,
                    managers: Optional[list[str]] = None) -> str:
    """横向对比多位基金经理（Track B 整合能力）。

    mode:
      - "topic"：同一主题下各经理的公开观点（需提供 keyword）
      - "method"：并列各经理的投资方法框架
      - "fund"：并列各经理代表基金的净值业绩规模
    keyword: topic 模式下的主题/标的关键词；
    managers: 指定对比的经理（留空则全部）。
    """
    return core.compare.compare_managers(mode, keyword=keyword, managers=managers)


@mcp.tool()
def score_fund(fund: str, manager: str) -> str:
    """用某经理的投资框架给一只基金打分（备数据+算机械指标+指引）。

    fund: 基金代码或名称；
    manager: 必须是指定框架归属的经理之一。
    """
    return core.score.score_fund(fund, manager)


@mcp.tool()
def generate_skill(name: str, company: Optional[str] = None,
                   style: Optional[str] = None,
                   representative: Optional[str] = None,
                   source: Optional[str] = None,
                   dry_run: bool = False) -> str:
    """复用性引擎（Track C）：传入大V姓名，按统一标准生成 Skill 骨架。

    name: 经理/大V 姓名；
    company / style / representative: 可选补充信息；
    source: 本地语料素材目录（.md/.txt），会导入到 corpus/媒体报道/；
    dry_run: 仅预览、不落盘。
    生成的经理目录会被所有工具自动识别，无需改动任何脚本。
    """
    msg = core.generate.build_skeleton(
        name, company=company, style=style,
        representative=representative, source=source, dry_run=dry_run)
    if not dry_run:
        msg += core.generate.research_checklist(name, source)
    return msg


@mcp.tool()
def fund_lookup(keyword: str, fund_type: Optional[str] = None,
                limit: int = 20) -> str:
    """在全市场约2.7万只基金中按名称/代码/拼音查找基金代码。"""
    return core.fund_lookup.fund_lookup(keyword, fund_type=fund_type, limit=limit)


@mcp.tool()
def build_index() -> str:
    """重建全部经理的 corpus_index.json（扫描语料）。"""
    return core.index.build_index()
