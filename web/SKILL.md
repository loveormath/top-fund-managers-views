---
name: top-fund-managers-views
description: Use the five-manager Fund Insight knowledge base for sourced questions, method-based simulations, fund-data checks, single-manager analysis, multi-manager comparison, or two-round meeting discussions involving 刘旭、张坤、张璐、谢治宇、赵诣. Trigger when users ask what these managers said, how their methods differ, how their disclosed portfolios align with their views, or want one or more of them to discuss an investment topic. Distinguish exact source quotes from method-based simulation and avoid presenting research assistance as investment advice.
---

# Fund Insight 五基金经理观点库

Use the registry at `config/managers.yaml` as the only manager list and path map. Do not hardcode or restore removed managers.

## Choose a workflow

- Use **single-manager analysis** for one selected manager. Search only that manager's files, then return their position, evidence, method inference, missing information, and confidence.
- Use **multi-manager summary** for 2–5 managers. Analyze each manager independently from their own files, then compare consensus, disagreements, evidence quality, and information gaps.
- Use **meeting discussion** for 2–5 managers. Produce an independent opening round, a second round where each manager responds to all opening views, and a neutral moderator report. Keep each manager's citations restricted to their own files.
- For a follow-up, preserve the selected managers and mode. Use the previous thread summary as context, but retrieve evidence again for the new question.

## Read sources in this order

1. Read `config/managers.yaml` and resolve the selected manager's paths.
2. Search direct statements in `references/managers/{经理}/corpus/`.
3. Read `references/managers/{经理}/method.md` for the sourced method framework.
4. Read `references/managers/{经理}/fund_data/` for disclosed holdings and fund snapshots.
5. Use `references/managers/{经理}/profile.md` for biography and `scorecard.md` for style-fit scoring.

Run local keyword search when useful:

```text
python "<skill-root>/scripts/search_corpus.py" "关键词" --manager 张坤 --context 2
```

Use one plain command at a time. Replace `<skill-root>` with the directory containing this file.

## Keep claims traceable

- Quote only text that appears exactly in a source file. Include the manager, document title, date or reporting period when available, and relative file path.
- Label any conclusion not stated directly as `基于方法论模拟：`.
- Treat holdings as reporting-period snapshots, not real-time positions. Include the relevant period.
- State when the corpus does not answer the question. Do not fill gaps with invented facts.
- Keep manager roles separate: one manager must not cite another manager's files as their own support.
- For comparisons, use the same dimensions across managers: selection logic, valuation, industry exposure, concentration, holding period, risk control, and evidence recency.

## Structure manager output

Return these fields when a structured answer is appropriate:

- `立场`: concise answer to the question.
- `直接证据`: exact quotes with source paths.
- `方法推演`: explicitly labeled simulations.
- `持仓证据`: reporting-period fund data with paths.
- `缺失信息`: facts the current corpus cannot establish.
- `置信度`: high, medium, or low, based on evidence specificity and recency.

For multi-manager summaries, add a consensus/disagreement matrix. For meetings, group content by round and finish with a moderator report covering agreement, unresolved disagreement, and facts requiring verification.

## Manager scope

- 刘旭：大成基金；长期价值、制造业、安全边际。
- 张坤：易方达基金；价值投资、高质量成长、长期持有。
- 张璐：永赢基金；先进制造、机器人、产业趋势。
- 谢治宇：兴证全球基金；自下而上、均衡配置、性价比。
- 赵诣：泉果基金；高端制造、成长投资、竞争格局。

Treat these labels as navigation hints, not conclusions. Verify the selected manager's method and corpus before answering.

## Boundaries

- Present outputs as research and learning assistance, not personalized investment advice.
- Do not claim to impersonate a real manager or write as though a simulated response were authentic speech.
- Do not update fund data from the internet unless the user explicitly asks for that separate action.
- Preserve user deletions and edits in `references/`; never restore deleted managers or duplicate directories automatically.
