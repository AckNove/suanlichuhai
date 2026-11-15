# -*- coding: utf-8 -*-
"""SQLite 备份与恢复（sqlite3 backup API；sha256 校验；最多保留 20 份）。"""
from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
from pathlib import Path

from . import db, repo

BACKUP_PREFIX = "app-"
RETENTION = 20


class BackupError(Exception):
    """备份/恢复业务异常。"""


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(str(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_dir() -> Path:
    env = os.environ.get("CCGS_BACKUP_DIR", "").strip()
    path = Path(env) if env else db.BACKUP_DIR
    if not path.is_absolute():
        path = db.ROOT / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _unique_path(directory: Path) -> Path:
    stamp = db.now_iso().replace("-", "").replace(":", "").replace("+08:00", "")
    stamp = stamp.replace("T", "-")[:15]
    base = "%s%s" % (BACKUP_PREFIX, stamp)
    candidate = directory / ("%s.db" % base)
    seq = 1
    while candidate.exists():
        seq += 1
        candidate = directory / ("%s-%02d.db" % (base, seq))
    return candidate


def _records(conn) -> list:
    try:
        rows = conn.execute(
            "SELECT * FROM backup_records ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error:
        return []


def _find_record(conn, ref: str) -> dict:
    try:
        row = conn.execute(
            "SELECT * FROM backup_records WHERE id = ? OR file_path = ? OR file_path LIKE ?",
            (ref, ref, "%/" + ref),
        ).fetchone()
    except sqlite3.Error:
        row = None
    return dict(row) if row is not None else None


def create_backup(conn=None, note: str = "", actor: str = "local") -> dict:
    """创建一致性备份并登记 backup_records；返回登记记录。"""
    own_conn = False
    if conn is None:
        conn = db.ensure_schema()
        own_conn = True
    try:
        directory = backup_dir()
        target = _unique_path(directory)
        dest = sqlite3.connect(str(target))
        try:
            conn.backup(dest)
        finally:
            dest.close()
        size = target.stat().st_size
        digest = sha256_file(target)
        backup_id = repo.generate_id(conn, "backups")
        created = db.now_iso()
        rel_path = db.rel_to_root(target)
        with db.transaction(conn):
            conn.execute(
                "INSERT INTO backup_records (id, created_at, file_path, size_bytes, sha256, note) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (backup_id, created, rel_path, size, digest, note or ""),
            )
            db.record_write(conn, actor=actor, action="BACKUP", entity_type="backups",
                            entity_id=backup_id, after={"id": backup_id, "file_path": rel_path,
                                                        "sha256": digest},
                            summary="创建数据库备份 %s" % backup_id)
        _prune(conn)
        return {"id": backup_id, "created_at": created, "file_path": rel_path,
                "size_bytes": size, "sha256": digest, "note": note or ""}
    finally:
        if own_conn:
            conn.close()


def _prune(conn) -> dict:
    """只保留最近 RETENTION 份；删除文件与登记记录。"""
    records = _records(conn)
    removed = []
    for record in records[RETENTION:]:
        path = record.get("file_path") or ""
        full = db.ROOT / path
        try:
            if full.exists() and full.resolve().parent == backup_dir().resolve():
                full.unlink()
        except OSError:
            pass
        try:
            with db.transaction(conn):
                conn.execute("DELETE FROM backup_records WHERE id = ?", (record["id"],))
        except sqlite3.Error:
            pass
        removed.append(record["id"])
    return {"removed": removed, "kept": min(len(records), RETENTION)}


def list_backups(conn) -> dict:
    records = _records(conn)
    for record in records:
        record["exists"] = (db.ROOT / (record.get("file_path") or "")).exists()
    return {"items": records, "total": len(records), "page": 1, "page_size": len(records)}


def resolve_backup(conn, ref: str) -> tuple:
    """按备份 ID / 文件名解析备份文件，返回 (记录, 绝对路径)。"""
    record = _find_record(conn, ref)
    if record is not None:
        path = db.ROOT / (record.get("file_path") or "")
        if not path.exists():
            raise BackupError("备份记录存在但文件缺失：%s" % record.get("file_path"))
        return record, path
    candidate = Path(ref)
    if not candidate.is_absolute():
        candidate = backup_dir() / ref
    if not candidate.exists():
        raise BackupError("找不到备份：%s" % ref)
    if candidate.resolve().parent != backup_dir().resolve():
        raise BackupError("仅允许恢复备份目录内的文件：%s" % ref)
    return None, candidate


def restore_backup(conn, ref: str, confirm: str = "") -> dict:
    """恢复备份。调用前必须关闭数据库连接（本函数会替换数据库文件）。

    - 校验 confirm == RESTORE
    - 若登记记录含 sha256，则校验文件完整性
    - 恢复前自动创建当前库的安全备份（safety_backup）
    """
    if str(confirm or "").strip().upper() != "RESTORE":
        raise BackupError("恢复操作必须显式确认：confirm=RESTORE")
    record, source = resolve_backup(conn, ref)
    digest = sha256_file(source)
    if record is not None and record.get("sha256") and record["sha256"] != digest:
        raise BackupError("备份文件 sha256 校验失败，拒绝恢复：%s" % record.get("file_path"))

    safety = None
    target = db.db_path()
    if target.exists():
        try:
            safety = create_backup(conn, note="restore 前自动安全备份", actor="system")
        except Exception as exc:  # noqa: BLE001 - 安全备份失败不阻断恢复，但记录原因
            safety = {"id": None, "note": "安全备份失败：%s" % exc}

    # 替换数据库文件前必须关闭调用方连接（WAL 模式下尤其重要）
    try:
        conn.close()
    except sqlite3.Error:
        pass

    for suffix in ("-wal", "-shm"):
        side = Path(str(target) + suffix)
        try:
            if side.exists():
                side.unlink()
        except OSError:
            pass
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(source), str(target))
    return {
        "restored": True,
        "restored_from": db.rel_to_root(source),
        "sha256": digest,
        "backup_id": record.get("id") if record else None,
        "safety_backup": safety,
    }
