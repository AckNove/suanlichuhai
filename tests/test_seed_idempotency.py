# -*- coding: utf-8 -*-
"""种子导入幂等性回归测试。

背景：旧版 `seed.import_demand_side` 用「当天日期」生成需求方公司 ID，
导致每次跨天启动都会新增 9 个未引用的重复 DEMANDER 公司（2026-11-19 实际发生）。
修复后要求：重复导入 0 新增，且公司 ID 由需求线索 ID 稳定派生。
"""
from __future__ import annotations

import unittest

from app.backend import db, seed
from tests import TempEnv


class DemandSeedIdempotencyTest(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv().__enter__()
        self.conn = db.ensure_schema()

    def tearDown(self):
        try:
            self.conn.close()
        except Exception:  # noqa: BLE001
            pass
        self.env.__exit__(None, None, None)

    def _company_count(self):
        return self.conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]

    def _demand_count(self):
        return self.conn.execute("SELECT COUNT(*) FROM demand_opportunities").fetchone()[0]

    def test_repeat_import_creates_nothing(self):
        first = seed.import_demand_side(self.conn)
        self.conn.commit()
        companies_after_first = self._company_count()
        demands_after_first = self._demand_count()
        self.assertGreater(companies_after_first, 0, "首次导入应创建需求方公司")
        self.assertEqual(demands_after_first, 9, "历史需求侧注册表应有 9 条需求线索")

        second = seed.import_demand_side(self.conn)
        self.conn.commit()
        self.assertEqual(second["companies"]["inserted"], 0, "重复导入不得新增公司")
        self.assertEqual(second["demands"]["inserted"], 0, "重复导入不得新增需求")
        self.assertEqual(self._company_count(), companies_after_first, "公司数量必须保持不变")
        self.assertEqual(self._demand_count(), demands_after_first, "需求数量必须保持不变")

    def test_company_id_is_derived_and_stable(self):
        seed.import_demand_side(self.conn)
        self.conn.commit()
        rows = self.conn.execute(
            "SELECT id, company_id FROM demand_opportunities ORDER BY id").fetchall()
        self.assertEqual(len(rows), 9)
        for demand_id, company_id in rows:
            self.assertEqual(
                company_id, "C-%s" % demand_id,
                "公司 ID 必须由需求线索 ID 稳定派生（%s -> C-%s），实际 %s"
                % (demand_id, demand_id, company_id))
            exists = self.conn.execute(
                "SELECT COUNT(*) FROM companies WHERE id=?", (company_id,)).fetchone()[0]
            self.assertEqual(exists, 1, "需求必须关联到已创建的公司 %s" % company_id)

    def test_no_unreferenced_demander_after_two_imports(self):
        seed.import_demand_side(self.conn)
        seed.import_demand_side(self.conn)
        self.conn.commit()
        unreferenced = self.conn.execute(
            "SELECT COUNT(*) FROM companies c WHERE c.company_type='DEMANDER' "
            "AND NOT EXISTS (SELECT 1 FROM demand_opportunities d WHERE d.company_id=c.id)"
        ).fetchone()[0]
        self.assertEqual(unreferenced, 0, "不得存在未关联需求的 DEMANDER 公司（重复公司缺陷）")


if __name__ == "__main__":
    unittest.main()
