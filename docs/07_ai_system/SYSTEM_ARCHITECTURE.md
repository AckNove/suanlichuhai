# CCGS AI 经营工作台 — 系统架构（SYSTEM ARCHITECTURE）

**版本：** v1.0（2026-11-16）
**状态：** 架构与契约 DONE；实现进度见 `MVP_ACCEPTANCE_REPORT.md`。

---

## 1. 系统目标

把「中国算力供给 → 海外/跨境需求」的介绍对接业务，做成一个**可运行、可审计、可交接**的本地经营工作台：

1. 线索与证据分离：公开线索不得自动变成合格客户/供应商；
2. 每一步升级都有记录（核验、资格、审批、匹配、商机）；
3. AI 只做研究、整理、分析、生成候选；关系、谈判、报价、签约、收款永远由 CEO 人工完成；
4. 系统不外联、不报价、不签约、不收款。

---

## 2. 总体架构

```
┌─────────────────────────────────────────────────────────────┐
│ 浏览器（本机）                                                │
│  app/web：原生 HTML+CSS+JS，零构建、零 CDN、hash 路由        │
└───────────────┬─────────────────────────────────────────────┘
                │ HTTP /api/*（同源，Flask 直接托管静态文件）
┌───────────────▼─────────────────────────────────────────────┐
│ Flask 后端  app/backend/server.py（127.0.0.1:8770）          │
│  ├─ api.py       资源 CRUD + 专用端点 + 参数校验              │
│  ├─ repo.py      数据访问（sqlite3，参数化 SQL）              │
│  ├─ matching.py  确定性 8 维评分匹配引擎（可解释）            │
│  ├─ csv_io.py    CSV 导入/导出（含模板）                      │
│  ├─ backup.py    sqlite3 backup API + sha256 + 保留策略      │
│  ├─ seed.py      历史线索导入 + 演示数据（标注 seed:）        │
│  └─ audit.py     写操作审计（audit_logs + project_activities）│
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│ SQLite  data/runtime/app.db（运行时生成，.gitignore 排除）   │
│  18 张表：公司/需求/供给/规格/证据/核验/资格/匹配/分析/       │
│  商机/报价/合同元数据/Agent任务/项目活动/知识/审计/审批/备份   │
└─────────────────────────────────────────────────────────────┘
                │
┌───────────────┴─────────────────────────────────────────────┐
│ 旁路组件（非 Web 进程）                                       │
│  ├─ agents/runner.py    11 个 Agent 的确定性任务执行器        │
│  ├─ .dsh/skills/        10 个项目 Skill（研究/核验/匹配规范）  │
│  ├─ data/research/      第一轮研究 CSV（可导入）               │
│  └─ backups/            备份文件（不入 Git）                  │
└─────────────────────────────────────────────────────────────┘
```

**设计取舍：**

- 单进程 Flask + SQLite：零运维、零费用、CEO 本机即可运行；不做多用户并发设计。
- 先契约后实现：`SPEC_DATABASE.md` / `SPEC_API.md` 是唯一权威，前后端按契约对齐。
- 前后端同源：Flask 托管 `app/web` 静态文件，避免 CORS 与第二个端口。
- Agent 不走 LLM 自动调用链：`runner.py` 执行确定性任务（数据审计、证据检查、CSV 导入、匹配、报告渲染、Schema 校验），工具与数据输入输出显式登记；LLM 作为「操作者」通过 Skill 使用这些工具，而不是系统内隐式自主循环。

---

## 3. 目录结构与职责

| 路径 | 职责 | 是否入库 |
|---|---|---|
| `app/backend/**` | Flask 后端、数据访问、匹配引擎、CSV、备份、种子、审计 | ✅ |
| `app/data/schema.sql` | 权威 DDL（18 表 + 索引） | ✅ |
| `app/data/seed/**` | 种子 CSV（历史线索、GPU 规格、证据） | ✅（已脱敏） |
| `app/web/**` | 前端工作台（index.html / styles.css / js/*） | ✅ |
| `.dsh/skills/**` | 10 个项目 Skill | ✅ |
| `agents/**` | 11 个 Agent 注册表 + 运行器 + 说明 | ✅ |
| `data/research/**` | 第一轮真实公开研究 CSV | ✅（仅公开信息） |
| `data/runtime/**` | 运行时 DB、备份、Agent 产物 | ❌ .gitignore |
| `data/private/**`、`private/**` | 真实商务敏感数据（报价/合同/联系人） | ❌ 永不入库 |
| `docs/**` | 商业文档、研究、合同条款设计、验收 | ✅（脱敏） |
| `tests/**` | unittest 测试 | ✅ |
| `scripts/**` | 环境/测试/冒烟/敏感扫描/备份脚本 | ✅ |

---

## 4. 18 个功能模块 → 实现映射

| # | 模块 | 前端路由 | 后端 | 数据表 |
|---|---|---|---|---|
| 1 | 经营总览 | `#/dashboard` | `GET /api/dashboard` | 聚合查询 |
| 2 | 需求管理 | `#/demands` | `/api/demands` | demand_opportunities |
| 3 | 供应商管理 | `#/suppliers` | `/api/suppliers` | companies(SUPPLIER) + compute_supply_resources |
| 4 | GPU 资源管理 | `#/supplies` | `/api/supplies` | compute_supply_resources |
| 5 | 证据来源管理 | `#/evidence` | `/api/evidence` | evidence_registry |
| 6 | 供应商核验 | `#/verify-supplier` | `/api/supplier-verifications` + `state/transitions` | supplier_verification |
| 7 | 需求资格核验 | `#/qualify-demand` | `/api/demand-qualifications` + `state/transitions` | demand_qualification |
| 8 | 算力规格标准化 | `#/specs` | `/api/specs` | compute_specifications |
| 9 | 供需智能匹配 | `#/matching` | `POST /api/match/run`、`/api/match/score` | matching_records |
| 10 | 采购分析报告 | `#/analyses` | `/api/procurement-analyses`、`reports/fee-scenarios` | procurement_analyses |
| 11 | 商机管理 | `#/opportunities` | `/api/opportunities` | commercial_opportunities |
| 12 | 项目进度 | `#/activities` | `/api/activities` | project_activities |
| 13 | Agent 任务 | `#/agents`、`#/tasks` | `/api/agents`、`/api/agent-tasks`、`agent-tasks/run` | agent_tasks |
| 14 | CEO 审批中心 | `#/approvals` | `/api/approvals/pending`、`/api/approvals/:id/decide` | approvals |
| 15 | 知识库 | `#/knowledge` | `/api/knowledge`、`search` | knowledge_records |
| 16 | CSV 导入导出 | 各页面按钮 | `/api/export/:table`、`/api/import/:table` | 全表 |
| 17 | 数据备份 | `#/settings` | `/api/backup`、`/api/backup/restore` | backup_records |
| 18 | 审计日志 | `#/audit` | `/api/audit-logs`（只读） | audit_logs |

---

## 5. 关键业务规则（服务端强制）

1. **线索不自动升级**：导入即 `LEAD` + `PUBLIC_LEAD` + `verified=0`；升级必须有人工核验/资格记录。
2. **核验门槛**：`VERIFIED` 需至少 1 条有效 `supplier_verification`；`QUALIFIED` 需核验分 ≥70 且 CEO 审批通过。
3. **匹配门槛**：`MATCHED` 需匹配结论为 `ADVANCE` 且分析经 `REVIEWED`；`WON/LOST` 仅 CEO 可设置。
4. **红线封顶**：命中「无合法转售权 / 跨境合规未筛查 / 数据驻留冲突」→ 总分封顶 39，禁止 ADVANCE。
5. **双方向收费必须披露**：商机记录须含 `double_sided_disclosure` 字段才能进入 COMMERCIAL。
6. **不托管资金**：系统无收款/付款/资金池字段与接口。
7. **审计不可删**：`audit_logs` 只允许 INSERT/SELECT。
8. **未知即未知**：缺失字段写 `unknown`/`待确认`，不得用推测值填充（尤其容量、价格、联系人、预算）。

---

## 6. 数据流（一条线索的完整生命周期）

```
网页/公开报道（web_search + web_fetch）
   ↓ 人工记录来源（URL/标题/发布者/发布时间/获取时间/信任度）
evidence_registry
   ↓ 关联
companies + demand_opportunities / compute_supply_resources（均为 LEAD）
   ↓ 公开信息研究（Skill: global-demand-research / china-compute-supply-research）
RESEARCHED（仍非合格）
   ↓ 有人工访谈或官方文件（Skill: supplier-verification / demand-qualification）
NEEDS_VERIFICATION → VERIFIED → QUALIFIED（CEO 审批）
   ↓ 规格标准化（Skill: gpu-spec-normalization）
compute_specifications
   ↓ 确定性匹配（Skill: compute-matching，8 维 100 分）
matching_records（ADVANCE / NEED_MORE_INFO / REJECT + 逐维解释）
   ↓ 采购分析（Skill: procurement-analysis）
procurement_analyses → commercial_opportunities（DRAFT → CEO 审批 → COMMERCIAL）
   ↓ 报价/合同（仅 CEO；系统只存元数据与审批状态）
quotes / contracts_metadata → WON / LOST
```

---

## 7. 运行形态

| 形态 | 命令 | 端口 | 用途 |
|---|---|---|---|
| 完整工作台 | `python -m app.backend.server` | 8770 | 前端 + API + 静态托管 |
| 测试 | `python -m unittest discover -s tests -v` | — | 单元/集成测试 |
| 冒烟 | `pwsh -File scripts/smoke_test.ps1` | 8770 | 起服务→打 11 个端点→关服务 |
| Agent 任务 | `python agents/runner.py run-all` | — | 确定性批处理，产物落 `data/runtime/agent_outputs/` |
| 备份 | `POST /api/backup`（或 `backup.create_backup()`） | — | `backups/app-YYYYMMDD-HHMMSS.db`（sha256 存 `backup_records`） |

---

## 8. 安全与隐私分层

| 层级 | 内容 | 存放 | 入库 |
|---|---|---|---|
| L1 公开 | 公开研究、公司官网信息、公开信号 | `data/research/`、`evidence_registry` | ✅ |
| L2 内部 | 内部判断、评分、分析草案 | 运行时 DB + `data/runtime/` | DB 不入库 |
| L3 敏感 | 真实联系人、报价、合同、付款信息 | `data/private/`、`private/` | ❌ 永不 |
| L4 凭据 | Token、PAT、密钥 | 本机凭据管理器/环境变量 | ❌ 永不 |

规则：仓库当前为 **Public**，只允许 L1 入库；`sensitive_scan.ps1` 在每次提交前扫描。

---

## 9. 已知限制（如实声明）

1. 单机单用户；无登录鉴权（仅绑定 127.0.0.1；如需多用户须先加认证）。
2. SQLite 非生产级高并发；数据量超过数十万行需迁移 PostgreSQL。
3. 匹配引擎为规则评分，不是市场定价；分数不代表报价或成交概率。
4. 浏览器自动化仅限本机 Chrome + CDP 的本地自测/截图（本轮前端 18 路由自测已用）；无邮件/私信/拨号发送能力；无 MCP 数据源；研究以公开网页文本为主。
5. 前端无构建链；代码量增长后建议引入打包（当前刻意保持零依赖）。
6. Agent 为「可审计的确定性任务执行器」，不是自主 LLM 循环；LLM 决策痕迹记录在任务记录中。
