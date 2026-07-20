---
name: top-fund-managers-views
description: >-
  中国顶流基金经理观点库——基于张坤（易方达）、谢治宇（兴证全球）、高楠（永赢）、刘旭（大成）、张璐（永赢）、赵诣（泉果）六位基金经理的全部公开观点原文语料，外加从语料蒸馏、有本人原话佐证的投资方法的可溯源 research skill。能做：
  (1) 溯源问答——他怎么看白酒/半导体/AI/消费/创新药等，引用其原话作答；
  (2) 讲解他的投资方法/框架/选股逻辑；
  (3) 前瞻应用——用他的方法分析当下任意主题/行业/个股，语料没谈过也能据框架推演；
  (4) 风格化点评——用他季报/采访的口吻写市场点评、季度展望；
  (5) 言行对照——用他全部基金真实数据（季度持仓/净值/业绩/规模/任职回报）核对"说的"与"买的"；
  (6) 多经理横向对比——用 compare_managers.py 横向对比六人的投资方法、观点、持仓风格、业绩表现；
  (7) 全市场查询对比——内置约2.7万只基金列表，按需抓任意基金真实数据做查询或对比；
  (8) 框架评分——给一只基金按指定经理的方法打分。
  When the user mentions 张坤/谢治宇/高楠 or any of their funds, asks their view on a sector/stock/theme, their 投资方法/框架/选股/风格/持仓/业绩/净值/规模, wants to apply their approach, a commentary in their tone, to check words vs holdings, to compare the three managers, or to look up/compare/score ANY China mutual fund——use this skill, even if they don't say "skill".
  引用忠于原文、不杜撰；推演与原话区分。研究学习辅助，非投资建议。
metadata:
  author: personal project (primary-source corpus of public materials)
  sources:
    - https://www.efunds.com.cn/manager/721.shtml
    - https://fund.eastmoney.com/manager/30198031.html
    - https://fund.eastmoney.com/manager/30561920.html
  license: 个人学习用途；语料为各基金经理公开披露内容
---

# 中国顶流基金经理观点库 Skill

让 AI 既能查到、引用**张坤、谢治宇、高楠、刘旭、张璐、赵诣**六位中国最热门基金经理**本人公开说过的话**，也能用**他们各自的投资方法**去聊任何相关的话题。

**三块根基**，都在 `references/managers/{经理}/` 里，都来自公开内容、可溯源：

- **原文语料** `references/managers/{经理}/corpus/`（部分经理用 `media/`） —— 各经理的全部公开观点：定期报告、媒体采访报道，外加简介与基金清单。
- **投资方法** `references/managers/{经理}/method.md` —— 从语料蒸馏出来的方法框架，**每一条都有他本人原话佐证**。
- **真实基金数据** `references/managers/{经理}/fund_data/`（部分经理用 `funds_data/`） —— 全部基金的真实数据快照：每季前十大重仓股、净值/业绩/规模/资产配置/任职回报。来自天天基金公开数据，可用 `scripts/fetch_fund_data.py` 刷新。先看 `references/managers/{经理}/fund_data/_index.md` 了解有哪些基金、覆盖哪些季度。
- **全市场基金（扩展）** `references/all_funds/fund_list.json` —— 全市场约2.7万只基金的列表（代码/名称/类型/拼音），可检索、识别、按类型筛选。

**经理列表动态发现**：`scripts/managers_list.py` 在运行时扫描 `references/managers/`，并容忍 `corpus/media/copus`、`fund_data/funds_data` 等目录名变体。新增一位经理只需往 `references/managers/` 放好目录，所有脚本即自动识别，**无需改任何脚本**。

六位基金经理：

| 经理 | 公司 | 代表作 | 风格标签 |
|---|---|---|---|
| **张坤** | 易方达基金 | 易方达蓝筹精选(005827) | 价值投资·高质量成长·长期持有·集中持仓 |
| **谢治宇** | 兴证全球基金 | 兴全合润(163406) | 均衡成长·自下而上·行业分散·大类配置 |
| **高楠** | 永赢基金 | 永赢睿信(019431) | 胜率+赔率·前瞻布局·积木式组合·左侧投资 |
| **刘旭** | 大成基金 | 大成高鑫股票A(000628) | 低换手·高集中·深度价值·长期持有 |
| **张璐** | 永赢基金 | 永赢先进制造智选混合发起A(018124) | Beta大通道·聚焦高端制造/半导体 |
| **赵诣** | 泉果基金（原农银汇理） | 农银汇理研究精选混合(000336) | 长坡厚雪·高端制造成长·行业分散个股集中 |

---

> 💡 本仓库同时可作为 **MCP server** 运行：把语料检索、横向对比、框架评分、复用生成等能力以 MCP 工具（共 7 个）暴露给任意 MCP 客户端（Claude Desktop / Cursor / WorkBuddy 等）。
> 安装与客户端配置见 README「作为 MCP Server 运行」；本地等价 CLI：`python -m top_fund_managers_mcp <search|compare|score|generate|lookup|index>`。

### 运行脚本的方式

本 skill 的脚本都用绝对路径自己定位数据、并已自带输出上限，所以**调用时务必保持成一条最朴素的命令**：

- ✅ 正确：`python "<本skill目录>/scripts/search_corpus.py" "白酒" --manager 张坤`
- ❌ 不要用 `cd … && python …`
- ❌ 不要加 `2>/dev/null`、`| head`、`>` 等重定向或管道
- ❌ 不要用 `;` / `&&` 把多个命令串起来——**一次只跑一个脚本**

`<本skill目录>` 就是本 SKILL.md 所在的目录。用绝对路径，不要先 `cd` 进去。

---

### 怎么回答：自然为主，按问题来

核心就一句话：**先查，再说；说他说过的，就引原文标出处；说推演的，就讲清是按他的方法推的。**

#### 几类常见问法

- **"张坤怎么看 X / 他对 X 什么观点"** —— 用 `search_corpus.py --manager 张坤` 找原文，引用关键段落并自然点明来源；有演变就把不同年份串起来讲。
- **"谢治宇的投资方法 / 框架是什么"** —— 读 `references/managers/谢治宇/method.md` 作答。
- **"用高楠的思路看看 X"** —— 先查他有没有直接谈过；没有就用 method.md 的框架推演，首句加粗声明非他本人观点。
- **"张坤和谢治宇的投资方法有什么区别"** —— 读两人的 method.md，从选股逻辑、持仓风格、行业偏好、换手率、回撤控制等维度对比。
- **"六位经理谁更看好半导体 / 他们的方法有什么本质区别"** —— 用 `compare_managers.py topic 半导体` 或 `compare_managers.py method` 跨经理横向并列，引用各自原文与方法框架（Track B 整合能力）。
- **"他重仓了什么 / 业绩怎样 / 规模多大"** —— 读 `references/managers/{经理}/fund_data/`。
- **"用张坤的标准给 XX 基金打个分"** —— 用 `score_fund.py --manager 张坤`，读 `scorecard.md` 打分。

---

### 言行对照：把"说的"和"做的"对起来

1. 从语料拿到他对某方向的**表态**，再从 `fund_data/{基金}/季度持仓.md` 拿到**对应季度的真实持仓**，两相对照。
2. 业绩/规模/重仓问题直接读 `净值业绩规模.md`。
3. **务必只用他任职区间内的季度**：曾任基金的持仓数据覆盖了整只基金历史，包含别的经理任职的季度。
4. 持仓数据是**季度快照**（季报披露），不是实时；引用时带上季度和数据日期。

---

### 查全市场任意基金

1. **先定位代码**：`python scripts/fund_lookup.py 关键词`
2. **再抓明细**：`python scripts/fetch_any_fund.py <代码>`
3. **对比场景**：把对方代码抓下来，和三位经理的基金数据并列分析。

---

### 给基金打分

1. `python scripts/score_fund.py <代码或名称> --manager <张坤|谢治宇|高楠|刘旭|张璐|赵诣>`
2. 读 `references/managers/{经理}/scorecard.md`，用评分卡逐项给分。
3. **守住定位**：衡量的是"与某经理投资风格的契合度"，不是基金好坏的绝对评判。

---

### 关键：语料里没有这个话题怎么办

1. 先检索，确认语料里确实没有他对该话题的直接表态；
2. **回答的第一句话就要加粗声明这不是他的原话**；
3. 再用 `method.md` 的框架去推演；
4. 推演里用到的、当前没把握的具体事实标"需核实"。

---

### 引用与诚实（底线）

- **引用要忠于原文**：引他的话，必须和 corpus 里的文字一致，不改写、不缩写后当原话。
- **出处要自然**：比如"他在2025年年报里写道""在2025年4月中国投资人峰会上他说"。**不要把内部记号写进回答**。
- **分清三种话**：①他的原话（忠实引用+自然出处）②按他方法的推演③需核实的事实。
- **不杜撰**：编造他没说过的话、或凭空捏造持仓/业绩/目标价，是最大的禁区。

---

### 边界

研究与学习辅助，不构成投资建议，不预测涨跌、不给买卖指令、不承诺收益。
