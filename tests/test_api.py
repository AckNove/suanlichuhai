# -*- coding: utf-8 -*-
"""HTTP API 测试：通用 CRUD、状态机 409、dashboard、匹配、审批、导出导入等。"""
from __future__ import annotations

import io
import unittest

from app.backend.server import create_app
from tests import TempEnv

BOM = b"\xef\xbb\xbf"


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv().__enter__()
        self.app = create_app(seed_data=True)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.env.__exit__(None, None, None)

    def _json(self, method, path, **kwargs):
        response = getattr(self.client, method)(path, **kwargs)
        return response, response.get_json(silent=True)

    # -- 健康检查 -----------------------------------------------------------
    def test_health(self):
        response, payload = self._json("get", "/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["version"], "1.0.0")
        self.assertEqual(payload["tables"], 18)
        self.assertIn("db", payload)
        self.assertIn("time", payload)

    def test_health_db(self):
        response, payload = self._json("get", "/api/health/db")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["table_count"], 18)
        self.assertEqual(len(payload["tables"]), 18)
        self.assertIsInstance(payload["recent_backups"], list)

    # -- 通用 CRUD ----------------------------------------------------------
    def test_list_pagination_filter_sort(self):
        response, payload = self._json("get", "/api/companies?company_type=DEMANDER&page_size=5")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["total"], 9)
        self.assertEqual(len(payload["items"]), 5)
        response, payload = self._json("get", "/api/demands?lead_grade=PUBLIC_LEAD")
        self.assertEqual(payload["total"], 9)
        response, payload = self._json("get", "/api/demands?sort=-id&page_size=3")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(payload["items"]), 3)
        response, payload = self._json("get", "/api/demands?q=训练")
        self.assertEqual(response.status_code, 200)

    def test_crud_lifecycle(self):
        response, payload = self._json("post", "/api/companies",
                                       json={"name": "接口测试公司", "company_type": "SUPPLIER"})
        self.assertEqual(response.status_code, 201)
        company = payload["item"]
        self.assertTrue(company["id"].startswith("C-"))
        item_id = company["id"]

        response, payload = self._json("get", "/api/companies/%s" % item_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["item"]["name"], "接口测试公司")

        response, payload = self._json("patch", "/api/companies/%s" % item_id,
                                       json={"region": "东南亚", "notes": "PATCH 局部更新"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["item"]["region"], "东南亚")
        self.assertEqual(payload["item"]["name"], "接口测试公司")

        response, payload = self._json("put", "/api/companies/%s" % item_id,
                                       json={"region": "东亚"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["item"]["region"], "东亚")

        response = self.client.delete("/api/companies/%s" % item_id)
        self.assertEqual(response.status_code, 204)
        response, payload = self._json("get", "/api/companies/%s" % item_id)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(payload["error"]["code"], "NOT_FOUND")

    def test_invalid_transition_409(self):
        response, payload = self._json("post", "/api/companies",
                                       json={"name": "状态机接口公司", "company_type": "SUPPLIER"})
        item_id = payload["item"]["id"]
        response, payload = self._json("patch", "/api/companies/%s" % item_id,
                                       json={"status": "VERIFIED"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload["error"]["code"], "CONFLICT")
        self.assertIn("允许目标状态", payload["error"]["message"])
        response, payload = self._json("get", "/api/companies/%s" % item_id)
        self.assertEqual(payload["item"]["status"], "LEAD")

    def test_validation_errors(self):
        response, payload = self._json("post", "/api/demands", json={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")
        response, payload = self._json("post", "/api/demands",
                                       json={"title": "线索", "lead_grade": "HOT"})
        self.assertEqual(response.status_code, 400)
        response, payload = self._json("post", "/api/companies", data="not-json",
                                       content_type="text/plain")
        self.assertEqual(response.status_code, 400)
        response, payload = self._json("get", "/api/unknown-resource")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(payload["error"]["code"], "NOT_FOUND")
        response, payload = self._json("get", "/api/demands/DEM-NOT-EXIST")
        self.assertEqual(response.status_code, 404)

    def test_read_only_resource_forbidden(self):
        response, payload = self._json("patch", "/api/activities/1", json={"summary": "改动"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(payload["error"]["code"], "FORBIDDEN")

    # -- dashboard ----------------------------------------------------------
    def test_dashboard(self):
        response, payload = self._json("get", "/api/dashboard")
        self.assertEqual(response.status_code, 200)
        counts = payload["counts"]
        self.assertEqual(counts["companies"], 27)
        self.assertEqual(counts["suppliers"], 18)
        self.assertEqual(counts["demanders"], 9)
        self.assertEqual(counts["supplies"], 18)
        self.assertEqual(counts["demands"], 9)
        self.assertGreaterEqual(counts["evidence"], 10)
        self.assertEqual(counts["matches"], 3)
        self.assertEqual(counts["pending_approvals"], 7)
        self.assertEqual(counts["knowledge"], 6)
        self.assertIn("supplier", payload["pipeline"])
        self.assertIn("demand", payload["pipeline"])
        self.assertIn("opportunity", payload["pipeline"])
        self.assertEqual(payload["grades"]["PUBLIC_LEAD"], 9)
        self.assertEqual(set(payload["grades"].keys()),
                         {"PUBLIC_LEAD", "INFERRED", "POTENTIAL", "VERIFIED", "QUALIFIED"})
        self.assertEqual(payload["verification"]["verified"], 0)
        self.assertEqual(payload["verification"]["needs_verification"], 18)
        self.assertIsInstance(payload["recent_activities"], list)
        alert_codes = {item["code"] for item in payload["alerts"]}
        self.assertIn("NO_LEGAL_ENTITY", alert_codes)
        self.assertIn("PUBLIC_REPO", alert_codes)

    # -- 匹配 ---------------------------------------------------------------
    def test_match_score_all_supplies(self):
        response, payload = self._json("post", "/api/match/score",
                                       json={"demand_id": "DEM-20261102-001"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["count"], 18)
        self.assertFalse(payload["persisted"])
        results = payload["results"]
        self.assertEqual(len(results), 18)
        scores = [item["score"] for item in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
        for item in results:
            self.assertEqual(len(item["dimensions"]), 8)
            self.assertGreaterEqual(item["score"], 0)
            self.assertLessEqual(item["score"], 100)
            self.assertIn(item["recommendation"], {"ADVANCE", "NEED_MORE_INFO", "REJECT"})
            self.assertIn(item["confidence"], {"HIGH", "MEDIUM", "LOW"})
        matches = self.client.get("/api/matches").get_json()
        self.assertEqual(matches["total"], 3, "/api/match/score 不应落库")

    def test_match_run_persists(self):
        response, payload = self._json("post", "/api/match/run", json={
            "demand_id": "DEM-20261102-001",
            "supply_ids": ["SUP-20261102-001", "SUP-20261102-007"],
            "persist": True,
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["persisted"])
        self.assertEqual(payload["count"], 2)
        for item in payload["results"]:
            self.assertTrue(item["id"].startswith("MATCH-"))
        matches = self.client.get("/api/matches").get_json()
        self.assertEqual(matches["total"], 5)
        match_id = payload["results"][0]["id"]
        response, detail = self._json("get", "/api/matches/%s" % match_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(detail["item"]["status"], "DRAFT")
        self.assertEqual(detail["item"]["analyst"], "local")

    def test_match_errors(self):
        response, payload = self._json("post", "/api/match/run", json={})
        self.assertEqual(response.status_code, 400)
        response, payload = self._json("post", "/api/match/score",
                                       json={"demand_id": "DEM-NOT-EXIST"})
        self.assertEqual(response.status_code, 404)
        response, payload = self._json("post", "/api/match/score",
                                       json={"demand_id": "DEM-20261102-001",
                                             "supply_ids": ["SUP-NOT-EXIST"]})
        self.assertEqual(response.status_code, 404)

    # -- 审批 ---------------------------------------------------------------
    def test_approvals_pending_and_decide(self):
        response, payload = self._json("get", "/api/approvals/pending")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["total"], 7)
        approval = payload["items"][0]
        self.assertEqual(approval["status"], "PENDING")
        approval_id = approval["id"]

        response, payload = self._json("post", "/api/approvals/%s/decide" % approval_id,
                                       json={"decision": "APPROVED", "decided_by": "CEO",
                                             "note": "单元测试批准"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["item"]["status"], "APPROVED")
        self.assertEqual(payload["item"]["decided_by"], "CEO")
        response, pending = self._json("get", "/api/approvals/pending")
        self.assertEqual(pending["total"], 6)

        response, payload = self._json("post", "/api/approvals/%s/decide" % approval_id,
                                       json={"decision": "REJECTED", "decided_by": "CEO"})
        self.assertEqual(response.status_code, 409)
        response, payload = self._json("post", "/api/approvals/%s/decide" % approval_id,
                                       json={"decision": "MAYBE"})
        self.assertEqual(response.status_code, 400)

    def test_approval_does_not_auto_upgrade_company(self):
        response, payload = self._json("post", "/api/companies",
                                       json={"name": "不自动升级公司", "company_type": "SUPPLIER"})
        company_id = payload["item"]["id"]
        approval = self.client.get("/api/approvals/pending").get_json()["items"][0]
        self.client.post("/api/approvals/%s/decide" % approval["id"],
                         json={"decision": "APPROVED", "decided_by": "CEO"})
        response, payload = self._json("get", "/api/companies/%s" % company_id)
        self.assertEqual(payload["item"]["status"], "LEAD", "审批不应自动升级业务状态")

    # -- 导出 / 导入 --------------------------------------------------------
    def test_export_endpoint(self):
        response = self.client.get("/api/export?entity=companies&format=csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["Content-Type"])
        self.assertIn("charset=utf-8", response.headers["Content-Type"])
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertTrue(response.data.startswith(BOM))
        response = self.client.get("/api/export?entity=not-an-entity")
        self.assertEqual(response.status_code, 400)

    def test_import_endpoint(self):
        raw = BOM + "id,name,company_type\n,CSV导入公司,SUPPLIER\n".encode("utf-8")
        response = self.client.post(
            "/api/import?entity=companies&mode=insert",
            data={"file": (io.BytesIO(raw), "companies.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["inserted"], 1)
        self.assertEqual(payload["errors"], [])
        response, companies = self._json("get", "/api/companies?q=CSV导入公司")
        self.assertGreaterEqual(companies["total"], 1)

    # -- 搜索 / 报表 / 状态机 -----------------------------------------------
    def test_search(self):
        response, payload = self._json("get", "/api/search?q=阿里&limit=10")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(payload["total"], 1)
        self.assertTrue(any(item["type"] == "company" for item in payload["results"]))
        response, payload = self._json("get", "/api/search?q=Runpod&limit=10")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(item["type"] == "evidence" for item in payload["results"]),
                        "证据表搜索应命中 Runpod 价目")
        response, payload = self._json("get", "/api/search?q=收费&limit=10")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(item["type"] == "knowledge" for item in payload["results"]),
                        "知识库搜索应命中收费原则")
        response, payload = self._json("get", "/api/search")
        self.assertEqual(response.status_code, 400)

    def test_reports(self):
        response, payload = self._json("get", "/api/reports/pipeline")
        self.assertEqual(response.status_code, 200)
        self.assertIn("counts", payload)
        self.assertTrue(payload["data_insufficient"])
        self.assertIsNone(payload["conversion"])
        response, payload = self._json("get", "/api/reports/fee-scenarios")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["example_only"])
        self.assertIn("不构成报价", payload["disclaimer"])
        text = str(payload)
        self.assertIn("X%", text)
        self.assertNotIn("10%", text)

    def test_state_transitions(self):
        response, payload = self._json("get", "/api/state/transitions")
        self.assertEqual(response.status_code, 200)
        self.assertIn("RESEARCHED", payload["transitions"]["supplier"]["LEAD"])
        self.assertIn("LEAD", payload["states"]["supplier"])
        self.assertEqual(payload["state_fields"]["companies"]["field"], "status")

    # -- Agent / Skill ------------------------------------------------------
    def test_agents_endpoint(self):
        response, payload = self._json("get", "/api/agents")
        self.assertEqual(response.status_code, 200)
        self.assertIn("agents", payload)
        if payload["agents"]:
            self.assertEqual(len(payload["agents"]), 11)
            self.assertIn("name", payload["agents"][0])

    def test_skills_endpoint(self):
        response, payload = self._json("get", "/api/skills")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(payload["count"], 6)
        for item in payload["items"]:
            self.assertTrue(item["name"])
            self.assertIn("path", item)

    def test_agent_task_run(self):
        response, payload = self._json("post", "/api/agent-tasks/TASK-20261116-010/run",
                                       json={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["task_id"], "TASK-20261116-010")
        self.assertIn(payload["status"], {"DONE", "BLOCKED", "FAILED"})
        if payload["status"] == "DONE":
            self.assertTrue(payload.get("output_path"))

    # -- 首页 ---------------------------------------------------------------
    def test_root_serves_frontend_or_fallback(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["Content-Type"])
        self.assertIn("<html", response.get_data(as_text=True).lower())


if __name__ == "__main__":
    unittest.main()
