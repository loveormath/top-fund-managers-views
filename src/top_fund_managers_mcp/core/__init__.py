"""core — 纯逻辑层，不依赖 MCP。

每个模块把原有脚本的能力重写为「返回字符串」的函数，
这样 CLI 与 MCP tool 共用同一份实现，输出完全一致。
目录结构变体（corpus/media/copus、fund_data/funds_data）在此层统一容忍。

导入本包后，managers/search/compare/score/generate/index/fund_lookup
均作为属性可用（见下方显式导入）。
"""

from . import managers, search, compare, score, generate, index, fund_lookup

__all__ = [
    "managers",
    "search",
    "compare",
    "score",
    "generate",
    "index",
    "fund_lookup",
]
