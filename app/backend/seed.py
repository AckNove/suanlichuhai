# -*- coding: utf-8 -*-
"""CCGS 种子数据装载（幂等：确定性 ID + INSERT OR IGNORE，已有数据不重复插入）。

数据来源：
- docs/handover-20261113/B-中国算力出海/01-供应侧档案/registry.csv → 18 家 SUPPLIER + 18 条供给资源
- docs/handover-20261113/B-中国算力出海/02-海外需求侧档案/registry.csv → 9 家 DEMANDER + 9 条需求
- docs/handover-20261113/B-中国算力出海/03-匹配与解释/registry.csv → 3 条历史匹配样例（DRAFT）
- docs/handover-20261113/B-中国算力出海/05-市场与竞争/证据表.md → ≥10 条证据
- app/data/seed/specs.csv / agent_tasks.csv / approvals.csv / knowledge.csv → 演示数据

所有种子记录在 notes 中标 seed:history-import / seed:demo。
历史线索一律 LEAD + PUBLIC_LEAD + verified=0；历史状态、历史模拟分只写 notes/字段说明，不升级正式状态。
"""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

from . import db

ROOT = db.ROOT
BUSINESS_DIR = ROOT / "docs" / "handover-20261113" / "B-中国算力出海"
SEED_DIR = ROOT / "app" / "data" / "seed"
SEED_DEMO_TOKEN = "seed:demo"
SEED_HISTORY_TOKEN = "seed:history-import"

SUPPLY_REGISTRY = BUSINESS_DIR / "01-供应侧档案" / "registry.csv"
DEMAND_REGISTRY = BUSINESS_DIR / "02-海外需求侧档案" / "registry.csv"
MATCH_REGISTRY = BUSINESS_DIR / "03-匹配与解释" / "registry.csv"
EVIDENCE_MD = BUSINESS_DIR / "05-市场与竞争" / "证据表.md"


# ---------------------------------------------------------------------------
# 读取工具（UTF-8/UTF-8-BOM/GBK 容错）
# ---------------------------------------------------------------------------
def read_text(path) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    raw = p.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def read_csv_rows(path) -> list:
    text = read_text(path)
    if not text.strip():
        return []
    try:
        return [dict(row) for row in csv.DictReader(io.StringIO(text))]
    except csv.Error:
        return []


def _clean(value) -> str:
    return (value or "").strip() if isinstance(value, str) else ("" if value is None else str(value).strip())


def _now() -> str:
    return db.now_iso()


# ---------------------------------------------------------------------------
# 通用插入
# ---------------------------------------------------------------------------
NUMERIC_FIELDS = {
    "compute_specifications": {"memory_gb", "memory_bandwidth_gbps", "fp16_tflops",
                               "tf32_tflops", "fp8_tflops", "power_kw_per_node"},
    "agent_tasks": {"requires_approval"},
    "compute_supply_resources": {"gpu_count", "sellable_gpu_count", "gpu_memory_gb",
                                 "training_capable", "inference_capable", "overseas_service",
                                 "verified"},
    "demand_opportunities": {"min_gpu_count", "max_gpu_count", "duration_months"},
    "matching_records": {"score"},
}


def _coerce(table: str, key: str, value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
    numeric = NUMERIC_FIELDS.get(table, set())
    if key in numeric:
        try:
            num = float(value)
            return int(num) if num.is_integer() else num
        except (TypeError, ValueError):
            return None
    return value


def insert_rows(conn, table: str, rows: list) -> dict:
    """按表字段白名单插入（INSERT OR IGNORE），返回 {"inserted": n, "skipped": n}。"""
    cols = set(db.table_columns(conn, table))
    if not cols:
        return {"inserted": 0, "skipped": len(rows), "missing_table": True}
    inserted = 0
    skipped = 0
    for row in rows:
        payload = {}
        for key, value in (row or {}).items():
            if key not in cols:
                continue
            payload[key] = _coerce(table, key, value)
        if "id" not in payload or not payload["id"]:
            skipped += 1
            continue
        keys = list(payload.keys())
        sql = 'INSERT OR IGNORE INTO "%s" (%s) VALUES (%s)' % (
            table, ", ".join('"%s"' % k for k in keys), ", ".join(["?"] * len(keys))
        )
        before = conn.total_changes
        try:
            conn.execute(sql, [payload[k] for k in keys])
        except Exception:
            skipped += 1
            continue
        if conn.total_changes > before:
            inserted += 1
        else:
            skipped += 1
    conn.commit()
    return {"inserted": inserted, "skipped": skipped}


# ---------------------------------------------------------------------------
# 历史交接数据导入
# ---------------------------------------------------------------------------
WORKLOAD_KEYWORDS = {
    "TRAINING": ["训练", "预训练", "微调", "训练/"],
    "INFERENCE": ["推理", "inference"],
    "MIXED": ["混合", "训练和推理", "训练与推理"],
}


def _workload_type(use_case: str) -> str:
    text = _clean(use_case)
    if not text:
        return ""
    has_training = any(k in text.lower() for k in ["训练", "微调", "预训练", "training"])
    has_inference = any(k in text.lower() for k in ["推理", "inference"])
    if has_training and has_inference:
        return "MIXED"
    if has_training:
        return "TRAINING"
    if has_inference:
        return "INFERENCE"
    if any(k in text for k in ["渲染", "仿真"]):
        return "RENDERING" if "渲染" in text else "SIMULATION"
    return ""


def _company_id_from(prefix: str, raw_id: str) -> str:
    parts = raw_id.split("-")
    if len(parts) >= 2:
        return "C-" + "-".join(parts[1:])
    return "C-" + raw_id


def _notes(marker: str, source_rel: str, raw_id: str, extra: str = "", raw_notes: str = "") -> str:
    chunks = [marker, "来源：%s" % source_rel, "原始ID：%s" % raw_id]
    if extra:
        chunks.append(extra)
    if raw_notes:
        chunks.append("历史备注：%s" % raw_notes)
    return "；".join(chunks)


def import_supply_side(conn) -> dict:
    rows = read_csv_rows(SUPPLY_REGISTRY)
    if not rows:
        return {"companies": {"inserted": 0, "skipped": 0, "missing_file": True},
                "supplies": {"inserted": 0, "skipped": 0}}
    source_rel = db.rel_to_root(SUPPLY_REGISTRY)
    now = _now()
    companies, supplies = [], []
    for row in rows:
        sid = _clean(row.get("id"))
        if not sid:
            continue
        cid = _company_id_from("SUP", sid)
        name = _clean(row.get("name")) or ("待确认供应商（%s）" % sid)
        region = _clean(row.get("region")) or "中国"
        overseas = _clean(row.get("overseas_regions"))
        raw_notes = _clean(row.get("notes"))
        evidence_ids = _clean(row.get("evidence_ids"))
        companies.append({
            "id": cid, "name": name, "name_en": "",
            "company_type": "SUPPLIER",
            "country": region,
            "region": overseas,
            "website": "",
            "business_summary": "历史交接供给线索（%s）；海外区域自述：%s"
                                % (_clean(row.get("type")) or "未分类", overseas or "未披露"),
            "status": "LEAD",
            "trust_level": "UNVERIFIED",
            "owner": "history-import",
            "tags": _clean(row.get("tags")),
            "notes": _notes(SEED_HISTORY_TOKEN, source_rel, sid,
                            "历史状态：%s（不映射为正式状态）" % (_clean(row.get("status")) or "未标注"),
                            raw_notes),
            "created_at": now, "updated_at": now,
        })
        supplies.append({
            "id": sid, "company_id": cid,
            "location_country": region, "location_city": "", "datacenter": "",
            "gpu_model": "", "gpu_count": None, "sellable_gpu_count": None, "gpu_memory_gb": None,
            "interconnect": "", "cluster_topology": "",
            "training_capable": 0, "inference_capable": 0,
            "network_bandwidth": "", "storage": "", "delivery_lead_time": "",
            "price_indication": "待确认", "pricing_model": "",
            "overseas_service": 0,
            "status": "LEAD", "verified": 0,
            "next_action": "补充公开证据并完成主体/授权/容量/交付核验（未核验前不得对外承诺）",
            "evidence_ids": evidence_ids,
            "notes": _notes(SEED_HISTORY_TOKEN, source_rel, sid,
                            "海外区域自述：%s；状态：LEAD；verified=0；价格：待确认"
                            % (overseas or "未披露"), raw_notes),
            "created_at": now, "updated_at": now,
        })
    stats = {"companies": insert_rows(conn, "companies", companies),
             "supplies": insert_rows(conn, "compute_supply_resources", supplies)}
    stats["rows_read"] = len(rows)
    return stats


def import_demand_side(conn) -> dict:
    rows = read_csv_rows(DEMAND_REGISTRY)
    if not rows:
        return {"companies": {"inserted": 0, "skipped": 0, "missing_file": True},
                "demands": {"inserted": 0, "skipped": 0}}
    source_rel = db.rel_to_root(DEMAND_REGISTRY)
    now = _now()
    companies, demands = [], []
    for index, row in enumerate(rows, start=1):
        did = _clean(row.get("id"))
        if not did:
            continue
        cid = "C-%s-%03d" % (db.today_stamp(), index)
        name = _clean(row.get("name")) or ("待确认需求方（%s）" % did)
        country = _clean(row.get("country"))
        use_case = _clean(row.get("use_case"))
        evidence_ids = _clean(row.get("evidence_ids"))
        raw_notes = _clean(row.get("notes"))
        companies.append({
            "id": cid, "name": name, "name_en": "",
            "company_type": "DEMANDER",
            "country": country, "region": "",
            "website": "",
            "business_summary": "历史交接需求线索（%s）；公开用途：%s"
                                % (_clean(row.get("type")) or "未分类", use_case or "未披露"),
            "status": "LEAD",
            "trust_level": "UNVERIFIED",
            "owner": "history-import",
            "tags": _clean(row.get("tags")),
            "notes": _notes(SEED_HISTORY_TOKEN, source_rel, did,
                            "历史状态：%s（不映射为正式状态）" % (_clean(row.get("status")) or "未标注"),
                            raw_notes),
            "created_at": now, "updated_at": now,
        })
        demands.append({
            "id": did, "company_id": cid,
            "title": "%s｜公开算力需求线索" % name,
            "workload_type": _workload_type(use_case),
            "gpu_models": "",
            "min_gpu_count": None, "max_gpu_count": None, "duration_months": None,
            "cluster_requirements": "", "network_requirements": "",
            "location_preference": country,
            "data_residency": "",
            "compliance_notes": "未筛查；公开线索，仅案头研究，未接触客户",
            "timeline": "",
            "budget_range": "UNKNOWN",
            "decision_maker": "",
            "lead_grade": "PUBLIC_LEAD",
            "status": "LEAD",
            "next_action": "仅案头研究；未升级线索等级；禁止外联与报价",
            "evidence_ids": evidence_ids,
            "notes": _notes(SEED_HISTORY_TOKEN, source_rel, did,
                            "lead_grade=PUBLIC_LEAD；status=LEAD；budget_range=UNKNOWN；"
                            "公开用途：%s" % (use_case or "未披露"), raw_notes),
            "created_at": now, "updated_at": now,
        })
    stats = {"companies": insert_rows(conn, "companies", companies),
             "demands": insert_rows(conn, "demand_opportunities", demands)}
    stats["rows_read"] = len(rows)
    return stats


def import_matches(conn) -> dict:
    rows = read_csv_rows(MATCH_REGISTRY)
    if not rows:
        return {"matches": {"inserted": 0, "skipped": 0, "missing_file": True}}
    source_rel = db.rel_to_root(MATCH_REGISTRY)
    now = _now()
    records = []
    for row in rows:
        mid = _clean(row.get("id"))
        if not mid:
            continue
        supply_id = _clean(row.get("supply_id"))
        demand_id = _clean(row.get("demand_id"))
        old_score = _clean(row.get("score"))
        old_status = _clean(row.get("status"))
        dimensions = {
            "legacy": {
                "source": SEED_HISTORY_TOKEN,
                "old_score": old_score,
                "old_status": old_status,
                "old_next_step": _clean(row.get("next_step")),
                "note": "历史交接样例的内部模拟分，非本系统 0–100 评分，不写入 score 字段",
            }
        }
        records.append({
            "id": mid, "demand_id": demand_id, "supply_id": supply_id,
            "score": None,
            "match_dimensions": json.dumps(dimensions, ensure_ascii=False),
            "why_match": "历史交接样例：供给 %s 与需求 %s 在历史档案中曾有模拟匹配记录" % (supply_id, demand_id),
            "why_not_match": "历史样例，非真实订单；历史模拟分 %s（非本系统评分）不可作为推进依据，"
                             "且双方均为未核验公开线索" % (old_score or "未记录"),
            "risks": "历史样例，非真实订单；供给未核验、需求未资格化、跨境合规未筛查",
            "confidence": "LOW",
            "recommendation": None,
            "status": "DRAFT",
            "analyst": "history-import",
            "created_at": now, "updated_at": now,
        })
    stats = {"matches": insert_rows(conn, "matching_records", records)}
    stats["rows_read"] = len(rows)
    return stats


def _mapping(url_text: str) -> str:
    match = re.search(r"https?://[^\s)｜|]+", url_text or "")
    return match.group(0).rstrip("。，；;、") if match else ""


def _confidence(raw: str) -> str:
    text = _clean(raw)
    if not text:
        return "UNVERIFIED"
    if "中" not in text and text.startswith("高"):
        return "HIGH"
    if "中高" in text:
        return "MEDIUM"
    if "中低" in text:
        return "LOW"
    if text.startswith("中"):
        return "MEDIUM"
    if "低" in text:
        return "LOW"
    return "UNVERIFIED"


def _cross_verified(raw: str) -> int:
    text = _clean(raw)
    if not text or "未" in text or "部分" in text:
        return 0
    return 1 if ("已打开" in text or "已核验" in text) else 0


def parse_evidence_table() -> list:
    text = read_text(EVIDENCE_MD)
    if not text.strip():
        return []
    header = None
    parsed = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if header is None:
            if cells and cells[0].upper() == "ID":
                header = cells
            continue
        if not cells or not re.match(r"^B-E\d+$", cells[0]):
            continue
        if len(cells) > len(header):
            cells = cells[: len(header) - 1] + ["｜".join(cells[len(header) - 1:])]
        elif len(cells) < len(header):
            cells += [""] * (len(header) - len(cells))
        parsed.append(dict(zip(header, cells)))
    return parsed


def _evidence_row(item: dict) -> dict:
    now = _now()
    claim = _clean(item.get("结论内容")) or _clean(item.get("原文或数据摘录")) or "历史证据条目"
    notes_parts = [
        SEED_HISTORY_TOKEN,
        "来源文件：%s" % db.rel_to_root(EVIDENCE_MD),
        "判定类型：%s" % (_clean(item.get("事实/推断/假设")) or "未标注"),
    ]
    conflict = _clean(item.get("冲突信息"))
    if conflict:
        notes_parts.append("冲突信息：%s" % conflict)
    excerpt = _clean(item.get("原文或数据摘录"))
    if excerpt:
        notes_parts.append("摘录：%s" % excerpt[:500])
    return {
        "id": _clean(item.get("ID")),
        "subject_type": "CLAIM",
        "subject_id": "",
        "claim": claim,
        "source_title": _clean(item.get("来源名称")),
        "url": _mapping(_clean(item.get("原始链接"))),
        "publisher": _clean(item.get("来源类型")),
        "published_at": _clean(item.get("发布时间")),
        "retrieved_at": _clean(item.get("获取时间")),
        "confidence": _confidence(item.get("可信度")),
        "cross_verified": _cross_verified(item.get("核验状态")),
        "notes": "；".join(notes_parts),
        "created_at": now,
    }


FALLBACK_EVIDENCE = [
    ("B-E22", "Runpod 官网公开 GPU 云价目页（按需/竞价），用于市场价格参考", "Runpod Pricing", "https://www.runpod.io/pricing", "已打开", "中高"),
    ("B-E23", "Lambda 官网公开 GPU 云价目页（按需/预留），用于市场价格参考", "Lambda Pricing", "https://lambda.ai/pricing", "已打开", "中高"),
    ("B-E24", "主要 GPU 云厂商普遍提供 H100/A100 单卡与整机租用形态", "公开行业观察", "", "未核验", "中"),
    ("B-E25", "中国智算中心普遍处于建设/爬坡期，可售容量与规划容量需区分", "公开行业观察", "", "未核验", "中"),
    ("B-E26", "跨境算力服务涉及数据出境与出口管制合规，需逐案筛查", "公开法规资料", "", "部分核验", "中高"),
    ("B-E27", "东南亚是 AI 推理与训练需求增长较快的区域之一", "公开行业报告", "", "未核验", "中"),
    ("B-E28", "中东主权 AI 与算力投资活跃，存在采购与合作机会", "公开新闻", "", "未核验", "中"),
    ("B-E29", "国内 GPU 供给存在型号代际与互联能力差异，需标准化对比", "公开规格资料", "", "部分核验", "中高"),
    ("B-E30", "转售/代理模式下需确认供应商对资源的合法处置权", "公开行业惯例", "", "未核验", "中"),
    ("B-E31", "对外报价与合同条款必须逐案确认，禁止引用未核验价格", "项目内部规则", "docs/00_project_audit/PROJECT_BRIEF.md", "已打开", "高"),
]


def import_evidence(conn) -> dict:
    parsed = parse_evidence_table()
    rows = [_evidence_row(item) for item in parsed if _clean(item.get("ID"))]
    rows = [r for r in rows if r["id"]]
    if len(rows) < 10:
        now = _now()
        rows = []
        for eid, claim, source, url, status, confidence in FALLBACK_EVIDENCE:
            rows.append({
                "id": eid, "subject_type": "CLAIM", "subject_id": "", "claim": claim,
                "source_title": source, "url": url, "publisher": "",
                "published_at": "", "retrieved_at": "",
                "confidence": _confidence(confidence), "cross_verified": _cross_verified(status),
                "notes": "%s；来源文件：%s（证据表解析失败时的内置回退清单）"
                         % (SEED_HISTORY_TOKEN, db.rel_to_root(EVIDENCE_MD)),
                "created_at": now,
            })
    stats = {"evidence": insert_rows(conn, "evidence_registry", rows)}
    stats["rows_read"] = len(parsed)
    return stats


# ---------------------------------------------------------------------------
# 演示种子（CSV）
# ---------------------------------------------------------------------------
def import_seed_csvs(conn) -> dict:
    stats = {}
    files = {
        "specs": ("compute_specifications", "specs.csv"),
        "agent_tasks": ("agent_tasks", "agent_tasks.csv"),
        "approvals": ("approvals", "approvals.csv"),
        "knowledge": ("knowledge_records", "knowledge.csv"),
    }
    for key, (table, filename) in files.items():
        rows = read_csv_rows(SEED_DIR / filename)
        if not rows:
            stats[key] = {"inserted": 0, "skipped": 0, "missing_file": True}
            continue
        for row in rows:
            notes = row.get("notes") or row.get("content_md") or ""
            if SEED_DEMO_TOKEN not in (row.get("notes") or "") and table in (
                    "compute_specifications", "approvals"):
                row["notes"] = ((row.get("notes") or "") + "；" + SEED_DEMO_TOKEN).strip("；")
        stats[key] = insert_rows(conn, table, rows)
    return stats


# ---------------------------------------------------------------------------
# 汇总入口
# ---------------------------------------------------------------------------
def seed_all(conn=None, include_history: bool = True, include_demo: bool = True) -> dict:
    """装载全部种子。幂等：重复调用不会产生重复记录。"""
    own_conn = False
    if conn is None:
        conn = db.ensure_schema()
        own_conn = True
    result = {"inserted": {}, "history_available": BUSINESS_DIR.exists()}
    try:
        steps = {}
        if include_history:
            steps.update(import_supply_side(conn))
            steps.update(import_demand_side(conn))
            steps.update(import_matches(conn))
            steps.update(import_evidence(conn))
        if include_demo:
            steps.update(import_seed_csvs(conn))
        for key, value in steps.items():
            if isinstance(value, dict) and "inserted" in value:
                result["inserted"][key] = value.get("inserted", 0)
        total = sum(result["inserted"].values())
        result["inserted_total"] = total
        return result
    finally:
        if own_conn:
            conn.close()


if __name__ == "__main__":  # python -m app.backend.seed
    info = seed_all()
    print("Seed result:", json.dumps(info, ensure_ascii=False, indent=2))
