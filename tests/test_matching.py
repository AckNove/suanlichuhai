# -*- coding: utf-8 -*-
"""确定性匹配引擎测试：8 维评分、推荐阈值、红线封顶、确定性。"""
from __future__ import annotations

import json
import unittest

from app.backend import db, matching, repo
from tests import TempEnv

STRONG_DEMAND = {
    "id": "DEM-UNIT-001",
    "gpu_models": "H100",
    "min_gpu_count": 100,
    "workload_type": "TRAINING",
    "location_preference": "新加坡",
    "company_country": "新加坡",
    "timeline": "2个月",
    "compliance_notes": "已筛查",
    "data_residency": "",
}
STRONG_SUPPLY = {
    "id": "SUP-UNIT-001",
    "gpu_model": "H100",
    "sellable_gpu_count": 200,
    "training_capable": 1,
    "location_country": "新加坡",
    "delivery_lead_time": "4周",
    "network_bandwidth": "3.2Tbps InfiniBand",
    "verified": 1,
    "status": "VERIFIED",
}


class MatchingEngineTest(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv().__enter__()
        self.conn = db.ensure_schema()

    def tearDown(self):
        try:
            self.conn.close()
        except Exception:  # noqa: BLE001
            pass
        self.env.__exit__(None, None, None)

    # -- 归一化 -------------------------------------------------------------
    def test_normalize_gpu(self):
        self.assertEqual(matching.normalize_gpu("NVIDIA H100 SXM5"), ["H100"])
        self.assertEqual(matching.normalize_gpu("H100SXM"), ["H100"])
        self.assertEqual(matching.normalize_gpu("昇腾910B"), ["910B"])
        self.assertEqual(matching.normalize_gpu("RTX 4090"), ["4090"])
        self.assertEqual(matching.normalize_gpu("H100,H200"), ["H100", "H200"])
        self.assertEqual(matching.normalize_gpu(""), [])
        self.assertEqual(matching.normalize_gpu(None), [])
        self.assertEqual(matching.normalize_gpu("未知型号XYZ"), [])

    def test_dimension_max_matches_spec(self):
        self.assertEqual(matching.DIMENSION_MAX, {
            "gpu_model": 30, "scale": 20, "workload": 15, "location": 10,
            "delivery": 10, "network": 5, "compliance": 5, "trust": 5,
        })
        self.assertEqual(sum(matching.DIMENSION_MAX.values()), 100)

    # -- 满分与推荐 ---------------------------------------------------------
    def test_strong_pair_full_score_advance(self):
        result = matching.score_pair(dict(STRONG_DEMAND), dict(STRONG_SUPPLY))
        self.assertEqual(result["score"], 100.0)
        self.assertEqual(result["recommendation"], "ADVANCE")
        self.assertEqual(result["confidence"], "HIGH")
        self.assertEqual(len(result["dimensions"]), 8)
        for name, dim in result["dimensions"].items():
            self.assertEqual(dim["max"], matching.DIMENSION_MAX[name])
            self.assertEqual(dim["score"], dim["max"], "%s 应满分" % name)
            self.assertTrue(dim["reason"])
        self.assertIn("精确匹配", result["dimensions"]["gpu_model"]["reason"])
        self.assertTrue(result["why_match"])
        self.assertIn("不得外发", result["why_not_match"])

    def test_recommendation_threshold_need_more_info(self):
        demand = {
            "gpu_models": "H100", "min_gpu_count": 100, "workload_type": "TRAINING",
            "timeline": "", "company_country": "", "location_preference": "",
            "compliance_notes": "",
        }
        supply = {
            "gpu_model": "H200", "sellable_gpu_count": 100, "training_capable": 1,
            "location_country": "", "verified": 0, "status": "LEAD",
        }
        result = matching.score_pair(demand, supply)
        self.assertEqual(result["dimensions"]["gpu_model"]["score"], 20)
        self.assertEqual(result["score"], 69.0)
        self.assertEqual(result["recommendation"], "NEED_MORE_INFO")

    def test_recommendation_threshold_reject(self):
        result = matching.score_pair({}, {})
        self.assertLess(result["score"], 40)
        self.assertEqual(result["recommendation"], "REJECT")

    def test_advance_after_network_info(self):
        demand = {
            "gpu_models": "H100", "min_gpu_count": 100, "workload_type": "TRAINING",
            "timeline": "", "company_country": "", "location_preference": "",
            "compliance_notes": "",
        }
        supply = {
            "gpu_model": "H200", "sellable_gpu_count": 100, "training_capable": 1,
            "location_country": "", "verified": 0, "status": "LEAD",
            "network_bandwidth": "3.2Tbps InfiniBand",
        }
        result = matching.score_pair(demand, supply)
        self.assertEqual(result["score"], 72.0)
        self.assertEqual(result["recommendation"], "ADVANCE")
        self.assertEqual(result["confidence"], "HIGH")

    # -- 各维度细节 ---------------------------------------------------------
    def test_gpu_same_group_and_alt_pair(self):
        same_group = matching.score_pair(
            {"gpu_models": "H100"},
            {"gpu_model": "H800"},
        )
        self.assertEqual(same_group["dimensions"]["gpu_model"]["score"], 20)
        self.assertIn("hopper", same_group["dimensions"]["gpu_model"]["reason"])
        alt_pair = matching.score_pair(
            {"gpu_models": "A100"},
            {"gpu_model": "H100"},
        )
        self.assertEqual(alt_pair["dimensions"]["gpu_model"]["score"], 10)
        incompatible = matching.score_pair(
            {"gpu_models": "H100"},
            {"gpu_model": "4090"},
        )
        self.assertEqual(incompatible["dimensions"]["gpu_model"]["score"], 0)

    def test_scale_deficit(self):
        result = matching.score_pair(
            {"min_gpu_count": 100, "gpu_models": "H100"},
            {"gpu_model": "H100", "sellable_gpu_count": 60},
        )
        self.assertEqual(result["dimensions"]["scale"]["score"], 12)

    def test_workload_mismatch(self):
        result = matching.score_pair(
            {"workload_type": "TRAINING", "gpu_models": "H100"},
            {"gpu_model": "H100", "training_capable": 0},
        )
        self.assertEqual(result["dimensions"]["workload"]["score"], 0)

    def test_location_region_and_delivery(self):
        result = matching.score_pair(
            {"gpu_models": "H100", "company_country": "中国",
             "compliance_notes": "已筛查", "timeline": "2个月"},
            {"gpu_model": "H100", "location_country": "香港",
             "delivery_lead_time": "90天"},
        )
        self.assertEqual(result["dimensions"]["location"]["score"], 6)
        self.assertEqual(result["dimensions"]["delivery"]["score"], 0)
        good_delivery = matching.score_pair(
            {"timeline": "2个月"},
            {"delivery_lead_time": "4周"},
        )
        self.assertEqual(good_delivery["dimensions"]["delivery"]["score"], 10)

    def test_trust_levels(self):
        lead = matching.score_pair({}, {"verified": 0, "status": "LEAD"})
        self.assertEqual(lead["dimensions"]["trust"]["score"], 1)
        researched = matching.score_pair({}, {"verified": 0, "status": "RESEARCHED"})
        self.assertEqual(researched["dimensions"]["trust"]["score"], 2)
        verified = matching.score_pair({}, {"verified": 1})
        self.assertEqual(verified["dimensions"]["trust"]["score"], 5)

    # -- 红线 ---------------------------------------------------------------
    def test_red_line_cross_border_unscreened_capped(self):
        demand = dict(STRONG_DEMAND)
        demand["company_country"] = "中国"
        demand["compliance_notes"] = ""
        demand["location_preference"] = "中国"
        supply = dict(STRONG_SUPPLY)
        supply["location_country"] = "新加坡"
        result = matching.score_pair(demand, supply)
        self.assertEqual(result["score"], 39.0, "命中红线后总分必须封顶 39")
        self.assertEqual(result["recommendation"], "REJECT")
        self.assertEqual(result["confidence"], "LOW")
        self.assertTrue(result["red_lines"])
        self.assertIn("跨境合规未筛查", result["why_not_match"])
        self.assertIn("封顶 39", result["why_not_match"])

    def test_red_line_data_residency(self):
        result = matching.score_pair(
            {"gpu_models": "H100", "data_residency": "数据需驻留中国",
             "company_country": "中国", "location_preference": "中国"},
            {"gpu_model": "H100", "location_country": "美国"},
        )
        self.assertEqual(result["dimensions"]["location"]["score"], 0)
        self.assertIn("数据驻留冲突", " ".join(result["red_lines"]))
        self.assertLessEqual(result["score"], 39)

    def test_red_line_resale_right_from_db(self):
        company = repo.create_item(self.conn, "companies",
                                   {"name": "无转售权测试公司", "company_type": "SUPPLIER"},
                                   actor="tester")
        supply = repo.create_item(self.conn, "supplies", {
            "company_id": company["id"], "gpu_model": "H100",
            "sellable_gpu_count": 100, "training_capable": 1,
            "location_country": "新加坡",
        }, actor="tester")
        repo.create_item(self.conn, "supplier-verifications", {
            "supplier_company_id": company["id"], "resale_right_ok": 0,
            "status": "PENDING",
        }, actor="tester")
        result = matching.score_pair(dict(STRONG_DEMAND), supply, conn=self.conn)
        self.assertLessEqual(result["score"], 39)
        self.assertEqual(result["dimensions"]["trust"]["score"], 0)
        self.assertTrue(any("转售权" in line for line in result["red_lines"]))
        self.assertIn("转售权", result["why_not_match"])

    # -- 批量 / 确定性 / 适配入口 -------------------------------------------
    def test_score_many_sorted_and_deterministic(self):
        supplies = [
            dict(STRONG_SUPPLY),
            {"id": "SUP-UNIT-002", "gpu_model": "4090", "location_country": "美国"},
            {"id": "SUP-UNIT-003", "gpu_model": "H100", "sellable_gpu_count": 100,
             "training_capable": 1, "location_country": "新加坡", "verified": 1},
        ]
        first = matching.score_many(dict(STRONG_DEMAND), supplies)
        second = matching.score_many(dict(STRONG_DEMAND), supplies)
        self.assertEqual(first, second, "同一输入必须输出完全一致")
        scores = [item["score"] for item in first]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(len(first), 3)
        for item in first:
            self.assertIn("supply_id", item)
            self.assertIn("dimensions", item)

    def test_score_aliases_equal_score_pair(self):
        base = matching.score_pair(dict(STRONG_DEMAND), dict(STRONG_SUPPLY))
        self.assertEqual(matching.score_match(dict(STRONG_DEMAND), dict(STRONG_SUPPLY)), base)
        self.assertEqual(matching.score(dict(STRONG_DEMAND), dict(STRONG_SUPPLY)), base)
        dimensions = json.loads(matching.dimensions_json(base))
        self.assertEqual(set(dimensions.keys()), set(matching.DIMENSION_MAX.keys()))
        self.assertEqual(len(dimensions), 8)

    def test_why_match_reason_contains_dimensions(self):
        result = matching.score_pair(dict(STRONG_DEMAND), dict(STRONG_SUPPLY))
        self.assertIn("GPU 型号", result["why_match"])
        self.assertIn("规模", result["why_match"])


if __name__ == "__main__":
    unittest.main()
