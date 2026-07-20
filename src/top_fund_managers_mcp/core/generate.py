# -*- coding: utf-8 -*-
"""复用性引擎（Track C：传入大V ID/链接，自动生成 Skill 骨架）。

给定一位投资大V（基金经理或其他公开投资人）的身份信息，按统一标准结构
一键生成可直接填充的 Skill 骨架。因经理列表由 managers 动态发现，生成新
经理目录后，所有工具自动识别，无需改动任何脚本。
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from ..config import MANAGERS_DIR


def _method_template(name, company, style):
    return f"""# {name}投资方法框架

> 从语料蒸馏出的方法框架，每一条用 {name} 本人原话佐证。
> 语料未直接谈论的话题，可用本框架推演，但须声明非本人原话。

## 1. 选股逻辑
- **核心表述**：TODO（用一句话概括其选股哲学）
- **原话佐证**：
  > "TODO（粘贴 {name} 本人原话，标注出处与年份）"

## 2. 行业偏好
- **偏好方向**：TODO
- **回避方向**：TODO
- **原话佐证**：
  > "TODO"

## 3. 仓位与集中度策略
- **仓位哲学**：TODO（集中 / 分散 / 动态）
- **原话佐证**：
  > "TODO"

## 4. 风险控制
- **回撤应对**：TODO
- **原话佐证**：
  > "TODO"

## 5. 估值方法
- **估值体系**：TODO（PE/PB/DCF/自由现金流…）
- **原话佐证**：
  > "TODO"

## 6. 退出标准
- **卖出条件**：TODO
- **原话佐证**：
  > "TODO"

---
*骨架由 generate_skill.py（Track C 复用性引擎）生成，待 Agent/人工填充语料与原话。*
"""


def _scorecard_template(name):
    return f"""# {name}框架评分卡

> 用 {name} 的投资方法给任意基金打分，衡量“与 {name} 投资风格的契合度”。

## 六维评分

| 维度 | 权重 | 评分依据 |
|---|---|---|
| 1. 选股逻辑契合 | 20分 | TODO：按 {name} 的选股标准评估 |
| 2. 行业偏好契合 | 20分 | 行业分布是否贴合其偏好 |
| 3. 仓位/集中度 | 15分 | 集中度是否符合其风格（集中/分散） |
| 4. 估值合理性 | 15分 | 重仓股估值是否在其估值框架内 |
| 5. 风险控制 | 15分 | 波动/回撤控制是否契合 |
| 6. 业绩印证 | 15分 | 长期业绩是否跑赢基准 |

## 评级标准

| 总分 | 评级 | 含义 |
|---|---|---|
| 80-100 | 高度契合 | 非常像 {name} 会买的基金 |
| 60-79 | 较为契合 | 有部分 {name} 风格特征 |
| 40-59 | 一般 | 风格中性，部分维度契合 |
| 20-39 | 不太契合 | 风格偏离较大 |
| 0-19 | 不契合 | 风格几乎相反 |

## 打分流程

1. 运行 `python -m top_fund_managers_mcp score <代码或名称> --manager {name}`
2. 脚本自动备好数据（funds_data/ 快照优先）
3. 按上表六维逐项给分
4. 给总分、评级、理由

## 重要提醒

- 这套分衡量的是“**与 {name} 投资风格的契合度**”，不是基金好坏的绝对评判
- 个股基本面数据无数据项标“需核实”
"""


def _intro_template(name, company, style):
    return f"""# {name}简介

## 基本信息

- **姓名**：{name}
- **公司**：{company or "TODO"}
- **管理规模**：TODO（截至最新数据）
- **代表基金**：TODO
- **任职起始**：TODO

## 投资风格标签

{style or "TODO（如：均衡价值·长期持有·大盘蓝筹）"}

## 职业履历

TODO（从公开资料整理）

## 投资方法概要

- **核心理念**：TODO
- **选股方法**：TODO
- **持仓风格**：TODO
- **行业偏好**：TODO
- **核心观点**：TODO

## 代表基金

| 基金名称 | 代码 | 任职日期 | 任职回报 |
|---|---|---|---|
| TODO | TODO | TODO | TODO |

## 数据来源

- TODO（官网 / 天天基金 / 媒体报道链接）
"""


def _profile_template(name, company):
    return f"""# {name} · 公开档案

> 由 generate_skill.py 生成的档案骨架，待补全。

- 公司：{company or "TODO"}
- 代表基金：TODO
- 管理规模：TODO
- 公开发言渠道：TODO（雪球 / 微博 / 公众号 / 官网）
"""


def _fund_list_template(title):
    return f"""# {title}

> 数据来源：TODO（基金公司官网 / 天天基金网）
> 抓取时间：{datetime.now().strftime('%Y-%m-%d')}

| 基金代码 | 基金名称 | 任职日期 | 任职回报 | 备注 |
|---|---|---|---|---|
| TODO | TODO | TODO | TODO | TODO |
"""


def _index_md_template(name):
    return f"""# {name} · 基金数据索引

> 本目录存放 {name} 各代表基金的真实数据快照（对齐新结构）。
> - `funds_data/`：每季前十大重仓股 + 净值/业绩/规模快照（基金N：code_名称/）。
> - `funds/`：定期报告原文归档（code_名称/reports/YYYY…md）。
> 用 `scripts/fetch_fund_data.py` 刷新，或用 `scripts/fetch_any_fund.py <代码>` 抓取对比基金。

## 已收录基金

| 文件夹 | 内容 |
|---|---|
| TODO_基金名 | 净值业绩规模.md + 季度持仓.md |

## 季度覆盖

TODO（列出已覆盖的季度，如 2024Q4 / 2025Q1 / 2025Q2 / 2025Q3）
"""


def build_skeleton(name, company=None, style=None, representative=None,
                   source=None, dry_run=False):
    """生成经理 Skill 骨架目录与文件（对齐新结构）。返回结果字符串。"""
    mgr_dir = MANAGERS_DIR / name
    if mgr_dir.exists() and any(mgr_dir.iterdir()):
        return (f"[跳过] 经理目录已存在且非空：{mgr_dir}\n"
                "       如需重建，请先手动备份/删除该目录。")

    if dry_run:
        msg = f"[dry-run] 将创建骨架：{mgr_dir}\n"
    else:
        # corpus 子目录（对齐新结构）
        for sub in ("简介.md", "管理基金_在任.md", "管理基金_曾任.md",
                    "基金经理手记", "媒体报道", "定期报告", "直播"):
            p = mgr_dir / "corpus" / sub
            if sub.endswith(".md"):
                p.write_text(_intro_template(name, company, style), encoding="utf-8")
            else:
                p.mkdir(parents=True, exist_ok=True)
                (p / ".gitkeep").write_text("", encoding="utf-8")
        (mgr_dir / "method.md").write_text(_method_template(name, company, style), encoding="utf-8")
        (mgr_dir / "scorecard.md").write_text(_scorecard_template(name), encoding="utf-8")
        (mgr_dir / "profile.md").write_text(_profile_template(name, company), encoding="utf-8")
        (mgr_dir / "corpus_index.json").write_text(
            json.dumps({
                "manager": name,
                "updated": datetime.now().strftime("%Y-%m-%d"),
                "documents": [
                    {"type": "其他", "title": f"{name}简介", "path": "简介.md"},
                    {"type": "其他", "title": f"{name} · 在任基金", "path": "管理基金_在任.md"},
                    {"type": "其他", "title": f"{name} · 曾任基金", "path": "管理基金_曾任.md"},
                ],
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        fd = mgr_dir / "funds_data"
        fd.mkdir(parents=True, exist_ok=True)
        (fd / "_index.md").write_text(_index_md_template(name), encoding="utf-8")
        (fd / "_index.json").write_text(
            json.dumps({"manager": name, "updated": datetime.now().strftime("%Y-%m-%d"),
                       "funds": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (fd / "管理过的基金一览.md").write_text(
            _fund_list_template(f"{name} · 管理过的基金一览"), encoding="utf-8")
        (mgr_dir / "funds").mkdir(parents=True, exist_ok=True)
        (mgr_dir / "funds" / ".gitkeep").write_text("", encoding="utf-8")
        msg = f"[完成] {name} 的 Skill 骨架已生成（对齐新结构，动态注册无需改脚本）。\n"

    # 导入本地语料素材
    if source:
        src = Path(source)
        if src.exists() and src.is_dir():
            dst = mgr_dir / "corpus" / "媒体报道"
            if not dry_run:
                dst.mkdir(parents=True, exist_ok=True)
            count = 0
            for f in src.rglob("*"):
                if f.suffix.lower() in (".md", ".txt", ".markdown"):
                    if not dry_run:
                        shutil.copy(f, dst / f.name)
                    count += 1
            msg += f"[素材] 已从 {src} 导入 {count} 个语料文件到 corpus/媒体报道/\n"
        else:
            msg += f"[警告] --source 路径不存在或非目录：{source}（已忽略）\n"

    return msg


def research_checklist(name, source):
    return f"""
============================================================
下一步：完成 {name} 的「采集 + 蒸馏」（Agent 驱动）
============================================================
1. [采集] 从公开渠道收集原话语料，放入：
     references/managers/{name}/corpus/定期报告/  （季报/中报/年报投资运作分析）
     references/managers/{name}/corpus/媒体报道/  （采访/演讲/公开报道）
     references/managers/{name}/corpus/基金经理手记/  （手记/公开信）
     references/managers/{name}/corpus/直播/  （直播/路演文字稿）
2. [蒸馏] 通读语料，把每条方法论填进 method.md，并附本人原话佐证
3. [数据] 用 scripts/fetch_fund_data.py 抓取代表基金真实数据到 funds_data/
4. [评分] 按该经理风格细化 scorecard.md 六维权重与依据
5. [索引] 跑 `python -m top_fund_managers_mcp index` 重建 corpus_index.json
6. [校验] 用 `search "关键词" --manager {name}` 验证可检索
============================================================
提示：采集可借助 雪球/微博/公众号 ID 或官网链接 + 搜索工具完成。
"""
