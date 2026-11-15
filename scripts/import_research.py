"""把第一轮真实公开研究（data/research/*.csv）导入 AI 经营工作台。

设计原则
--------
1. 幂等：按 CSV 的固定 ID（DEM/SUP/MATCH/EV-R1-*）判定是否已导入，重复运行不会重复插入。
2. 不升级：导入后一律保持 LEAD / DRAFT / OPEN 等初始状态，lead_grade 只允许
   PUBLIC_LEAD 或 INFERRED，绝不自动变成 VERIFIED / QUALIFIED。
3. 不编造：CSV 中为空的字段一律留空，不做推测填充；推断内容显式加「推断」前缀。
4. 留痕：全部走 app.backend.repo.create_item（自动写 audit_logs + project_activities）。

用法
----
    python scripts/import_research.py                 # 导入到默认库 data/runtime/app.db
    python scripts/import_research.py --db D:\\path\\x.db
    python scripts/import_research.py --dry-run       # 只统计，不写库
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backend import db, repo  # noqa: E402

RESEARCH_DIR = ROOT / "data" / "research"
ACTOR = "research-import"
REQUIRED_FILES = [
    "demand_candidates.csv",
    "supply_candidates.csv",
    "matches.csv",
    "evidence_registry.csv",
]


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def read_csv(name: str) -> list:
    path = RESEARCH_DIR / name
    if not path.exists():
        raise SystemExit("缺少研究文件：%s" % path)
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def clean(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def table_of(conn, res: str) -> str:
    return repo.get_spec(res)["table"]


def exists(conn, res: str, item_id: str) -> bool:
    row = conn.execute(
        'SELECT 1 FROM "%s" WHERE id = ? LIMIT 1' % table_of(conn, res), (item_id,)
    ).fetchone()
    return row is not None


def add(conn, res: str, data: dict, stats: dict, dry_run: bool) -> bool:
    """插入一条记录；已存在则跳过。返回是否新增。"""
    item_id = clean(data.get("id"))
    key = "%s:%s" % (res, item_id)
    if exists(conn, res, item_id):
        stats["skipped"] += 1
        stats["detail"].append("SKIP " + key)
        return False
    if dry_run:
        stats["would_insert"] += 1
        stats["detail"].append("DRY  " + key)
        return False
    repo.create_item(conn, res, data, actor=ACTOR)
    stats["inserted"] += 1
    stats["detail"].append("ADD  " + key)
    return True


def find_company(conn, name: str) -> str:
    """按企业名（忽略首尾空白）复用已有 companies 记录，避免重复建档。"""
    row = conn.execute(
        "SELECT id FROM companies WHERE TRIM(name) = ? LIMIT 1", (name.strip(),)
    ).fetchone()
    return row[0] if row else ""


# ---------------------------------------------------------------------------
# 映射规则
# ---------------------------------------------------------------------------
def workload_type(gpu_inference: str) -> str:
    text = clean(gpu_inference)
    has_train = "训练" in text
    has_infer = "推理" in text
    if has_train and has_infer:
        return "MIXED"
    if has_train:
        return "TRAINING"
    if has_infer:
        return "INFERENCE"
    return "MIXED"


def lead_grade(signal_type: str) -> str:
    """公开线索 -> PUBLIC_LEAD；推断需求 -> INFERRED。绝不升级。"""
    return "INFERRED" if "推断" in clean(signal_type) else "PUBLIC_LEAD"


SUBJECT_TYPE_MAP = {
    "demand": "DEMAND",
    "supply": "SUPPLY",
    "match": "MATCH",
    "company": "COMPANY",
    "claim": "CLAIM",
}


# ---------------------------------------------------------------------------
# 导入步骤
# ---------------------------------------------------------------------------
def import_demands(conn, rows, stats, dry_run):
    for row in rows:
        cid = clean(row.get("id"))
        if not cid:
            continue
        name = clean(row.get("name"))
        company_id = find_company(conn, name) or "C-" + cid
        add(
            conn,
            "companies",
            {
                "id": company_id,
                "name": name,
                "name_en": clean(row.get("name_en")),
                "company_type": "DEMANDER",
                "country": clean(row.get("region")),
                "region": clean(row.get("region")),
                "website": clean(row.get("website")),
                "business_summary": clean(row.get("business")),
                "status": "LEAD",
                "trust_level": clean(row.get("trust_level")) or "UNVERIFIED",
                "owner": ACTOR,
                "tags": "research-round1;demand",
                "notes": "第一轮公开研究导入（%s）；分级=公开线索/推断需求，不得自动升级。"
                % clean(row.get("signal_type")),
            },
            stats,
            dry_run,
        )
        add(
            conn,
            "demands",
            {
                "id": cid,
                "company_id": company_id,
                "title": "%s（%s）GPU 算力需求假设" % (name, clean(row.get("signal_type")) or "公开线索"),
                "workload_type": workload_type(row.get("gpu_inference")),
                "gpu_models": "",
                "cluster_requirements": "推断（非已核实事实）：" + clean(row.get("hypothesis_specs")),
                "network_requirements": "",
                "location_preference": clean(row.get("region")),
                "data_residency": "",
                "compliance_notes": "待确认：" + clean(row.get("open_questions")),
                "timeline": "",
                "budget_range": "UNKNOWN",
                "decision_maker": "",
                "lead_grade": lead_grade(row.get("signal_type")),
                "status": "LEAD",
                "next_action": clean(row.get("next_step")),
                "evidence_ids": clean(row.get("evidence_ids")),
            },
            stats,
            dry_run,
        )


def import_supplies(conn, rows, stats, dry_run):
    for row in rows:
        sid = clean(row.get("id"))
        if not sid:
            continue
        name = clean(row.get("name"))
        company_id = find_company(conn, name) or "C-" + sid
        add(
            conn,
            "companies",
            {
                "id": company_id,
                "name": name,
                "name_en": "",
                "company_type": "SUPPLIER",
                "country": "中国",
                "region": clean(row.get("region")),
                "website": clean(row.get("website")),
                "parent": clean(row.get("parent")),
                "listed_code": clean(row.get("listed_code")),
                "business_summary": clean(row.get("resource_summary")),
                "status": "LEAD",
                "trust_level": clean(row.get("trust_level")) or "UNVERIFIED",
                "owner": ACTOR,
                "tags": "research-round1;supply",
                "notes": "第一轮公开研究导入（%s）；出海能力表述来自官网自述，未核验。"
                % clean(row.get("lead_grade")),
            },
            stats,
            dry_run,
        )
        add(
            conn,
            "supplies",
            {
                "id": sid,
                "company_id": company_id,
                "location_country": "中国",
                "location_city": clean(row.get("region")),
                "datacenter": "",
                "gpu_model": "",
                "gpu_count": None,
                "sellable_gpu_count": None,
                "gpu_memory_gb": None,
                "interconnect": "",
                "cluster_topology": "",
                "training_capable": 0,
                "inference_capable": 0,
                "network_bandwidth": "",
                "storage": "",
                "delivery_lead_time": "",
                "price_indication": "待确认",
                "pricing_model": "",
                "overseas_service": 0,
                "status": "LEAD",
                "verified": 0,
                "next_action": clean(row.get("next_step")),
                "evidence_ids": clean(row.get("evidence_ids")),
            },
            stats,
            dry_run,
        )


def import_evidence(conn, rows, stats, dry_run):
    for row in rows:
        eid = clean(row.get("id"))
        if not eid:
            continue
        subject_type = SUBJECT_TYPE_MAP.get(clean(row.get("subject_type")).lower(), "OTHER")
        add(
            conn,
            "evidence",
            {
                "id": eid,
                "subject_type": subject_type,
                "subject_id": clean(row.get("subject_id")),
                "claim": clean(row.get("claim")),
                "source_title": clean(row.get("source_title")),
                "url": clean(row.get("url")),
                "publisher": clean(row.get("publisher")),
                "published_at": clean(row.get("published_at")),
                "retrieved_at": clean(row.get("retrieved_at")),
                "confidence": clean(row.get("confidence")) or "UNVERIFIED",
                "cross_verified": 1 if clean(row.get("cross_verified")).startswith("是") else 0,
                "notes": clean(row.get("notes")),
            },
            stats,
            dry_run,
        )


def import_matches(conn, rows, stats, dry_run):
    for row in rows:
        mid = clean(row.get("id"))
        if not mid:
            continue
        why_not = clean(row.get("why_not_match"))
        add(
            conn,
            "matches",
            {
                "id": mid,
                "demand_id": clean(row.get("demand_id")),
                "supply_id": clean(row.get("supply_id")),
                "score": float(clean(row.get("match_score")) or 0),
                "why_match": clean(row.get("why_match")),
                "why_not_match": why_not,
                "risks": "研究性粗评；关键缺口见 why_not_match。「可推进」仅指内部核验，非对外商机。",
                "confidence": clean(row.get("confidence")),
                "recommendation": clean(row.get("recommendation")),
                "status": "DRAFT",
                "analyst": "research-round1（内部草稿，未外发）",
            },
            stats,
            dry_run,
        )


def import_opportunity(conn, matches, stats, dry_run):
    """只有研究结论为 ADVANCE 的匹配才建商机草稿，且保持 OPEN / PENDING。"""
    for row in matches:
        if not clean(row.get("recommendation")).startswith("ADVANCE"):
            continue
        mid = clean(row.get("id"))
        oid = "OPP-" + mid.replace("MATCH-", "")
        add(
            conn,
            "commercial-opportunities",
            {
                "id": oid,
                "demand_id": clean(row.get("demand_id")),
                "supply_id": clean(row.get("supply_id")),
                "match_id": mid,
                "title": "%s × %s：算力供给合作（研究性商机草稿）"
                % (clean(row.get("demand_id")), clean(row.get("supply_id"))),
                "stage": "OPEN",
                "model_type": "INTRO",
                "fee_payer": "PENDING_CEO_DECISION",
                "fee_basis": "",
                "fee_terms": "未报价、未接触；收费结构与双边披露待 CEO 决定，不得写死费率。",
                "conflict_disclosed": 0,
                "ceo_approval_status": "PENDING",
                "next_step": clean(row.get("next_step")),
                "owner": "lead",
            },
            stats,
            dry_run,
        )


def import_approvals(conn, stats, dry_run):
    add(
        conn,
        "approvals",
        {
            "id": "APR-R1-001",
            "approval_type": "EXTERNAL_CONTACT_AUTHORIZATION",
            "subject": "以「登甲智能」为第一家核验供应商，并授权 CEO 发出首次外部联系",
            "requested_by": "lead",
            "payload_json": json.dumps(
                {
                    "supplier_id": "SUP-R1-001",
                    "match_id": "MATCH-R1-001",
                    "demand_id": "DEM-R1-004",
                    "options": ["A 批准", "B 更换目标", "C 暂不接触"],
                    "note": "未授权前不得发送任何邮件/私信/报价；本系统不代发。",
                },
                ensure_ascii=False,
            ),
            "status": "PENDING",
        },
        stats,
        dry_run,
    )
    add(
        conn,
        "approvals",
        {
            "id": "APR-R1-002",
            "approval_type": "REPO_VISIBILITY",
            "subject": "将 GitHub 仓库 AckNove/suanlichuhai 由 Public 改为 Private",
            "requested_by": "lead",
            "payload_json": json.dumps(
                {
                    "repo": "AckNove/suanlichuhai",
                    "reason": "仓库当前匿名可读，商业文档与经营资料存在外泄风险",
                    "note": "本系统无权限修改仓库可见性，需 CEO 在 GitHub 设置中操作。",
                },
                ensure_ascii=False,
            ),
            "status": "PENDING",
        },
        stats,
        dry_run,
    )


def import_knowledge(conn, stats, dry_run):
    add(
        conn,
        "knowledge",
        {
            "id": "KN-R1-001",
            "title": "第一轮研究结论：先做东南亚 GPUaaS 扩容需求，供应商从登甲智能开始核验",
            "category": "RESEARCH",
            "content_md": (
                "# 第一轮研究结论（2026-11-16）\n\n"
                "- 需求优先：东南亚「主权 AI / GPUaaS 运营商扩容」，首选印尼 Lintasarta（DEM-R1-004，推断需求）。\n"
                "- 供应商顺序：登甲智能（SUP-R1-001）→ 硅基流动（SUP-R1-003）→ 天顿数据（SUP-R1-002，证据不足）。\n"
                "- 唯一内部可推进组合：MATCH-R1-001（62/100，仅内部核验）。\n"
                "- 不得自动升级：所有记录保持 LEAD / DRAFT / OPEN，升级与对外一律 CEO。\n"
                "- 详细出处：docs/05_research/MARKET_RESEARCH_ROUND1.md、data/research/*.csv。\n"
            ),
            "tags": "research;round1;positioning",
            "source": "docs/05_research/MARKET_RESEARCH_ROUND1.md",
            "status": "DRAFT",
        },
        stats,
        dry_run,
    )
    add(
        conn,
        "knowledge",
        {
            "id": "KN-R1-002",
            "title": "第一轮证据缺口清单（未核实项，禁止对外引用）",
            "category": "EVIDENCE_GAP",
            "content_md": (
                "# 证据缺口（2026-11-16）\n\n"
                "- 40 条证据中 14 条仅标题级，正文未打开，已标 UNVERIFIED/待确认。\n"
                "- 登甲智能：可售卡型、卡量、机房位置、海外节点、70% 海外客户均为官网自述。\n"
                "- 天顿数据：可核来源不足 2 条，建议下一轮仍不足即关闭候选。\n"
                "- 硅基流动：词元跨境涉数据出境，未经律师评估不得对外承诺。\n"
                "- Lintasarta：扩容属推断，需客户侧确认；印尼数据驻留可能与我方供给冲突。\n"
            ),
            "tags": "research;evidence;gaps",
            "source": "docs/05_research/EVIDENCE_REGISTRY.md、data/research/evidence_registry.csv",
            "status": "DRAFT",
        },
        stats,
        dry_run,
    )


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="导入第一轮真实公开研究数据")
    parser.add_argument("--db", default="", help="数据库路径（默认 data/runtime/app.db）")
    parser.add_argument("--dry-run", action="store_true", help="只统计不写库")
    args = parser.parse_args(argv)

    for name in REQUIRED_FILES:
        if not (RESEARCH_DIR / name).exists():
            raise SystemExit("缺少研究文件：%s" % (RESEARCH_DIR / name))

    demands = read_csv("demand_candidates.csv")
    supplies = read_csv("supply_candidates.csv")
    matches = read_csv("matches.csv")
    evidence = read_csv("evidence_registry.csv")

    db_file = db.ensure_schema(args.db or None)
    conn = db_file

    stats = {"inserted": 0, "skipped": 0, "would_insert": 0, "detail": []}

    import_demands(conn, demands, stats, args.dry_run)
    import_supplies(conn, supplies, stats, args.dry_run)
    import_evidence(conn, evidence, stats, args.dry_run)
    import_matches(conn, matches, stats, args.dry_run)
    import_opportunity(conn, matches, stats, args.dry_run)
    import_approvals(conn, stats, args.dry_run)
    import_knowledge(conn, stats, args.dry_run)

    if not args.dry_run:
        db.activity(
            conn,
            actor=ACTOR,
            action="IMPORT",
            entity_type="research",
            summary="第一轮真实公开研究导入（需求 %d / 供给 %d / 匹配 %d / 证据 %d）"
            % (len(demands), len(supplies), len(matches), len(evidence)),
        )

    mode = "DRY-RUN" if args.dry_run else "IMPORTED"
    print("[%s] db=%s" % (mode, db.db_path()))
    print(
        "  inserted=%d skipped=%d would_insert=%d"
        % (stats["inserted"], stats["skipped"], stats["would_insert"])
    )
    for line in stats["detail"]:
        print("   - " + line)
    print("  需求 %d / 供给 %d / 匹配 %d / 证据 %d" % (len(demands), len(supplies), len(matches), len(evidence)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
