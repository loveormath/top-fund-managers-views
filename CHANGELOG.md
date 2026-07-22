# Changelog

## [2.1.0] - 2026-07-19

### Added

- 新增数据总结提示词功能

## [2.0.0] - 2026-07-18

### Added

- 新增 Fund Insight 完整应用：Vue 3 + TypeScript 前端，以及 FastAPI + LangGraph 后端。
- 新增单人总结、多人总结和两轮会议讨论三种工作流，支持 SSE 流式输出与继续追问。
- 新增 DeepSeek 密钥加密存储、模型与余额查询、讨论历史和本地混合检索索引。
- 新增 Docker Compose 单机部署、后端测试、前端测试和响应式界面。
- 基金经理扩展为刘旭、张坤、张璐、谢治宇、赵诣五位，并由统一注册表驱动。

### Changed

- 统一基金经理资料目录为 `profile.md`、`method.md`、`scorecard.md`、`corpus/` 和 `fund_data/`。
- 重写项目 README、Skill 定义与旧脚本，移除硬编码经理名单。
- 语料索引改为相对路径，便于本地、容器和不同操作系统复用。

### Removed

- 移除不再使用的高楠资料、重复的 `谢治宇1` 目录和旧 WorkBuddy 部署说明。

## [1.0.0] - 2026-07-10

### Added
- 初始版本，覆盖三位中国顶流基金经理：张坤（易方达）、谢治宇（兴证全球）、高楠（永赢）
- 每位经理包含：
  - 投资方法框架 `method.md`（含原话佐证）
  - 评分卡 `scorecard.md`
  - 原文语料 `corpus/`（定期报告、媒体报道、简介、基金清单）
  - 真实基金数据 `fund_data/`（季度持仓、净值业绩规模）
- 全市场约2.7万只基金列表 `references/all_funds/fund_list.json`
- Python 脚本工具链：
  - `search_corpus.py` — 语料检索
  - `fund_lookup.py` — 基金代码查询
  - `fetch_any_fund.py` — 任意基金数据抓取
  - `score_fund.py` — 框架评分
  - `build_index.py` — 语料索引重建
  - `build_fund_list.py` — 全市场基金列表重建
  - `fetch_fund_data.py` — 经理基金数据刷新
