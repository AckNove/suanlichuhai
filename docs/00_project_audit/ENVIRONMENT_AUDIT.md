# 环境与工具审计（2026-11-16 00:37–00:45 Asia/Shanghai）

> 执行人：AI 项目总负责人（Lead）。命令均为本机实测，非推断。

## 1. 磁盘

| 盘符 | 已用 | 可用 | 结论 |
|------|------|------|------|
| C: | 173.2 GB | 26.8 GB | 仅系统与程序，项目不落 C |
| D: | 225.1 GB | 50.6 GB | 项目根所在，容量充足 |

- 项目根：`D:\ChinaCompute\suanlichuhai`（已存在，含历史 Git 仓库）
- 缓存：`D:\ChinaCompute\cache`（pip / uv / npm / playwright 子目录已建）
- 临时：`D:\ChinaCompute\temp`
- 已提供 `scripts/setup_dev_env.ps1`：仅在**当前进程**设置 `TEMP/TMP/PIP_CACHE_DIR/UV_CACHE_DIR/npm_config_cache/PLAYWRIGHT_BROWSERS_PATH`，不写系统/用户级环境变量（符合 CEO「不改全局环境」要求）。

## 2. 运行时

| 工具 | 版本/状态 |
|------|-----------|
| Python | 3.9.1（`D:\DeliveryOptimization\miniconda\python.exe`） |
| Node.js | v24.14.0 |
| Git | 2.53.0.windows.2 |
| VS Code | 未在命令行确认（不影响交付；可后补） |
| Harness | DeepSeek Harness，Web GUI http://127.0.0.1:10581 |

## 3. Python 依赖实测

| 可用 | 不可用 |
|------|--------|
| flask 3.1.0, sqlalchemy 2.0.29, pydantic 2.6.4, jinja2 3.1.2, pandas 1.5.3, openpyxl 3.1.2, requests 2.31.0, httpx 0.28.1, bs4 4.12.3, lxml 5.1.0, PyYAML 6.0, python-docx 0.8.11, fitz(PyMuPDF), PyPDF2, sqlite3, zoneinfo | fastapi, uvicorn, pytest, python-pptx, playwright, pytesseract |

结论：技术栈定为 **Flask + SQLite + 原生前端 + unittest**，不引入需要联网安装的依赖。

## 4. Harness 能力清单（实测）

| 能力 | 状态 | 说明 |
|------|------|------|
| Web Search | 可用 | `web_search` 工具 |
| 网页读取 | 可用 | `web_fetch`（HTTP 抓取，非浏览器渲染） |
| 浏览器自动化 | **不可用** | 无 Playwright/Chrome 控制工具；不得宣称具备 |
| PDF 解析 | 部分可用 | PyMuPDF / PyPDF2 可本地解析，无 OCR |
| Python 执行 | 可用 | 3.9.1 |
| Git | 可用 | push 凭据已存在（Windows Credential Manager，username=AckNove） |
| MCP 连接 | 0 个 | `mcp_connector_status` 返回 0 条连接 |
| 数据库 | 可用 | SQLite（stdlib），无外部 DB 服务 |
| 文件工具 | 可用 | read/write/edit/glob/grep |
| 子 Agent / Team | 可用 | Agent Teams 已启用 |
| 定时任务 | 可用 | schedule_* 工具（本项目未使用） |

## 5. GitHub 访问

- `git ls-remote` 与 `git push --dry-run` 均成功（exit 0），推送凭据有效。
- 仓库 **Public**（匿名 `git -c credential.helper= ls-remote` 可直接读到分支）。
- 风险处置：见 `GITHUB_AUDIT.md`；需 CEO 决策是否改 Private，本次不自行改动。

## 6. 缓存与临时文件策略

- 所有 Python/pip/uv/npm 缓存指向 `D:\ChinaCompute\cache`。
- 运行期数据库、导出、备份指向 `D:\ChinaCompute\suanlichuhai\data\runtime`、`data\exports`、`backups`（均 gitignore）。
- Harness 自身安装于 C 盘（`C:\Users\25803\AppData\Local\Programs\DeepSeek Harness`），其内部缓存无法在不改系统配置前提下迁移；如实报告。

## 7. 未决/需 CEO 确认

1. 是否将 GitHub 仓库改为 Private（建议改，但需 CEO 授权）。
2. VS Code 是否为指定 IDE（不影响交付）。
3. 是否允许安装 pytest 等开发依赖（当前用 unittest 规避，无需安装）。
