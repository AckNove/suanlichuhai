# -*- coding: utf-8 -*-
"""Tests for the CCGS deterministic agent runner (stdlib unittest, Python 3.9).

These tests never touch ``data/runtime/app.db``: each test builds a throw-away
SQLite database from ``app/data/schema.sql`` (falling back to the ```sql blocks
of ``docs/07_ai_system/SPEC_DATABASE.md`` when the backend file is missing) and
points ``CCGS_DB_PATH`` / ``CCGS_AGENT_OUTPUT_DIR`` / ``CCGS_IMPORT_DIR`` at a
temporary directory.

Run with::

    python -m unittest tests.test_agents_runner -v
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents import runner  # noqa: E402

SCHEMA_PATH = ROOT / "app" / "data" / "schema.sql"
SPEC_PATH = ROOT / "docs" / "07_ai_system" / "SPEC_DATABASE.md"
SKILLS_DIR = ROOT / ".dsh" / "skills"
REGISTRY_PATH = ROOT / "agents" / "registry.json"

RUNNER_SCRIPT = ROOT / "agents" / "runner.py"

EXPECTED_AGENTS = [
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
]

EXPECTED_SKILLS = [
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
]

REQUIRED_AGENT_FIELDS = [
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
]

REQUIRED_SKILL_SECTIONS = [
    "## ① 输入",
    "## ② 操作步骤",
    "## ③ 工具要求",
    "## ④ 输出",
    "## ⑤ 质量标准",
    "## ⑥ 权限边界",
]

NOW = "2026-11-16T00:00:00+08:00"


def load_schema_sql():
    """Return the authoritative DDL: schema.sql first, SPEC sql blocks second."""
    if SCHEMA_PATH.exists():
        text = SCHEMA_PATH.read_text(encoding="utf-8")
        if "CREATE TABLE" in text.upper():
            return text
    if SPEC_PATH.exists():
        text = SPEC_PATH.read_text(encoding="utf-8")
        blocks = re.findall(r"```sql\s*(.*?)```", text, re.S | re.I)
        joined = "\n\n".join(blocks)
        if "CREATE TABLE" in joined.upper():
            return joined
    raise unittest.SkipTest("schema.sql 与 SPEC_DATABASE.md 均不可用")


def run_cli(*args, env=None):
    """Run the runner as a real CLI process (script entry point) and parse JSON."""
    child_env = dict(os.environ)
    child_env["PYTHONIOENCODING"] = "utf-8"
    if env:
        child_env.update(env)
    proc = subprocess.run(
        [sys.executable, str(RUNNER_SCRIPT)] + list(args),
        cwd=str(ROOT),
        env=child_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    return proc


class RegistryAndSkillsTest(unittest.TestCase):
    """Pure static checks: registry.json and the 10 SKILL.md files."""

    def test_registry_file_is_utf8_array_of_11(self):
        self.assertTrue(REGISTRY_PATH.exists(), "agents/registry.json 不存在")
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 11)
        names = [item["name"] for item in data]
        self.assertEqual(len(names), len(set(names)), "Agent name 必须唯一")
        self.assertEqual(sorted(names), sorted(EXPECTED_AGENTS))

    def test_registry_entries_have_required_fields(self):
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))
        allowed_tools = set(runner.ALLOWED_TOOLS)
        for agent in data:
            label = agent.get("name", "(未命名)")
            for field in REQUIRED_AGENT_FIELDS:
                self.assertIn(field, agent, "%s 缺少字段 %s" % (label, field))
            self.assertEqual(agent["status"], "ACTIVE", label)
            self.assertIsInstance(agent["approval_required"], bool, label)
            for field in ("inputs", "tools", "skills", "outputs", "task_types"):
                self.assertIsInstance(agent[field], list, "%s.%s 应为数组" % (label, field))
                self.assertTrue(agent[field], "%s.%s 不应为空" % (label, field))
            self.assertIsInstance(agent["permissions"], dict, label)
            self.assertIsInstance(agent["permissions"].get("read"), list, label)
            self.assertIsInstance(agent["permissions"].get("write"), list, label)
            for tool in agent["tools"]:
                self.assertIn(tool, allowed_tools, "%s 声明了未知工具 %s" % (label, tool))
            for skill in agent["skills"]:
                self.assertIn(skill, EXPECTED_SKILLS, "%s 引用了未知 Skill %s" % (label, skill))
            for task_type in agent["task_types"]:
                self.assertIn(task_type, runner.TASK_TYPES, "%s 未知 task_type" % label)

    def test_runner_validate_registry_ok(self):
        result = runner.validate_registry()
        self.assertTrue(result["ok"], result["problems"])
        self.assertEqual(result["count"], 11)

    def test_ten_skills_exist_with_six_sections(self):
        for name in EXPECTED_SKILLS:
            path = SKILLS_DIR / name / "SKILL.md"
            self.assertTrue(path.exists(), "缺少 Skill：%s" % path)
            text = path.read_text(encoding="utf-8")
            info = runner.parse_skill(name)
            self.assertTrue(info["exists"], name)
            self.assertEqual(info["problems"], [], "%s: %s" % (name, info["problems"]))
            for field in ("name", "description", "version", "owner", "tools"):
                self.assertTrue(info["meta"].get(field), "%s frontmatter 缺少 %s" % (name, field))
            self.assertEqual(str(info["meta"]["version"]), "1.0", name)
            self.assertEqual(info["meta"]["name"], name)
            for header in REQUIRED_SKILL_SECTIONS:
                self.assertIn(header, text, "%s 缺少章节 %s" % (name, header))
        result = runner.validate_skills()
        self.assertTrue(result["ok"], result["problems"])
        self.assertEqual(result["count"], 10)

    def test_skills_declare_only_available_tools(self):
        allowed = set(runner.ALLOWED_TOOLS)
        for name in EXPECTED_SKILLS:
            info = runner.parse_skill(name)
            declared = set(info["tools"])
            self.assertTrue(declared, name)
            unknown = declared - allowed
            self.assertFalse(unknown, "%s 声明了未实现的工具：%s" % (name, sorted(unknown)))

    def test_no_agent_claims_forbidden_automation(self):
        """No registry skill may promise e-mail sending / auto-closing deals."""
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))
        blob = json.dumps(data, ensure_ascii=False).lower()
        for forbidden in ("自动发邮件", "自动成交", "自动报价", "auto_send_email", "smtp"):
            self.assertNotIn(forbidden, blob)


class TempDBTestCase(unittest.TestCase):
    """Base class: fresh temp DB seeded with a tiny but realistic fixture set."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ccgs_runner_test_"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.db_file = self.tmp / "app.db"
        self.out_dir = self.tmp / "agent_outputs"
        self.import_dir = self.tmp / "import"
        self.import_dir.mkdir()
        self._create_db()
        self._saved_env = {}
        for key, value in (
            ("CCGS_DB_PATH", str(self.db_file)),
            ("CCGS_AGENT_OUTPUT_DIR", str(self.out_dir)),
            ("CCGS_IMPORT_DIR", str(self.import_dir)),
        ):
            self._saved_env[key] = os.environ.get(key)
            os.environ[key] = value

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    # -- fixture construction -------------------------------------------------
    def _create_db(self):
        conn = sqlite3.connect(str(self.db_file))
        try:
            conn.executescript(load_schema_sql())
            self._seed(conn)
            conn.commit()
        finally:
            conn.close()

    def _seed(self, conn):
        conn.execute(
            "INSERT INTO companies (id, name, name_en, company_type, country, status,"
            " trust_level, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            ("C-001", "测试算力供应商", "Test Compute Supplier", "SUPPLIER", "China",
             "LEAD", "UNVERIFIED", NOW, NOW),
        )
        conn.execute(
            "INSERT INTO companies (id, name, name_en, company_type, country, status,"
            " trust_level, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            ("C-002", "测试海外需求方", "Test Overseas Buyer", "DEMANDER", "Singapore",
             "LEAD", "UNVERIFIED", NOW, NOW),
        )
        conn.execute(
            "INSERT INTO demand_opportunities (id, company_id, title, workload_type, gpu_models,"
            " min_gpu_count, duration_months, location_preference, timeline, lead_grade, status,"
            " created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("DEM-20261116-001", "C-002", "海外推理集群需求（测试）", "INFERENCE", "H100",
             64, 12, "Singapore", "2027Q1", "PUBLIC_LEAD", "LEAD", NOW, NOW),
        )
        conn.execute(
            "INSERT INTO demand_opportunities (id, company_id, title, workload_type, gpu_models,"
            " min_gpu_count, timeline, lead_grade, status, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("DEM-20261116-002", "C-002", "海外训练集群需求（测试）", "TRAINING", "H200",
             32, "2027Q2", "INFERRED", "RESEARCHED", NOW, NOW),
        )
        conn.execute(
            "INSERT INTO compute_supply_resources (id, company_id, location_country, location_city,"
            " datacenter, gpu_model, gpu_count, sellable_gpu_count, gpu_memory_gb, interconnect,"
            " training_capable, inference_capable, network_bandwidth, delivery_lead_time,"
            " price_indication, status, verified, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("SUP-20261116-001", "C-001", "China", "Guangzhou", "测试机房 A", "H100",
             128, 96, 80, "NVLink", 1, 1, "100Gbps", "8 weeks", "待确认", "RESEARCHED", 0,
             NOW, NOW),
        )
        conn.execute(
            "INSERT INTO compute_supply_resources (id, company_id, location_country, location_city,"
            " gpu_model, gpu_count, sellable_gpu_count, training_capable, inference_capable,"
            " price_indication, status, verified, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("SUP-20261116-002", "C-001", "China", "Shaoguan", "A100", 32, 16, 1, 1,
             "待确认", "LEAD", 0, NOW, NOW),
        )
        conn.execute(
            "INSERT INTO evidence_registry (id, subject_type, subject_id, claim, source_title,"
            " url, publisher, published_at, retrieved_at, confidence, cross_verified, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            ("EV-001", "COMPANY", "C-001", "测试供应商官网自述拥有 H100 资源",
             "测试官网", "https://example.com/supplier", "example.com", "2026-11-01",
             NOW, "MEDIUM", 1, NOW),
        )
        conn.execute(
            "INSERT INTO evidence_registry (id, subject_type, subject_id, claim, confidence,"
            " cross_verified, created_at) VALUES (?,?,?,?,?,?,?)",
            ("EV-002", "DEMAND", "DEM-20261116-001", "公开报道称该需求方计划采购算力",
             "BOGUS", 0, NOW),
        )
        conn.execute(
            "INSERT INTO supplier_verification (id, supplier_company_id, status, score,"
            " created_at, updated_at) VALUES (?,?,?,?,?,?)",
            ("SV-001", "C-001", "PENDING", None, NOW, NOW),
        )
        conn.execute(
            "INSERT INTO approvals (id, approval_type, subject, requested_by, requested_at,"
            " status) VALUES (?,?,?,?,?,?)",
            ("APR-001", "SUPPLIER_QUALIFICATION", "测试供应商升级 QUALIFIED",
             "supplier-verification", NOW, "PENDING"),
        )
        task_types = list(runner.TASK_TYPES)
        match_ref = json.dumps(
            {
                "demand_id": "DEM-20261116-001",
                "supply_ids": ["SUP-20261116-001", "SUP-20261116-002"],
            },
            ensure_ascii=False,
        )
        for index, agent in enumerate(EXPECTED_AGENTS):
            task_type = task_types[index % len(task_types)]
            input_ref = match_ref if task_type == "match_compute" else None
            conn.execute(
                "INSERT INTO agent_tasks (id, agent_name, task_type, title, input_ref,"
                " priority, status, requires_approval, created_at, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    "TASK-20261116-%03d" % (index + 1),
                    agent,
                    task_type,
                    "种子任务：%s / %s" % (agent, task_type),
                    input_ref,
                    "P2",
                    "QUEUED",
                    0,
                    NOW,
                    NOW,
                ),
            )

    # -- helpers --------------------------------------------------------------
    def fetch_task(self, task_id):
        conn = sqlite3.connect(str(self.db_file))
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("SELECT * FROM agent_tasks WHERE id=?", (task_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def fetch_scalar(self, sql, params=()):
        conn = sqlite3.connect(str(self.db_file))
        try:
            row = conn.execute(sql, params).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def read_output(self, path):
        p = Path(path)
        if not p.is_absolute():
            p = ROOT / p
        self.assertTrue(p.exists(), "产物文件不存在：%s" % p)
        return json.loads(p.read_text(encoding="utf-8"))


class RunnerHappyPathTest(TempDBTestCase):
    def test_validate_all_with_temp_db(self):
        result = runner.validate_all()
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["registry"]["count"], 11)
        self.assertEqual(result["skills"]["count"], 10)
        database = result["database"]
        self.assertTrue(database["checked"], database)
        self.assertEqual(database["missing_tables"], [])
        self.assertEqual(database["missing_indexes"], [])
        self.assertEqual(database["counts"]["agent_tasks"], 11)

    def test_list_returns_11_seeded_tasks(self):
        result = runner.list_tasks()
        self.assertEqual(result["total"], 11)
        self.assertEqual(len(result["items"]), 11)
        ids = {item["id"] for item in result["items"]}
        self.assertIn("TASK-20261116-001", ids)
        self.assertTrue(all(item["status"] == "QUEUED" for item in result["items"]))
        filtered = runner.list_tasks(agent="Matching Engine")
        self.assertEqual(filtered["total"], 1)
        self.assertIn(filtered["items"][0]["task_type"], runner.TASK_TYPES)

    def test_show_agent_returns_skills_and_task_counts(self):
        info = runner.show_agent("Matching Engine")
        self.assertEqual(info["agent"]["name"], "Matching Engine")
        self.assertTrue(info["skill_details"])
        for detail in info["skill_details"]:
            self.assertTrue(detail["exists"], detail["name"])
            self.assertEqual(detail["problems"], [])
        self.assertEqual(info["task_counts"].get("QUEUED"), 1)
        self.assertIn(info["recent_tasks"][0]["task_type"], runner.TASK_TYPES)
        with self.assertRaises(runner.RunnerError):
            runner.show_agent("Not An Agent")

    def test_create_task_generates_text_id_and_side_effects(self):
        created = runner.create_task(
            "Data Manager", "data_audit", "手工创建的数据体检", priority="P1"
        )
        self.assertRegex(created["task_id"], r"^TASK-\d{8}-\d{3}$")
        self.assertEqual(created["status"], "QUEUED")
        row = self.fetch_task(created["task_id"])
        self.assertEqual(row["priority"], "P1")
        self.assertEqual(self.fetch_scalar("SELECT COUNT(*) FROM project_activities"), 1)
        self.assertEqual(self.fetch_scalar("SELECT COUNT(*) FROM audit_logs"), 1)
        with self.assertRaises(runner.RunnerError):
            runner.create_task("Data Manager", "not_a_type", "x")
        with self.assertRaises(runner.RunnerError):
            runner.create_task("Nobody", "data_audit", "x")

    def test_run_data_audit_marks_done_and_writes_output(self):
        result = runner.run_task("TASK-20261116-001")
        self.assertEqual(result["status"], "DONE")
        self.assertEqual(result["task_type"], "data_audit")
        payload = self.read_output(result["output_path"])
        self.assertEqual(payload["counts"]["companies"], 2)
        self.assertEqual(payload["counts"]["demand_opportunities"], 2)
        self.assertEqual(payload["missing_tables"], [])
        # The fixture intentionally contains one illegal confidence value so the
        # audit must report it rather than silently passing.
        self.assertEqual(len(payload["invalid_status_values"]), 1)
        self.assertEqual(payload["invalid_status_values"][0]["table"], "evidence_registry")
        self.assertEqual(payload["invalid_status_values"][0]["value"], "BOGUS")
        self.assertIn("entities_without_evidence", payload)
        self.assertIn("output_sha256", result["result"])

        row = self.fetch_task("TASK-20261116-001")
        self.assertEqual(row["status"], "DONE")
        self.assertTrue(row["started_at"])
        self.assertTrue(row["finished_at"])
        self.assertEqual(row["output_path"], result["output_path"])
        self.assertTrue(row["result_summary"])
        self.assertIsNone(row["error"])
        self.assertGreaterEqual(self.fetch_scalar("SELECT COUNT(*) FROM project_activities"), 2)
        self.assertGreaterEqual(self.fetch_scalar("SELECT COUNT(*) FROM audit_logs"), 2)

    def test_run_evidence_check_reports_gaps(self):
        task = runner.create_task("Data Manager", "evidence_check", "证据待补清单")
        result = runner.run_task(task["task_id"])
        self.assertEqual(result["status"], "DONE")
        payload = self.read_output(result["output_path"])
        self.assertEqual(payload["total"], 2)
        self.assertGreaterEqual(payload["counts"]["missing_url_or_source_title"], 1)
        self.assertGreaterEqual(payload["counts"]["invalid_or_missing_confidence"], 1)
        self.assertGreaterEqual(payload["counts"]["not_cross_verified"], 1)
        self.assertIn("待补清单", payload["notes"][0])

    def test_run_schema_validate_compares_schema_and_db(self):
        task = runner.create_task("QA", "schema_validate", "schema 一致性校验")
        result = runner.run_task(task["task_id"])
        self.assertEqual(result["status"], "DONE", result)
        payload = self.read_output(result["output_path"])
        self.assertTrue(payload["ok"], payload["problems"])
        self.assertEqual(payload["problems"], [])
        self.assertEqual(payload["missing_tables_in_db"], [])
        self.assertEqual(payload["missing_indexes_in_db"], [])
        self.assertTrue(payload["schema_file"]["exists"], payload["schema_file"])
        self.assertEqual(len(payload["db_tables"]), 18)

    def test_run_match_compute_builtin_fallback_is_labelled(self):
        task = runner.create_task(
            "Matching Engine",
            "match_compute",
            "测试匹配",
            input_ref=json.dumps(
                {
                    "demand_id": "DEM-20261116-001",
                    "supply_ids": ["SUP-20261116-001"],
                }
            ),
        )
        result = runner.run_task(task["task_id"])
        self.assertEqual(result["status"], "DONE", result)
        payload = self.read_output(result["output_path"])
        source = payload["implementation_source"]
        self.assertTrue(
            source == "builtin_equivalent" or source.startswith("app.backend.matching"),
            source,
        )
        if source == "builtin_equivalent":
            self.assertEqual(payload["implementation_status"], "UNVERIFIED")
            self.assertFalse(payload["persisted"])
        self.assertEqual(len(payload["results"]), 1)
        item = payload["results"][0]
        self.assertEqual(len(item["dimensions"]), 8)
        self.assertIn(item["recommendation"], ("ADVANCE", "NEED_MORE_INFO", "REJECT"))
        self.assertTrue(0 <= item["score"] <= 100)
        self.assertIn(item["supply_id"], ("SUP-20261116-001",))

    def test_run_match_compute_accepts_text_input_ref(self):
        task = runner.create_task(
            "Matching Engine",
            "match_compute",
            "文本 input_ref 匹配",
            input_ref="demand_id=DEM-20261116-001 supply_ids=SUP-20261116-001,SUP-20261116-002",
        )
        result = runner.run_task(task["task_id"])
        self.assertEqual(result["status"], "DONE", result)
        payload = self.read_output(result["output_path"])
        self.assertEqual(payload["supply_count"], 2)

    def test_run_report_render_writes_markdown_and_allows_non_asii(self):
        task = runner.create_task("Research Director", "report_render", "测试报告渲染")
        result = runner.run_task(task["task_id"])
        self.assertEqual(result["status"], "DONE", result)
        path = Path(result["output_path"])
        if not path.is_absolute():
            path = ROOT / path
        self.assertEqual(path.suffix, ".md")
        text = path.read_text(encoding="utf-8")
        self.assertIn("## 1. 数据概览", text)
        self.assertIn("需求", text)

    def test_run_all_executes_seeded_queue(self):
        result = runner.run_all(status="QUEUED")
        self.assertEqual(result["count"], 11)
        self.assertEqual(result["failed"], 0, result)
        self.assertGreaterEqual(result["done"], 8)
        statuses = {item["status"] for item in result["results"]}
        self.assertTrue(statuses <= {"DONE", "BLOCKED", "FAILED"})
        for item in result["results"]:
            if item["status"] == "DONE":
                self.assertTrue(Path(item["output_path"]).exists()
                                or (ROOT / item["output_path"]).exists(), item)
        outputs = [p for p in self.out_dir.glob("*") if p.is_file()]
        self.assertGreaterEqual(len(outputs), result["done"])

    def test_rerun_and_unknown_tasks_raise_clean_errors(self):
        task = runner.create_task("Data Manager", "data_audit", "只能跑一次")
        self.assertEqual(runner.run_task(task["task_id"])["status"], "DONE")
        with self.assertRaises(runner.RunnerError):
            runner.run_task(task["task_id"])
        with self.assertRaises(runner.RunnerError):
            runner.run_task("TASK-29990101-999")

    def test_cli_list_show_create_run_validate(self):
        proc = run_cli("list")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        listed = json.loads(proc.stdout)
        self.assertEqual(listed["total"], 11)

        proc = run_cli("show", "Data Manager")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        shown = json.loads(proc.stdout)
        self.assertEqual(shown["agent"]["name"], "Data Manager")

        proc = run_cli(
            "create", "--agent", "QA", "--type", "schema_validate", "--title", "CLI 创建的校验任务"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        created = json.loads(proc.stdout)
        self.assertTrue(created["task_id"].startswith("TASK-"))

        proc = run_cli("run", created["task_id"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        ran = json.loads(proc.stdout)
        self.assertEqual(ran["status"], "DONE")
        self.assertTrue(Path(ran["output_path"]).exists()
                        or (ROOT / ran["output_path"]).exists())

        proc = run_cli("validate")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        validated = json.loads(proc.stdout)
        self.assertTrue(validated["ok"])

    def test_run_all_cli_exit_code_zero(self):
        proc = run_cli("run-all", "--status", "QUEUED")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["count"], 11)
        self.assertEqual(result["failed"], 0)


class MissingDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ccgs_runner_missing_"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self._saved = os.environ.get("CCGS_DB_PATH")
        os.environ["CCGS_DB_PATH"] = str(self.tmp / "does_not_exist.db")

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("CCGS_DB_PATH", None)
        else:
            os.environ["CCGS_DB_PATH"] = self._saved

    def test_missing_db_is_a_clean_runner_error(self):
        with self.assertRaises(runner.RunnerError) as ctx:
            runner.list_tasks()
        self.assertIn("数据库不存在", str(ctx.exception))

    def test_validate_still_passes_without_database(self):
        result = runner.validate_all()
        self.assertTrue(result["ok"])
        self.assertFalse(result["database"]["checked"])
        self.assertIn("数据库不存在", result["database"]["note"])

    def test_cli_run_reports_error_exit_code_2(self):
        proc = run_cli("list")
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("error", json.loads(proc.stderr))


if __name__ == "__main__":
    unittest.main()
