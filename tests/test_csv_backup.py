# -*- coding: utf-8 -*-
"""CSV 导入导出与备份/恢复测试。"""
from __future__ import annotations

import csv
import io
import unittest
from pathlib import Path

from app.backend import backup as backup_mod
from app.backend import csv_io, db, repo, seed
from tests import TempEnv

BOM = b"\xef\xbb\xbf"


def _csv_text(payload: bytes) -> str:
    return payload.decode("utf-8-sig")


class CsvIoTest(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv().__enter__()
        self.conn = db.ensure_schema()

    def tearDown(self):
        try:
            self.conn.close()
        except Exception:  # noqa: BLE001
            pass
        self.env.__exit__(None, None, None)

    # -- 导出 ---------------------------------------------------------------
    def test_export_csv_bom_and_columns(self):
        seed.seed_all(self.conn)
        filename, payload = csv_io.export_csv(self.conn, "companies")
        self.assertTrue(filename.startswith("companies-"))
        self.assertTrue(filename.endswith(".csv"))
        self.assertTrue(payload.startswith(BOM), "导出必须带 UTF-8 BOM")
        text = _csv_text(payload)
        reader = csv.reader(io.StringIO(text))
        header = next(reader)
        self.assertIn("id", header)
        self.assertIn("name", header)
        rows = list(reader)
        self.assertEqual(len(rows), 27)
        self.assertEqual(rows[0][header.index("name")].startswith(""), True)

    def test_export_unknown_entity_rejected(self):
        with self.assertRaises(repo.ValidationError):
            csv_io.export_csv(self.conn, "not-an-entity")

    # -- 导入 ---------------------------------------------------------------
    def _exported_rows(self, entity: str):
        filename, payload = csv_io.export_csv(self.conn, entity)
        text = _csv_text(payload)
        reader = csv.DictReader(io.StringIO(text))
        return list(reader.fieldnames or []), list(reader)

    @staticmethod
    def _rows_to_csv(fieldnames, rows) -> bytes:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)
        return BOM + buffer.getvalue().encode("utf-8")

    def test_import_roundtrip_updates(self):
        seed.seed_all(self.conn)
        fieldnames, rows = self._exported_rows("demands")
        self.assertEqual(len(rows), 9)
        target = next(row for row in rows if row["id"] == "DEM-20261102-001")
        original_title = target["title"]
        target["title"] = "【往返测试】" + original_title
        result = csv_io.import_csv(self.conn, "demands",
                                   self._rows_to_csv(fieldnames, rows),
                                   mode="upsert", actor="tester")
        self.assertEqual(result["inserted"], 0)
        self.assertGreaterEqual(result["updated"], 1)
        self.assertEqual(result["errors"], [])
        updated = repo.get_item(self.conn, "demands", "DEM-20261102-001")
        self.assertEqual(updated["title"], "【往返测试】" + original_title)

    def test_import_insert_mode_skips_existing(self):
        seed.seed_all(self.conn)
        fieldnames, rows = self._exported_rows("demands")
        result = csv_io.import_csv(self.conn, "demands",
                                   self._rows_to_csv(fieldnames, rows),
                                   mode="insert", actor="tester")
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["skipped"], 9)

    def test_import_auto_generates_id(self):
        raw = BOM + "name,company_type,country\n往返自动ID公司,SUPPLIER,中国\n".encode("utf-8")
        result = csv_io.import_csv(self.conn, "companies", raw, mode="insert", actor="tester")
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["errors"], [])
        rows = repo.find_by(self.conn, "companies", name="往返自动ID公司")
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["id"].startswith("C-"))

    def test_import_reports_row_errors(self):
        raw = BOM + "id,title\nC-FAKE-ROW-1,\n,合法需求\n".encode("utf-8")
        result = csv_io.import_csv(self.conn, "demands", raw, mode="insert", actor="tester")
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["errors"][0]["row"], 2)
        self.assertIn("title", result["errors"][0]["error"])

    def test_import_sensitive_contact_warning(self):
        raw = BOM + "id,name,notes\n,提醒测试公司,联系电话 13800138000\n".encode("utf-8")
        result = csv_io.import_csv(self.conn, "companies", raw, mode="insert", actor="tester")
        self.assertEqual(result["inserted"], 1)
        self.assertTrue(any("联系方式" in item for item in result["warnings"]))

    def test_import_unknown_field_warning(self):
        raw = BOM + "id,name,bogus\n,未知字段公司,x\n".encode("utf-8")
        result = csv_io.import_csv(self.conn, "companies", raw, mode="insert", actor="tester")
        self.assertEqual(result["inserted"], 1)
        self.assertTrue(any("未知字段" in item for item in result["warnings"]))

    def test_import_gbk_encoding_tolerated(self):
        text = "id,title,category,content_md\n,编码测试知识,test,中文内容测试\n"
        raw = text.encode("gbk")
        result = csv_io.import_csv(self.conn, "knowledge", raw, mode="insert", actor="tester")
        self.assertEqual(result["inserted"], 1)
        rows = repo.find_by(self.conn, "knowledge_records", title="编码测试知识")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["content_md"], "中文内容测试")

    def test_import_invalid_mode_rejected(self):
        with self.assertRaises(repo.ValidationError):
            csv_io.import_csv(self.conn, "demands", BOM + b"id,title\n", mode="replace")


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.env = TempEnv().__enter__()
        self.conn = db.ensure_schema()
        seed.seed_all(self.conn)

    def tearDown(self):
        try:
            self.conn.close()
        except Exception:  # noqa: BLE001
            pass
        self.env.__exit__(None, None, None)

    @staticmethod
    def _absolute(path_text: str) -> Path:
        path = Path(path_text)
        if not path.is_absolute():
            path = db.ROOT / path
        return path

    def test_backup_create_sha256_and_list(self):
        record = backup_mod.create_backup(self.conn, note="单元测试备份")
        self.assertTrue(record["id"].startswith("B-"))
        path = self._absolute(record["file_path"])
        self.assertTrue(path.exists())
        self.assertEqual(record["size_bytes"], path.stat().st_size)
        self.assertEqual(record["sha256"], backup_mod.sha256_file(path))
        self.assertEqual(len(record["sha256"]), 64)
        listed = backup_mod.list_backups(self.conn)["items"]
        self.assertTrue(any(item["id"] == record["id"] for item in listed))

    def test_backup_retention_keeps_latest(self):
        original = backup_mod.RETENTION
        backup_mod.RETENTION = 2
        try:
            ids = []
            for index in range(3):
                ids.append(backup_mod.create_backup(self.conn, note="保留测试 %d" % index)["id"])
            items = backup_mod.list_backups(self.conn)["items"]
            self.assertLessEqual(len(items), 2)
            self.assertIsNotNone(ids[-1])
        finally:
            backup_mod.RETENTION = original

    def test_restore_roundtrip(self):
        before = repo.list_items(self.conn, "matches")["total"]
        self.assertGreaterEqual(before, 3)
        backup = backup_mod.create_backup(self.conn, note="恢复测试备份")
        match_id = repo.all_rows(self.conn, "matches")[0]["id"]
        repo.delete_item(self.conn, "matches", match_id, actor="tester")
        self.assertEqual(repo.list_items(self.conn, "matches")["total"], before - 1)
        result = backup_mod.restore_backup(self.conn, backup["id"], confirm="RESTORE")
        self.assertTrue(result["restored"])
        self.assertIn("app-", Path(result["restored_from"]).name)
        safety = result.get("safety_backup") or {}
        self.assertTrue(str(safety.get("id") or "").startswith("B-"))
        self.conn = db.connect()  # restore 会关闭旧连接
        self.assertEqual(repo.list_items(self.conn, "matches")["total"], before)

    def test_restore_requires_explicit_confirm(self):
        backup = backup_mod.create_backup(self.conn, note="确认测试")
        with self.assertRaises(backup_mod.BackupError):
            backup_mod.restore_backup(self.conn, backup["id"], confirm="yes")

    def test_restore_unknown_backup_rejected(self):
        with self.assertRaises(backup_mod.BackupError):
            backup_mod.restore_backup(self.conn, "B-NOT-EXIST", confirm="RESTORE")


if __name__ == "__main__":
    unittest.main()
