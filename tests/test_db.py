# -*- coding: utf-8 -*-
"""数据库与种子数据测试：建表、WAL、幂等、真实性规则、ID、审计、状态机。"""
from __future__ import annotations

import re
import unittest

from app.backend import db, repo, seed
from tests import TempEnv


class SchemaSeedTest(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv().__enter__()
        self.conn = db.ensure_schema()

    def tearDown(self):
        try:
            self.conn.close()
        except Exception:  # noqa: BLE001 - 连接可能已被 restore 关闭
            pass
        self.env.__exit__(None, None, None)

    # -- 建表 ---------------------------------------------------------------
    def test_schema_tables_and_pragmas(self):
        tables = db.list_tables(self.conn)
        self.assertEqual(len(tables), 18, "应有 18 张表，实际：%s" % tables)
        expected = [
            "companies", "demand_opportunities", "compute_supply_resources",
            "compute_specifications", "evidence_registry", "supplier_verification",
            "demand_qualification", "matching_records", "procurement_analyses",
            "commercial_opportunities", "quotes", "contracts_metadata", "agent_tasks",
            "project_activities", "knowledge_records", "audit_logs", "approvals",
            "backup_records",
        ]
        for name in expected:
            self.assertIn(name, tables)
        self.assertEqual(len(db.table_columns(self.conn, "companies")), 17)
        self.assertEqual(len(db.table_columns(self.conn, "compute_supply_resources")), 25)
        self.assertEqual(self.conn.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal")
        self.assertEqual(self.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_schema_idempotent(self):
        again = db.ensure_schema()
        try:
            self.assertEqual(len(db.list_tables(again)), 18)
        finally:
            again.close()

    # -- 种子 ---------------------------------------------------------------
    def test_seed_counts_and_idempotent(self):
        first = seed.seed_all(self.conn)
        self.assertGreater(first["inserted_total"], 0)
        self.assertEqual(first["inserted"].get("supplies"), 18)
        self.assertEqual(first["inserted"].get("demands"), 9)
        self.assertEqual(first["inserted"].get("matches"), 3)
        self.assertEqual(first["inserted"].get("specs"), 10)
        self.assertEqual(first["inserted"].get("agent_tasks"), 11)
        self.assertEqual(first["inserted"].get("knowledge"), 6)
        self.assertGreaterEqual(first["inserted"].get("evidence", 0), 10)
        self.assertEqual(db.safe_count(self.conn, "companies"), 27)
        second = seed.seed_all(self.conn)
        self.assertEqual(second["inserted_total"], 0, "重复装载种子必须零新增")
        self.assertEqual(db.safe_count(self.conn, "companies"), 27)
        self.assertEqual(db.safe_count(self.conn, "compute_supply_resources"), 18)
        self.assertEqual(db.safe_count(self.conn, "demand_opportunities"), 9)
        self.assertEqual(db.safe_count(self.conn, "matching_records"), 3)
        self.assertEqual(db.safe_count(self.conn, "compute_specifications"), 10)
        self.assertEqual(db.safe_count(self.conn, "agent_tasks"), 11)
        self.assertEqual(db.safe_count(self.conn, "approvals"), 7)
        self.assertEqual(db.safe_count(self.conn, "knowledge_records"), 6)

    def test_history_seed_truthfulness(self):
        seed.seed_all(self.conn)
        supply = repo.get_item(self.conn, "supplies", "SUP-20261102-001")
        self.assertEqual(int(supply["verified"]), 0)
        self.assertEqual(supply["status"], "LEAD")
        self.assertEqual(supply["price_indication"], "待确认")
        demand = repo.get_item(self.conn, "demands", "DEM-20261102-001")
        self.assertEqual(demand["lead_grade"], "PUBLIC_LEAD")
        self.assertEqual(demand["status"], "LEAD")
        self.assertEqual(demand["budget_range"], "UNKNOWN")
        match = repo.get_item(self.conn, "matches", "MATCH-20261102-001")
        self.assertEqual(match["status"], "DRAFT")
        self.assertEqual(match["analyst"], "history-import")
        self.assertIsNone(match["score"], "历史模拟分不得写入正式评分字段")
        self.assertIn("历史样例，非真实订单", match["why_not_match"])
        # 敏感指针字段不允许进入数据库
        self.assertNotIn("sensitive_ptr", db.table_columns(self.conn, "compute_supply_resources"))
        self.assertNotIn("sensitive_ptr", db.table_columns(self.conn, "companies"))
        # 证据链：Runpod / Lambda 公开价目必须在库
        runpod = repo.get_item(self.conn, "evidence", "B-E22")
        lambda_ev = repo.get_item(self.conn, "evidence", "B-E23")
        self.assertIn("runpod", (runpod["url"] or "").lower())
        self.assertIn("lambda", (lambda_ev["url"] or "").lower())
        self.assertIn("证据表.md", runpod["notes"] or "")
        self.assertGreaterEqual(db.safe_count(self.conn, "evidence_registry"), 10)

    def test_demo_seed_notes_and_status(self):
        seed.seed_all(self.conn)
        specs = repo.all_rows(self.conn, "specs")
        self.assertEqual(len(specs), 10)
        for row in specs:
            self.assertIn("公开规格参考，非报价", row["notes"] or "")
            self.assertIn("seed:demo", row["notes"] or "")
        tasks = repo.all_rows(self.conn, "agent-tasks")
        self.assertEqual(len(tasks), 11)
        self.assertTrue(all(row["status"] == "QUEUED" for row in tasks))
        approvals = repo.all_rows(self.conn, "approvals")
        self.assertTrue(5 <= len(approvals) <= 8)
        self.assertTrue(all(row["status"] == "PENDING" for row in approvals))
        knowledge = repo.all_rows(self.conn, "knowledge")
        self.assertEqual(len(knowledge), 6)
        self.assertTrue(all(row["status"] == "PUBLISHED" for row in knowledge))

    # -- ID 生成 ------------------------------------------------------------
    def test_generated_id_prefixes(self):
        pairs = [
            ("companies", "C"), ("demands", "DEM"), ("supplies", "SUP"),
            ("matches", "MATCH"), ("commercial-opportunities", "OPP"),
            ("approvals", "APR"), ("agent-tasks", "TASK"), ("knowledge", "KN"),
            ("backups", "B"),
        ]
        for res, prefix in pairs:
            item_id = repo.generate_id(self.conn, res)
            self.assertRegex(item_id, r"^%s-\d{8}-\d{3}$" % re.escape(prefix),
                             "资源 %s 的 ID 前缀/格式不符：%s" % (res, item_id))

    # -- 审计 ---------------------------------------------------------------
    def test_audit_truncates_to_2000_chars(self):
        seed.seed_all(self.conn)
        big = {"payload": "汉" * 3000}
        db.record_write(self.conn, actor="tester", action="TEST", entity_type="unit",
                        entity_id="U-1", before=big, after=big, summary="审计截断测试")
        self.conn.commit()
        row = self.conn.execute(
            "SELECT before_json, after_json FROM audit_logs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertLessEqual(len(row["before_json"]), 2000)
        self.assertLessEqual(len(row["after_json"]), 2000)
        activity = self.conn.execute(
            "SELECT * FROM project_activities ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(activity["action"], "TEST")
        self.assertEqual(activity["actor"], "tester")

    def test_crud_writes_audit_and_activity(self):
        company = repo.create_item(self.conn, "companies", {"name": "审计测试公司"}, actor="tester")
        self.assertTrue(company["id"].startswith("C-"))
        updated = repo.update_item(self.conn, "companies", company["id"],
                                   {"region": "东南亚"}, actor="tester")
        self.assertEqual(updated["region"], "东南亚")
        audit_count = self.conn.execute(
            "SELECT COUNT(*) FROM audit_logs WHERE entity='companies' AND entity_id=?",
            (company["id"],),
        ).fetchone()[0]
        self.assertGreaterEqual(int(audit_count), 2)
        activities = self.conn.execute(
            "SELECT COUNT(*) FROM project_activities WHERE entity_type='companies' AND entity_id=?",
            (company["id"],),
        ).fetchone()[0]
        self.assertGreaterEqual(int(activities), 2)
        repo.delete_item(self.conn, "companies", company["id"], actor="tester")
        with self.assertRaises(repo.NotFoundError):
            repo.get_item(self.conn, "companies", company["id"])

    # -- 状态机 -------------------------------------------------------------
    def test_invalid_transition_raises_conflict(self):
        company = repo.create_item(self.conn, "companies",
                                   {"name": "状态机测试公司", "company_type": "SUPPLIER"},
                                   actor="tester")
        self.assertEqual(company["status"], "LEAD")
        with self.assertRaises(repo.ConflictError) as ctx:
            repo.update_item(self.conn, "companies", company["id"],
                             {"status": "VERIFIED"}, actor="tester")
        message = str(ctx.exception)
        self.assertIn("允许目标状态", message)
        self.assertIn("VERIFIED", message)
        self.assertEqual(repo.get_item(self.conn, "companies", company["id"])["status"], "LEAD")

    def test_verified_requires_supplier_verification(self):
        company = repo.create_item(self.conn, "companies",
                                   {"name": "核验守卫公司", "company_type": "SUPPLIER"},
                                   actor="tester")
        repo.update_item(self.conn, "companies", company["id"], {"status": "RESEARCHED"},
                         actor="tester")
        repo.update_item(self.conn, "companies", company["id"], {"status": "NEEDS_VERIFICATION"},
                         actor="tester")
        with self.assertRaises(repo.ConflictError):
            repo.update_item(self.conn, "companies", company["id"], {"status": "VERIFIED"},
                             actor="tester")

    def test_delete_with_dependents_conflict(self):
        supplier = next(row for row in repo.all_rows(self.conn, "companies")
                        if row["company_type"] == "SUPPLIER") if db.safe_count(
            self.conn, "companies") else None
        seed.seed_all(self.conn)
        supplier = repo.find_by(self.conn, "companies", company_type="SUPPLIER")[0]
        with self.assertRaises(repo.ConflictError):
            repo.delete_item(self.conn, "companies", supplier["id"], actor="tester")

    # -- 健康兜底 -----------------------------------------------------------
    def test_safe_count_missing_table(self):
        self.assertEqual(db.safe_count(self.conn, "table_not_exists"), 0)
        self.assertEqual(db.list_tables(self.conn).__class__, list)


if __name__ == "__main__":
    unittest.main()
