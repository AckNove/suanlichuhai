# -*- coding: utf-8 -*-
"""CCGS 通用 CRUD 仓库：字段白名单、分页排序白名单、模糊搜索、状态机校验、ID 生成。

设计要点：
- 所有可写字段来自实际表结构（PRAGMA table_info），未知字段忽略，绝不拼接用户输入到 SQL 标识符。
- 状态迁移强校验：非法迁移抛 ConflictError(409)，message 含允许的目标状态。
- 公开线索不得自动升级：VERIFIED/QUALIFIED/ACTIVE/MATCHED 等关键状态有额外前置条件校验。
- 写操作统一记录 audit_logs 与 project_activities。
"""
from __future__ import annotations

import re
import sqlite3

from . import db


class ApiError(Exception):
    status = 500
    code = "INTERNAL"

    def __init__(self, message: str, code: str = None, extra: dict = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.extra = extra or {}

    def to_dict(self) -> dict:
        body = {"error": {"code": self.code, "message": self.message}}
        if self.extra:
            body["error"].update(self.extra)
        return body


class ValidationError(ApiError):
    status = 400
    code = "VALIDATION_ERROR"


class NotFoundError(ApiError):
    status = 404
    code = "NOT_FOUND"


class ConflictError(ApiError):
    status = 409
    code = "CONFLICT"


class ForbiddenError(ApiError):
    status = 403
    code = "FORBIDDEN"


# ---------------------------------------------------------------------------
# 资源定义
# ---------------------------------------------------------------------------
RESOURCES = {
    "companies": {
        "table": "companies", "prefix": "C",
        "search": ["name", "name_en", "business_summary", "notes", "tags", "country", "region"],
        "required": ["name"], "default_sort": "-created_at",
    },
    "demands": {
        "table": "demand_opportunities", "prefix": "DEM",
        "search": ["title", "gpu_models", "cluster_requirements", "network_requirements",
                   "compliance_notes", "next_action", "location_preference"],
        "required": ["title"], "default_sort": "-created_at",
    },
    "supplies": {
        "table": "compute_supply_resources", "prefix": "SUP",
        "search": ["gpu_model", "datacenter", "location_city", "location_country",
                   "notes", "next_action", "interconnect"],
        "required": [], "default_sort": "-created_at",
    },
    "specs": {
        "table": "compute_specifications", "prefix": "SPEC",
        "search": ["gpu_model", "vendor", "notes", "form_factor"],
        "required": ["gpu_model"], "default_sort": "gpu_model",
    },
    "evidence": {
        "table": "evidence_registry", "prefix": "EV",
        "search": ["claim", "source_title", "publisher", "notes", "url"],
        "required": ["subject_type", "claim"], "default_sort": "-created_at",
    },
    "supplier-verifications": {
        "table": "supplier_verification", "prefix": "SV",
        "search": ["notes", "gaps", "verified_by"],
        "required": [], "default_sort": "-created_at",
    },
    "demand-qualifications": {
        "table": "demand_qualification", "prefix": "DQ",
        "search": ["notes", "gaps", "qualified_by"],
        "required": [], "default_sort": "-created_at",
    },
    "matches": {
        "table": "matching_records", "prefix": "MATCH",
        "search": ["why_match", "why_not_match", "analyst", "risks"],
        "required": ["demand_id", "supply_id", "why_match", "why_not_match"],
        "default_sort": "-created_at",
    },
    "procurement-analyses": {
        "table": "procurement_analyses", "prefix": "PA",
        "search": ["title", "recommendation", "risks", "assumptions"],
        "required": ["title"], "default_sort": "-created_at",
    },
    "commercial-opportunities": {
        "table": "commercial_opportunities", "prefix": "OPP",
        "search": ["title", "next_step", "fee_basis", "fee_terms", "owner"],
        "required": ["title"], "default_sort": "-created_at",
    },
    "quotes": {
        "table": "quotes", "prefix": "QUOTE",
        "search": ["quote_type", "terms", "status"],
        "required": [], "default_sort": "-created_at",
    },
    "contracts": {
        "table": "contracts_metadata", "prefix": "CT",
        "search": ["contract_type", "counterparty_demand", "counterparty_supply", "notes"],
        "required": [], "default_sort": "-created_at",
    },
    "agent-tasks": {
        "table": "agent_tasks", "prefix": "TASK",
        "search": ["agent_name", "title", "task_type", "result_summary", "error"],
        "required": ["agent_name", "title"], "default_sort": "-created_at",
    },
    "activities": {
        "table": "project_activities", "prefix": None,
        "search": ["actor", "action", "entity_type", "summary", "detail"],
        "required": [], "default_sort": "-ts", "read_only": True,
    },
    "knowledge": {
        "table": "knowledge_records", "prefix": "KN",
        "search": ["title", "category", "content_md", "tags", "source"],
        "required": ["title"], "default_sort": "-created_at",
    },
    "approvals": {
        "table": "approvals", "prefix": "APR",
        "search": ["approval_type", "subject", "decision_note", "payload_json"],
        "required": ["approval_type", "subject"], "default_sort": "-requested_at",
    },
    "audit-logs": {
        "table": "audit_logs", "prefix": None,
        "search": ["actor", "action", "entity", "note"],
        "required": [], "default_sort": "-ts", "read_only": True,
    },
    "backups": {
        "table": "backup_records", "prefix": "B",
        "search": ["file_path", "note"], "required": [],
        "default_sort": "-created_at", "read_only": True,
    },
}

# 后端对前端也使用 dataset 短名：
RESOURCE_ALIASES = {
    "supplier-verifications": "supplier-verifications",
    "demand-qualifications": "demand-qualifications",
    "agent-tasks": "agent-tasks",
    "audit-logs": "audit-logs",
}

RESERVED_PARAMS = {"q", "sort", "page", "page_size", "format"}

# ---------------------------------------------------------------------------
# 状态机
# ---------------------------------------------------------------------------
SUPPLIER_STATES = ["LEAD", "RESEARCHED", "NEEDS_VERIFICATION", "VERIFIED", "QUALIFIED",
                   "ACTIVE", "INSUFFICIENT_INFO", "PAUSED", "EXPIRED", "REJECTED", "CEO_PENDING"]
DEMAND_STATES = ["LEAD", "RESEARCHED", "NEEDS_VERIFICATION", "VERIFIED", "QUALIFIED",
                 "MATCHED", "COMMERCIAL", "WON", "LOST", "NOT_MATCHED",
                 "INSUFFICIENT_INFO", "PAUSED", "EXPIRED", "REJECTED", "CEO_PENDING"]

TRANSITIONS = {
    "supplier": {
        "LEAD": ["RESEARCHED", "INSUFFICIENT_INFO", "PAUSED", "REJECTED"],
        "RESEARCHED": ["NEEDS_VERIFICATION", "INSUFFICIENT_INFO", "PAUSED", "REJECTED"],
        "NEEDS_VERIFICATION": ["VERIFIED", "INSUFFICIENT_INFO", "PAUSED", "REJECTED"],
        "VERIFIED": ["QUALIFIED", "PAUSED", "EXPIRED", "REJECTED"],
        "QUALIFIED": ["ACTIVE", "PAUSED", "EXPIRED", "REJECTED"],
        "ACTIVE": ["PAUSED", "EXPIRED"],
        "INSUFFICIENT_INFO": ["RESEARCHED", "PAUSED", "REJECTED"],
        "PAUSED": ["RESEARCHED", "NEEDS_VERIFICATION", "VERIFIED", "QUALIFIED", "EXPIRED", "REJECTED"],
        "EXPIRED": ["RESEARCHED"],
        "REJECTED": ["LEAD"],
        "CEO_PENDING": ["VERIFIED", "QUALIFIED", "ACTIVE", "REJECTED"],
    },
    "demand": {
        "LEAD": ["RESEARCHED", "INSUFFICIENT_INFO", "NOT_MATCHED", "PAUSED", "REJECTED"],
        "RESEARCHED": ["NEEDS_VERIFICATION", "INSUFFICIENT_INFO", "NOT_MATCHED", "PAUSED", "REJECTED"],
        "NEEDS_VERIFICATION": ["VERIFIED", "INSUFFICIENT_INFO", "NOT_MATCHED", "PAUSED", "REJECTED"],
        "VERIFIED": ["QUALIFIED", "MATCHED", "NOT_MATCHED", "PAUSED", "EXPIRED", "REJECTED"],
        "QUALIFIED": ["MATCHED", "NOT_MATCHED", "PAUSED", "EXPIRED", "REJECTED"],
        "MATCHED": ["COMMERCIAL", "NOT_MATCHED", "PAUSED", "EXPIRED", "LOST"],
        "COMMERCIAL": ["WON", "LOST", "PAUSED", "EXPIRED"],
        "WON": [],
        "LOST": ["LEAD"],
        "NOT_MATCHED": ["RESEARCHED", "PAUSED", "REJECTED"],
        "INSUFFICIENT_INFO": ["RESEARCHED", "PAUSED", "REJECTED"],
        "PAUSED": ["RESEARCHED", "NEEDS_VERIFICATION", "VERIFIED", "QUALIFIED",
                   "MATCHED", "EXPIRED", "REJECTED"],
        "EXPIRED": ["RESEARCHED"],
        "REJECTED": ["LEAD"],
        "CEO_PENDING": ["VERIFIED", "QUALIFIED", "MATCHED", "COMMERCIAL", "WON", "LOST", "REJECTED"],
    },
    "match": {
        "DRAFT": ["REVIEWED", "REJECTED"],
        "REVIEWED": ["CEO_PENDING", "APPROVED", "REJECTED"],
        "CEO_PENDING": ["APPROVED", "REJECTED"],
        "APPROVED": [],
        "REJECTED": ["DRAFT"],
    },
    "supplier_verification": {
        "PENDING": ["IN_REVIEW", "REJECTED"],
        "IN_REVIEW": ["VERIFIED", "REJECTED"],
        "VERIFIED": [],
        "REJECTED": ["PENDING"],
    },
    "demand_qualification": {
        "PENDING": ["IN_REVIEW", "REJECTED"],
        "IN_REVIEW": ["QUALIFIED", "REJECTED"],
        "QUALIFIED": [],
        "REJECTED": ["PENDING"],
    },
    "opportunity": {
        "OPEN": ["DISCLOSED", "CLOSED_LOST"],
        "DISCLOSED": ["INTRODUCED", "CLOSED_LOST"],
        "INTRODUCED": ["TERM_SHEET", "CLOSED_LOST"],
        "TERM_SHEET": ["CA", "CLOSED_LOST"],
        "CA": ["CLOSED_WON", "CLOSED_LOST"],
        "CLOSED_WON": [],
        "CLOSED_LOST": [],
    },
    "agent_task": {
        "QUEUED": ["RUNNING", "CANCELLED"],
        "RUNNING": ["DONE", "BLOCKED", "FAILED", "CANCELLED"],
        "BLOCKED": ["QUEUED", "CANCELLED"],
        "FAILED": ["QUEUED", "CANCELLED"],
        "DONE": [],
        "CANCELLED": [],
    },
    "approval": {
        "PENDING": ["APPROVED", "REJECTED", "RETURNED"],
        "RETURNED": ["PENDING"],
        "APPROVED": [],
        "REJECTED": [],
    },
    "procurement": {
        "DRAFT": ["REVIEWED", "ARCHIVED"],
        "REVIEWED": ["APPROVED", "REJECTED", "ARCHIVED"],
        "APPROVED": ["ARCHIVED"],
        "REJECTED": ["DRAFT", "ARCHIVED"],
        "ARCHIVED": ["DRAFT"],
    },
    "quote": {
        "DRAFT": ["REVIEWED", "APPROVED", "REJECTED"],
        "REVIEWED": ["APPROVED", "REJECTED"],
        "APPROVED": [],
        "REJECTED": ["DRAFT"],
    },
    "contract": {
        "NOT_STARTED": ["IN_REVIEW"],
        "IN_REVIEW": ["SIGNED", "TERMINATED"],
        "SIGNED": ["TERMINATED"],
        "TERMINATED": [],
    },
    "knowledge": {
        "DRAFT": ["PUBLISHED", "ARCHIVED"],
        "PUBLISHED": ["DRAFT", "ARCHIVED"],
        "ARCHIVED": ["DRAFT"],
    },
}

# 资源 -> (状态字段, 状态机名, 创建时允许的初始状态)
STATE_FIELDS = {
    "companies": ("status", "supplier", ["LEAD", "RESEARCHED", "INSUFFICIENT_INFO", "PAUSED"]),
    "demands": ("status", "demand", ["LEAD", "RESEARCHED", "INSUFFICIENT_INFO", "NOT_MATCHED", "PAUSED"]),
    "supplies": ("status", "supplier", ["LEAD", "RESEARCHED", "INSUFFICIENT_INFO", "PAUSED"]),
    "matches": ("status", "match", ["DRAFT"]),
    "supplier-verifications": ("status", "supplier_verification", ["PENDING", "IN_REVIEW"]),
    "demand-qualifications": ("status", "demand_qualification", ["PENDING", "IN_REVIEW"]),
    "procurement-analyses": ("status", "procurement", ["DRAFT"]),
    "commercial-opportunities": ("stage", "opportunity", ["OPEN"]),
    "quotes": ("status", "quote", ["DRAFT"]),
    "contracts": ("signature_status", "contract", ["NOT_STARTED"]),
    "agent-tasks": ("status", "agent_task", ["QUEUED"]),
    "knowledge": ("status", "knowledge", ["DRAFT"]),
    "approvals": ("status", "approval", ["PENDING"]),
}

LEAD_GRADES = ["PUBLIC_LEAD", "INFERRED", "POTENTIAL", "VERIFIED", "QUALIFIED"]

# 删除前检查的引用关系（父资源短名, 子表名, 外键列）
DEPENDENTS = [
    ("companies", "demand_opportunities", "company_id"),
    ("companies", "compute_supply_resources", "company_id"),
    ("companies", "supplier_verification", "supplier_company_id"),
    ("demands", "demand_qualification", "demand_id"),
    ("demands", "matching_records", "demand_id"),
    ("demands", "procurement_analyses", "demand_id"),
    ("supplies", "matching_records", "supply_id"),
]


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def get_spec(res: str) -> dict:
    spec = RESOURCES.get(res)
    if spec is None:
        raise NotFoundError("未知资源类型：%s" % res)
    return spec


def get_table(res: str) -> str:
    return get_spec(res)["table"]


def columns(conn: sqlite3.Connection, res: str) -> list:
    return db.table_columns(conn, get_table(res))


def _row_to_dict(row) -> dict:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def _filter_payload(conn: sqlite3.Connection, res: str, data: dict) -> dict:
    cols = set(columns(conn, res))
    out = {}
    if not isinstance(data, dict):
        raise ValidationError("请求体必须是 JSON 对象")
    for key, value in data.items():
        if key in cols and key not in ("created_at",):
            out[key] = value
    return out


def _validate_required(res: str, payload: dict, existing: dict = None) -> None:
    for field in get_spec(res).get("required", []):
        value = payload.get(field)
        if value is None and existing is not None:
            value = existing.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError("缺少必填字段：%s" % field)


def _normalize_scalar(value):
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (dict, list)):
        import json
        return json.dumps(value, ensure_ascii=False)
    return value


def _int_param(value, default: int, minimum: int = 1, maximum: int = None) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    if n < minimum:
        n = minimum
    if maximum is not None and n > maximum:
        n = maximum
    return n


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# ---------------------------------------------------------------------------
# ID 生成
# ---------------------------------------------------------------------------
def generate_id(conn: sqlite3.Connection, res: str) -> str:
    spec = get_spec(res)
    prefix = spec.get("prefix")
    if not prefix:
        raise ValidationError("该资源不支持自动 ID：%s" % res)
    table = spec["table"]
    date = db.today_stamp()
    like = "%s-%s-%%" % (prefix, date)
    row = None
    try:
        row = conn.execute(
            'SELECT id FROM "%s" WHERE id LIKE ? ORDER BY id DESC LIMIT 1' % table, (like,)
        ).fetchone()
    except sqlite3.Error:
        row = None
    seq = 1
    if row is not None:
        m = re.search(r"(\d+)$", str(row["id"]))
        if m:
            seq = int(m.group(1)) + 1
    return "%s-%s-%03d" % (prefix, date, seq)


# ---------------------------------------------------------------------------
# 查询
# ---------------------------------------------------------------------------
def list_items(conn: sqlite3.Connection, res: str, params: dict = None) -> dict:
    spec = get_spec(res)
    table = spec["table"]
    params = dict(params or {})
    cols = columns(conn, res)
    if not cols:
        return {"items": [], "total": 0, "page": 1, "page_size": 50}

    where = []
    args = []
    for key, value in params.items():
        if key in RESERVED_PARAMS or key in ("id", "format"):
            continue
        if key not in cols or value in (None, ""):
            continue
        where.append('"%s" = ?' % key)
        args.append(value)

    q = (params.get("q") or "").strip()
    if q:
        search_cols = [c for c in spec.get("search", []) if c in cols]
        if search_cols:
            terms = []
            for c in search_cols:
                terms.append('COALESCE("%s", \'\') LIKE ? ESCAPE \'\\\'' % c)
                args.append("%" + _escape_like(q) + "%")
            where.append("(" + " OR ".join(terms) + ")")

    page = _int_param(params.get("page"), 1, 1)
    page_size = _int_param(params.get("page_size"), 50, 1, 200)

    sort = (params.get("sort") or spec.get("default_sort") or "").strip()
    direction = "ASC"
    if sort.startswith("-"):
        direction = "DESC"
        sort = sort[1:]
    if sort not in cols:
        sort = "created_at" if "created_at" in cols else ("ts" if "ts" in cols else ("id" if "id" in cols else cols[0]))
        direction = "DESC"
    order_sql = '"%s" %s' % (sort, direction)

    sql_where = (" WHERE " + " AND ".join(where)) if where else ""
    try:
        total = conn.execute('SELECT COUNT(*) AS c FROM "%s"%s' % (table, sql_where), args).fetchone()["c"]
        rows = conn.execute(
            'SELECT * FROM "%s"%s ORDER BY %s LIMIT ? OFFSET ?' % (table, sql_where, order_sql),
            args + [page_size, (page - 1) * page_size],
        ).fetchall()
    except sqlite3.Error as exc:
        raise ApiError("查询失败：%s" % exc)
    return {
        "items": [_row_to_dict(r) for r in rows],
        "total": int(total),
        "page": page,
        "page_size": page_size,
    }


def get_item(conn: sqlite3.Connection, res: str, item_id: str) -> dict:
    table = get_table(res)
    try:
        row = conn.execute('SELECT * FROM "%s" WHERE id = ?' % table, (item_id,)).fetchone()
    except sqlite3.Error as exc:
        raise ApiError("查询失败：%s" % exc)
    if row is None:
        raise NotFoundError("记录不存在：%s/%s" % (res, item_id))
    return _row_to_dict(row)


def all_rows(conn: sqlite3.Connection, res: str) -> list:
    table = get_table(res)
    order = "id ASC"
    cols = columns(conn, res)
    if "created_at" in cols:
        order = "created_at DESC, id DESC"
    rows = conn.execute('SELECT * FROM "%s" ORDER BY %s' % (table, order)).fetchall()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# 状态机校验
# ---------------------------------------------------------------------------
def machine_name(conn: sqlite3.Connection, res: str, row: dict) -> str:
    state_field, machine, _initial = STATE_FIELDS[res]
    if res == "companies" and (row or {}).get("company_type") == "DEMANDER":
        return "demand"
    return machine


def allowed_transitions(res: str, machine: str, state: str) -> list:
    table = TRANSITIONS.get(machine, {})
    return list(table.get(state, []))


def _ceo_approved(conn: sqlite3.Connection, approval_types, entity_id: str) -> bool:
    """检查是否存在针对该实体的 CEO 已批准审批记录。"""
    if not entity_id:
        return False
    placeholders = ",".join(["?"] * len(approval_types))
    sql = (
        "SELECT 1 FROM approvals WHERE status='APPROVED' AND approval_type IN (%s) "
        "AND (subject LIKE ? OR COALESCE(payload_json,'') LIKE ?) LIMIT 1" % placeholders
    )
    args = list(approval_types) + ["%" + entity_id + "%", "%" + entity_id + "%"]
    try:
        return conn.execute(sql, args).fetchone() is not None
    except sqlite3.Error:
        return False


def _guard_company(conn, row: dict, new_status: str, actor: str) -> None:
    cid = row.get("id")
    is_demander = row.get("company_type") == "DEMANDER"
    if is_demander:
        return _guard_demand_like(conn, "company", cid, new_status, actor)
    if new_status == "VERIFIED":
        hit = conn.execute(
            "SELECT 1 FROM supplier_verification WHERE supplier_company_id=? AND status='VERIFIED' LIMIT 1",
            (cid,),
        ).fetchone()
        if not hit:
            raise ConflictError(
                "不允许直接升级为 VERIFIED：需先存在 supplier_verification.status=VERIFIED 的核验记录；"
                "允许目标状态：%s" % ", ".join(allowed_transitions("companies", "supplier", row.get("status") or "LEAD"))
            )
    elif new_status == "QUALIFIED":
        v = conn.execute(
            "SELECT score FROM supplier_verification WHERE supplier_company_id=? AND status='VERIFIED' "
            "ORDER BY score DESC LIMIT 1", (cid,),
        ).fetchone()
        if not v or v["score"] is None or int(v["score"]) < 70:
            raise ConflictError("不允许升级为 QUALIFIED：需 supplier_verification.score>=70（当前不满足）")
        if not _ceo_approved(conn, ("SUPPLIER_QUALIFIED", "SUPPLIER_QUALIFICATION",
                                    "QUALIFY_SUPPLIER", "SUPPLIER_VERIFICATION"), cid):
            raise ConflictError("不允许升级为 QUALIFIED：需 CEO 审批通过（approvals.status=APPROVED）")
    elif new_status == "ACTIVE":
        if not _ceo_approved(conn, ("SUPPLIER_ACTIVE", "ACTIVATE_SUPPLIER", "SUPPLIER_ACTIVATION"), cid):
            raise ConflictError("不允许升级为 ACTIVE：需 CEO 审批通过（approvals.status=APPROVED）")


def _guard_demand_like(conn, kind: str, entity_id: str, new_status: str, actor: str) -> None:
    """需求/需求方公司的关键状态前置条件。"""
    if kind == "demand":
        demand_id = entity_id
    else:
        demand_id = None
    if new_status == "VERIFIED":
        ok = False
        if demand_id:
            ok = conn.execute(
                "SELECT 1 FROM demand_qualification WHERE demand_id=? AND status='QUALIFIED' LIMIT 1",
                (demand_id,),
            ).fetchone() is not None
        if not ok:
            ok = _ceo_approved(conn, ("DEMAND_VERIFIED", "VERIFY_DEMAND", "DEMAND_QUALIFICATION"),
                               entity_id or "")
        if not ok:
            raise ConflictError("不允许升级为 VERIFIED：需 demand_qualification.status=QUALIFIED 或 CEO 手工核验记录")
    elif new_status == "MATCHED":
        if not demand_id:
            raise ConflictError("不允许升级为 MATCHED：公司主体需通过 demand_opportunities 匹配流程")
        hit = conn.execute(
            "SELECT 1 FROM matching_records WHERE demand_id=? AND recommendation='ADVANCE' "
            "AND status='REVIEWED' LIMIT 1", (demand_id,),
        ).fetchone()
        if not hit:
            raise ConflictError("不允许升级为 MATCHED：需存在 matching_records(recommendation=ADVANCE, status=REVIEWED)")
    elif new_status in ("WON", "LOST"):
        if (actor or "").strip().upper() != "CEO":
            raise ForbiddenError("WON/LOST 仅 CEO 可置位（X-Actor 需为 CEO）")


def _validate_transition(conn, res: str, row: dict, new_state: str, actor: str) -> None:
    if res not in STATE_FIELDS:
        return
    state_field, _machine, _initial = STATE_FIELDS[res]
    old_state = (row or {}).get(state_field)
    if new_state == old_state:
        return
    machine = machine_name(conn, res, row)
    table = TRANSITIONS.get(machine, {})
    if old_state not in table:
        raise ConflictError("当前状态 %s 不在 %s 状态机定义中，禁止迁移" % (old_state, machine))
    allowed = table.get(old_state, [])
    if new_state not in allowed:
        raise ConflictError(
            "非法状态迁移：%s → %s；允许目标状态：%s"
            % (old_state, new_state, ", ".join(allowed) if allowed else "（终态，无）")
        )
    # 关键状态的前置条件（公开线索不得自动升级）
    if res == "companies":
        _guard_company(conn, row, new_state, actor)
    elif res == "demands":
        _guard_demand_like(conn, "demand", row.get("id"), new_state, actor)
    elif res == "supplies":
        if new_state == "VERIFIED" and not row.get("verified"):
            raise ConflictError("不允许升级为 VERIFIED：算力资源需先完成核验（verified=1）")
    elif res == "matches":
        if new_state == "APPROVED":
            pass  # 审批链由 status=CEO_PENDING 控制，不额外阻断


def _validate_enum_fields(conn, res: str, payload: dict) -> None:
    if res == "demands" and "lead_grade" in payload and payload["lead_grade"] not in LEAD_GRADES:
        raise ValidationError("lead_grade 非法，允许值：%s" % ", ".join(LEAD_GRADES))


# ---------------------------------------------------------------------------
# 写操作
# ---------------------------------------------------------------------------
def create_item(conn: sqlite3.Connection, res: str, data: dict, actor: str = "local",
                ip: str = None) -> dict:
    spec = get_spec(res)
    if spec.get("read_only"):
        raise ForbiddenError("只读资源不支持创建：%s" % res)
    payload = _filter_payload(conn, res, data)
    _validate_required(res, payload)
    _validate_enum_fields(conn, res, payload)

    cols = columns(conn, res)
    if not payload.get("id"):
        payload["id"] = generate_id(conn, res)
    now = db.now_iso()
    if "created_at" in cols:
        payload.setdefault("created_at", now)
    if "updated_at" in cols:
        payload.setdefault("updated_at", now)

    if res in STATE_FIELDS:
        state_field, _machine, initial = STATE_FIELDS[res]
        state = payload.get(state_field)
        if state is not None and state not in initial:
            raise ValidationError(
                "创建时 %s 仅允许初始状态：%s（当前：%s）"
                % (state_field, ", ".join(initial), state)
            )

    for key in list(payload.keys()):
        payload[key] = _normalize_scalar(payload[key])

    table = spec["table"]
    keys = list(payload.keys())
    sql = 'INSERT INTO "%s" (%s) VALUES (%s)' % (
        table, ", ".join('"%s"' % k for k in keys), ", ".join(["?"] * len(keys))
    )
    try:
        with db.transaction(conn):
            conn.execute(sql, [payload[k] for k in keys])
            created = get_item(conn, res, payload["id"])
            db.record_write(conn, actor=actor, action="CREATE", entity_type=res,
                            entity_id=str(payload["id"]), before=None, after=created,
                            summary="创建%s %s" % (res, payload["id"]), ip=ip)
    except sqlite3.IntegrityError as exc:
        raise ConflictError("创建失败（主键冲突或外键约束）：%s" % exc)
    except sqlite3.Error as exc:
        raise ApiError("创建失败：%s" % exc)
    return created


def update_item(conn: sqlite3.Connection, res: str, item_id: str, data: dict,
                actor: str = "local", ip: str = None, partial: bool = True) -> dict:
    spec = get_spec(res)
    if spec.get("read_only"):
        raise ForbiddenError("只读资源不支持修改：%s" % res)
    before = get_item(conn, res, item_id)
    payload = _filter_payload(conn, res, data)
    payload.pop("id", None)
    _validate_required(res, payload, existing=before)
    _validate_enum_fields(conn, res, payload)

    cols = columns(conn, res)
    if res in STATE_FIELDS:
        state_field, _machine, _initial = STATE_FIELDS[res]
        if state_field in payload:
            _validate_transition(conn, res, before, payload[state_field], actor)

    if not payload:
        return before
    if "updated_at" in cols and "updated_at" not in payload:
        payload["updated_at"] = db.now_iso()
    for key in payload:
        payload[key] = _normalize_scalar(payload[key])

    sets = ", ".join('"%s" = ?' % k for k in payload.keys())
    args = list(payload.values()) + [item_id]
    try:
        with db.transaction(conn):
            conn.execute('UPDATE "%s" SET %s WHERE id = ?' % (spec["table"], sets), args)
            after = get_item(conn, res, item_id)
            db.record_write(conn, actor=actor, action="UPDATE", entity_type=res,
                            entity_id=str(item_id), before=before, after=after,
                            summary="更新%s %s" % (res, item_id), ip=ip)
    except sqlite3.IntegrityError as exc:
        raise ConflictError("更新失败（约束冲突）：%s" % exc)
    except sqlite3.Error as exc:
        raise ApiError("更新失败：%s" % exc)
    return after


def delete_item(conn: sqlite3.Connection, res: str, item_id: str,
                actor: str = "local", ip: str = None) -> None:
    spec = get_spec(res)
    if spec.get("read_only"):
        raise ForbiddenError("只读资源不支持删除：%s" % res)
    before = get_item(conn, res, item_id)
    for parent_res, child_table, fk_col in DEPENDENTS:
        if RESOURCES[parent_res]["table"] != spec["table"]:
            continue
        try:
            hit = conn.execute(
                'SELECT 1 FROM "%s" WHERE "%s" = ? LIMIT 1' % (child_table, fk_col), (item_id,)
            ).fetchone()
        except sqlite3.Error:
            hit = None
        if hit is not None:
            raise ConflictError("存在关联数据（%s.%s），禁止删除：%s/%s"
                                % (child_table, fk_col, res, item_id))
    try:
        with db.transaction(conn):
            conn.execute('DELETE FROM "%s" WHERE id = ?' % spec["table"], (item_id,))
            db.record_write(conn, actor=actor, action="DELETE", entity_type=res,
                            entity_id=str(item_id), before=before, after=None,
                            summary="删除%s %s" % (res, item_id), ip=ip)
    except sqlite3.IntegrityError as exc:
        raise ConflictError("删除失败（外键约束）：%s" % exc)
    except sqlite3.Error as exc:
        raise ApiError("删除失败：%s" % exc)


# ---------------------------------------------------------------------------
# 报表辅助
# ---------------------------------------------------------------------------
def status_counts(conn: sqlite3.Connection, table: str, column: str = "status") -> dict:
    try:
        rows = conn.execute(
            'SELECT "%s" AS k, COUNT(*) AS c FROM "%s" GROUP BY "%s" ORDER BY c DESC'
            % (column, table, column)
        ).fetchall()
        return {str(r["k"]): int(r["c"]) for r in rows if r["k"] is not None}
    except sqlite3.Error:
        return {}


def find_by(conn: sqlite3.Connection, table: str, **filters) -> list:
    """内部使用：按列等值查询（列名来自代码常量，不接用户输入）。"""
    where = " AND ".join('"%s" = ?' % k for k in filters)
    args = list(filters.values())
    try:
        rows = conn.execute('SELECT * FROM "%s" WHERE %s' % (table, where), args).fetchall()
        return [_row_to_dict(r) for r in rows]
    except sqlite3.Error:
        return []
