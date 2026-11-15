"""CCGS deterministic agent task runner (Python 3.9, standard library only).

Responsibilities
----------------
* Validate ``agents/registry.json`` and ``.dsh/skills/*/SKILL.md`` consistency.
* Create / list / inspect ``agent_tasks`` rows and execute deterministic task
  types without any LLM, network access or business-data mutation:

  - ``data_audit``       table counts, grade/status distributions, invalid
                         status values, entities without evidence
  - ``evidence_check``   evidence rows with missing url / confidence /
                         cross-verification
  - ``csv_ingest``       validate ``data/import/*.csv`` headers and enums
                         (never writes business tables)
  - ``match_compute``    try ``app.backend.matching`` first, otherwise use the
                         built-in equivalent of the documented 8-dimension
                         scoring model; the implementation source is recorded
  - ``report_render``    render a Markdown report from funnel/match data
  - ``schema_validate``  compare schema.sql / SPEC_DATABASE.md / live DB

The runner is read-only on business data. It only writes its own task status
(``agent_tasks``) plus side-effect rows in ``project_activities`` /
``audit_logs`` when those tables exist, and artifact files under
``data/runtime/agent_outputs/`` (gitignored).

CLI
---
    python -m agents.runner list
    python -m agents.runner show "Matching Engine"
    python -m agents.runner create --agent "Data Manager" --type data_audit --title "..."
    python -m agents.runner run TASK-20261116-001
    python -m agents.runner run-all --status QUEUED
    python -m agents.runner validate

Database path: ``CCGS_DB_PATH`` env var, default ``data/runtime/app.db``.
Task IDs are TEXT: ``TASK-YYYYMMDD-NNN`` (consistent with the backend repo).
"""

from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import sqlite3
import sys
import traceback
from pathlib import Path

# 支持 `python agents/runner.py ...` 与 `python -m agents.runner ...` 两种入口：
# 确保项目根在 sys.path，match_compute 才能按需 import app.backend.matching。
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

TASK_TYPES = (
    "data_audit",
    "evidence_check",
    "csv_ingest",
    "match_compute",
    "report_render",
    "schema_validate",
)

TASK_STATUSES = ("QUEUED", "RUNNING", "DONE", "BLOCKED", "FAILED", "CANCELLED")

EXPECTED_AGENT_COUNT = 11

EXPECTED_AGENTS = (
    "Research Director",
    "Global Demand Intelligence",
    "China Supply Intelligence",
    "Supplier Verification",
    "Compute Analyst",
    "Matching Engine",
    "Procurement Analyst",
    "Cross-border Research",
    "Commercial Operations",
    "Data Manager",
    "QA",
)

EXPECTED_SKILLS = (
    "global-demand-research",
    "china-compute-supply-research",
    "supplier-verification",
    "gpu-spec-normalization",
    "demand-qualification",
    "compute-matching",
    "procurement-analysis",
    "cross-border-risk-screening",
    "evidence-management",
    "commercial-operations",
)

EXPECTED_TABLES = (
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
)

EXPECTED_INDEXES = (
    "idx_companies_type",
    "idx_demands_status",
    "idx_supplies_status",
    "idx_evidence_subject",
    "idx_match_demand",
    "idx_audit_ts",
    "idx_activities_ts",
)

ALLOWED_TOOLS = (
    "web_search",
    "web_fetch",
    "read",
    "write",
    "edit",
    "python",
    "sqlite3",
    "csv",
    "git",
    "backend_api",
    "runner",
)

REQUIRED_AGENT_FIELDS = (
    "name",
    "display_name_zh",
    "role",
    "objective",
    "inputs",
    "tools",
    "skills",
    "outputs",
    "permissions",
    "approval_required",
    "task_types",
    "status",
    "notes",
)

SKILL_SECTIONS = (
    "## ① 输入",
    "## ② 操作步骤",
    "## ③ 工具要求",
    "## ④ 输出",
    "## ⑤ 质量标准",
    "## ⑥ 权限边界",
)

ENUM_CHECKS = (
    ("companies", "company_type", ("SUPPLIER", "DEMANDER", "PARTNER", "BOTH")),
    (
        "companies",
        "status",
        (
            "LEAD",
            "RESEARCHED",
            "NEEDS_VERIFICATION",
            "VERIFIED",
            "QUALIFIED",
            "ACTIVE",
            "INSUFFICIENT_INFO",
            "PAUSED",
            "EXPIRED",
            "REJECTED",
            "CEO_PENDING",
        ),
    ),
    ("companies", "trust_level", ("HIGH", "MEDIUM", "LOW", "UNVERIFIED")),
    (
        "demand_opportunities",
        "workload_type",
        ("TRAINING", "FINETUNE", "INFERENCE", "RENDERING", "SIMULATION", "MIXED"),
    ),
    (
        "demand_opportunities",
        "lead_grade",
        ("PUBLIC_LEAD", "INFERRED", "POTENTIAL", "VERIFIED", "QUALIFIED"),
    ),
    (
        "demand_opportunities",
        "status",
        (
            "LEAD",
            "RESEARCHED",
            "NEEDS_VERIFICATION",
            "VERIFIED",
            "QUALIFIED",
            "MATCHED",
            "COMMERCIAL",
            "WON",
            "LOST",
            "NOT_MATCHED",
            "PAUSED",
            "REJECTED",
            "CEO_PENDING",
        ),
    ),
    (
        "compute_supply_resources",
        "status",
        (
            "LEAD",
            "RESEARCHED",
            "NEEDS_VERIFICATION",
            "VERIFIED",
            "QUALIFIED",
            "ACTIVE",
            "INSUFFICIENT_INFO",
            "PAUSED",
            "EXPIRED",
            "REJECTED",
            "CEO_PENDING",
        ),
    ),
    (
        "evidence_registry",
        "subject_type",
        ("COMPANY", "DEMAND", "SUPPLY", "MATCH", "CLAIM", "OTHER"),
    ),
    ("evidence_registry", "confidence", ("HIGH", "MEDIUM", "LOW", "UNVERIFIED")),
    ("supplier_verification", "status", ("PENDING", "IN_REVIEW", "VERIFIED", "REJECTED")),
    ("demand_qualification", "status", ("PENDING", "IN_REVIEW", "QUALIFIED", "REJECTED")),
    ("matching_records", "status", ("DRAFT", "REVIEWED", "CEO_PENDING", "APPROVED", "REJECTED")),
    ("matching_records", "recommendation", ("ADVANCE", "NEED_MORE_INFO", "REJECT")),
    ("matching_records", "confidence", ("LOW", "MEDIUM", "HIGH")),
    (
        "commercial_opportunities",
        "stage",
        ("OPEN", "DISCLOSED", "INTRODUCED", "TERM_SHEET", "CA", "CLOSED_WON", "CLOSED_LOST"),
    ),
    (
        "commercial_opportunities",
        "model_type",
        ("ADVISORY", "INTRO", "CHANNEL", "JOINT", "PMC"),
    ),
    ("agent_tasks", "status", TASK_STATUSES),
    ("agent_tasks", "task_type", TASK_TYPES),
    ("approvals", "status", ("PENDING", "APPROVED", "REJECTED", "RETURNED")),
)

CSV_ENTITY_FIELDS = {
    "companies": ("name", "company_type", "country", "status", "trust_level"),
    "demand_opportunities": (
        "title",
        "workload_type",
        "lead_grade",
        "status",
        "min_gpu_count",
    ),
    "compute_supply_resources": (
        "company_id",
        "gpu_model",
        "gpu_count",
        "status",
        "verified",
    ),
    "evidence_registry": ("subject_type", "claim", "confidence", "url"),
    "compute_specifications": ("gpu_model", "vendor", "memory_gb"),
    "supplier_verification": ("supplier_company_id", "status", "score"),
    "demand_qualification": ("demand_id", "status", "score"),
    "matching_records": ("demand_id", "supply_id", "score", "recommendation"),
    "procurement_analyses": ("demand_id", "title", "status"),
    "commercial_opportunities": ("demand_id", "title", "stage"),
    "quotes": ("opportunity_id", "quote_type", "status"),
    "contracts_metadata": ("opportunity_id", "contract_type", "signature_status"),
    "approvals": ("approval_type", "subject", "status"),
    "agent_tasks": ("agent_name", "task_type", "title", "status"),
}

CSV_ENTITY_ALIASES = {
    "demand": "demand_opportunities",
    "demands": "demand_opportunities",
    "demand_opportunities": "demand_opportunities",
    "supply": "compute_supply_resources",
    "supplies": "compute_supply_resources",
    "compute_supply_resources": "compute_supply_resources",
    "company": "companies",
    "companies": "companies",
    "evidence": "evidence_registry",
    "evidence_registry": "evidence_registry",
    "spec": "compute_specifications",
    "specs": "compute_specifications",
    "specifications": "compute_specifications",
    "matching": "matching_records",
    "matches": "matching_records",
    "quotes": "quotes",
    "contracts": "contracts_metadata",
    "approvals": "approvals",
    "agent_tasks": "agent_tasks",
    "procurement": "procurement_analyses",
    "commercial": "commercial_opportunities",
}

REGION_KEYWORDS = {
    "middle east": ("UAE", "SAUDI", "QATAR", "KUWAIT", "OMAN", "BAHRAIN", "ISRAEL"),
    "中东": ("UAE", "SAUDI", "QATAR", "KUWAIT", "OMAN", "BAHRAIN", "ISRAEL"),
    "southeast asia": ("SINGAPORE", "MALAYSIA", "INDONESIA", "THAILAND", "VIETNAM", "PHILIPPINES"),
    "东南亚": ("SINGAPORE", "MALAYSIA", "INDONESIA", "THAILAND", "VIETNAM", "PHILIPPINES"),
    "europe": ("GERMANY", "FRANCE", "UK", "NETHERLANDS", "SWEDEN", "FINLAND", "POLAND"),
    "欧洲": ("GERMANY", "FRANCE", "UK", "NETHERLANDS", "SWEDEN", "FINLAND", "POLAND"),
    "asia pacific": ("SINGAPORE", "JAPAN", "KOREA", "MALAYSIA", "INDONESIA", "AUSTRALIA"),
    "亚太": ("SINGAPORE", "JAPAN", "KOREA", "MALAYSIA", "INDONESIA", "AUSTRALIA"),
}

COUNTRY_ALIASES = {
    "UAE": ("uae", "u.a.e", "united arab emirates", "阿联酋", "迪拜", "dubai", "abu dhabi"),
    "SAUDI": ("saudi", "ksa", "沙特", "riyadh", "jeddah"),
    "QATAR": ("qatar", "卡塔尔", "doha"),
    "SINGAPORE": ("singapore", "新加坡"),
    "MALAYSIA": ("malaysia", "马来西亚", "johor", "柔佛"),
    "INDONESIA": ("indonesia", "印尼", "印度尼西亚", "jakarta"),
    "JAPAN": ("japan", "日本", "tokyo"),
    "KOREA": ("korea", "韩国", "seoul"),
    "USA": ("usa", "u.s", "united states", "美国"),
    "UK": ("uk", "united kingdom", "英国", "london"),
    "GERMANY": ("germany", "德国", "frankfurt"),
    "CHINA": ("china", "中国", "mainland", "境内"),
    "HONG KONG": ("hong kong", "香港"),
}

GPU_FAMILY = {
    "H100": "hopper",
    "H200": "hopper",
    "H800": "hopper",
    "H20": "hopper",
    "GH200": "hopper",
    "B200": "blackwell",
    "B300": "blackwell",
    "GB200": "blackwell",
    "A100": "ampere",
    "A800": "ampere",
    "A40": "ampere",
    "A30": "ampere",
    "A10": "ampere",
    "3090": "ampere",
    "4090": "ada",
    "L40": "ada",
    "L40S": "ada",
    "L20": "ada",
    "MI300": "cdna3",
    "MI300X": "cdna3",
    "MI325X": "cdna3",
}

TRAINING_WORKLOADS = ("TRAINING", "FINETUNE")
INFERENCE_WORKLOADS = ("INFERENCE",)

RED_LINE_RESALE = "供应商无合法转售权（supplier_verification.resale_right_ok=0）"


class RunnerError(Exception):
    """Raised for usage / state errors (bad agent, bad task, missing DB)."""


class BlockedError(RunnerError):
    """Raised when a task cannot run because preconditions are missing."""


# ---------------------------------------------------------------------------
# Paths and database helpers
# ---------------------------------------------------------------------------


def repo_root():
    return Path(__file__).resolve().parents[1]


def db_path():
    env = os.environ.get("CCGS_DB_PATH", "").strip()
    root = repo_root()
    if env:
        p = Path(env)
        return p if p.is_absolute() else (root / p)
    return root / "data" / "runtime" / "app.db"


def output_dir():
    env = os.environ.get("CCGS_AGENT_OUTPUT_DIR", "").strip()
    root = repo_root()
    p = Path(env) if env else (root / "data" / "runtime" / "agent_outputs")
    if not p.is_absolute():
        p = root / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def import_dir():
    env = os.environ.get("CCGS_IMPORT_DIR", "").strip()
    root = repo_root()
    return Path(env) if env else (root / "data" / "import")


def registry_path():
    return repo_root() / "agents" / "registry.json"


def skills_dir():
    return repo_root() / ".dsh" / "skills"


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _ensure_db(path=None):
    p = Path(path) if path else db_path()
    if not p.exists():
        raise RunnerError(
            "数据库不存在：%s\n请先启动后端（python -m app.backend.server）或运行 scripts/init_db.ps1，"
            "也可用环境变量 CCGS_DB_PATH 指定数据库路径。" % p
        )
    return p


def _connect(path=None):
    p = _ensure_db(path)
    conn = sqlite3.connect(str(p), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _table_names(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r["name"] for r in rows]


def _has_table(conn, name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _columns(conn, table):
    return [r["name"] for r in conn.execute("PRAGMA table_info(%s)" % table).fetchall()]


def _count(conn, table):
    try:
        return conn.execute("SELECT COUNT(*) AS c FROM %s" % table).fetchone()["c"]
    except sqlite3.Error:
        return None


def _distribution(conn, table, column):
    if not _has_table(conn, table):
        return {}
    cols = _columns(conn, table)
    if column not in cols:
        return {}
    rows = conn.execute(
        "SELECT %s AS v, COUNT(*) AS c FROM %s GROUP BY %s ORDER BY c DESC"
        % (column, table, column)
    ).fetchall()
    out = {}
    for row in rows:
        key = row["v"] if row["v"] is not None else "(NULL)"
        out[str(key)] = row["c"]
    return out


def _store_path(path):
    try:
        return Path(path).resolve().relative_to(repo_root()).as_posix()
    except (ValueError, OSError):
        return str(path)


def _write_json(task, payload):
    path = output_dir() / ("%s_%s.json" % (task["id"], task["task_type"]))
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8")
    return path


def _write_text(task, suffix, text):
    path = output_dir() / ("%s_%s.%s" % (task["id"], task["task_type"], suffix))
    path.write_text(text, encoding="utf-8")
    return path


def _digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _truncate(text, limit=1000):
    text = str(text)
    return text if len(text) <= limit else text[: limit - 3] + "..."


# ---------------------------------------------------------------------------
# Registry and skill validation
# ---------------------------------------------------------------------------


def _read_frontmatter(text):
    meta = {}
    body = text
    if not text.startswith("---"):
        return meta, body
    parts = text.split("---", 2)
    if len(parts) < 3:
        return meta, body
    fm = parts[1]
    body = parts[2]
    current_key = None
    for raw in fm.splitlines():
        if not raw.strip():
            continue
        stripped = raw.strip()
        if stripped.startswith("- ") and current_key is not None:
            if not isinstance(meta.get(current_key), list):
                meta[current_key] = []
            meta[current_key].append(stripped[2:].strip())
            continue
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            current_key = key
            if value == "":
                meta[key] = []
            else:
                meta[key] = value
    return meta, body


def parse_skill(skill_name):
    directory = skills_dir() / skill_name
    path = directory / "SKILL.md"
    if not path.exists():
        return {"name": skill_name, "path": str(path), "exists": False, "problems": ["SKILL.md 不存在"]}
    text = path.read_text(encoding="utf-8")
    meta, body = _read_frontmatter(text)
    problems = []
    for field in ("name", "description", "version", "owner", "tools"):
        if not meta.get(field):
            problems.append("frontmatter 缺少 %s" % field)
    if meta.get("name") and meta["name"] != skill_name:
        problems.append("frontmatter name=%r 与目录名不一致" % meta["name"])
    if meta.get("version") and str(meta["version"]) != "1.0":
        problems.append("version 应为 1.0，实际 %r" % meta["version"])
    sections = {}
    for header in SKILL_SECTIONS:
        sections[header] = header in body
        if header not in body:
            problems.append("缺少章节 %s" % header)
    if len(body.strip()) < 300:
        problems.append("正文过短（<300 字符）")
    tools = meta.get("tools") or []
    if isinstance(tools, str):
        tools = [tools]
    return {
        "name": skill_name,
        "path": str(path),
        "exists": True,
        "meta": meta,
        "description": meta.get("description", ""),
        "version": str(meta.get("version", "")),
        "owner": meta.get("owner", ""),
        "tools": tools,
        "sections": sections,
        "problems": problems,
    }


def validate_skills():
    skills = []
    problems = []
    for name in EXPECTED_SKILLS:
        info = parse_skill(name)
        skills.append(info)
        for problem in info["problems"]:
            problems.append("%s: %s" % (name, problem))
    return {
        "ok": not problems,
        "expected": len(EXPECTED_SKILLS),
        "count": sum(1 for s in skills if s["exists"]),
        "skills": skills,
        "problems": problems,
    }


def load_registry():
    path = registry_path()
    if not path.exists():
        raise RunnerError("Agent 注册表不存在：%s" % path)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise RunnerError("registry.json 不是合法 JSON：%s" % exc)
    if not isinstance(data, list):
        raise RunnerError("registry.json 顶层必须是数组")
    return data


def get_agent(name):
    for agent in load_registry():
        if agent.get("name") == name:
            return agent
    return None


def validate_registry():
    problems = []
    agents = []
    try:
        data = load_registry()
    except RunnerError as exc:
        return {"ok": False, "count": 0, "agents": [], "problems": [str(exc)]}

    if len(data) != EXPECTED_AGENT_COUNT:
        problems.append("Agent 数量应为 %d，实际 %d" % (EXPECTED_AGENT_COUNT, len(data)))
    names = [a.get("name") for a in data if isinstance(a, dict)]
    if len(names) != len(set(names)):
        duplicates = sorted({n for n in names if names.count(n) > 1})
        problems.append("Agent name 重复：%s" % ", ".join(str(d) for d in duplicates))
    missing_agents = sorted(set(EXPECTED_AGENTS) - set(names))
    extra_agents = sorted(n for n in set(names) - set(EXPECTED_AGENTS) if n)
    if missing_agents:
        problems.append("缺少 Agent：%s" % ", ".join(missing_agents))
    if extra_agents:
        problems.append("多余 Agent：%s" % ", ".join(extra_agents))

    skill_names = set(EXPECTED_SKILLS)
    for agent in data:
        if not isinstance(agent, dict):
            problems.append("registry 成员必须是对象")
            continue
        label = agent.get("name") or "(未命名)"
        for field in REQUIRED_AGENT_FIELDS:
            if field not in agent:
                problems.append("%s: 缺少字段 %s" % (label, field))
        if agent.get("status") != "ACTIVE":
            problems.append("%s: status 应为 ACTIVE" % label)
        if not isinstance(agent.get("approval_required"), bool):
            problems.append("%s: approval_required 必须是布尔值" % label)
        for field in ("inputs", "tools", "skills", "outputs", "task_types"):
            value = agent.get(field)
            if not isinstance(value, list) or not value:
                problems.append("%s: %s 必须是非空数组" % (label, field))
        perms = agent.get("permissions")
        if not isinstance(perms, dict) or not isinstance(perms.get("read"), list) or not isinstance(
            perms.get("write"), list
        ):
            problems.append("%s: permissions 必须包含 read/write 数组" % label)
        for skill in agent.get("skills") or []:
            if skill not in skill_names:
                problems.append("%s: 引用未知 Skill %s" % (label, skill))
        for task_type in agent.get("task_types") or []:
            if task_type not in TASK_TYPES:
                problems.append("%s: 未知 task_type %s" % (label, task_type))
        for tool in agent.get("tools") or []:
            if tool not in ALLOWED_TOOLS:
                problems.append("%s: 未知工具 %s" % (label, tool))
        if not str(agent.get("display_name_zh", "")).strip():
            problems.append("%s: display_name_zh 为空" % label)
        agents.append(agent)

    return {
        "ok": not problems,
        "expected": EXPECTED_AGENT_COUNT,
        "count": len(data),
        "agents": [a.get("name") for a in data if isinstance(a, dict)],
        "problems": problems,
    }


def validate_database(path=None):
    p = Path(path) if path else db_path()
    info = {
        "checked": False,
        "path": str(p),
        "exists": p.exists(),
        "missing_tables": [],
        "missing_indexes": [],
        "counts": {},
        "problems": [],
        "note": "",
    }
    if not p.exists():
        info["note"] = "数据库不存在，跳过 DB 校验（registry/skills 校验不受影响）"
        return info
    try:
        conn = _connect(p)
        try:
            tables = _table_names(conn)
            info["checked"] = True
            info["missing_tables"] = [t for t in EXPECTED_TABLES if t not in tables]
            indexes = [
                r["name"]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            ]
            info["missing_indexes"] = [i for i in EXPECTED_INDEXES if i not in indexes]
            info["counts"] = {t: _count(conn, t) for t in EXPECTED_TABLES if t in tables}
            if info["missing_tables"]:
                info["problems"].append("缺少数据表：%s" % ", ".join(info["missing_tables"]))
            if info["missing_indexes"]:
                info["problems"].append("缺少索引：%s" % ", ".join(info["missing_indexes"]))
        finally:
            conn.close()
    except sqlite3.Error as exc:
        info["problems"].append("数据库读取失败：%s" % exc)
    return info


def validate_all():
    reg = validate_registry()
    skills = validate_skills()
    db = validate_database()
    ok = bool(reg["ok"] and skills["ok"])
    return {
        "ok": ok,
        "generated_at": _now(),
        "registry": reg,
        "skills": skills,
        "database": db,
    }


# ---------------------------------------------------------------------------
# Task persistence helpers
# ---------------------------------------------------------------------------


def _task_row(conn, task_id):
    return conn.execute("SELECT * FROM agent_tasks WHERE id=?", (task_id,)).fetchone()


def _side_effects(conn, actor, action, entity, entity_id, summary, detail, before=None, after=None):
    """Best-effort activity + audit writing. Returns skipped table list."""
    skipped = []
    ts = _now()
    if _has_table(conn, "project_activities"):
        try:
            conn.execute(
                "INSERT INTO project_activities (ts, actor, action, entity_type, entity_id, summary, detail)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ts, actor, action, entity, str(entity_id), _truncate(summary), _truncate(detail, 2000)),
            )
        except sqlite3.Error as exc:
            skipped.append("project_activities: %s" % exc)
    else:
        skipped.append("project_activities: table missing")
    if _has_table(conn, "audit_logs"):
        try:
            conn.execute(
                "INSERT INTO audit_logs (ts, actor, action, entity, entity_id, before_json, after_json, ip, note)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ts,
                    actor,
                    action,
                    entity,
                    str(entity_id),
                    json.dumps(before, ensure_ascii=False) if before is not None else None,
                    json.dumps(after, ensure_ascii=False) if after is not None else None,
                    None,
                    _truncate(detail, 1900),
                ),
            )
        except sqlite3.Error as exc:
            skipped.append("audit_logs: %s" % exc)
    else:
        skipped.append("audit_logs: table missing")
    try:
        conn.commit()
    except sqlite3.Error:
        pass
    return skipped


def _update_task(conn, task_id, **fields):
    if not fields:
        return
    fields["updated_at"] = _now()
    keys = sorted(fields.keys())
    sql = "UPDATE agent_tasks SET %s WHERE id=?" % ", ".join("%s=?" % k for k in keys)
    conn.execute(sql, [fields[k] for k in keys] + [task_id])
    conn.commit()


def _new_task_id(conn):
    """生成 TASK-YYYYMMDD-NNN，与 app.backend.repo.generate_id 的命名规则一致。"""
    stamp = datetime.datetime.now().strftime("%Y%m%d")
    prefix = "TASK-%s-" % stamp
    row = None
    try:
        row = conn.execute(
            "SELECT id FROM agent_tasks WHERE id LIKE ? ORDER BY id DESC LIMIT 1",
            (prefix + "%",),
        ).fetchone()
    except sqlite3.Error:
        row = None
    seq = 1
    if row is not None:
        match = re.search(r"(\d+)$", str(row["id"]))
        if match:
            seq = int(match.group(1)) + 1
    return "%s%03d" % (prefix, seq)


def create_task(agent_name, task_type, title, input_ref=None, priority="P2", requires_approval=False, db=None):
    if agent_name not in EXPECTED_AGENTS:
        raise RunnerError("未知 Agent：%s（可选值见 agents/registry.json）" % agent_name)
    agent = get_agent(agent_name)
    if agent is None:
        raise RunnerError("Agent 未注册：%s" % agent_name)
    if task_type not in TASK_TYPES:
        raise RunnerError("未知 task_type：%s（可选：%s）" % (task_type, ", ".join(TASK_TYPES)))
    if not str(title or "").strip():
        raise RunnerError("--title 不能为空")

    conn = _connect(db)
    try:
        if not _has_table(conn, "agent_tasks"):
            raise RunnerError("agent_tasks 表不存在，数据库可能尚未初始化")
        task_id = _new_task_id(conn)
        try:
            conn.execute(
                "INSERT INTO agent_tasks"
                " (id, agent_name, task_type, title, input_ref, priority, status, requires_approval, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, 'QUEUED', ?, ?, ?)",
                (
                    task_id,
                    agent_name,
                    task_type,
                    title,
                    input_ref,
                    priority or "P2",
                    1 if requires_approval else 0,
                    _now(),
                    _now(),
                ),
            )
        except sqlite3.Error as exc:
            raise RunnerError("创建任务失败：%s" % exc)
        conn.commit()
        skipped = _side_effects(
            conn,
            "agents.runner",
            "agent_task.create",
            "agent_task",
            task_id,
            "创建 agent 任务：%s / %s" % (agent_name, task_type),
            "title=%s; input_ref=%s" % (title, input_ref or ""),
            after={"id": task_id, "agent_name": agent_name, "task_type": task_type, "title": title},
        )
        return {
            "task_id": task_id,
            "agent_name": agent_name,
            "task_type": task_type,
            "title": title,
            "status": "QUEUED",
            "input_ref": input_ref,
            "audit_skipped": skipped,
        }
    finally:
        conn.close()


def list_tasks(status=None, agent=None, limit=100):
    conn = _connect()
    try:
        if not _has_table(conn, "agent_tasks"):
            raise RunnerError("agent_tasks 表不存在，数据库可能尚未初始化")
        clauses = []
        params = []
        if status:
            clauses.append("status=?")
            params.append(status)
        if agent:
            clauses.append("agent_name=?")
            params.append(agent)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            "SELECT * FROM agent_tasks%s ORDER BY id DESC LIMIT ?" % where,
            params + [int(limit)],
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) AS c FROM agent_tasks%s" % where, params).fetchone()["c"]
        items = []
        for row in rows:
            item = dict(row)
            items.append(
                {
                    "id": item.get("id"),
                    "agent_name": item.get("agent_name"),
                    "task_type": item.get("task_type"),
                    "title": item.get("title"),
                    "status": item.get("status"),
                    "priority": item.get("priority"),
                    "input_ref": item.get("input_ref"),
                    "output_path": item.get("output_path"),
                    "started_at": item.get("started_at"),
                    "finished_at": item.get("finished_at"),
                    "result_summary": item.get("result_summary"),
                    "error": item.get("error"),
                }
            )
        return {"items": items, "total": total}
    finally:
        conn.close()


def show_agent(name):
    agent = get_agent(name)
    if agent is None:
        raise RunnerError("未知 Agent：%s（可选值见 agents/registry.json）" % name)
    skill_details = []
    for skill_name in agent.get("skills", []):
        info = parse_skill(skill_name)
        skill_details.append(
            {
                "name": skill_name,
                "exists": info["exists"],
                "description": info.get("description", ""),
                "owner": info.get("owner", ""),
                "version": info.get("version", ""),
                "tools": info.get("tools", []),
                "problems": info.get("problems", []),
            }
        )
    conn = _connect()
    try:
        counts = {}
        if _has_table(conn, "agent_tasks"):
            for row in conn.execute(
                "SELECT status AS s, COUNT(*) AS c FROM agent_tasks WHERE agent_name=? GROUP BY status",
                (name,),
            ).fetchall():
                counts[str(row["s"])] = row["c"]
            recent = [
                {
                    "id": r["id"],
                    "task_type": r["task_type"],
                    "title": r["title"],
                    "status": r["status"],
                }
                for r in conn.execute(
                    "SELECT * FROM agent_tasks WHERE agent_name=? ORDER BY id DESC LIMIT 10", (name,)
                ).fetchall()
            ]
        else:
            recent = []
    finally:
        conn.close()
    return {
        "agent": agent,
        "skill_details": skill_details,
        "task_counts": counts,
        "recent_tasks": recent,
    }


# ---------------------------------------------------------------------------
# Task handlers
# ---------------------------------------------------------------------------


def _evidence_less_entities(conn, subject_type, table, label_column):
    if not _has_table(conn, table) or not _has_table(conn, "evidence_registry"):
        return {"total": None, "items": [], "note": "表不存在，无法检查"}
    label = label_column if label_column in _columns(conn, table) else "id"
    rows = conn.execute(
        "SELECT t.id AS id, t.%s AS label FROM %s t WHERE NOT EXISTS ("
        " SELECT 1 FROM evidence_registry e WHERE e.subject_type=? AND CAST(e.subject_id AS TEXT)=CAST(t.id AS TEXT))"
        " ORDER BY t.id LIMIT 200" % (label, table),
        (subject_type,),
    ).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) AS c FROM %s t WHERE NOT EXISTS ("
        " SELECT 1 FROM evidence_registry e WHERE e.subject_type=? AND CAST(e.subject_id AS TEXT)=CAST(t.id AS TEXT))"
        % table,
        (subject_type,),
    ).fetchone()["c"]
    return {
        "total": total,
        "items": [
            {"id": r["id"], "label": r["label"] if r["label"] is not None else "(未命名)"} for r in rows
        ],
    }


def _orphan_evidence(conn):
    if not _has_table(conn, "evidence_registry"):
        return None
    mapping = {
        "COMPANY": "companies",
        "DEMAND": "demand_opportunities",
        "SUPPLY": "compute_supply_resources",
        "MATCH": "matching_records",
    }
    orphans = []
    for row in conn.execute(
        "SELECT id, subject_type, subject_id, claim FROM evidence_registry ORDER BY id"
    ).fetchall():
        table = mapping.get(str(row["subject_type"] or "").upper())
        if not table or not _has_table(conn, table):
            continue
        exists = conn.execute(
            "SELECT 1 FROM %s WHERE CAST(id AS TEXT)=CAST(? AS TEXT)" % table,
            (row["subject_id"],),
        ).fetchone()
        if not exists:
            orphans.append(
                {
                    "evidence_id": row["id"],
                    "subject_type": row["subject_type"],
                    "subject_id": row["subject_id"],
                    "claim": _truncate(row["claim"], 120),
                }
            )
    return orphans


def task_data_audit(conn, task):
    tables = set(_table_names(conn))
    counts = {t: _count(conn, t) for t in EXPECTED_TABLES if t in tables}
    missing_tables = [t for t in EXPECTED_TABLES if t not in tables]
    distributions = {
        "companies.status": _distribution(conn, "companies", "status"),
        "companies.company_type": _distribution(conn, "companies", "company_type"),
        "demand_opportunities.lead_grade": _distribution(
            conn, "demand_opportunities", "lead_grade"
        ),
        "demand_opportunities.status": _distribution(conn, "demand_opportunities", "status"),
        "compute_supply_resources.status": _distribution(
            conn, "compute_supply_resources", "status"
        ),
        "matching_records.recommendation": _distribution(
            conn, "matching_records", "recommendation"
        ),
        "supplier_verification.status": _distribution(conn, "supplier_verification", "status"),
        "demand_qualification.status": _distribution(conn, "demand_qualification", "status"),
        "agent_tasks.status": _distribution(conn, "agent_tasks", "status"),
    }

    invalid_status = []
    for table, column, allowed in ENUM_CHECKS:
        if table not in tables or column not in _columns(conn, table):
            continue
        for row in conn.execute(
            "SELECT %s AS v, COUNT(*) AS c FROM %s WHERE %s IS NOT NULL GROUP BY %s"
            % (column, table, column, column)
        ).fetchall():
            value = str(row["v"])
            if value not in allowed:
                invalid_status.append(
                    {"table": table, "column": column, "value": value, "count": row["c"]}
                )

    evidence_less = {
        "companies": _evidence_less_entities(conn, "COMPANY", "companies", "name"),
        "demand_opportunities": _evidence_less_entities(
            conn, "DEMAND", "demand_opportunities", "title"
        ),
        "compute_supply_resources": _evidence_less_entities(
            conn, "SUPPLY", "compute_supply_resources", "gpu_model"
        ),
    }

    result = {
        "generated_at": _now(),
        "task_id": task["id"],
        "agent_name": task["agent_name"],
        "db": _store_path(db_path()),
        "tables": {t: (t in tables) for t in EXPECTED_TABLES},
        "missing_tables": missing_tables,
        "counts": counts,
        "distributions": distributions,
        "invalid_status_values": invalid_status,
        "entities_without_evidence": evidence_less,
        "orphan_evidence": _orphan_evidence(conn),
        "notes": [
            "只读审计：runner 不修改业务数据。",
            "entities_without_evidence 按 evidence_registry.subject_type/subject_id 关联。",
            "invalid_status_values 为发现项，不代表 runner 会修复。",
        ],
    }
    path = _write_json(task, result)
    summary = "数据体检：%d 张表有数据；非法状态值 %d 项；无证据实体：公司 %s / 需求 %s / 供给 %s" % (
        len(counts),
        len(invalid_status),
        _none_text((evidence_less["companies"] or {}).get("total")),
        _none_text((evidence_less["demand_opportunities"] or {}).get("total")),
        _none_text((evidence_less["compute_supply_resources"] or {}).get("total")),
    )
    if missing_tables:
        summary += "；缺表 %d 张" % len(missing_tables)
    return {
        "status": "DONE",
        "result": result,
        "output_path": _store_path(path),
        "summary": summary,
    }


def _none_text(value):
    return "n/a" if value is None else str(value)


def task_evidence_check(conn, task):
    if not _has_table(conn, "evidence_registry"):
        raise BlockedError("evidence_registry 表不存在，请先初始化数据库")
    columns = _columns(conn, "evidence_registry")
    rows = [dict(r) for r in conn.execute("SELECT * FROM evidence_registry ORDER BY id").fetchall()]
    allowed_confidence = ("HIGH", "MEDIUM", "LOW", "UNVERIFIED")
    missing_url = []
    invalid_confidence = []
    unverified = []
    not_cross_verified = []
    missing_retrieved = []
    for row in rows:
        claim = _truncate(row.get("claim"), 140)
        base = {
            "evidence_id": row.get("id"),
            "subject_type": row.get("subject_type"),
            "subject_id": row.get("subject_id"),
            "claim": claim,
            "confidence": row.get("confidence"),
            "url": row.get("url"),
        }
        if not str(row.get("url") or "").strip() and not str(row.get("source_title") or "").strip():
            missing_url.append(base)
        confidence = str(row.get("confidence") or "").strip()
        if confidence not in allowed_confidence:
            invalid_confidence.append(base)
        if confidence == "UNVERIFIED":
            unverified.append(base)
        if not int(row.get("cross_verified") or 0):
            not_cross_verified.append(base)
        if not str(row.get("retrieved_at") or "").strip():
            missing_retrieved.append(base)

    result = {
        "generated_at": _now(),
        "task_id": task["id"],
        "agent_name": task["agent_name"],
        "db": _store_path(db_path()),
        "total": len(rows),
        "counts": {
            "missing_url_or_source_title": len(missing_url),
            "invalid_or_missing_confidence": len(invalid_confidence),
            "unverified": len(unverified),
            "not_cross_verified": len(not_cross_verified),
            "missing_retrieved_at": len(missing_retrieved),
        },
        "missing_url_or_source_title": missing_url,
        "invalid_or_missing_confidence": invalid_confidence,
        "unverified": unverified,
        "not_cross_verified": not_cross_verified,
        "missing_retrieved_at": missing_retrieved,
        "notes": [
            "待补清单：url/来源标题为空、confidence 缺失或非法、cross_verified=0 的条目。",
            "runner 只报告缺口，不修改 evidence_registry。",
        ],
    }
    path = _write_json(task, result)
    summary = "证据体检：共 %d 条；缺 URL/来源 %d；信任度缺失或非法 %d；未交叉验证 %d" % (
        len(rows),
        len(missing_url),
        len(invalid_confidence),
        len(not_cross_verified),
    )
    return {
        "status": "DONE",
        "result": result,
        "output_path": _store_path(path),
        "summary": summary,
    }


def _detect_csv_entity(path):
    stem = path.stem.lower()
    for alias in sorted(CSV_ENTITY_ALIASES.keys(), key=len, reverse=True):
        if alias in stem:
            return CSV_ENTITY_ALIASES[alias]
    return None


def task_csv_ingest(conn, task):
    directory = import_dir()
    if not directory.exists():
        raise BlockedError("导入目录不存在：%s" % directory)
    files = sorted(directory.glob("*.csv"))
    reports = []
    for path in files:
        report = {
            "file": str(path),
            "entity": _detect_csv_entity(path),
            "rows": 0,
            "columns": [],
            "missing_columns": [],
            "empty_required": [],
            "invalid_values": [],
            "errors": [],
        }
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                header = reader.fieldnames or []
                report["columns"] = header
                expected = CSV_ENTITY_FIELDS.get(report["entity"])
                if expected:
                    report["missing_columns"] = [c for c in expected if c not in header]
                seen = set()
                for index, row in enumerate(reader, start=2):
                    report["rows"] += 1
                    if not any(str(v or "").strip() for v in row.values()):
                        report["errors"].append({"line": index, "error": "空行"})
                        continue
                    if expected:
                        for column in expected:
                            if column not in header:
                                continue
                            if not str(row.get(column) or "").strip():
                                report["empty_required"].append({"line": index, "column": column})
                    key = str(row.get("id") or row.get(header[0]) if header else "").strip()
                    if key:
                        if key in seen:
                            report["invalid_values"].append(
                                {"line": index, "column": "id", "value": key, "error": "重复主键"}
                            )
                        seen.add(key)
                for table, column, allowed in ENUM_CHECKS:
                    if report["entity"] != table or column not in header:
                        continue
                    for row_index, row in enumerate(
                        csv.DictReader(open(path, "r", encoding="utf-8-sig", newline="")), start=2
                    ):
                        value = str(row.get(column) or "").strip()
                        if value and value not in allowed:
                            report["invalid_values"].append(
                                {
                                    "line": row_index,
                                    "column": column,
                                    "value": value,
                                    "error": "不在允许枚举内",
                                }
                            )
                if report["entity"] is None:
                    report["errors"].append(
                        {"line": 1, "error": "无法从文件名识别实体，仅做基础结构检查"}
                    )
        except (OSError, UnicodeDecodeError, csv.Error) as exc:
            report["errors"].append({"line": 0, "error": "读取失败：%s" % exc})
        for key in ("empty_required", "invalid_values", "errors"):
            if len(report[key]) > 50:
                report[key] = report[key][:50] + [{"truncated": len(report[key]) - 50}]
        reports.append(report)

    result = {
        "generated_at": _now(),
        "task_id": task["id"],
        "agent_name": task["agent_name"],
        "import_dir": str(directory),
        "files": len(files),
        "reports": reports,
        "total_rows": sum(r["rows"] for r in reports),
        "wrote_database": False,
        "notes": [
            "csv_ingest 只校验字段与枚举，不写数据库（避免与后端并发写冲突）。",
            "实际导入请使用后端 POST /api/import 或人工确认后执行。",
        ],
    }
    path = _write_json(task, result)
    problem_rows = sum(len(r["empty_required"]) + len(r["invalid_values"]) for r in reports)
    summary = "CSV 校验：%d 个文件、%d 行；问题记录 %d 条；未写库" % (
        len(files),
        result["total_rows"],
        problem_rows,
    )
    if not files:
        summary = "CSV 校验：%s 下无 CSV 文件；未写库" % directory
    return {
        "status": "DONE",
        "result": result,
        "output_path": _store_path(path),
        "summary": summary,
    }


# ---- matching --------------------------------------------------------------


def _parse_input_ref(input_ref):
    if not input_ref:
        return {}
    text = str(input_ref).strip()
    if text.startswith("{"):
        try:
            value = json.loads(text)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            pass
    parsed = {}
    # 业务 ID 为 TEXT（如 DEM-20261116-001 / SUP-20261116-002），同时兼容整数旧样例。
    for match in re.finditer(
        r"(demand_id|demand|supply_ids?|supplies?)\s*[:=]\s*(.*?)"
        r"(?=\s+(?:demand_id|demand|supply_ids?|supplies?)\s*[:=]|$)",
        text,
        re.I | re.S,
    ):
        key = match.group(1).lower()
        raw = match.group(2).strip()
        raw = raw.strip().strip("[]{}()")
        ids = [
            part.strip().strip("\"'")
            for part in re.split(r"[,;\s]+", raw)
            if part.strip().strip("\"'")
        ]
        if key.startswith("demand"):
            if ids:
                parsed["demand_id"] = ids[0]
        else:
            parsed.setdefault("supply_ids", []).extend(ids)
    return parsed


def _as_id(value):
    """把业务主键转成 TEXT 形式；空值返回 None。"""
    if value is None:
        return None
    text = str(value).strip().strip("\"'")
    if not text or text.lower() in ("none", "null"):
        return None
    return text


def _as_int(value):
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _as_bool(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "y", "是", "支持"):
        return True
    if text in ("0", "false", "no", "n", "否", "不支持"):
        return False
    return None


def _norm_gpu(value):
    text = str(value or "").upper().strip()
    text = re.sub(r"\b(NVIDIA|AMD|GPU|加速卡)\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _gpu_tokens(value):
    text = _norm_gpu(value)
    if not text:
        return []
    return [t for t in re.split(r"[,;/、|\s]+", text) if t]


def _gpu_family(token):
    for key in sorted(GPU_FAMILY.keys(), key=len, reverse=True):
        if key in token:
            return GPU_FAMILY[key]
    return None


def score_gpu_model(demand_gpu_models, supply_gpu_model):
    demand_tokens = _gpu_tokens(demand_gpu_models)
    supply_token = _norm_gpu(supply_gpu_model)
    if not demand_tokens:
        return 10, "需求未标注 GPU 型号，按未知处理（10/30）"
    if not supply_token:
        return 10, "供给未标注 GPU 型号，按未知处理（10/30）"
    for token in demand_tokens:
        if token == supply_token or token in supply_token or supply_token in token:
            return 30, "型号精确匹配：%s" % supply_token
    supply_family = _gpu_family(supply_token)
    for token in demand_tokens:
        family = _gpu_family(token)
        if family and supply_family and family == supply_family:
            return 20, "同代兼容：%s ≈ %s（%s）" % (supply_token, token, family)
    for token in demand_tokens:
        if _gpu_family(token) and supply_family:
            return 10, "跨代可替代：%s vs %s，需人工确认" % (supply_token, token)
    if _gpu_family(supply_token) is None:
        return 10, "供给型号未在已知族谱中，按可替代处理"
    return 0, "型号不兼容：%s vs %s" % (supply_token, ", ".join(demand_tokens))


def score_scale(demand_min, supply_sellable):
    demand = _as_int(demand_min)
    supply = _as_int(supply_sellable)
    if demand is None or demand <= 0:
        return 20, "需求未给出最小规模，不扣分"
    if supply is None or supply <= 0:
        return 5, "供给可售规模未知，按未知处理（5/20）"
    if supply >= demand:
        return 20, "可售 %d ≥ 需求最小 %d" % (supply, demand)
    deficit_pct = (demand - supply) / float(demand) * 100.0
    deduction = int((deficit_pct + 9.999) // 10) * 2
    return max(0, 20 - deduction), "可售 %d 低于需求 %d（缺口 %.0f%%，扣 %d 分）" % (
        supply,
        demand,
        deficit_pct,
        deduction,
    )


def score_workload(workload, training_capable, inference_capable):
    workload = str(workload or "").upper().strip()
    training = _as_bool(training_capable)
    inference = _as_bool(inference_capable)
    if workload in TRAINING_WORKLOADS:
        if training is True:
            return 15, "训练/微调负载，供给声明 training_capable"
        if training is False:
            return 0, "训练/微调负载，供给明确不支持训练"
        return 5, "训练能力未知，按未知处理（5/15）"
    if workload in INFERENCE_WORKLOADS:
        if inference is True:
            return 15, "推理负载，供给声明 inference_capable"
        if inference is False:
            return 0, "推理负载，供给明确不支持推理"
        return 5, "推理能力未知，按未知处理（5/15）"
    if not workload:
        return 5, "负载类型未知，按未知处理（5/15）"
    if training is True or inference is True:
        return 15, "负载 %s，供给具备训练或推理能力" % workload
    if training is False and inference is False:
        return 0, "负载 %s，供给声明不具备训练/推理能力" % workload
    return 5, "负载 %s 的能力未知，按未知处理（5/15）" % workload


def _country_in_text(country, text):
    if not country:
        return False
    country = str(country).upper().strip()
    aliases = COUNTRY_ALIASES.get(country, (country.lower(),))
    lowered = str(text or "").lower()
    return any(alias in lowered for alias in aliases)


def score_location(preference, supply_country, supply_city):
    pref = str(preference or "").strip()
    country = str(supply_country or "").strip()
    if not pref:
        return 4, "需求未限定位置，按未知处理（4/10）"
    if not country:
        return 4, "供给位置未知，按未知处理（4/10）"
    if _country_in_text(country, pref) or _country_in_text(country, supply_city):
        return 10, "供给国家/城市与需求偏好匹配：%s" % country
    lowered = pref.lower()
    for keyword, countries in REGION_KEYWORDS.items():
        if keyword in lowered and country.upper() in countries:
            return 6, "区域匹配：%s 属于需求区域「%s」" % (country, keyword)
    return 0, "位置不匹配：需求「%s」vs 供给「%s」" % (pref, country)


def _lead_time_months(value):
    text = str(value or "").strip().lower()
    if not text:
        return None
    if any(word in text for word in ("现货", "ready", "in stock", "即插")):
        return 0.5
    months = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:个?月|month)", text)
    if months:
        return float(months.group(1))
    weeks = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:周|week)", text)
    if weeks:
        return float(weeks.group(1)) / 4.0
    days = re.search(r"([0-9]+)\s*(?:天|day)", text)
    if days:
        return float(days.group(1)) / 30.0
    number = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
    if number:
        return float(number.group(1))
    return None


def _deadline_months(timeline):
    text = str(timeline or "").strip()
    if not text:
        return None
    now = datetime.date.today()
    q = re.search(r"(20[0-9]{2})\s*[-/年]?\s*Q([1-4])", text, re.I)
    if q:
        year = int(q.group(1))
        quarter = int(q.group(2))
        target = datetime.date(year, quarter * 3, 1)
        return max(0.0, (target - now).days / 30.0)
    ym = re.search(r"(20[0-9]{2})\s*[-/年]\s*([01]?[0-9])", text)
    if ym:
        target = datetime.date(int(ym.group(1)), max(1, min(12, int(ym.group(2)))), 1)
        return max(0.0, (target - now).days / 30.0)
    relative = re.search(r"([0-9]+)\s*(?:个?月|month)", text)
    if relative:
        return float(relative.group(1))
    return None


def score_delivery(timeline, lead_time):
    deadline = _deadline_months(timeline)
    lead = _lead_time_months(lead_time)
    if deadline is None:
        return 5, "需求时间窗未知，按未知处理（5/10）"
    if lead is None:
        return 5, "交付周期未知，按未知处理（5/10）"
    if lead <= deadline:
        return 10, "交付周期 %.1f 月 ≤ 时间窗 %.1f 月" % (lead, deadline)
    return 0, "交付周期 %.1f 月 > 时间窗 %.1f 月" % (lead, deadline)


def score_network(network_bandwidth):
    if str(network_bandwidth or "").strip():
        return 5, "网络带宽有描述：%s" % str(network_bandwidth).strip()
    return 2, "网络带宽未知，按未知处理（2/5）"


def _latest_verification(conn, company_id):
    if not _has_table(conn, "supplier_verification") or company_id is None:
        return None
    try:
        return conn.execute(
            "SELECT * FROM supplier_verification WHERE supplier_company_id=? ORDER BY id DESC LIMIT 1",
            (company_id,),
        ).fetchone()
    except sqlite3.Error:
        return None


def _compliance_context(conn, demand, supply):
    notes = []
    redlines = []
    verification = _latest_verification(conn, supply.get("company_id"))
    if verification is not None:
        resale_ok = _as_bool(dict(verification).get("resale_right_ok"))
        if resale_ok is False:
            redlines.append(RED_LINE_RESALE)
    residency = str(demand.get("data_residency") or "").strip()
    supply_country = str(supply.get("location_country") or "").strip()
    if residency and supply_country:
        if not _country_in_text(supply_country, residency):
            redlines.append(
                "数据驻留冲突：需求要求「%s」，供给位于 %s" % (residency, supply_country)
            )
            notes.append("data_residency 与供给国家不一致，需合规复核")
    screened = False
    if _has_table(conn, "demand_qualification") and demand.get("id") is not None:
        try:
            row = conn.execute(
                "SELECT * FROM demand_qualification WHERE demand_id=? ORDER BY id DESC LIMIT 1",
                (demand.get("id"),),
            ).fetchone()
            if row is not None and _as_bool(dict(row).get("compliance_screened")) is True:
                screened = True
        except sqlite3.Error:
            pass
    if str(demand.get("compliance_notes") or "").strip():
        screened = screened or bool(str(demand.get("compliance_notes")).strip())
    if str(supply.get("overseas_service") or "").strip():
        screened = screened or True
    return redlines, screened, notes


def score_compliance(conn, demand, supply):
    redlines, screened, notes = _compliance_context(conn, demand, supply)
    if redlines:
        return 0, "命中红线：" + "；".join(redlines), redlines, notes
    if screened:
        return 5, "已完成合规筛查（需求合规备注/核验记录/海外服务声明）", redlines, notes
    return 2, "未见合规筛查记录，按未筛查处理（2/5）", redlines, notes


def score_trust(supply, company_row):
    status = str(supply.get("status") or "").upper()
    if _as_bool(supply.get("verified")) is True or status in ("VERIFIED", "QUALIFIED", "ACTIVE"):
        return 5, "供给已验证/状态 %s" % (status or "VERIFIED")
    if status in (
        "NEEDS_VERIFICATION",
        "RESEARCHED",
        "CEO_PENDING",
        "INSUFFICIENT_INFO",
    ):
        return 3, "供给处于 %s，尚未验证" % status
    if company_row is not None:
        company_status = str(dict(company_row).get("status") or "").upper()
        trust = str(dict(company_row).get("trust_level") or "").upper()
        if company_status in ("VERIFIED", "QUALIFIED", "ACTIVE") or trust in ("HIGH", "MEDIUM"):
            return 5, "公司状态 %s / 信任度 %s" % (company_status, trust)
    return 1, "供给为 LEAD 或状态未知，按低信任处理"


def _recommendation(total):
    if total >= 70:
        return "ADVANCE"
    if total >= 40:
        return "NEED_MORE_INFO"
    return "REJECT"


def _confidence(total, unknowns, redlines):
    if redlines or total < 40:
        return "LOW"
    if total >= 70 and not unknowns:
        return "HIGH"
    return "MEDIUM"


def _company_row(conn, company_id):
    if company_id is None or not _has_table(conn, "companies"):
        return None
    try:
        return conn.execute("SELECT * FROM companies WHERE id=?", (company_id,)).fetchone()
    except sqlite3.Error:
        return None


def builtin_match_score(conn, demand, supply):
    demand = dict(demand)
    supply = dict(supply)
    dimensions = {}
    unknowns = 0

    score, reason = score_gpu_model(demand.get("gpu_models"), supply.get("gpu_model"))
    dimensions["gpu_model"] = {"score": score, "max": 30, "reason": reason}
    if score == 10 and not demand.get("gpu_models"):
        unknowns += 1

    score, reason = score_scale(demand.get("min_gpu_count"), supply.get("sellable_gpu_count"))
    dimensions["scale"] = {"score": score, "max": 20, "reason": reason}
    if _as_int(supply.get("sellable_gpu_count")) in (None, 0):
        unknowns += 1

    score, reason = score_workload(
        demand.get("workload_type"),
        supply.get("training_capable"),
        supply.get("inference_capable"),
    )
    dimensions["workload"] = {"score": score, "max": 15, "reason": reason}
    if score == 5:
        unknowns += 1

    score, reason = score_location(
        demand.get("location_preference"),
        supply.get("location_country"),
        supply.get("location_city"),
    )
    dimensions["location"] = {"score": score, "max": 10, "reason": reason}
    if score == 4:
        unknowns += 1

    score, reason = score_delivery(demand.get("timeline"), supply.get("delivery_lead_time"))
    dimensions["delivery"] = {"score": score, "max": 10, "reason": reason}
    if score == 5:
        unknowns += 1

    score, reason = score_network(supply.get("network_bandwidth"))
    dimensions["network"] = {"score": score, "max": 5, "reason": reason}
    if score == 2:
        unknowns += 1

    score, reason, redlines, compliance_notes = score_compliance(conn, demand, supply)
    dimensions["compliance"] = {"score": score, "max": 5, "reason": reason}
    if score == 2:
        unknowns += 1

    company = _company_row(conn, supply.get("company_id"))
    score, reason = score_trust(supply, company)
    dimensions["trust"] = {"score": score, "max": 5, "reason": reason}

    total = sum(dim["score"] for dim in dimensions.values())
    capped = False
    if redlines and total > 39:
        total = 39
        capped = True

    why_match = [
        "%s：%s" % (key, dim["reason"])
        for key, dim in dimensions.items()
        if dim["score"] >= dim["max"] * 0.6
    ]
    why_not_match = [
        "%s：%s" % (key, dim["reason"])
        for key, dim in dimensions.items()
        if dim["score"] < dim["max"] * 0.6
    ]
    risks = list(redlines) + list(compliance_notes)
    if capped:
        why_not_match.append("命中红线，总分封顶 39（命中前 %d）" % (total + 1))
    recommendation = _recommendation(total)
    confidence = _confidence(total, unknowns, redlines)
    return {
        "supply_id": supply.get("id"),
        "supply_company_id": supply.get("company_id"),
        "supply_gpu_model": supply.get("gpu_model"),
        "supply_status": supply.get("status"),
        "score": round(total, 1),
        "dimensions": dimensions,
        "why_match": why_match,
        "why_not_match": why_not_match,
        "risks": risks,
        "redlines": redlines,
        "confidence": confidence,
        "recommendation": recommendation,
        "unknown_dimensions": unknowns,
    }


def _find_backend_scorer():
    """Try to import app.backend.matching. Returns (fn, source, note)."""
    root = str(repo_root())
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        from app.backend import matching  # type: ignore
    except Exception as exc:  # noqa: BLE001 - integration is optional
        return None, "builtin_equivalent", "app.backend.matching 不可导入：%s" % exc
    for name in ("score_match", "score", "compute_score", "match_score", "calculate_score"):
        fn = getattr(matching, name, None)
        if callable(fn):
            return fn, "app.backend.matching.%s" % name, None
    return None, "builtin_equivalent", "app.backend.matching 已导入但未找到评分函数，使用内置等价实现"


def _call_backend_scorer(fn, demand, supply):
    try:
        result = fn(dict(demand), dict(supply))
    except TypeError:
        result = fn(demand=dict(demand), supply=dict(supply))
    if not isinstance(result, dict) or "score" not in result:
        raise TypeError("评分函数返回结构不符合预期（需含 score 的 dict）")
    dimensions = result.get("dimensions") or {}
    if not isinstance(dimensions, dict):
        dimensions = {}
    return {
        "supply_id": dict(supply).get("id"),
        "supply_company_id": dict(supply).get("company_id"),
        "score": round(float(result["score"]), 1),
        "dimensions": dimensions,
        "why_match": result.get("why_match") or [],
        "why_not_match": result.get("why_not_match") or [],
        "risks": result.get("risks") or [],
        "redlines": result.get("risks") if result.get("redlines") is None else result.get("redlines"),
        "confidence": result.get("confidence") or _confidence(float(result["score"]), 0, []),
        "recommendation": result.get("recommendation") or _recommendation(float(result["score"])),
        "unknown_dimensions": result.get("unknown_dimensions", 0),
    }


def task_match_compute(conn, task):
    if not _has_table(conn, "demand_opportunities") or not _has_table(
        conn, "compute_supply_resources"
    ):
        raise BlockedError("demand_opportunities 或 compute_supply_resources 表不存在")
    parsed = _parse_input_ref(task["input_ref"])
    demand_id = _as_id(parsed.get("demand_id") or parsed.get("demand"))
    # 兼容种子任务：input_ref 只写了一个需求 ID（如 "DEM-20261102-001"）。
    # 只读匹配试算，此时对全部非 REJECTED 供给评分，不落业务表。
    raw_ref = str(task["input_ref"] or "").strip().strip("\"'")
    if demand_id is None and raw_ref and not parsed:
        if re.match(r"^[A-Za-z][A-Za-z0-9]*[-_][A-Za-z0-9-]+$", raw_ref):
            exists = conn.execute(
                "SELECT 1 FROM demand_opportunities WHERE id=?", (raw_ref,)
            ).fetchone()
            if exists is not None:
                demand_id = raw_ref
    if demand_id is None:
        raise BlockedError(
            "input_ref 缺少 demand_id；示例：--input-ref '{\"demand_id\":\"DEM-20261116-001\",\"supply_ids\":[\"SUP-20261116-001\"]}' 或 --input-ref DEM-20261116-001"
        )
    demand = conn.execute(
        "SELECT * FROM demand_opportunities WHERE id=?", (demand_id,)
    ).fetchone()
    if demand is None:
        raise BlockedError("需求不存在：id=%s" % demand_id)
    supply_ids = parsed.get("supply_ids") or parsed.get("supplies") or []
    if isinstance(supply_ids, (int, str)):
        supply_ids = [supply_ids]
    supply_ids = [sid for sid in (_as_id(v) for v in supply_ids) if sid is not None]
    if supply_ids:
        placeholders = ",".join("?" for _ in supply_ids)
        supplies = conn.execute(
            "SELECT * FROM compute_supply_resources WHERE id IN (%s) ORDER BY id" % placeholders,
            supply_ids,
        ).fetchall()
        missing = sorted(set(supply_ids) - {row["id"] for row in supplies})
        if missing:
            raise BlockedError("供给不存在：id=%s" % ", ".join(str(m) for m in missing))
    else:
        supplies = conn.execute(
            "SELECT * FROM compute_supply_resources WHERE status != 'REJECTED' ORDER BY id"
        ).fetchall()
    if not supplies:
        raise BlockedError("没有可评分的供给记录")

    fn, source, note = _find_backend_scorer()
    backend_errors = []
    results = []
    implementation_source = source
    for supply in supplies:
        item = None
        if fn is not None:
            try:
                item = _call_backend_scorer(fn, demand, supply)
            except Exception as exc:  # noqa: BLE001 - fall back to builtin
                backend_errors.append("supply_id=%s: %s" % (supply["id"], exc))
                implementation_source = "builtin_equivalent"
        if item is None:
            item = builtin_match_score(conn, demand, supply)
            implementation_source = "builtin_equivalent"
        results.append(item)

    results.sort(key=lambda r: r["score"], reverse=True)
    result = {
        "generated_at": _now(),
        "task_id": task["id"],
        "agent_name": task["agent_name"],
        "db": _store_path(db_path()),
        "implementation_source": implementation_source,
        # builtin_equivalent 是 SPEC 评分规则的独立等价实现，未与后端实现逐例对拍，
        # 因此标注 UNVERIFIED；调用 app.backend.matching.* 时标注 BACKEND。
        "implementation_status": (
            "UNVERIFIED" if implementation_source == "builtin_equivalent" else "BACKEND"
        ),
        "backend_import_note": note,
        "backend_errors": backend_errors,
        "demand_id": demand_id,
        "demand_title": demand["title"],
        "supply_count": len(results),
        "results": results,
        "persisted": False,
        "notes": [
            "匹配结果仅写入产物文件，不写 matching_records（业务表由后端/人工复核后落库）。",
            "input_ref 未提供 supply_ids 时，对全部非 REJECTED 供给做只读评分（候选清单）。",
            "implementation_source=app.backend.matching.* / implementation_status=BACKEND 表示调用后端实现；"
            "builtin_equivalent / UNVERIFIED 表示使用 runner 内置的 SPEC 等价评分，未与后端逐例对拍。",
            "ADVANCE 仅为建议，需人工 REVIEWED 与 CEO 审批才可对外。",
        ],
    }
    path = _write_json(task, result)
    top = results[0] if results else None
    summary = "匹配评分：需求 %s，供给 %d 条，实现来源 %s；最高分 %s（supply %s，%s）" % (
        demand_id,
        len(results),
        implementation_source,
        top["score"] if top else "n/a",
        top["supply_id"] if top else "n/a",
        top["recommendation"] if top else "n/a",
    )
    return {
        "status": "DONE",
        "result": result,
        "output_path": _store_path(path),
        "summary": summary,
    }


# ---- report render ---------------------------------------------------------


def task_report_render(conn, task):
    required = ("demand_opportunities", "compute_supply_resources", "agent_tasks")
    missing = [t for t in required if not _has_table(conn, t)]
    if missing:
        raise BlockedError("缺少表：%s" % ", ".join(missing))

    counts = {t: _count(conn, t) for t in EXPECTED_TABLES if _has_table(conn, t)}
    demand_status = _distribution(conn, "demand_opportunities", "status")
    demand_grade = _distribution(conn, "demand_opportunities", "lead_grade")
    supply_status = _distribution(conn, "compute_supply_resources", "status")
    match_reco = _distribution(conn, "matching_records", "recommendation")
    match_status = _distribution(conn, "matching_records", "status")
    verification = _distribution(conn, "supplier_verification", "status")
    qualification = _distribution(conn, "demand_qualification", "status")
    opp_stage = _distribution(conn, "commercial_opportunities", "stage")
    evidence_confidence = _distribution(conn, "evidence_registry", "confidence")
    task_status = _distribution(conn, "agent_tasks", "status")
    approvals_pending = None
    if _has_table(conn, "approvals"):
        try:
            approvals_pending = conn.execute(
                "SELECT COUNT(*) AS c FROM approvals WHERE status='PENDING'"
            ).fetchone()["c"]
        except sqlite3.Error:
            approvals_pending = None
    recent_activities = []
    if _has_table(conn, "project_activities"):
        try:
            recent_activities = [
                dict(r)
                for r in conn.execute(
                    "SELECT ts, actor, action, entity_type, entity_id, summary FROM project_activities ORDER BY id DESC LIMIT 10"
                ).fetchall()
            ]
        except sqlite3.Error:
            recent_activities = []

    lines = []
    lines.append("# %s" % (task["title"] or "CCGS 数据报告"))
    lines.append("")
    lines.append("> 由 `agents/runner.py` 生成（确定性任务，无 LLM 推理、无网络请求）。")
    lines.append("")
    lines.append("| 项目 | 值 |")
    lines.append("|------|----|")
    lines.append("| 生成时间 | %s |" % _now())
    lines.append("| 任务 ID | %s |" % task["id"])
    lines.append("| Agent | %s |" % task["agent_name"])
    lines.append("| task_type | %s |" % task["task_type"])
    lines.append("| 数据库 | `%s` |" % _store_path(db_path()))
    lines.append("")
    lines.append("## 1. 数据概览")
    lines.append("")
    lines.append("| 表 | 行数 |")
    lines.append("|----|------|")
    for table in EXPECTED_TABLES:
        if table in counts:
            lines.append("| %s | %s |" % (table, counts[table]))
    lines.append("")
    lines.append("## 2. 需求漏斗")
    lines.append("")
    lines.append("- 状态分布：%s" % _fmt_dist(demand_status))
    lines.append("- 线索分级：%s" % _fmt_dist(demand_grade))
    lines.append("")
    lines.append("## 3. 供给状态")
    lines.append("")
    lines.append("- 状态分布：%s" % _fmt_dist(supply_status))
    lines.append("")
    lines.append("## 4. 匹配候选")
    lines.append("")
    lines.append("- 建议分布：%s" % _fmt_dist(match_reco))
    lines.append("- 记录状态：%s" % _fmt_dist(match_status))
    if _has_table(conn, "matching_records"):
        try:
            rows = conn.execute(
                "SELECT id, demand_id, supply_id, score, recommendation, status, confidence"
                " FROM matching_records ORDER BY score DESC LIMIT 20"
            ).fetchall()
            if rows:
                lines.append("")
                lines.append("| id | demand | supply | score | recommendation | status | confidence |")
                lines.append("|----|--------|--------|-------|----------------|--------|------------|")
                for row in rows:
                    lines.append(
                        "| %s | %s | %s | %s | %s | %s | %s |"
                        % (
                            row["id"],
                            row["demand_id"],
                            row["supply_id"],
                            row["score"],
                            row["recommendation"],
                            row["status"],
                            row["confidence"],
                        )
                    )
        except sqlite3.Error:
            pass
    lines.append("")
    lines.append("## 5. 核验覆盖")
    lines.append("")
    lines.append("- 供应商核验：%s" % _fmt_dist(verification))
    lines.append("- 需求资格核验：%s" % _fmt_dist(qualification))
    lines.append("")
    lines.append("## 6. 商机与审批")
    lines.append("")
    lines.append("- 商机阶段：%s" % _fmt_dist(opp_stage))
    lines.append("- 待 CEO 审批：%s" % ("n/a" if approvals_pending is None else approvals_pending))
    lines.append("")
    lines.append("## 7. 证据健康")
    lines.append("")
    lines.append("- 证据信任度：%s" % _fmt_dist(evidence_confidence))
    lines.append("")
    lines.append("## 8. Agent 任务")
    lines.append("")
    lines.append("- 任务状态：%s" % _fmt_dist(task_status))
    lines.append("")
    lines.append("## 9. 最近活动")
    lines.append("")
    if recent_activities:
        lines.append("| 时间 | 执行者 | 动作 | 对象 | 摘要 |")
        lines.append("|------|--------|------|------|------|")
        for row in recent_activities:
            lines.append(
                "| %s | %s | %s | %s:%s | %s |"
                % (
                    row.get("ts"),
                    row.get("actor"),
                    row.get("action"),
                    row.get("entity_type"),
                    row.get("entity_id"),
                    row.get("summary"),
                )
            )
    else:
        lines.append("（无活动记录）")
    lines.append("")
    lines.append("## 10. 已知限制")
    lines.append("")
    lines.append("- 本报告是数据库快照，不包含 LLM 研究判断、预测或对外话术。")
    lines.append("- 种子数据与未核验线索不代表真实商机；不得直接用于对外材料。")
    lines.append("- 分数 / 状态均为系统内部记录，对外使用须经人工复核与 CEO 审批。")
    lines.append("")

    path = _write_text(task, "md", "\n".join(lines))
    result = {
        "generated_at": _now(),
        "task_id": task["id"],
        "counts": counts,
        "demand_status": demand_status,
        "demand_grade": demand_grade,
        "supply_status": supply_status,
        "match_recommendation": match_reco,
        "approvals_pending": approvals_pending,
    }
    summary = "报告渲染：%d 张表；需求 %s 条、供给 %s 条；输出 %s" % (
        len(counts),
        counts.get("demand_opportunities"),
        counts.get("compute_supply_resources"),
        _store_path(path),
    )
    return {
        "status": "DONE",
        "result": result,
        "output_path": _store_path(path),
        "summary": summary,
    }


def _fmt_dist(dist):
    if not dist:
        return "（无数据）"
    return "，".join("%s=%s" % (k, v) for k, v in dist.items())


# ---- schema validate -------------------------------------------------------


def _parse_sql_objects(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    tables = set(
        m.group(1).lower()
        for m in re.finditer(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"\[]?([A-Za-z_][A-Za-z0-9_]*)", text, re.I)
    )
    indexes = set(
        m.group(1).lower()
        for m in re.finditer(r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"\[]?([A-Za-z_][A-Za-z0-9_]*)", text, re.I)
    )
    return tables, indexes


def _spec_sql_text():
    spec = repo_root() / "docs" / "07_ai_system" / "SPEC_DATABASE.md"
    if not spec.exists():
        return None
    text = spec.read_text(encoding="utf-8", errors="replace")
    blocks = re.findall(r"```sql\s*(.*?)```", text, re.S | re.I)
    return "\n\n".join(blocks)


def task_schema_validate(conn, task):
    spec_text = _spec_sql_text()
    if spec_text is None:
        raise BlockedError("docs/07_ai_system/SPEC_DATABASE.md 不存在，无法校验表清单")
    spec_tables = set(
        m.group(1).lower()
        for m in re.finditer(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"\[]?([A-Za-z_][A-Za-z0-9_]*)",
            spec_text,
            re.I,
        )
    )
    spec_indexes = set(
        m.group(1).lower()
        for m in re.finditer(
            r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"\[]?([A-Za-z_][A-Za-z0-9_]*)",
            spec_text,
            re.I,
        )
    )
    db_tables = set(_table_names(conn))
    db_indexes = set(
        r["name"].lower()
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    )
    columns = {table: _columns(conn, table) for table in db_tables}
    counts = {t: _count(conn, t) for t in EXPECTED_TABLES if t in db_tables}

    schema_path = repo_root() / "app" / "data" / "schema.sql"
    schema_info = {"path": _store_path(schema_path), "exists": schema_path.exists()}
    problems = []
    warnings = []
    if schema_path.exists():
        schema_tables, schema_indexes = _parse_sql_objects(schema_path)
        schema_info["tables"] = sorted(schema_tables)
        schema_info["indexes"] = sorted(schema_indexes)
        schema_info["missing_vs_spec"] = sorted(spec_tables - schema_tables)
        schema_info["extra_vs_spec"] = sorted(schema_tables - spec_tables)
        if schema_info["missing_vs_spec"]:
            problems.append("schema.sql 缺少 SPEC 表：%s" % ", ".join(schema_info["missing_vs_spec"]))
        if schema_info["extra_vs_spec"]:
            problems.append("schema.sql 存在 SPEC 未定义表：%s" % ", ".join(schema_info["extra_vs_spec"]))
        for index in EXPECTED_INDEXES:
            if index not in schema_indexes:
                warnings.append("schema.sql 未定义索引 %s" % index)
    else:
        schema_info["note"] = "app/data/schema.sql 不存在（后端可能尚未生成），仅校验运行库与 SPEC"

    expected_tables = set(t.lower() for t in EXPECTED_TABLES)
    missing_in_db = sorted(expected_tables - db_tables)
    extra_in_db = sorted(db_tables - expected_tables)
    missing_indexes = sorted(i for i in EXPECTED_INDEXES if i not in db_indexes)
    if missing_in_db:
        problems.append("运行库缺少表：%s" % ", ".join(missing_in_db))
    if extra_in_db:
        warnings.append("运行库存在 SPEC 之外的表：%s" % ", ".join(extra_in_db))
    if missing_indexes:
        warnings.append("运行库缺少索引：%s" % ", ".join(missing_indexes))
    if spec_tables != expected_tables:
        only_spec = sorted(spec_tables - expected_tables)
        only_const = sorted(expected_tables - spec_tables)
        warnings.append(
            "SPEC 解析表与常量清单差异：spec 多 %s / 常量多 %s"
            % (only_spec or "无", only_const or "无")
        )

    result = {
        "generated_at": _now(),
        "task_id": task["id"],
        "agent_name": task["agent_name"],
        "db": _store_path(db_path()),
        "spec_tables": sorted(spec_tables),
        "spec_indexes": sorted(spec_indexes),
        "expected_tables": list(EXPECTED_TABLES),
        "db_tables": sorted(db_tables),
        "db_indexes": sorted(db_indexes),
        "missing_tables_in_db": missing_in_db,
        "extra_tables_in_db": extra_in_db,
        "missing_indexes_in_db": missing_indexes,
        "columns": {k: v for k, v in columns.items() if k in expected_tables},
        "counts": counts,
        "schema_file": schema_info,
        "problems": problems,
        "warnings": warnings,
        "ok": not problems,
    }
    path = _write_json(task, result)
    summary = "schema 校验：SPEC %d 表 / 运行库 %d 表；问题 %d 项；警告 %d 项" % (
        len(spec_tables),
        len(db_tables),
        len(problems),
        len(warnings),
    )
    status = "DONE"
    if not result["ok"]:
        status = "BLOCKED"
    return {
        "status": status,
        "result": result,
        "output_path": _store_path(path),
        "summary": summary,
    }


TASK_HANDLERS = {
    "data_audit": task_data_audit,
    "evidence_check": task_evidence_check,
    "csv_ingest": task_csv_ingest,
    "match_compute": task_match_compute,
    "report_render": task_report_render,
    "schema_validate": task_schema_validate,
}


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def run_task(task_id, db=None):
    """Run one agent task. Importable by the backend API.

    Returns a dict with task_id, status, result, output_path, summary and the
    side-effect tables that were skipped (when absent).
    """
    task_id = _as_id(task_id)
    if task_id is None:
        raise RunnerError("task_id 不能为空（业务库主键为 TEXT，如 TASK-20261116-001）")
    conn = _connect(db)
    try:
        if not _has_table(conn, "agent_tasks"):
            raise RunnerError("agent_tasks 表不存在，请先初始化数据库")
        task = _task_row(conn, task_id)
        if task is None:
            raise RunnerError("任务不存在：id=%s" % task_id)
        task = dict(task)
        status = str(task.get("status") or "").upper()
        if status == "RUNNING":
            raise RunnerError("任务 %s 正在运行中，请勿重复执行" % task_id)
        if status == "DONE":
            raise RunnerError("任务 %s 已完成，如需重跑请先重置状态" % task_id)
        if status == "CANCELLED":
            raise RunnerError("任务 %s 已取消，不可执行" % task_id)
        task_type = str(task.get("task_type") or "")
        handler = TASK_HANDLERS.get(task_type)
        if handler is None:
            raise RunnerError(
                "未知 task_type：%r（可选：%s）" % (task_type, ", ".join(TASK_TYPES))
            )
        agent_name = task.get("agent_name")
        if agent_name not in EXPECTED_AGENTS:
            raise RunnerError("未知 Agent：%s" % agent_name)

        before = {k: task.get(k) for k in ("status", "started_at", "finished_at", "output_path")}
        _update_task(
            conn,
            task_id,
            status="RUNNING",
            started_at=_now(),
            finished_at=None,
            output_path=None,
            result_summary=None,
            error=None,
        )
        actor = "agents.runner/%s" % agent_name
        _side_effects(
            conn,
            actor,
            "agent_task.start",
            "agent_task",
            task_id,
            "开始执行任务：%s" % task["title"],
            "task_type=%s" % task_type,
            before=before,
            after={"status": "RUNNING"},
        )

        task["status"] = "RUNNING"
        outcome = None
        error_text = None
        try:
            outcome = handler(conn, task)
        except BlockedError as exc:
            error_text = str(exc)
            outcome = {
                "status": "BLOCKED",
                "result": {"error": error_text, "error_type": "BLOCKED"},
                "output_path": None,
                "summary": "阻塞：%s" % error_text,
            }
        except sqlite3.Error as exc:
            error_text = "数据库错误：%s" % exc
            outcome = {
                "status": "FAILED",
                "result": {"error": error_text, "error_type": "DATABASE"},
                "output_path": None,
                "summary": "失败：%s" % error_text,
            }
        except RunnerError as exc:
            error_text = str(exc)
            outcome = {
                "status": "FAILED",
                "result": {"error": error_text, "error_type": "RUNNER"},
                "output_path": None,
                "summary": "失败：%s" % error_text,
            }
        except Exception as exc:  # noqa: BLE001 - persist failure instead of crashing
            error_text = "%s: %s" % (type(exc).__name__, exc)
            detail = traceback.format_exc(limit=5)
            outcome = {
                "status": "FAILED",
                "result": {"error": error_text, "traceback": detail, "error_type": "UNEXPECTED"},
                "output_path": None,
                "summary": "失败：%s" % error_text,
            }

        final_status = outcome["status"]
        output_path = outcome.get("output_path")
        result = outcome.get("result") or {}
        if output_path:
            try:
                result.setdefault("output_sha256", _digest(repo_root() / output_path))
            except (OSError, ValueError):
                pass
        summary = _truncate(outcome.get("summary") or "", 500)
        _update_task(
            conn,
            task_id,
            status=final_status,
            finished_at=_now(),
            output_path=output_path,
            result_summary=summary,
            error=error_text,
        )
        skipped = _side_effects(
            conn,
            actor,
            "agent_task.finish",
            "agent_task",
            task_id,
            summary,
            "status=%s; output=%s" % (final_status, output_path),
            before={"status": "RUNNING"},
            after={"status": final_status, "output_path": output_path},
        )
        return {
            "task_id": task_id,
            "agent_name": agent_name,
            "task_type": task_type,
            "status": final_status,
            "summary": summary,
            "result": result,
            "output_path": output_path,
            "error": error_text,
            "audit_skipped": skipped,
        }
    finally:
        conn.close()


def run_all(status="QUEUED", agent=None, limit=50, db=None):
    conn = _connect(db)
    try:
        if not _has_table(conn, "agent_tasks"):
            raise RunnerError("agent_tasks 表不存在，请先初始化数据库")
        clauses = ["status=?"]
        params = [status or "QUEUED"]
        if agent:
            clauses.append("agent_name=?")
            params.append(agent)
        rows = conn.execute(
            "SELECT id FROM agent_tasks WHERE %s ORDER BY priority, id LIMIT ?"
            % " AND ".join(clauses),
            params + [int(limit)],
        ).fetchall()
        task_ids = [r["id"] for r in rows]
    finally:
        conn.close()
    results = []
    for task_id in task_ids:
        try:
            results.append(run_task(task_id, db=db))
        except RunnerError as exc:
            results.append(
                {"task_id": task_id, "status": "ERROR", "error": str(exc), "summary": str(exc)}
            )
    return {
        "requested_status": status,
        "agent": agent,
        "count": len(results),
        "done": sum(1 for r in results if r["status"] == "DONE"),
        "blocked": sum(1 for r in results if r["status"] == "BLOCKED"),
        "failed": sum(1 for r in results if r["status"] == "FAILED"),
        "results": results,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m agents.runner",
        description="CCGS 确定性 Agent 任务运行器（stdlib，只读业务数据，产物写入 data/runtime/agent_outputs/）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="列出 agent_tasks")
    p_list.add_argument("--status", default=None)
    p_list.add_argument("--agent", default=None)
    p_list.add_argument("--limit", type=int, default=50)

    p_show = sub.add_parser("show", help="查看某个 Agent 的注册信息与任务")
    p_show.add_argument("agent")

    p_create = sub.add_parser("create", help="创建 agent 任务")
    p_create.add_argument("--agent", required=True)
    p_create.add_argument("--type", required=True, dest="task_type")
    p_create.add_argument("--title", required=True)
    p_create.add_argument("--input-ref", default=None)
    p_create.add_argument("--priority", default="P2")
    p_create.add_argument("--approval", action="store_true", help="requires_approval=1")

    p_run = sub.add_parser("run", help="执行一个任务")
    p_run.add_argument("task_id", help="任务 ID（TEXT，如 TASK-20261116-001）")

    p_all = sub.add_parser("run-all", help="批量执行指定状态的任务")
    p_all.add_argument("--status", default="QUEUED")
    p_all.add_argument("--agent", default=None)
    p_all.add_argument("--limit", type=int, default=50)

    sub.add_parser("validate", help="校验 registry.json / skills / 数据库")
    return parser


def _print_json(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            _print_json(list_tasks(status=args.status, agent=args.agent, limit=args.limit))
            return 0
        if args.command == "show":
            _print_json(show_agent(args.agent))
            return 0
        if args.command == "create":
            _print_json(
                create_task(
                    args.agent,
                    args.task_type,
                    args.title,
                    input_ref=args.input_ref,
                    priority=args.priority,
                    requires_approval=args.approval,
                )
            )
            return 0
        if args.command == "run":
            result = run_task(args.task_id)
            _print_json(result)
            if result["status"] == "DONE":
                return 0
            if result["status"] == "BLOCKED":
                return 3
            return 4
        if args.command == "run-all":
            result = run_all(status=args.status, agent=args.agent, limit=args.limit)
            _print_json(result)
            return 0 if result["failed"] == 0 else 4
        if args.command == "validate":
            result = validate_all()
            _print_json(result)
            return 0 if result["ok"] else 1
        parser.error("未知命令")
        return 2
    except RunnerError as exc:
        print(json.dumps({"error": {"type": type(exc).__name__, "message": str(exc)}}, ensure_ascii=False), file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - CLI should fail cleanly
        print(
            json.dumps(
                {"error": {"type": type(exc).__name__, "message": str(exc)}},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
