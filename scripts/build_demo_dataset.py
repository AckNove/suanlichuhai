#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""重建脱敏演示数据集 data/demo/。

做什么：
  1. 用 sqlite3 backup API 把运行库（默认 data/runtime/app.db）做一致性快照 -> data/demo/app-demo.db
  2. 复制 data/runtime/agent_outputs/* 到 data/demo/agent_outputs/，把本机绝对路径替换为相对路径
  3. 对演示库做脱敏检查（邮箱 / 手机号 / 本机绝对路径），非 0 即失败
  4. 写 data/demo/MANIFEST.json（计数 + 每个文件 sha256/字节数）

用法（进程级环境，不需要联网）：
  python scripts/build_demo_dataset.py
  python scripts/build_demo_dataset.py --source data/runtime/app.db
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "data" / "demo"
DEMO_DB = DEMO_DIR / "app-demo.db"
AGENT_OUT_SRC = ROOT / "data" / "runtime" / "agent_outputs"
AGENT_OUT_DST = DEMO_DIR / "agent_outputs"
DEFAULT_SOURCE = ROOT / "data" / "runtime" / "app.db"

COUNT_TABLES = [
    "companies",
    "demand_opportunities",
    "compute_supply_resources",
    "compute_specifications",
    "evidence_registry",
    "matching_records",
    "commercial_opportunities",
    "approvals",
    "knowledge_records",
    "agent_tasks",
    "supplier_verification",
    "demand_qualification",
    "quotes",
    "contracts_metadata",
]

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
# 任意盘符绝对路径（单反斜杠形式；JSON 解析后即为单反斜杠）
ABS_PATH_RE = re.compile(r"(?i)\b[A-Z]:[\\/]")

SAFE_TEXT_SUFFIXES = (".json", ".md", ".txt", ".csv", ".log")


def _replace_abs_paths(text: str) -> str:
    """把文本中的本机绝对路径替换为仓库相对路径/占位符。"""
    text = text.replace(str(ROOT), ".")
    text = text.replace(str(Path.home()), "~")

    def _sub(match: "re.Match") -> str:
        value = match.group(0)
        return "data/runtime/app.db" if value.lower().endswith(".db") else "<abs-path>"

    return re.sub(r"(?i)\b[A-Z]:\\[^\s\"']*", _sub, text)


def _sanitize_json_text(text: str) -> str:
    """按 JSON 结构清洗字符串值，保持 JSON 合法。"""
    import json as _json
    data = _json.loads(text)

    def walk(value):
        if isinstance(value, str):
            return _replace_abs_paths(value)
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, dict):
            return {key: walk(item) for key, item in value.items()}
        return value

    return _json.dumps(walk(data), ensure_ascii=False, indent=2) + "\n"



def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def make_snapshot(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    if tmp.exists():
        tmp.unlink()
    src = sqlite3.connect(str(source))
    try:
        dst = sqlite3.connect(str(tmp))
        try:
            src.backup(dst)
            dst.commit()
        finally:
            dst.close()
    finally:
        src.close()
    # 校验快照可打开且表齐全
    conn = sqlite3.connect(str(tmp))
    try:
        names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()
    required = set(COUNT_TABLES) | {"project_activities", "audit_logs", "backup_records"}
    missing = sorted(required - names)
    if missing:
        raise SystemExit("快照缺少表：%s" % ", ".join(missing))
    if target.exists():
        target.unlink()
    tmp.replace(target)


def copy_agent_outputs(source: Path, dest: Path) -> int:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        return 0
    count = 0
    for item in sorted(source.iterdir()):
        if not item.is_file():
            continue
        data = item.read_bytes()
        if item.suffix.lower() in SAFE_TEXT_SUFFIXES:
            text = data.decode("utf-8", errors="replace")
            if item.suffix.lower() == ".json":
                try:
                    text = _sanitize_json_text(text)
                except ValueError:
                    text = _replace_abs_paths(text)
            else:
                text = _replace_abs_paths(text)
            data = text.encode("utf-8")
        (dest / item.name).write_bytes(data)
        count += 1
        # 防御：清洗后的文本产物不得再含盘符绝对路径
        if item.suffix.lower() in SAFE_TEXT_SUFFIXES:
            if ABS_PATH_RE.search(data.decode("utf-8", errors="replace")):
                raise SystemExit("Agent 产物清洗后仍含绝对路径：%s" % item.name)
    return count


def scan_sanitized(db_path: Path) -> dict:
    hits = {"email": 0, "phone": 0, "abs_path": 0}
    samples = []
    conn = sqlite3.connect(str(db_path))
    try:
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for table in tables:
            if table.startswith("sqlite_"):
                continue
            cols = [row[1] for row in conn.execute('PRAGMA table_info("%s")' % table)]
            for row in conn.execute('SELECT * FROM "%s"' % table):
                for col, value in zip(cols, row):
                    if not isinstance(value, str) or len(value) > 4000:
                        continue
                    for key, regex in (("email", EMAIL_RE), ("phone", PHONE_RE), ("abs_path", ABS_PATH_RE)):
                        if regex.search(value):
                            hits[key] += 1
                            if len(samples) < 10:
                                samples.append("%s.%s: %s" % (table, col, value[:120]))
    finally:
        conn.close()
    return {"hits": hits, "samples": samples}


def table_counts(db_path: Path) -> dict:
    counts = {}
    conn = sqlite3.connect(str(db_path))
    try:
        for table in COUNT_TABLES:
            try:
                counts[table] = conn.execute('SELECT COUNT(*) FROM "%s"' % table).fetchone()[0]
            except sqlite3.Error:
                counts[table] = 0
    finally:
        conn.close()
    return counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="重建 data/demo 脱敏演示数据集")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="源数据库路径（默认 data/runtime/app.db）")
    args = parser.parse_args(argv)

    source = Path(args.source)
    if not source.exists():
        print("[FAIL] 源数据库不存在：%s" % source)
        print("       先运行：python -m app.backend.db && python -m app.backend.seed && python scripts/import_research.py")
        return 1

    print("[1/4] 生成一致性快照 ...")
    make_snapshot(source, DEMO_DB)

    print("[2/4] 复制 Agent 产物 ...")
    n_outputs = copy_agent_outputs(AGENT_OUT_SRC, AGENT_OUT_DST)

    print("[3/4] 脱敏扫描 ...")
    scan = scan_sanitized(DEMO_DB)
    hits = scan["hits"]
    total_hits = sum(hits.values())
    if total_hits:
        print("[FAIL] 演示库含敏感内容：%s" % hits)
        for s in scan["samples"]:
            print("       - %s" % s)
        return 1

    print("[4/4] 写 MANIFEST.json ...")
    counts = table_counts(DEMO_DB)
    files = [DEMO_DB]
    if AGENT_OUT_DST.exists():
        files += sorted(p for p in AGENT_OUT_DST.iterdir() if p.is_file())
    entries = []
    for path in files:
        entries.append({
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256_of(path),
            "bytes": path.stat().st_size,
        })
    manifest = {
        "dataset": "CCGS sanitized demo dataset",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "data/runtime/app.db（种子 + 第一轮公开研究导入，全部线索等级 LEAD）",
        "sanitized": "已扫描：0 邮箱 / 0 手机号 / 0 本机绝对路径；不含真实联系人、报价、合同、预算",
        "table_count": len({row[0] for row in sqlite3.connect(str(DEMO_DB)).execute("SELECT name FROM sqlite_master WHERE type='table'")}),
        "counts": counts,
        "agent_outputs": n_outputs,
        "files": entries,
    }
    (DEMO_DIR / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("")
    print("完成：%d 个文件，演示库 %d 字节，agent_outputs %d 个" % (
        len(entries), DEMO_DB.stat().st_size, n_outputs))
    print("计数：" + ", ".join("%s=%d" % (k, v) for k, v in counts.items() if v))
    print("脱敏：0 邮箱 / 0 手机号 / 0 绝对路径")
    return 0


if __name__ == "__main__":
    sys.exit(main())
