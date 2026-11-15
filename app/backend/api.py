# -*- coding: utf-8 -*-
"""CCGS 后端 API（Flask Blueprint，挂载 /api）。

实现 docs/07_ai_system/SPEC_API.md：
- 18 个通用 CRUD 资源（activities / audit-logs / backups 只读）
- health / dashboard / match / export / import / backup / restore / search
- agents / skills / agent-tasks run / approvals / reports / state / health-db

所有请求在本机运行（127.0.0.1），X-Actor 缺省 local；写操作均落 audit_logs + project_activities。
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import traceback
from contextlib import contextmanager
from pathlib import Path

from flask import Blueprint, Response, jsonify, request

from . import backup as backup_mod
from . import csv_io, db, matching, repo

ROOT = db.ROOT
AGENTS_DIR = ROOT / "agents"
SKILLS_DIR = ROOT / ".dsh" / "skills"
WEB_DIR = ROOT / "app" / "web"

bp = Blueprint("ccgs_api", __name__, url_prefix="/api")

VERSION = "1.0.0"

# 跨表搜索范围
SEARCH_SOURCES = [
    ("company", "companies", "name", ["name", "business_summary", "notes", "country", "region"]),
    ("demand", "demand_opportunities", "title", ["title", "location_preference", "gpu_models", "compliance_notes"]),
    ("supply", "compute_supply_resources", "gpu_model", ["gpu_model", "datacenter", "location_city", "notes"]),
    ("evidence", "evidence_registry", "claim", ["claim", "source_title", "notes"]),
    ("knowledge", "knowledge_records", "title", ["title", "content_md", "tags"]),
]
SEARCH_TABLES = {
    "company": ("companies", "name"),
    "demand": ("demand_opportunities", "title"),
    "supply": ("compute_supply_resources", "gpu_model"),
    "evidence": ("evidence_registry", "claim"),
    "knowledge": ("knowledge_records", "title"),
}


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def _actor() -> str:
    raw = (request.headers.get("X-Actor") or "local").strip()
    return (raw or "local")[:120]


def _ip() -> str:
    return request.remote_addr or ""


def _json_body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise repo.ValidationError("请求体必须是 JSON 对象（Content-Type: application/json）")
    return data


@contextmanager
def _connection():
    conn = db.connect()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass


def _safe_scalar(conn, sql: str, args=(), default=0):
    try:
        row = conn.execute(sql, args).fetchone()
        if row is None or row[0] is None:
            return default
        return row[0]
    except sqlite3.Error:
        return default


def _count_table(conn, table: str) -> int:
    try:
        return db.safe_count(conn, table)
    except sqlite3.Error:
        return 0


def _like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _snippet(row: dict, fields: list, keyword: str, limit: int = 140) -> str:
    lowered = keyword.lower()
    for field in fields:
        text = row.get(field)
        if not text or not isinstance(text, str):
            continue
        index = text.lower().find(lowered)
        if index >= 0:
            start = max(0, index - 40)
            return text[start:start + limit]
        if text.strip():
            return text[:limit]
    return ""


# ---------------------------------------------------------------------------
# 错误处理
# ---------------------------------------------------------------------------
def register_error_handlers(app) -> None:
    @app.errorhandler(repo.ApiError)
    def _handle_api_error(exc):  # noqa: ANN001
        error = {"code": exc.code, "message": exc.message}
        extra = getattr(exc, "extra", None)
        if isinstance(extra, dict):
            for key, value in extra.items():
                error.setdefault(key, value)
        return jsonify({"error": error}), getattr(exc, "status", 500)

    @app.errorhandler(404)
    def _handle_404(exc):  # noqa: ANN001
        if request.path.startswith("/api/"):
            return jsonify({"error": {"code": "NOT_FOUND",
                                      "message": "接口或记录不存在：%s" % request.path}}), 404
        return exc

    @app.errorhandler(405)
    def _handle_405(exc):  # noqa: ANN001
        if request.path.startswith("/api/"):
            return jsonify({"error": {"code": "METHOD_NOT_ALLOWED",
                                      "message": "方法不允许：%s %s" % (request.method, request.path)}}), 405
        return exc

    @app.errorhandler(Exception)
    def _handle_unexpected(exc):  # noqa: ANN001
        traceback.print_exc()
        return jsonify({"error": {"code": "INTERNAL", "message": "服务器内部错误：%s" % exc}}), 500


# ---------------------------------------------------------------------------
# 通用 CRUD
# ---------------------------------------------------------------------------
@bp.route("/<res>", methods=["GET"])
def list_resource(res: str):
    with _connection() as conn:
        params = dict(request.args)
        data = repo.list_items(conn, res, params)
        return jsonify(data)


@bp.route("/<res>", methods=["POST"])
def create_resource(res: str):
    data = _json_body()
    actor, ip = _actor(), _ip()
    with _connection() as conn:
        item = repo.create_item(conn, res, data, actor=actor, ip=ip)
        return jsonify({"item": item}), 201


@bp.route("/<res>/<item_id>", methods=["GET", "PUT", "PATCH", "DELETE"])
def item_resource(res: str, item_id: str):
    actor, ip = _actor(), _ip()
    if request.method == "GET":
        with _connection() as conn:
            return jsonify({"item": repo.get_item(conn, res, item_id)})
    if request.method == "DELETE":
        with _connection() as conn:
            repo.delete_item(conn, res, item_id, actor=actor, ip=ip)
        return Response(status=204)
    data = _json_body()
    with _connection() as conn:
        item = repo.update_item(conn, res, item_id, data, actor=actor, ip=ip,
                                partial=(request.method == "PATCH"))
        return jsonify({"item": item})


# ---------------------------------------------------------------------------
# 健康检查 / 总览
# ---------------------------------------------------------------------------
@bp.route("/health", methods=["GET"])
def health():
    try:
        conn = db.connect()
        try:
            tables = len(db.list_tables(conn))
        finally:
            conn.close()
        return jsonify({"status": "ok", "version": VERSION, "db": db.rel_to_root(db.db_path()),
                        "time": db.now_iso(), "tables": tables})
    except Exception as exc:  # noqa: BLE001 - 健康检查不能崩
        return jsonify({"status": "degraded", "version": VERSION,
                        "db": db.rel_to_root(db.db_path()), "time": db.now_iso(),
                        "tables": 0, "error": str(exc)})


@bp.route("/dashboard", methods=["GET"])
def dashboard():
    with _connection() as conn:
        counts = {
            "companies": _count_table(conn, "companies"),
            "suppliers": _safe_scalar(conn, "SELECT COUNT(*) FROM companies WHERE company_type='SUPPLIER'"),
            "demanders": _safe_scalar(conn, "SELECT COUNT(*) FROM companies WHERE company_type='DEMANDER'"),
            "supplies": _count_table(conn, "compute_supply_resources"),
            "demands": _count_table(conn, "demand_opportunities"),
            "evidence": _count_table(conn, "evidence_registry"),
            "matches": _count_table(conn, "matching_records"),
            "opportunities": _count_table(conn, "commercial_opportunities"),
            "agent_tasks": _count_table(conn, "agent_tasks"),
            "pending_approvals": _safe_scalar(conn, "SELECT COUNT(*) FROM approvals WHERE status='PENDING'"),
            "knowledge": _count_table(conn, "knowledge_records"),
        }
        grades = {grade: 0 for grade in repo.LEAD_GRADES}
        try:
            for row in conn.execute(
                    "SELECT lead_grade AS g, COUNT(*) AS c FROM demand_opportunities GROUP BY lead_grade"):
                if row["g"] in grades:
                    grades[row["g"]] = int(row["c"])
        except sqlite3.Error:
            pass
        verification = {
            "verified": _safe_scalar(conn, "SELECT COUNT(*) FROM compute_supply_resources WHERE verified=1"),
            "needs_verification": _safe_scalar(
                conn, "SELECT COUNT(*) FROM compute_supply_resources WHERE verified=0"),
            "rejected": _safe_scalar(conn, "SELECT COUNT(*) FROM companies WHERE status='REJECTED'"),
        }
        try:
            recent = repo.list_items(conn, "activities", {"page_size": "10"})["items"]
        except Exception:  # noqa: BLE001
            recent = []
        github_approved = _safe_scalar(
            conn, "SELECT COUNT(*) FROM approvals WHERE approval_type='GITHUB_VISIBILITY' "
                  "AND status='APPROVED'")
        alerts = [
            {"level": "WARN", "code": "NO_LEGAL_ENTITY",
             "message": "公司主体未设立，签约与收款为 BLOCKED"},
        ]
        if not github_approved:
            alerts.append({"level": "WARN", "code": "PUBLIC_REPO",
                           "message": "GitHub 仓库仍为 Public，建议 CEO 授权改 Private"})
        pipeline = {
            "supplier": repo.status_counts(conn, "compute_supply_resources", "status"),
            "demand": repo.status_counts(conn, "demand_opportunities", "status"),
            "opportunity": repo.status_counts(conn, "commercial_opportunities", "stage"),
        }
        return jsonify({"counts": counts, "pipeline": pipeline, "grades": grades,
                        "verification": verification, "recent_activities": recent,
                        "alerts": alerts, "time": db.now_iso()})


@bp.route("/health/db", methods=["GET"])
def health_db():
    with _connection() as conn:
        tables = []
        for name in db.list_tables(conn):
            tables.append({"table": name, "rows": _count_table(conn, name)})
        try:
            backups = backup_mod.list_backups(conn)["items"][:5]
        except Exception:  # noqa: BLE001
            backups = []
        return jsonify({"db": db.rel_to_root(db.db_path()), "tables": tables,
                        "table_count": len(tables), "recent_backups": backups,
                        "time": db.now_iso()})


# ---------------------------------------------------------------------------
# 匹配引擎
# ---------------------------------------------------------------------------
def _demand_with_company(conn, demand_id: str) -> dict:
    demand = repo.get_item(conn, "demands", demand_id)
    try:
        company = repo.get_item(conn, "companies", demand.get("company_id"))
        demand["company_country"] = company.get("country")
        demand["company_name"] = company.get("name")
    except repo.ApiError:
        demand["company_country"] = demand.get("location_preference")
    return demand


def _supply_with_company(conn, supply_id: str) -> dict:
    supply = repo.get_item(conn, "supplies", supply_id)
    try:
        company = repo.get_item(conn, "companies", supply.get("company_id"))
        supply["company_country"] = company.get("country")
        supply["company_name"] = company.get("name")
        supply["company_status"] = company.get("status")
        supply["company_trust_level"] = company.get("trust_level")
    except repo.ApiError:
        supply["company_country"] = supply.get("location_country")
    return supply


def _run_match(persist_default: bool):
    data = _json_body()
    persist = bool(data.get("persist", persist_default))
    demand_id = (data.get("demand_id") or "").strip()
    if not demand_id:
        raise repo.ValidationError("缺少必填字段：demand_id")
    supply_ids = data.get("supply_ids") or []
    if not isinstance(supply_ids, list):
        raise repo.ValidationError("supply_ids 必须是数组")
    actor, ip = _actor(), _ip()
    with _connection() as conn:
        demand = _demand_with_company(conn, demand_id)
        if supply_ids:
            supplies = []
            for supply_id in supply_ids:
                if not isinstance(supply_id, str) or not supply_id.strip():
                    raise repo.ValidationError("supply_ids 中存在非法 ID")
                supplies.append(_supply_with_company(conn, supply_id.strip()))
        else:
            supplies = [_supply_with_company(conn, row["id"]) for row in repo.all_rows(conn, "supplies")]
        results = []
        for supply in supplies:
            scored = matching.score_pair(demand, supply, conn=conn)
            result = {
                "demand_id": demand_id,
                "supply_id": supply["id"],
                "score": scored.get("score"),
                "dimensions": scored.get("dimensions") or {},
                "why_match": scored.get("why_match"),
                "why_not_match": scored.get("why_not_match"),
                "confidence": scored.get("confidence"),
                "recommendation": scored.get("recommendation"),
                "red_lines": scored.get("red_lines") or [],
                "risks": scored.get("risks"),
            }
            if persist:
                record = repo.create_item(conn, "matches", {
                    "demand_id": demand_id,
                    "supply_id": supply["id"],
                    "score": result["score"],
                    "match_dimensions": matching.dimensions_json(scored),
                    "why_match": result["why_match"],
                    "why_not_match": result["why_not_match"],
                    "risks": result["risks"],
                    "confidence": result["confidence"],
                    "recommendation": result["recommendation"],
                    "status": "DRAFT",
                    "analyst": actor,
                }, actor=actor, ip=ip)
                result["id"] = record["id"]
            results.append(result)
        results.sort(key=lambda item: (-(item.get("score") or 0), item.get("supply_id")))
        return jsonify({"demand_id": demand_id, "count": len(results), "results": results,
                        "persisted": bool(persist), "time": db.now_iso()})


@bp.route("/match/run", methods=["POST"])
def match_run():
    return _run_match(True)


@bp.route("/match/score", methods=["POST"])
def match_score():
    return _run_match(False)


# ---------------------------------------------------------------------------
# CSV 导出 / 导入
# ---------------------------------------------------------------------------
@bp.route("/export", methods=["GET"])
def export_entity():
    entity = (request.args.get("entity") or "").strip()
    if not entity:
        raise repo.ValidationError("缺少参数：entity")
    fmt = (request.args.get("format") or "csv").strip().lower()
    if fmt != "csv":
        raise repo.ValidationError("format 仅支持 csv")
    with _connection() as conn:
        filename, payload = csv_io.export_csv(conn, entity)
    response = Response(payload, content_type="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = 'attachment; filename="%s"' % filename
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@bp.route("/import", methods=["POST"])
def import_entity():
    entity = (request.args.get("entity") or "").strip()
    if not entity:
        raise repo.ValidationError("缺少参数：entity")
    mode = (request.args.get("mode") or "upsert").strip().lower()
    upload = request.files.get("file")
    if upload is not None:
        raw = upload.read()
    else:
        raw = request.get_data()
    if not raw:
        raise repo.ValidationError("缺少 CSV 内容：请使用 multipart 字段 file 或 text/csv 原始 body")
    actor = _actor()
    with _connection() as conn:
        result = csv_io.import_csv(conn, entity, raw, mode=mode, actor=actor)
    return jsonify(result)


# ---------------------------------------------------------------------------
# 备份 / 恢复
# ---------------------------------------------------------------------------
@bp.route("/backup", methods=["POST"])
def create_backup():
    data = request.get_json(silent=True) or {}
    note = str(data.get("note") or "").strip()
    with _connection() as conn:
        record = backup_mod.create_backup(conn, note=note, actor=_actor())
    return jsonify(record)


@bp.route("/backup/restore", methods=["POST"])
def restore_backup():
    data = _json_body()
    ref = data.get("id") or data.get("file_path")
    if not ref:
        raise repo.ValidationError("缺少备份标识：id 或 file_path")
    confirm = str(data.get("confirm") or "")
    conn = db.connect()
    try:
        result = backup_mod.restore_backup(conn, str(ref), confirm=confirm)
    except backup_mod.BackupError as exc:
        raise repo.ConflictError(str(exc))
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass
    # 恢复后重新连接写审计与活动
    try:
        conn = db.connect()
        try:
            db.record_write(conn, actor=_actor(), action="RESTORE", entity_type="backups",
                            entity_id=str(result.get("backup_id") or ref),
                            after={"restored_from": result.get("restored_from"),
                                   "sha256": result.get("sha256")},
                            summary="从备份恢复数据库：%s" % result.get("restored_from"))
            conn.commit()
        finally:
            conn.close()
    except sqlite3.Error:
        pass
    safety = result.get("safety_backup") or {}
    return jsonify({"restored": True,
                    "safety_backup": safety.get("id") if isinstance(safety, dict) else None,
                    "safety_backup_detail": safety,
                    "restored_from": result.get("restored_from"),
                    "sha256": result.get("sha256")})


# ---------------------------------------------------------------------------
# 跨表搜索
# ---------------------------------------------------------------------------
@bp.route("/search", methods=["GET"])
def search():
    keyword = (request.args.get("q") or "").strip()
    if not keyword:
        raise repo.ValidationError("缺少参数：q")
    try:
        limit = max(1, min(int(request.args.get("limit") or 20), 100))
    except ValueError:
        limit = 20
    pattern = "%" + _like(keyword) + "%"
    results = []
    with _connection() as conn:
        for kind, table, title_col, fields in SEARCH_SOURCES:
            cols = set(db.table_columns(conn, table))
            searchable = [col for col in fields if col in cols]
            if not searchable:
                continue
            where = " OR ".join('COALESCE("%s", \'\') LIKE ? ESCAPE \'\\\'' % col for col in searchable)
            try:
                rows = conn.execute(
                    'SELECT * FROM "%s" WHERE %s LIMIT ?' % (table, where),
                    [pattern] * len(searchable) + [limit * 3],
                ).fetchall()
            except sqlite3.Error:
                continue
            for row in rows:
                row = dict(row)
                title = row.get(title_col) or row.get("name") or row.get("id")
                lowered = keyword.lower()
                score = 1.0 if title and lowered in str(title).lower() else 0.6
                results.append({"type": kind, "id": row.get("id"), "title": title,
                                "snippet": _snippet(row, searchable, keyword), "score": score})
    results.sort(key=lambda item: (-item["score"], item["type"], str(item["id"])))
    results = results[:limit]
    return jsonify({"query": keyword, "total": len(results), "results": results})


# ---------------------------------------------------------------------------
# Agent / Skill 元数据
# ---------------------------------------------------------------------------
@bp.route("/agents", methods=["GET"])
def agents():
    path = AGENTS_DIR / "registry.json"
    if not path.exists():
        return jsonify({"agents": [], "items": [], "count": 0,
                        "note": "agents/registry.json 尚不存在（可能尚未生成），稍后重试"})
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return jsonify({"agents": [], "items": [], "count": 0,
                        "note": "agents/registry.json 读取失败：%s" % exc})
    if isinstance(payload, list):
        return jsonify({"agents": payload, "items": payload, "count": len(payload),
                        "source": "agents/registry.json"})
    if isinstance(payload, dict):
        payload.setdefault("items", payload.get("agents") or [])
        payload.setdefault("count", len(payload.get("items") or []))
        payload["source"] = "agents/registry.json"
        return jsonify(payload)
    return jsonify({"agents": [], "items": [], "count": 0, "note": "registry.json 结构未知"})


def _parse_frontmatter(text: str) -> dict:
    """极简 frontmatter 解析（key: value 与 - 列表），不依赖 PyYAML。"""
    data = {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return data
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        return data
    current = None
    for line in lines[1:end]:
        if not line.strip() or line.strip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            key, value = match.group(1), match.group(2).strip()
            if value.startswith("[") and value.endswith("]"):
                data[key] = [part.strip().strip("\"'") for part in value[1:-1].split(",") if part.strip()]
            elif value:
                data[key] = value.strip("\"'")
            else:
                data[key] = []
            current = key
            continue
        item = re.match(r"^\s*-\s+(.*)$", line)
        if item and current:
            if not isinstance(data.get(current), list):
                data[current] = []
            data[current].append(item.group(1).strip().strip("\"'"))
    return data


def _skill_entry(skill_dir: Path) -> dict:
    path = skill_dir / "SKILL.md"
    entry = {"name": skill_dir.name, "title": "", "description": "",
             "inputs": [], "tools": [], "outputs": [], "path": db.rel_to_root(path)}
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return entry
    front = _parse_frontmatter(text)
    entry["name"] = front.get("name") or skill_dir.name
    entry["description"] = front.get("description") or front.get("summary") or ""
    for field in ("inputs", "tools", "outputs"):
        value = front.get(field)
        if isinstance(value, list):
            entry[field] = value
        elif isinstance(value, str) and value:
            entry[field] = [part.strip() for part in value.split(",") if part.strip()]
    for line in text.splitlines():
        if line.startswith("# "):
            entry["title"] = line[2:].strip()
            break
    if not entry["description"]:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith(("#", "---", ">", "|", "-", "*")) \
                    and not stripped.startswith("```"):
                entry["description"] = stripped[:200]
                break
    return entry


@bp.route("/skills", methods=["GET"])
def skills():
    if not SKILLS_DIR.exists():
        return jsonify({"skills": [], "items": [], "count": 0,
                        "note": ".dsh/skills 目录不存在，稍后重试"})
    entries = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        if not (skill_dir / "SKILL.md").exists():
            continue
        entries.append(_skill_entry(skill_dir))
    return jsonify({"skills": entries, "items": entries, "count": len(entries)})


# ---------------------------------------------------------------------------
# Agent 任务执行（委托 agents/runner.py）
# ---------------------------------------------------------------------------
@bp.route("/agent-tasks/<task_id>/run", methods=["POST"])
def run_agent_task(task_id: str):
    with _connection() as conn:
        task = repo.get_item(conn, "agent-tasks", task_id)
    runner_dir = str(ROOT)
    if runner_dir not in sys.path:
        sys.path.insert(0, runner_dir)
    try:
        from agents import runner  # noqa: PLC0415 - 可选依赖，延迟导入
        payload = runner.run_task(task_id, db=str(db.db_path()))
    except Exception as exc:  # noqa: BLE001 - 返回结构化失败，不透传异常
        return jsonify({"task_id": task_id, "status": "FAILED",
                        "error": str(exc), "output_path": task.get("output_path"),
                        "detail": "执行器异常；任务状态请以数据库实际值为准"})
    with _connection() as conn:
        try:
            row = repo.get_item(conn, "agent-tasks", task_id)
        except repo.ApiError:
            row = task
    status = (payload.get("status") if isinstance(payload, dict) else None) or row.get("status")
    return jsonify({"task_id": task_id, "status": status,
                    "result": payload.get("result") if isinstance(payload, dict) else payload,
                    "summary": payload.get("summary") if isinstance(payload, dict) else "",
                    "output_path": (payload.get("output_path") if isinstance(payload, dict) else None)
                    or row.get("output_path")})


# ---------------------------------------------------------------------------
# 审批
# ---------------------------------------------------------------------------
@bp.route("/approvals/pending", methods=["GET"])
def pending_approvals():
    with _connection() as conn:
        data = repo.list_items(conn, "approvals", {"status": "PENDING", "page_size": "200",
                                                   "sort": "-requested_at"})
        data["count"] = data["total"]
        return jsonify(data)


@bp.route("/approvals/<approval_id>/decide", methods=["POST"])
def decide_approval(approval_id: str):
    data = _json_body()
    decision = str(data.get("decision") or "").strip().upper()
    if decision not in ("APPROVED", "REJECTED", "RETURNED"):
        raise repo.ValidationError("decision 仅支持 APPROVED / REJECTED / RETURNED")
    decided_by = str(data.get("decided_by") or "CEO").strip() or "CEO"
    note = str(data.get("note") or "").strip()
    actor = decided_by
    with _connection() as conn:
        item = repo.update_item(conn, "approvals", approval_id, {
            "status": decision,
            "decided_by": decided_by,
            "decided_at": db.now_iso(),
            "decision_note": note,
        }, actor=actor, ip=_ip())
        db.activity(conn, actor=actor, action="DECIDE", entity_type="approvals",
                    entity_id=approval_id, summary="审批 %s：%s" % (approval_id, decision),
                    detail=note)
        conn.commit()
    return jsonify({"item": item, "decision": decision,
                    "note": "系统不会自动批准；审批结论仅记录，不自动升级业务状态"})


# ---------------------------------------------------------------------------
# 报表 / 状态机
# ---------------------------------------------------------------------------
@bp.route("/reports/pipeline", methods=["GET"])
def report_pipeline():
    with _connection() as conn:
        counts = {
            "supplies": repo.status_counts(conn, "compute_supply_resources", "status"),
            "demands": repo.status_counts(conn, "demand_opportunities", "status"),
            "opportunities": repo.status_counts(conn, "commercial_opportunities", "stage"),
            "matches": repo.status_counts(conn, "matching_records", "status"),
        }
        won = _safe_scalar(conn, "SELECT COUNT(*) FROM demand_opportunities WHERE status='WON'")
        total_demands = _safe_scalar(conn, "SELECT COUNT(*) FROM demand_opportunities")
        conversion = None
        data_insufficient = True
        if won and total_demands:
            conversion = {"demand_to_won": round(float(won) / float(total_demands), 4),
                          "won": won, "total_demands": total_demands}
            data_insufficient = False
        return jsonify({"counts": counts, "conversion": conversion,
                        "data_insufficient": data_insufficient,
                        "note": "无成交历史：转化率返回 null；不对外承诺任何成交数字",
                        "time": db.now_iso()})


@bp.route("/reports/fee-scenarios", methods=["GET"])
def report_fee_scenarios():
    return jsonify({
        "example_only": True,
        "disclaimer": "以下仅为收费结构示例，不构成报价；费率逐案商议、书面协议确认并经 CEO 审批，禁止写死费率。",
        "scenarios": [
            {"name": "成功费（成交后）", "when": "撮合成功并签约后",
             "fee_basis": "按合同金额的协商比例（占位符 X%，逐案确认）",
             "risk": "需明确成功定义、付款节点与退费条件"},
            {"name": "固定服务费（分阶段）", "when": "研究/核验/引荐阶段",
             "fee_basis": "按阶段工作量协商（占位符 Y，逐案确认）",
             "risk": "需明确交付物与验收标准"},
            {"name": "买方付费（采购顾问）", "when": "代表需求方做采购分析",
             "fee_basis": "按项目协商（占位符 Z，逐案确认）",
             "risk": "须披露与供给方的利益冲突"},
        ],
        "approval": "收费框架须 CEO 审批（approval_type=FEE_FRAMEWORK）",
        "time": db.now_iso(),
    })


@bp.route("/state/transitions", methods=["GET"])
def state_transitions():
    state_fields = {}
    for res, value in repo.STATE_FIELDS.items():
        state_fields[res] = {"field": value[0], "machine": value[1], "initial": value[2]}
    return jsonify({
        "transitions": repo.TRANSITIONS,
        "states": {"supplier": repo.SUPPLIER_STATES, "demand": repo.DEMAND_STATES},
        "state_fields": state_fields,
        "note": "状态迁移由后端强校验；非法迁移返回 409 CONFLICT 并给出允许目标状态",
    })
