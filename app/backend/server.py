# -*- coding: utf-8 -*-
"""CCGS 后端开发服务器入口。

启动：
    python -m app.backend.server
    powershell -File scripts/run_server.ps1

环境变量：
    CCGS_PORT      监听端口（默认 8770）
    CCGS_HOST      监听地址（默认 127.0.0.1，仅本机）
    CCGS_DB_PATH   数据库路径（默认 data/runtime/app.db）
    CCGS_SEED      设为 0 时启动不导入种子数据
"""
from __future__ import annotations

import json
import os

from flask import Flask, Response, send_from_directory

from . import api, db, seed

ROOT = db.ROOT
WEB_DIR = ROOT / "app" / "web"
INDEX_FILE = WEB_DIR / "index.html"

FALLBACK_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>CCGS 内部经营工作台</title>
<style>
 body{font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;background:#0f1419;color:#e6e6e6;
      max-width:820px;margin:8vh auto;padding:0 24px;line-height:1.7}
 h1{font-size:22px;color:#7cc4ff} code{background:#1c2530;padding:2px 6px;border-radius:4px;color:#ffd479}
 li{margin:6px 0} .note{color:#9aa7b3;font-size:13px;margin-top:24px}
</style></head><body>
<h1>CCGS 内部经营工作台 · 后端已启动</h1>
<p>前端静态目录 <code>app/web/</code> 尚不存在或缺少 <code>index.html</code>，因此这里显示后端说明页。</p>
<p>后端 API 可用（同源 <code>/api/*</code>）：</p>
<ul>
 <li><code>GET /api/health</code> 健康检查</li>
 <li><code>GET /api/dashboard</code> 经营总览</li>
 <li><code>GET /api/demands</code> / <code>/api/supplies</code> / <code>/api/evidence</code> 等资源列表</li>
 <li><code>POST /api/match/run</code> 确定性匹配</li>
</ul>
<p class="note">本工作台仅绑定 127.0.0.1，本地单用户使用；不发送邮件/私信，不生成正式报价或合同。</p>
</body></html>"""


def create_app(seed_data=None, db_path=None) -> Flask:
    """创建 Flask 应用：建表 + 幂等种子（CCGS_SEED=0 可关闭）+ API + 静态前端。"""
    if db_path is not None:
        os.environ["CCGS_DB_PATH"] = str(db_path)
    static_folder = str(WEB_DIR) if WEB_DIR.exists() else None
    app = Flask(__name__, static_folder=static_folder, static_url_path="")
    try:
        app.json.ensure_ascii = False
    except AttributeError:  # pragma: no cover - Flask 2.x 兼容
        app.config["JSON_AS_ASCII"] = False

    conn = db.ensure_schema()
    try:
        if seed_data is None:
            seed_data = os.environ.get("CCGS_SEED", "1").strip() != "0"
        stats = seed.seed_all(conn) if seed_data else None
    finally:
        conn.close()
    app.config["CCGS_SEED_STATS"] = stats
    app.config["CCGS_SEED_ENABLED"] = bool(seed_data)

    app.register_blueprint(api.bp)
    api.register_error_handlers(app)

    @app.route("/")
    def index():
        if INDEX_FILE.exists():
            return Response(INDEX_FILE.read_bytes(),
                            content_type="text/html; charset=utf-8")
        return Response(FALLBACK_HTML, content_type="text/html; charset=utf-8")

    @app.route("/favicon.ico")
    def favicon():
        for name in ("favicon.ico", "favicon.svg", "logo.svg"):
            candidate = WEB_DIR / name
            if candidate.exists():
                return send_from_directory(str(WEB_DIR), name)
        return Response(status=204)

    return app


def _startup_banner(app: Flask, host: str, port: int) -> str:
    conn = db.connect()
    try:
        tables = db.list_tables(conn)
        counts = {
            "companies": db.safe_count(conn, "companies"),
            "supplies": db.safe_count(conn, "compute_supply_resources"),
            "demands": db.safe_count(conn, "demand_opportunities"),
            "evidence": db.safe_count(conn, "evidence_registry"),
            "matches": db.safe_count(conn, "matching_records"),
            "agent_tasks": db.safe_count(conn, "agent_tasks"),
            "approvals": db.safe_count(conn, "approvals"),
        }
    finally:
        conn.close()
    stats = app.config.get("CCGS_SEED_STATS")
    lines = [
        "=" * 64,
        "CCGS 内部经营工作台 · 后端",
        "  地址:   http://%s:%d" % (host, port),
        "  数据库: %s（WAL）" % db.rel_to_root(db.db_path()),
        "  前端:   %s" % ("app/web/ 已加载" if INDEX_FILE.exists() else "app/web/ 缺失，/ 显示说明页"),
        "  表数量: %d" % len(tables),
        "  数据量: %s" % json.dumps(counts, ensure_ascii=False),
        "  种子:   %s" % ("已启用（幂等）" if app.config.get("CCGS_SEED_ENABLED")
                          else "已关闭（CCGS_SEED=0）"),
    ]
    if stats:
        lines.append("  本次新增: %s" % json.dumps(stats.get("inserted", {}), ensure_ascii=False))
    lines.append("  关闭种子: 设置环境变量 CCGS_SEED=0")
    lines.append("=" * 64)
    return "\n".join(lines)


def main() -> None:
    host = os.environ.get("CCGS_HOST", "127.0.0.1").strip() or "127.0.0.1"
    try:
        port = int(os.environ.get("CCGS_PORT", "8770"))
    except ValueError:
        port = 8770
    app = create_app()
    print(_startup_banner(app, host, port))
    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()
