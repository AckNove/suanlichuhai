# -*- coding: utf-8 -*-
"""CCGS 确定性供需匹配引擎（0–100 分，8 维可解释评分）。

严格按 docs/07_ai_system/SPEC_API.md 第 3 节：
- GPU 型号 30 / 规模 20 / 负载 15 / 地点 10 / 交付 10 / 网络 5 / 合规 5 / 信任 5
- recommendation：>=70 ADVANCE；40–69 NEED_MORE_INFO；<40 REJECT
- 命中红线（无合法转售权 / 未筛查跨境合规 / 数据驻留冲突）→ 总分封顶 39

引擎是确定性的（同一输入同一输出），不调用 LLM、不随机、不外发。
"""
from __future__ import annotations

import json
import math
import re

DIMENSION_MAX = {
    "gpu_model": 30,
    "scale": 20,
    "workload": 15,
    "location": 10,
    "delivery": 10,
    "network": 5,
    "compliance": 5,
    "trust": 5,
}

# GPU 型号归一化：把各家口径统一到简短型号
GPU_ALIASES = {
    "H100SXM": "H100", "H100SXM5": "H100", "H100PCIE": "H100", "H100NVL": "H100",
    "H200SXM": "H200", "H200NVL": "H200",
    "H800SXM": "H800", "H800PCIE": "H800",
    "A100SXM": "A100", "A100PCIE": "A100", "A10080G": "A100", "A10040G": "A100",
    "A800SXM": "A800", "A800PCIE": "A800",
    "B200SXM": "B200", "GB200": "B200", "B100": "B100",
    "昇腾910B": "910B", "ASCEND910B": "910B", "910B": "910B",
    "昇腾910C": "910C", "ASCEND910C": "910C", "910C": "910C",
    "思元590": "590", "MLU590": "590", "寒武纪590": "590",
    "RTX4090": "4090", "4090": "4090",
    "RTX3090": "3090", "3090": "3090",
    "H20": "H20",
}

GPU_GROUPS = {
    "H100": "hopper", "H200": "hopper", "H800": "hopper", "H20": "hopper",
    "B200": "blackwell", "B100": "blackwell",
    "A100": "ampere80", "A800": "ampere80",
    "910B": "ascend", "910C": "ascend",
    "590": "cambricon",
    "4090": "consumer", "3090": "consumer",
}

# 明确可替代（不同代际/不同体系但常见迁移路径）
ALT_PAIRS = [
    frozenset(("A100", "H100")),
    frozenset(("A800", "H800")),
    frozenset(("A100", "910B")),
    frozenset(("A800", "910B")),
    frozenset(("A100", "590")),
    frozenset(("H100", "B200")),
]

DATACENTER_GPUS = {"H100", "H200", "H800", "H20", "B200", "B100", "A100", "A800", "910B", "910C", "590"}

COUNTRY_REGION = {
    "中国": "东亚", "中国大陆": "东亚", "香港": "东亚", "澳门": "东亚", "台湾": "东亚",
    "日本": "东亚", "韩国": "东亚",
    "新加坡": "东南亚", "马来西亚": "东南亚", "印度尼西亚": "东南亚", "印尼": "东南亚",
    "泰国": "东南亚", "越南": "东南亚", "菲律宾": "东南亚", "柬埔寨": "东南亚", "老挝": "东南亚",
    "缅甸": "东南亚", "文莱": "东南亚",
    "印度": "南亚", "巴基斯坦": "南亚", "孟加拉国": "南亚",
    "沙特": "中东", "沙特阿拉伯": "中东", "阿联酋": "中东", "卡塔尔": "中东",
    "阿曼": "中东", "科威特": "中东", "巴林": "中东", "以色列": "中东", "土耳其": "中东",
    "美国": "北美", "加拿大": "北美", "墨西哥": "北美",
    "英国": "欧洲", "德国": "欧洲", "法国": "欧洲", "荷兰": "欧洲", "爱尔兰": "欧洲",
    "西班牙": "欧洲", "意大利": "欧洲", "波兰": "欧洲", "瑞典": "欧洲", "瑞士": "欧洲",
    "澳大利亚": "大洋洲", "新西兰": "大洋洲",
    "巴西": "南美", "阿根廷": "南美", "智利": "南美",
    "南非": "非洲", "尼日利亚": "非洲", "肯尼亚": "非洲", "埃及": "非洲",
}
KNOWN_COUNTRIES = sorted(COUNTRY_REGION.keys(), key=len, reverse=True)

CROSS_BORDER_SCREENED_KEYWORDS = ["已筛查", "已做合规", "合规筛查通过", "已评估跨境", "律师意见",
                                  "已完成合规", "已通过合规", "compliance_screened"]
COMPLIANCE_RED_KEYWORDS = ["红线", "禁止", "制裁", "受限", "违法", "不允许", "出口管制禁止"]

DIM_LABELS = {
    "gpu_model": "GPU 型号",
    "scale": "规模",
    "workload": "负载能力",
    "location": "地点/数据驻留",
    "delivery": "交付周期",
    "network": "网络",
    "compliance": "合规",
    "trust": "信任/核验",
}


def normalize_gpu(text) -> list:
    """解析卡型文本为归一化型号列表。"""
    if not text:
        return []
    raw = str(text).upper().replace("NVIDIA", " ").replace("TESLA", " ")
    parts = re.split(r"[,，、;；/\s]+", raw)
    out = []
    for part in parts:
        token = part.strip().replace("-", "").replace("_", "")
        if not token:
            continue
        token = GPU_ALIASES.get(token, token)
        # 处理 "H100SXM" 类粘连写法
        if token not in GPU_GROUPS:
            for alias, norm in GPU_ALIASES.items():
                if token.startswith(alias):
                    token = norm
                    break
        if token in GPU_GROUPS or re.match(r"^(H|A)\d{2,3}$", token):
            if token not in out:
                out.append(token)
    return out


def _gpu_dimension(demand: dict, supply: dict) -> dict:
    wanted = normalize_gpu(demand.get("gpu_models"))
    offered = normalize_gpu(supply.get("gpu_model"))
    if not wanted and not offered:
        return _dim("gpu_model", 5, "需求与供给均未明确 GPU 型号，无法判断兼容性（保守计分）")
    if not wanted:
        return _dim("gpu_model", 5, "需求未明确 GPU 型号，仅能按供给型号记录")
    if not offered:
        return _dim("gpu_model", 3, "供给未披露 GPU 型号，需供应商澄清")

    best = 0
    best_reason = ""
    for w in wanted:
        for o in offered:
            if w == o:
                score, reason = 30, "精确匹配：需求 %s 与供给 %s 一致" % (w, o)
            elif GPU_GROUPS.get(w) == GPU_GROUPS.get(o) and GPU_GROUPS.get(w) is not None:
                score, reason = 20, "同代/同级别：%s 与 %s 同属 %s 系列" % (w, o, GPU_GROUPS.get(w))
            elif frozenset((w, o)) in ALT_PAIRS:
                score, reason = 10, "可替代：%s 与 %s 属常见迁移路径（需实测兼容）" % (w, o)
            elif w in DATACENTER_GPUS and o in DATACENTER_GPUS:
                score, reason = 10, "可替代（不同代际/体系）：%s ↔ %s，需验证软件栈与性能" % (w, o)
            else:
                score, reason = 0, "不兼容：需求 %s，供给 %s" % (w, o)
            if score > best:
                best, best_reason = score, reason
    return _dim("gpu_model", best, best_reason)


def _dim(name: str, score, reason: str) -> dict:
    return {"score": round(float(score), 1), "max": DIMENSION_MAX[name], "reason": reason}


def _scale_dimension(demand: dict, supply: dict) -> dict:
    min_count = _as_int(demand.get("min_gpu_count"))
    supply_count = _as_int(supply.get("sellable_gpu_count")) or _as_int(supply.get("gpu_count"))
    if not min_count:
        return _dim("scale", 10, "需求未给出最小 GPU 规模，无法完整评估")
    if not supply_count:
        return _dim("scale", 5, "供给未披露可售 GPU 数量")
    if supply_count >= min_count:
        return _dim("scale", 20, "可售 %d 卡 ≥ 需求最小 %d 卡" % (supply_count, min_count))
    deficit = (min_count - supply_count) / float(min_count)
    penalty = int(math.ceil(deficit / 0.1)) * 2
    score = max(0, 20 - penalty)
    return _dim("scale", score, "可售 %d 卡 < 需求最小 %d 卡，缺口约 %d%%，按每 10%% 扣 2 分"
                % (supply_count, min_count, int(round(deficit * 100))))


def _workload_dimension(demand: dict, supply: dict) -> dict:
    wt = (demand.get("workload_type") or "").upper()
    training = bool(_as_int(supply.get("training_capable")))
    inference = bool(_as_int(supply.get("inference_capable")))
    if wt in ("TRAINING", "FINETUNE"):
        if training:
            return _dim("workload", 15, "训练/微调需求，供给标注 training_capable=1")
        return _dim("workload", 0, "训练/微调需求，但供给未标注训练能力")
    if wt == "INFERENCE":
        if inference:
            return _dim("workload", 15, "推理需求，供给标注 inference_capable=1")
        return _dim("workload", 0, "推理需求，但供给未标注推理能力")
    if wt == "MIXED":
        if training and inference:
            return _dim("workload", 15, "混合负载需求，供给同时支持训练与推理")
        if training or inference:
            return _dim("workload", 7, "混合负载需求，供给仅标注单一能力")
        return _dim("workload", 0, "混合负载需求，供给未标注训练/推理能力")
    if wt in ("RENDERING", "SIMULATION"):
        if training or inference:
            return _dim("workload", 8, "渲染/仿真负载，按通用 GPU 能力估算")
        return _dim("workload", 0, "渲染/仿真负载，供给未标注 GPU 能力")
    if training or inference:
        return _dim("workload", 5, "需求负载类型未知，按供给声明能力保守计分")
    return _dim("workload", 0, "需求负载类型未知且供给未标注能力")


def _location_dimension(demand: dict, supply: dict):
    """返回 (dimension, red_line_or_None)。"""
    country = (supply.get("location_country") or "").strip()
    demand_country = (demand.get("company_country") or "").strip()
    preference = (demand.get("location_preference") or "").strip()
    region = COUNTRY_REGION.get(country)
    demand_region = COUNTRY_REGION.get(demand_country)

    # 数据驻留冲突（红线）
    residency = (demand.get("data_residency") or "").strip()
    if residency and country:
        mentioned = [c for c in KNOWN_COUNTRIES if c in residency]
        if mentioned:
            if country not in mentioned and not any(
                COUNTRY_REGION.get(m) == region for m in mentioned
            ):
                reason = "数据驻留冲突：需求要求驻留 %s，供给位于 %s" % ("/".join(mentioned), country)
                return _dim("location", 0, reason), reason
        elif any(k in residency for k in ("境内", "本地", "中国")):
            if country not in ("中国", "中国大陆"):
                reason = "数据驻留冲突：需求要求数据留在境内/中国，供给位于 %s" % country
                return _dim("location", 0, reason), reason

    if not country:
        return _dim("location", 4, "供给地点未知，待供应商澄清"), None
    if demand_country and country == demand_country:
        return _dim("location", 10, "国家匹配：%s" % country), None
    if preference and country in preference:
        return _dim("location", 10, "供给国家出现在需求地点偏好中：%s" % country), None
    if region and (
        (preference and region in preference)
        or (demand_region and region == demand_region)
    ):
        return _dim("location", 6, "区域匹配：%s 属 %s" % (country, region)), None
    if preference or demand_country:
        return _dim("location", 2, "地点不一致：供给 %s，需求 %s"
                    % (country, demand_country or preference)), None
    return _dim("location", 4, "需求未明确地点偏好，供给位于 %s" % country), None


_WINDOW_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(个月|月|周|星期|天|日|weeks?|months?|days?|week|month|day)", re.IGNORECASE
)


def _parse_days(text):
    if not text:
        return None
    matches = _WINDOW_RE.findall(str(text))
    if not matches:
        return None
    best = None
    for value, unit in matches:
        n = float(value)
        u = unit.lower()
        if u in ("个月", "月", "month", "months"):
            days = n * 30
        elif u in ("周", "星期", "week", "weeks"):
            days = n * 7
        else:
            days = n
        if best is None or days < best:
            best = days
    return best


def _delivery_dimension(demand: dict, supply: dict) -> dict:
    need = _parse_days(demand.get("timeline"))
    lead = _parse_days(supply.get("delivery_lead_time"))
    if need is None:
        return _dim("delivery", 5, "需求时间窗未明确，无法判断交付周期")
    if lead is None:
        return _dim("delivery", 5, "供给未披露交付周期")
    if lead <= need:
        return _dim("delivery", 10, "交付周期约 %d 天 ≤ 需求时间窗约 %d 天" % (lead, need))
    return _dim("delivery", 0, "交付周期约 %d 天 > 需求时间窗约 %d 天（明显超期）" % (lead, need))


def _network_dimension(demand: dict, supply: dict) -> dict:
    parts = [supply.get("network_bandwidth"), supply.get("interconnect"),
             supply.get("cluster_topology")]
    if any(str(p or "").strip() for p in parts):
        detail = "；".join(str(p).strip() for p in parts if str(p or "").strip())
        return _dim("network", 5, "有互联/带宽描述：%s" % detail[:80])
    return _dim("network", 2, "网络/互联信息未知，需补充带宽与拓扑")


def _compliance_dimension(demand: dict, supply: dict, cross_border: bool, compliance_screened: bool):
    notes = str(demand.get("compliance_notes") or "")
    lowered = notes.lower()
    if cross_border and not compliance_screened and not any(k in notes for k in CROSS_BORDER_SCREENED_KEYWORDS):
        reason = "跨境合规未筛查（红线）：需求方与供给位于不同国家/地区，尚无合规筛查记录"
        return _dim("compliance", 0, reason), reason
    if any(k in lowered or k in notes for k in COMPLIANCE_RED_KEYWORDS):
        reason = "合规红线命中：需求方合规备注包含禁止/受限/制裁类表述"
        return _dim("compliance", 0, reason), reason
    if compliance_screened or any(k in notes for k in CROSS_BORDER_SCREENED_KEYWORDS):
        return _dim("compliance", 5, "跨境合规已筛查（或存在筛查记录）"), None
    return _dim("compliance", 2, "合规尚未筛查，按未筛查计 2 分"), None


def _trust_dimension(supply: dict) -> dict:
    if _as_int(supply.get("verified")) == 1:
        return _dim("trust", 5, "供给记录已核验（verified=1）")
    status = (supply.get("status") or "").upper()
    if status in ("VERIFIED", "QUALIFIED", "ACTIVE"):
        return _dim("trust", 5, "供应商状态 %s" % status)
    if status == "NEEDS_VERIFICATION":
        return _dim("trust", 3, "供应商处于待核验阶段")
    if status == "RESEARCHED":
        return _dim("trust", 2, "供应商仅完成案头研究")
    return _dim("trust", 1, "供应商/资源仍为公开线索（LEAD），未核验")


def _as_int(value):
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _confidence(total: float, red_lines: list, demand: dict, supply: dict) -> str:
    if red_lines:
        return "LOW"
    key_fields = [
        bool(normalize_gpu(demand.get("gpu_models"))),
        bool(_as_int(demand.get("min_gpu_count"))),
        bool((supply.get("location_country") or "").strip()),
        bool(normalize_gpu(supply.get("gpu_model"))),
        bool(_as_int(supply.get("sellable_gpu_count")) or _as_int(supply.get("gpu_count"))),
    ]
    completeness = sum(1 for f in key_fields if f) / float(len(key_fields))
    if total >= 70 and completeness >= 0.8:
        return "HIGH"
    if completeness >= 0.4:
        return "MEDIUM"
    return "LOW"


def _recommendation(total: float) -> str:
    if total >= 70:
        return "ADVANCE"
    if total >= 40:
        return "NEED_MORE_INFO"
    return "REJECT"


def score_pair(demand: dict, supply: dict, conn=None) -> dict:
    """对一组需求/供给评分。

    demand 需含 demand_opportunities 字段（可选 company_country / company_region）；
    supply 需含 compute_supply_resources 字段。
    conn 可选：用于查询 supplier_verification（转售权红线）与 demand_qualification（合规筛查）。
    """
    demand = demand or {}
    supply = supply or {}
    red_lines = []

    dims = {}
    dims["gpu_model"] = _gpu_dimension(demand, supply)
    dims["scale"] = _scale_dimension(demand, supply)
    dims["workload"] = _workload_dimension(demand, supply)

    location_dim, residency_red = _location_dimension(demand, supply)
    dims["location"] = location_dim
    if residency_red:
        red_lines.append(residency_red)

    dims["delivery"] = _delivery_dimension(demand, supply)
    dims["network"] = _network_dimension(demand, supply)

    supply_country = (supply.get("location_country") or "").strip()
    demand_country = (demand.get("company_country") or "").strip()
    cross_border = bool(supply_country and demand_country and supply_country != demand_country)
    compliance_screened = False
    if conn is not None:
        if demand.get("id"):
            try:
                row = conn.execute(
                    "SELECT 1 FROM demand_qualification WHERE demand_id=? AND compliance_screened=1 LIMIT 1",
                    (demand.get("id"),),
                ).fetchone()
                compliance_screened = row is not None
            except Exception:
                compliance_screened = False
    if demand.get("compliance_screened"):
        compliance_screened = True
    compliance_dim, compliance_red = _compliance_dimension(
        demand, supply, cross_border, compliance_screened)
    dims["compliance"] = compliance_dim
    if compliance_red:
        red_lines.append(compliance_red)

    dims["trust"] = _trust_dimension(supply)

    # 供应商转售权红线（有核验记录且明确无转售权）
    if conn is not None and supply.get("company_id"):
        try:
            row = conn.execute(
                "SELECT resale_right_ok FROM supplier_verification WHERE supplier_company_id=? "
                "ORDER BY updated_at DESC LIMIT 1", (supply.get("company_id"),),
            ).fetchone()
            if row is not None and row["resale_right_ok"] == 0:
                reason = "无合法转售权（红线）：供应商核验记录 resale_right_ok=0"
                red_lines.append(reason)
                dims["trust"] = _dim("trust", 0, "供应商核验记录显示无权转售该算力")
        except Exception:
            pass

    total = round(sum(d["score"] for d in dims.values()), 1)
    if red_lines:
        total = min(total, 39.0)

    positive = []
    negative = []
    for name, dim in dims.items():
        ratio = dim["score"] / float(dim["max"]) if dim["max"] else 0
        if ratio >= 0.7:
            positive.append("%s %s/%s：%s" % (DIM_LABELS[name], dim["score"], dim["max"], dim["reason"]))
        elif ratio < 0.5:
            negative.append("%s %s/%s：%s" % (DIM_LABELS[name], dim["score"], dim["max"], dim["reason"]))

    if positive:
        why_match = "；".join(positive)
    elif dims:
        why_match = "暂无显著匹配优势，各维度得分偏低，仅作为待澄清线索"
    else:
        why_match = "无可用匹配信息"

    if red_lines:
        why_not_match = "命中红线，总分封顶 39：" + "；".join(red_lines)
        if negative:
            why_not_match += "。其他弱项：" + "；".join(negative)
    elif negative:
        why_not_match = "；".join(negative)
    else:
        why_not_match = "未发现明显不匹配项；但证据与合规仍需人工核验，匹配结果仅为内部候选，不得外发或视为承诺"

    confidence = _confidence(total, red_lines, demand, supply)
    recommendation = _recommendation(total)
    result = {
        "score": total,
        "dimensions": dims,
        "why_match": why_match,
        "why_not_match": why_not_match,
        "confidence": confidence,
        "recommendation": recommendation,
        "red_lines": red_lines,
        "risks": "；".join(red_lines) if red_lines else "",
    }
    return result


def score_match(demand: dict, supply: dict, conn=None) -> dict:
    """兼容 agents/runner.py 的后端评分适配入口（等价于 score_pair）。"""
    return score_pair(demand, supply, conn=conn)


def score(demand: dict, supply: dict, conn=None) -> dict:
    return score_pair(demand, supply, conn=conn)


def score_many(demand: dict, supplies: list, conn=None) -> list:
    """批量评分并按分数降序（同分按 supply_id 升序，保证确定性）。"""
    results = []
    for supply in supplies or []:
        scored = score_pair(demand, supply, conn=conn)
        scored["demand_id"] = demand.get("id")
        scored["supply_id"] = supply.get("id")
        results.append(scored)
    results.sort(key=lambda r: (-float(r["score"]), str(r.get("supply_id") or "")))
    return results


def dimensions_json(result: dict) -> str:
    return json.dumps(result.get("dimensions") or {}, ensure_ascii=False)
