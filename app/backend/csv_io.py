# -*- coding: utf-8 -*-
"""CSV 导入导出（UTF-8 BOM 导出；导入 UTF-8-BOM/GBK 容错；字段白名单 + 逐行错误报告）。"""
from __future__ import annotations

import csv
import io
import re
import zipfile

from . import db, repo

# 导出/导入允许的实体（与 SPEC_API 第 3 节一致）
EXPORT_ENTITIES = [
    "companies", "demands", "supplies", "specs", "evidence",
    "supplier-verifications", "demand-qualifications", "matches",
    "procurement-analyses", "commercial-opportunities", "quotes", "contracts",
    "agent-tasks", "knowledge", "approvals",
]

SENSITIVE_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),          # 邮箱
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),          # 手机号
    re.compile(r"(微信|WeChat|wechat)\s*[:：]?\s*[A-Za-z][-_A-Za-z0-9]{4,}"),
]


def _decode(raw) -> str:
    if isinstance(raw, str):
        return raw.lstrip("\ufeff")
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            return (raw or b"").decode(enc).lstrip("\ufeff")
        except UnicodeDecodeError:
            continue
    return (raw or b"").decode("utf-8", errors="replace").lstrip("\ufeff")


def _csv_bytes(header: list, rows: list) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow(["" if row.get(col) is None else row.get(col) for col in header])
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def export_csv(conn, entity: str) -> tuple:
    """返回 (filename, bytes)。UTF-8 BOM，便于 Excel 直接打开。"""
    if entity not in EXPORT_ENTITIES:
        raise repo.ValidationError("不支持导出的实体：%s（允许：%s）"
                                   % (entity, ", ".join(EXPORT_ENTITIES)))
    table = repo.get_table(entity)
    rows = repo.all_rows(conn, entity)
    header = db.table_columns(conn, table)
    filename = "%s-%s.csv" % (entity, db.today_stamp())
    return filename, _csv_bytes(header, rows)


def export_zip(conn) -> tuple:
    """全部实体打包为 zip（备用能力，/api/export 未暴露）。"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for entity in EXPORT_ENTITIES:
            try:
                name, payload = export_csv(conn, entity)
            except Exception:
                continue
            zf.writestr(name, payload)
    return "ccgs-export-%s.zip" % db.today_stamp(), buffer.getvalue()


def _sensitive_hits(row: dict) -> list:
    text = " ".join(str(v) for k, v in row.items()
                    if k in ("notes", "business_summary", "description", "next_action", "claim"))
    hits = []
    for pattern in SENSITIVE_PATTERNS:
        for match in pattern.finditer(text):
            hits.append(match.group(0)[:40])
    return hits


def import_csv(conn, entity: str, raw, mode: str = "upsert", actor: str = "local") -> dict:
    """导入 CSV。mode=insert 仅新增；mode=upsert 按 id 更新。返回逐行错误。"""
    if entity not in EXPORT_ENTITIES:
        raise repo.ValidationError("不支持导入的实体：%s" % entity)
    if mode not in ("insert", "upsert"):
        raise repo.ValidationError("mode 仅支持 insert 或 upsert")
    table = repo.get_table(entity)
    known = set(db.table_columns(conn, table))
    if not known:
        raise repo.ValidationError("目标表不存在：%s" % table)

    text = _decode(raw)
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = [name for name in (reader.fieldnames or []) if name]
    if not fieldnames:
        raise repo.ValidationError("CSV 为空或缺少表头")

    warnings = []
    unknown = [name for name in fieldnames if name not in known]
    if unknown:
        warnings.append("已忽略未知字段：%s" % ", ".join(unknown))
    if "id" not in fieldnames:
        warnings.append("CSV 缺少 id 列：将自动生成主键")

    inserted = updated = skipped = 0
    errors = []
    row_number = 1
    try:
        for raw_row in reader:
            row_number += 1
            if raw_row is None:
                continue
            if not any((value or "").strip() for value in raw_row.values() if isinstance(value, str)):
                continue
            payload = {}
            for key, value in raw_row.items():
                if key in known and key not in ("created_at", "updated_at"):
                    payload[key] = value.strip() if isinstance(value, str) else value
                    if payload[key] == "":
                        payload[key] = None
            hits = _sensitive_hits(payload)
            if hits:
                warnings.append("第 %d 行疑似包含联系方式（%s），请确认不得进入公开备注"
                                % (row_number, ", ".join(hits)))
            item_id = payload.get("id")
            exists = False
            if item_id:
                try:
                    repo.get_item(conn, entity, item_id)
                    exists = True
                except repo.NotFoundError:
                    exists = False
            try:
                if exists and mode == "insert":
                    skipped += 1
                    continue
                if exists:
                    repo.update_item(conn, entity, item_id, payload, actor=actor,
                                     ip="csv-import", partial=True)
                    updated += 1
                else:
                    repo.create_item(conn, entity, payload, actor=actor, ip="csv-import")
                    inserted += 1
            except repo.ApiError as exc:
                errors.append({"row": row_number, "error": exc.message})
            except Exception as exc:  # noqa: BLE001 - 逐行报告，不中断导入
                errors.append({"row": row_number, "error": "导入失败：%s" % exc})
    except csv.Error as exc:
        raise repo.ValidationError("CSV 解析失败：%s" % exc)

    db.activity(conn, actor=actor, action="IMPORT", entity_type=entity,
                entity_id="", summary="CSV 导入 %s：新增 %d / 更新 %d / 跳过 %d / 失败 %d"
                % (entity, inserted, updated, skipped, len(errors)), detail="")
    conn.commit()
    return {"entity": entity, "mode": mode, "inserted": inserted, "updated": updated,
            "skipped": skipped, "errors": errors, "warnings": warnings}
