# CCGS · 中国算力国际化项目（AI 原生经营工作台）

**English name:** China Compute Globalization Services (CCGS)
**项目代号：** suanlichuhai
**版本：** v1.0.0（内部 MVP）
**筹建主体：** 未设立（主体设立中，待 CEO 决策）
**状态：** 内部工作台 · 本地单用户 · 不对外发送邮件/私信 · 不生成正式报价

> **一句话：** 连接中国可商业化的智算资源与全球 AI 计算需求的专业算力采购与市场拓展服务商。
> 我们卖的不是 GPU，而是需求分析、规格定义、资源寻源、供应商核验、方案比较、风险识别、商务协调与持续采购管理。

---

## 1. 诚实声明（必读）

本项目处于 **零成交、零协议、零回款** 的筹建阶段。仓库内任何公司名称、线索、匹配结果均为**公开信息研究线索**，不代表：

- 已与任何供应商达成合作或代理授权；
- 任何客户存在采购意向、预算或决策；
- 已完成供应商合格核验或需求方资格核验；
- 已产生真实订单、收入或交付。

所有线索分级严格区分：`公开线索 → 推断需求 → 潜在机会 → 已核实需求 → 已合格商机`。系统**不允许**自动把公开线索升级为合格客户或合格供应商；`VERIFIED` / `QUALIFIED` / `WON` 等状态必须有人工核验记录与 CEO 审批。

对外材料（话术、介绍、One Pager）均为 **DRAFT 草案**，未经 CEO Arthur 书面批准不得外发。

---

## 2. 仓库结构

```
suanlichuhai/
├── README.md                    本文件
├── .gitignore                   敏感数据与运行时产物忽略规则
├── docs/
│   ├── 00_project_audit/        项目审计、环境审计、GitHub 审计、执行基线
│   ├── 01_strategy/             公司定位、商业模式、产品服务、价值主张、竞争、目标客户
│   ├── 02_commercial/           供应商开发手册、客户开发手册、合作模式、收费框架
│   ├── 03_sales/                中英双语销售工具包（10 组）
│   ├── 04_contracts/            商务条款设计（非律师合同）
│   ├── 05_research/             第一轮真实公开信息研究（需求/供给/匹配/证据）
│   ├── 06_operations/           经营手册、商机漏斗、审批矩阵、风险登记、跨境流程
│   ├── 07_ai_system/            数据库/API 契约、架构、工具清单、Agent-Skill 规范
│   ├── 08_final/                验收报告、交接说明、CEO 下一步
│   └── handover-20261113/       2026-11-13 历史交接快照（75 份资料，只读）
├── app/
│   ├── backend/                 Flask + SQLite 后端（REST API）
│   ├── web/                     原生 JS 前端工作台（18 模块，无构建、无 CDN）
│   └── data/                    schema.sql、种子数据（脱敏/公开来源）
├── .dsh/skills/                 10 个项目专属 Skills
├── agents/                      11 个 Agent 注册表 + 确定性任务运行器
├── data/
│   ├── research/                研究阶段 CSV（脱敏）
│   └── runtime/                 运行时数据库/备份/Agent 产物（gitignore，不提交）
├── scripts/                     环境、启停、测试、安检、备份脚本
└── tests/                       unittest 测试
```

---

## 3. 快速开始（Windows / D 盘优先）

```powershell
# 0) 进入项目
cd D:\ChinaCompute\suanlichuhai

# 1) 初始化开发环境（仅当前进程生效，缓存/临时文件全部指向 D 盘）
. .\scripts\setup_dev_env.ps1

# 2) 初始化数据库 + 历史种子数据（幂等）
powershell -ExecutionPolicy Bypass -File scripts\init_db.ps1       # 等价于 python -m app.backend.db 再 python -m app.backend.seed

# 3)（可选）导入第一轮研究线索/证据（幂等，全部 LEAD 级，不自动升级）
python scripts\import_research.py    # 读 data\research\*.csv；重复运行自动 SKIP

# 4) 启动后端 + 前端工作台（同源）
python -m app.backend.server
# 浏览器打开 http://127.0.0.1:8770

# 5) 运行测试
python -m unittest discover -s tests -v
```

详细说明见 [docs/07_ai_system/RUNBOOK.md](docs/07_ai_system/RUNBOOK.md)。

---

## 4. 能力清单（真实可用性）

| 能力 | 状态 | 说明 |
|---|---|---|
| Web 搜索 | ✅ 可用 | Harness 内置 web_search |
| 网页读取 | ✅ 可用 | web_fetch，HTML → 文本 |
| 浏览器自动化 | 🟡 部分可用 | 本机 Chrome + CDP 可做本地页面自测/截图；未装 Playwright，不做自动登录/发帖/外联 |
| PDF 解析 | 🟡 部分可用 | PyMuPDF 可提取文本；无 OCR，扫描件不可读 |
| Python / SQLite / CSV | ✅ 可用 | 后端与数据分析主力 |
| Git / GitHub 推送 | ✅ 可用 | 凭据有效；仅 Lead 执行 |
| MCP 连接器 | ❌ 0 个 | 未连接任何 MCP Server |
| 发邮件 / 发私信 / 拨号 | ❌ 不提供 | 外联权归 CEO，系统不实现 |
| 自动报价 / 自动签约 | ❌ 不提供 | 需 CEO 审批，系统只生成草稿 |

完整清单与验证方法见 [docs/07_ai_system/TOOLING_INVENTORY.md](docs/07_ai_system/TOOLING_INVENTORY.md)。

---

## 5. 安全与数据分级

- **GitHub 仓库当前为 Public**：只推送代码、脱敏文档与技术结构。
- **绝不入库**：真实联系人/私人联系方式、真实供应商报价、合同、密钥、真实业务数据库、客户隐私数据、未授权商业资料。
- 运行时真实数据只存本地 `data/runtime/`（已 gitignore）。
- 敏感商务资料放 `private/` 或 `**/99-敏感商务_仅本项目/`（已 gitignore）。
- 提交前运行：`powershell -ExecutionPolicy Bypass -File scripts\sensitive_scan.ps1`。
- 建议 CEO 将仓库改为 Private（**需 CEO 授权，项目未自行修改**）。

---

## 6. 业务文档索引

| 主题 | 文档 |
|---|---|
| 公司定位 | [COMPANY_POSITIONING.md](docs/01_strategy/COMPANY_POSITIONING.md) |
| 商业模式 | [BUSINESS_MODEL.md](docs/01_strategy/BUSINESS_MODEL.md) |
| 产品服务目录 | [PRODUCT_SERVICE_CATALOG.md](docs/01_strategy/PRODUCT_SERVICE_CATALOG.md) |
| 价值主张 | [VALUE_PROPOSITION.md](docs/01_strategy/VALUE_PROPOSITION.md) |
| 竞争定位 | [COMPETITIVE_POSITIONING.md](docs/01_strategy/COMPETITIVE_POSITIONING.md) |
| 目标客户 | [TARGET_CUSTOMERS.md](docs/01_strategy/TARGET_CUSTOMERS.md) |
| 供应商开发 | [SUPPLIER_ACQUISITION_PLAYBOOK.md](docs/02_commercial/SUPPLIER_ACQUISITION_PLAYBOOK.md) |
| 客户开发 | [CUSTOMER_ACQUISITION_PLAYBOOK.md](docs/02_commercial/CUSTOMER_ACQUISITION_PLAYBOOK.md) |
| 合作模式 | [COOPERATION_MODELS.md](docs/02_commercial/COOPERATION_MODELS.md) |
| 收费框架 | [PRICING_AND_FEE_FRAMEWORK.md](docs/02_commercial/PRICING_AND_FEE_FRAMEWORK.md) |
| 销售工具包 | [docs/03_sales/](docs/03_sales/README.md) |
| 商务条款 | [docs/04_contracts/](docs/04_contracts/) |
| 第一轮研究 | [docs/05_research/](docs/05_research/MARKET_RESEARCH_ROUND1.md) |
| 经营流程 | [BUSINESS_OPERATING_MANUAL.md](docs/06_operations/BUSINESS_OPERATING_MANUAL.md) |
| CEO 审批 | [CEO_APPROVAL_MATRIX.md](docs/06_operations/CEO_APPROVAL_MATRIX.md) |
| 风险登记 | [COMMERCIAL_RISK_REGISTER.md](docs/06_operations/COMMERCIAL_RISK_REGISTER.md) |
| AI 系统 | [SYSTEM_ARCHITECTURE.md](docs/07_ai_system/SYSTEM_ARCHITECTURE.md) |
| 验收报告 | [MVP_ACCEPTANCE_REPORT.md](docs/08_acceptance/MVP_ACCEPTANCE_REPORT.md) |
| 交接总览 | [FINAL_HANDOVER.md](FINAL_HANDOVER.md) |
| CEO 下一步 | [CEO_NEXT_ACTIONS.md](CEO_NEXT_ACTIONS.md) |

---

## 7. 历史资料

2026-11-13 交接快照保留在 [docs/handover-20261113/](docs/handover-20261113/)，含 75 份资料、18 条供应侧公开线索、9 条需求侧公开线索、3 组内部模拟匹配样例。该快照是**历史存档，只读**，其中内容不得直接当作当前事实；当前事实以本仓库 `docs/00_project_audit/PROJECT_BRIEF.md` 与数据库状态为准。

历史分支：`cursor/handover-20261113-5b36`（未删除、未合并）。
当前开发分支：`ai-build-20261116`。
`main` 分支未被覆盖。

---

## 8. 许可与使用

内部项目，未开源授权。未经 CEO Arthur 书面批准，不得复制、外发、对外引用本仓库任何商业内容。
