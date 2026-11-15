# CCGS 工具与能力清单（TOOLING INVENTORY）

**核验时间：** 2026-11-16（Asia/Shanghai，第 1 轮）
**核验方法：** 逐项实际调用或检查版本/路径，不以「文档声称」为准。
**结论摘要：** 可完成「公开信息研究 + 本地系统开发 + 文档生产 + 本地浏览器自测」；**不具备**外联发送、自动报价、MCP 集成能力；浏览器自动化仅限本机 Chrome 自测（非生产外联）。

---

## 1. 能力矩阵

| # | 能力 | 状态 | 真实证据 | 限制 / 边界 |
|---|---|---|---|---|
| 1 | Web 搜索 | ✅ 可用 | Harness `web_search` 实际返回结果 | 结果可能滞后/被 SEO 污染，必须记录来源与获取时间 |
| 2 | 网页读取 | ✅ 可用 | `web_fetch` 返回解码文本 | 动态渲染页面、登录墙、反爬页面读不到；读不到须标注「未获取」 |
| 3 | 浏览器自动化 | 🟡 部分可用 | 本机 Chrome + CDP 8888/9222 可无头自测与截图（本轮前端 18 路由自测已验证）；无 Playwright | 不做自动登录、发帖、表单提交、外联 |
| 4 | PDF 文本解析 | 🟡 部分可用 | PyMuPDF(fitz) 1.x、PyPDF2 已安装 | 无 OCR；扫描件、图片型 PDF 不可读 |
| 5 | Python 运行时 | ✅ 可用 | Python 3.9.1（D:\DeliveryOptimization\miniconda） | 3.9 语法限制：无 match、无运行时 `X \| Y` 注解 |
| 6 | 数据库 | ✅ 可用 | SQLite3（标准库） | 单机单文件；并发写入受限；非生产级 |
| 7 | 文件读写 | ✅ 可用 | read/write/edit/glob/grep | — |
| 8 | Git | ✅ 可用 | git 2.53.0；push --dry-run 成功 | 仅 Lead 执行；禁止 force push |
| 9 | GitHub 访问 | ✅ 可用 | 匿名 ls-remote 成功（仓库 Public）+ Windows 凭据管理器已有 PAT | 不修改仓库可见性（需 CEO 授权） |
| 10 | Node.js | ✅ 可用 | v24.14.0（用于前端语法检查） | 前端不依赖 Node 运行 |
| 11 | CSV / Excel | ✅ 可用 | pandas 1.5.3、openpyxl | 大文件需分块 |
| 12 | MCP 连接器 | ❌ 0 个 | `mcp_connector_status` 无连接 | 未接入任何第三方业务数据源 |
| 13 | 邮件发送 | ❌ 不提供 | 无 SMTP 配置、无发送工具 | 外联权归 CEO；系统不含发送功能 |
| 14 | 即时消息 / 私信 | ❌ 不提供 | 无 LinkedIn/WhatsApp/Telegram 集成 | 同上 |
| 15 | 自动拨号 | ❌ 不提供 | 无电话系统集成 | 同上 |
| 16 | 付费数据源 | ❌ 不采购 | 无预算授权 | 只用公开信息 |
| 17 | 定时任务 | ✅ 可用 | Harness `schedule_*` | 仅在 CEO 明确要求时创建 |
| 18 | 团队协作 | ✅ 可用 | Agent Teams（Lead + 7 teammates） | 共享同一文件系统；写作用域须隔离 |

---

## 2. Python 依赖实测

| 依赖 | 状态 | 用途 |
|---|---|---|
| flask 3.1.0 | ✅ | 后端 Web 框架 |
| sqlalchemy 2.0.29 | ✅ | 可选；本项目直接用 sqlite3 更轻 |
| pandas 1.5.3 | ✅ | CSV 处理 |
| openpyxl | ✅ | Excel 导入导出（可选） |
| PyYAML | ✅ | Skill frontmatter 解析 |
| python-docx | ✅ | 文档生成（可选） |
| requests / httpx / bs4 / lxml | ✅ | 研究阶段抓取解析（本轮以 web_fetch 为主） |
| fitz (PyMuPDF) / PyPDF2 | ✅ | PDF 文本提取 |
| fastapi / uvicorn | ❌ | 未安装，不使用 |
| pytest | ❌ | 未安装，使用标准库 unittest |
| playwright / pytesseract | ❌ | 未安装；浏览器自测改用本机 Chrome + CDP；OCR 仍缺失 |
| python-pptx | ❌ | 不生成 PPT |

> 不安装新依赖的理由：CEO 授权「优先使用已有工具和低成本方案」「不盲目安装大量插件」。如后续确需 pytest/OCR，列 CEO 待批。

---

## 3. 工具 × 业务模块映射

| 业务动作 | 使用工具 | 产出落点 |
|---|---|---|
| 海外需求线索发现 | web_search + web_fetch | `evidence_registry`、`demand_opportunities`、`docs/05_research/` |
| 中国供给线索发现 | web_search + web_fetch | `compute_supply_resources`、`docs/05_research/` |
| 供应商核验 | 人工访谈记录 + 文档证据 | `supplier_verification`（**无自动抓取即判定 VERIFIED 的能力**） |
| GPU 规格标准化 | 公开规格 + 内部知识库 | `compute_specifications` |
| 供需匹配 | 本地确定性评分引擎（Python） | `matching_records`（可解释、可复核） |
| 采购分析报告 | Python 汇总 + Markdown 模板 | `procurement_analyses`、`data/runtime/agent_outputs/` |
| 商务材料 | 文档撰写（中英双语） | `docs/03_sales/`（DRAFT，需 CEO 批准） |
| 外联发送 | **无工具** | 由 CEO 人工执行，系统只准备材料 |
| 报价 / 签约 | **无工具** | CEO 保留权限；系统只生成草案与条款设计 |
| 数据备份 | sqlite3 backup API + 脚本 | `data/runtime/backups/`（本地，不入库） |

---

## 4. 环境事实（核验记录）

- 磁盘：D 盘可用约 50.6 GB（项目 + 缓存 + 临时文件全部在 D 盘）；C 盘约 26.8 GB 未使用。
- 项目根：`D:\ChinaCompute\suanlichuhai`（不在 C 盘；C 盘无项目副本）。
- 缓存：`D:\ChinaCompute\cache`（pip/uv/npm）；临时：`D:\ChinaCompute\temp`；均由 `scripts/setup_dev_env.ps1` 进程级设置。
- Harness 本体安装在 `C:\Users\25803\AppData\Local\Programs\DeepSeek Harness`，其自身缓存不可迁移，**如实报告**；项目不向其写入业务数据。
- 浏览器：本机 Chrome + CDP 可做本地自测/截图（无 Playwright）；不做登录墙、验证码与外联操作。
- MCP：0 连接。

---

## 5. 不得宣称的能力（红线）

以下能力**本系统不具备**，任何文档、界面、汇报中不得声称已具备：

1. 自动向客户/供应商发送邮件、私信、消息；
2. 自动拨打电话或语音外呼；
3. 自动生成并对外发出正式报价；
4. 自动签署合同、电子签章；
5. 自动收款、付款、资金托管；
6. 自动判定供应商「已核实/已合格」；
7. 自动判定客户「已核实需求/已合格商机」；
8. 实时抓取 LinkedIn / Sales Navigator / YC / Hugging Face 的结构化数据（仅能读取公开页面文本，且可能被反爬）。
