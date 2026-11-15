# -*- coding: utf-8 -*-
"""CCGS 数据库连接管理、建表、事务与审计/活动写入。

- 默认库：<项目根>/data/runtime/app.db；环境变量 CCGS_DB_PATH 可覆盖（相对路径按项目根解析）。
- WAL + 外键开启；所有时间字段为 ISO-8601 文本（+08:00）。
- audit_logs / project_activities 为系统写，before/after JSON 截断 2000 字符。
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 项目根：app/backend/db.py -> app/backend -> app -> 根
ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "app" / "data" / "schema.sql"
DEFAULT_DB_REL = Path("data") / "runtime" / "app.db"
BACKUP_DIR = ROOT / "backups"

TZ = timezone(timedelta(hours=8))
AUDIT_TEXT_LIMIT = 2000

TABLES = [
    "companies",
    "demand_opportunities",
    "compute_supply_resources",
    "compute_specifications",
    "evidence_registry",
    "supplier_verification",
    "demand_qualification",
    "matching_records",
    "procurement_analyses",
    "commercial_opportunities",
    "quotes",
    "contracts_metadata",
    "agent_tasks",
    "project_activities",
    "knowledge_records",
    "audit_logs",
    "approvals",
    "backup_records",
]


def now_iso() -> str:
    """当前时间，东八区 ISO-8601，秒级精度。"""
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def today_stamp() -> str:
    return datetime.now(TZ).strftime("%Y%m%d")


def resolve_db_path(raw: str = "") -> Path:
    """把 db 路径解析为绝对路径；空值走默认 data/runtime/app.db。"""
    text = (raw or os.environ.get("CCGS_DB_PATH") or "").strip()
    if not text:
        return ROOT / DEFAULT_DB_REL
    p = Path(text)
    if not p.is_absolute():
        p = ROOT / p
    return p


def db_path() -> Path:
    return resolve_db_path()


def rel_to_root(path) -> str:
    """返回相对项目根的 POSIX 风格路径；不在根内则返回绝对路径字符串。"""
    p = Path(path).resolve()
    try:
        return p.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(p)


def connect(path=None) -> sqlite3.Connection:
    """打开连接：自动建目录、WAL、外键、Row 工厂。"""
    p = Path(path) if path else db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=15000")
    except sqlite3.Error:
        # 只读介质等极端场景不阻断连接建立
        pass
    return conn


def read_schema_sql() -> str:
    if SCHEMA_PATH.exists():
        return SCHEMA_PATH.read_text(encoding="utf-8")
    # 兜底：文件缺失时给出最小可运行 schema（不改变契约语义）
    return (
        "CREATE TABLE IF NOT EXISTS companies (id TEXT PRIMARY KEY, name TEXT NOT NULL);"
    )


def ensure_schema(path=None) -> sqlite3.Connection:
    """幂等建表并返回连接（调用方负责 close）。"""
    conn = connect(path)
    conn.executescript(read_schema_sql())
    conn.commit()
    return conn


def init_db(path=None) -> dict:
    """建表 + 基础信息，返回 {"db_path":..., "tables":...}。"""
    conn = ensure_schema(path)
    try:
        return {"db_path": rel_to_root(db_path() if path is None else path),
                "tables": list_tables(conn)}
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection):
    """事务 helper：异常回滚，正常提交。"""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        return row is not None
    except sqlite3.Error:
        return False


def list_tables(conn: sqlite3.Connection) -> list:
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return [r["name"] for r in rows]
    except sqlite3.Error:
        return []


def table_columns(conn: sqlite3.Connection, table: str) -> list:
    try:
        rows = conn.execute('PRAGMA table_info("%s")' % table.replace('"', "")).fetchall()
        return [r["name"] for r in rows]
    except sqlite3.Error:
        return []


def safe_count(conn: sqlite3.Connection, table: str) -> int:
    """缺表/异常时返回 0，保证 dashboard/health 不崩。"""
    try:
        row = conn.execute('SELECT COUNT(*) AS c FROM "%s"' % table.replace('"', "")).fetchone()
        return int(row["c"]) if row else 0
    except sqlite3.Error:
        return 0


def _truncate_json(payload, limit: int = AUDIT_TEXT_LIMIT):
    if payload is None:
        return None
    if isinstance(payload, str):
        text = payload
    else:
        try:
            text = json.dumps(payload, ensure_ascii=False, default=str)
        except Exception:
            text = str(payload)
    if len(text) > limit:
        text = text[:limit]
    return text


def audit(conn: sqlite3.Connection, actor: str, action: str, entity: str = "",
          entity_id: str = "", before=None, after=None, ip: str = None,
          note: str = None) -> None:
    """写审计日志（append-only）。before/after 序列化并截断到 2000 字符。"""
    conn.execute(
        "INSERT INTO audit_logs (ts, actor, action, entity, entity_id, before_json, after_json, ip, note) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (now_iso(), actor or "local", action or "", entity or "", entity_id or "",
         _truncate_json(before), _truncate_json(after), ip, note),
    )


def activity(conn: sqlite3.Connection, actor: str, action: str, entity_type: str = "",
             entity_id: str = "", summary: str = "", detail: str = None) -> None:
    """写项目活动时间线。"""
    conn.execute(
        "INSERT INTO project_activities (ts, actor, action, entity_type, entity_id, summary, detail) "
        "VALUES (?,?,?,?,?,?,?)",
        (now_iso(), actor or "local", action or "", entity_type or "", entity_id or "",
         summary or "", detail),
    )


def record_write(conn: sqlite3.Connection, actor: str, action: str, entity_type: str,
                 entity_id: str, before=None, after=None, summary: str = "",
                 detail: str = None, ip: str = None) -> None:
    """一次写入同时记录审计与活动（CRUD 统一入口）。"""
    audit(conn, actor=actor, action=action, entity=entity_type, entity_id=entity_id,
          before=before, after=after, ip=ip)
    activity(conn, actor=actor, action=action, entity_type=entity_type,
             entity_id=entity_id, summary=summary or action, detail=detail)


if __name__ == "__main__":  # 便于 `python -m app.backend.db` 初始化
    info = init_db()
    print("DB initialized:", info["db_path"])
    print("Tables:", ", ".join(info["tables"]))
