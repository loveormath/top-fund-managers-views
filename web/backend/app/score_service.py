import json
import re
from pathlib import Path


CONTAINER_REF_DIR = Path("/app/references")

if CONTAINER_REF_DIR.exists():
    REFERENCES_DIR = CONTAINER_REF_DIR
else:
    REFERENCES_DIR = Path(__file__).resolve().parent.parent.parent / "references"


def find_fund_code(keyword):
    fund_list_file = REFERENCES_DIR / "all_funds" / "fund_list.json"
    if not fund_list_file.exists():
        return None

    with open(fund_list_file, "r", encoding="utf-8") as f:
        funds = json.load(f)

    keyword_lower = keyword.lower()
    for fund in funds:
        if (keyword_lower in fund.get("code", "").lower()
                or keyword_lower in fund.get("name", "").lower()
                or keyword_lower in fund.get("pinyin", "").lower()):
            return fund
    return None


def load_fund_data(fund_dir):
    holdings_file = fund_dir / "季度持仓.md"
    perf_file = fund_dir / "净值业绩规模.md"

    data = {"holdings": "", "performance": ""}
    if holdings_file.exists():
        data["holdings"] = holdings_file.read_text(encoding="utf-8")
    if perf_file.exists():
        data["performance"] = perf_file.read_text(encoding="utf-8")
    return data


def analyze_concentration(holdings_text):
    ratio_pattern = re.findall(r'\|\s*\d+\s*\|\s*\S+\s*\|\s*\S+\s*\|\s*([\d.]+)\s*\|', holdings_text)
    if ratio_pattern:
        return sum(float(r) for r in ratio_pattern[:10])
    return None


def generate_fund_prompt_service(fund_input: str, manager: str, registry_state) -> dict:
    if fund_input.isdigit() and len(fund_input) == 6:
        fund_code = fund_input
        fund_name = "待查"
    else:
        fund_info = find_fund_code(fund_input)
        if fund_info:
            fund_code = fund_info["code"]
            fund_name = fund_info["name"]
        else:
            return {"success": False, "error": f"未找到匹配 '{fund_input}' 的基金。"}
    mgr_public = registry_state.public(manager)
    manager_chinese_name = getattr(mgr_public, "name", manager)
    representative = "未配置"
    representative_funds = getattr(mgr_public, "representative_funds", None)

    if representative_funds and len(representative_funds) > 0:
        rep_fund = representative_funds[0]
        rep_code = ""
        rep_name = ""
        try:
            if isinstance(rep_fund, dict):
                rep_code = rep_fund.get("code", "")
                rep_name = rep_fund.get("name", "")
            else:
                rep_code = getattr(rep_fund, "code", "")
                rep_name = getattr(rep_fund, "name", "")
        except Exception:
            pass

        if rep_code or rep_name:
            representative = f"{rep_code}_{rep_name}"
    mgr_fund_dir = REFERENCES_DIR / "managers" / manager_chinese_name / "fund_data"
    target_fund_dir = None

    for d in mgr_fund_dir.iterdir() if mgr_fund_dir.exists() else []:
        if d.is_dir() and fund_code in d.name:
            target_fund_dir = d
            break

    if not target_fund_dir:
        cache_dir = REFERENCES_DIR / "fund_data_cache"
        for d in cache_dir.iterdir() if cache_dir.exists() else []:
            if fund_code in d.name:
                target_fund_dir = d
                break

    if not target_fund_dir:
        return {
            "success": False,
            "error": f"本地未找到基金数据，请先确保 references 目录中存在该基金数据文件夹（代码：{fund_code}）。"
        }

    fund_data = load_fund_data(target_fund_dir)
    concentration_str = "未知"
    if fund_data.get("holdings"):
        concentration = analyze_concentration(fund_data["holdings"])
        if concentration:
            concentration_str = f"{concentration:.2f}%"

    scorecard_file = REFERENCES_DIR / "managers" / manager_chinese_name / "scorecard.md"
    scorecard_content = scorecard_file.read_text(encoding="utf-8") if scorecard_file.exists() else "（未配置评分卡指引）"
    full_prompt = f"""你现在是选定的基金经理专家审查员。
请严格基于以下提供的新基金本地机械指标与提取出的数据，并对照专属的六维评分卡规则，进行风格契合度审计。

【基本信息】
- 基金代码：{fund_code}
- 基金名称：{fund_name}
- 拟审查框架：{manager_chinese_name}
- 框架代表参考基金：{representative}

=== 📊 提取出的机械指标与数据 ===
- 前十大持仓集中度：{concentration_str}

[季度持仓明细]
{fund_data.get('holdings', '暂无持仓数据')}

[净值业绩与规模走势]
{fund_data.get('performance', '暂无业绩数据')}

=== 🎯 专属六维评分卡打分指引 (Scorecard) ===
{scorecard_content}

---
### 🔍 你的分析任务：
请读取上述评分卡，按六维评分卡逐项对该基金进行深度契合度分析并给出最终打分。
注意：这套分衡量的是“与 {manager_chinese_name} 投资风格的契合度”，不是基金好坏的绝对评判。请保持客观与严厉。"""

    return {
        "success": True,
        "fund_code": fund_code,
        "fund_name": fund_name,
        "prompt": full_prompt
    }