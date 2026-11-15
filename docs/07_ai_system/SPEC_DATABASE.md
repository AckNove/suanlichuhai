# SPEC · 数据库设计（v1.0，权威契约）

> 实现：SQLite（标准库 sqlite3 或 SQLAlchemy），单文件。默认路径 `data/runtime/app.db`（gitignore）。
> 环境变量 `CCGS_DB_PATH` 可覆盖。所有时间字段为 ISO-8601 文本（`YYYY-MM-DDTHH:MM:SS+08:00`）。
> 本文件为 backend 实现的权威 DDL 契约；frontend / agents 均按此字段编程。

## 0. 设计原则

1. 15 类核心实体 + 3 个支撑表（approvals / backup_records / project_activities）。
2. 状态机强约束：**不得自动把公开线索升级为合格客户/供应商**；服务端校验合法状态迁移。
3. 真实数据与公开数据分离：`data/runtime/app.db` 为本地业务库；公开仓库不含真实业务库。
4. 所有写操作写 `audit_logs`（before/after JSON）与 `project_activities`。
5. 证据链：任何企业/资源/需求的关键主张都应可通过 `evidence_registry` 追溯。

## 1. DDL

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- 1) 公司（供给方/需求方/伙伴统一）
CREATE TABLE IF NOT EXISTS companies (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  name_en TEXT,
  company_type TEXT NOT NULL DEFAULT 'SUPPLIER',  -- SUPPLIER/DEMANDER/PARTNER/BOTH
  country TEXT, region TEXT, website TEXT, parent TEXT, listed_code TEXT,
  business_summary TEXT,
  status TEXT NOT NULL DEFAULT 'LEAD',
  trust_level TEXT NOT NULL DEFAULT 'UNVERIFIED',  -- HIGH/MEDIUM/LOW/UNVERIFIED
  owner TEXT, tags TEXT, notes TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

-- 2) 需求机会
CREATE TABLE IF NOT EXISTS demand_opportunities (
  id TEXT PRIMARY KEY,
  company_id TEXT REFERENCES companies(id),
  title TEXT NOT NULL,
  workload_type TEXT,             -- TRAINING/FINETUNE/INFERENCE/RENDERING/SIMULATION/MIXED
  gpu_models TEXT,                -- 逗号分隔，如 "H100,H200"
  min_gpu_count INTEGER, max_gpu_count INTEGER, duration_months INTEGER,
  cluster_requirements TEXT, network_requirements TEXT,
  location_preference TEXT, data_residency TEXT, compliance_notes TEXT,
  timeline TEXT, budget_range TEXT DEFAULT 'UNKNOWN',
  decision_maker TEXT,
  lead_grade TEXT NOT NULL DEFAULT 'PUBLIC_LEAD', -- PUBLIC_LEAD/INFERRED/POTENTIAL/VERIFIED/QUALIFIED
  status TEXT NOT NULL DEFAULT 'LEAD',
  next_action TEXT, evidence_ids TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

-- 3) 算力供给资源
CREATE TABLE IF NOT EXISTS compute_supply_resources (
  id TEXT PRIMARY KEY,
  company_id TEXT REFERENCES companies(id),
  location_country TEXT, location_city TEXT, datacenter TEXT,
  gpu_model TEXT, gpu_count INTEGER, sellable_gpu_count INTEGER, gpu_memory_gb INTEGER,
  interconnect TEXT, cluster_topology TEXT,
  training_capable INTEGER DEFAULT 0, inference_capable INTEGER DEFAULT 0,
  network_bandwidth TEXT, storage TEXT, delivery_lead_time TEXT,
  price_indication TEXT DEFAULT '待确认', pricing_model TEXT,
  overseas_service INTEGER DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'LEAD',
  verified INTEGER NOT NULL DEFAULT 0,
  next_action TEXT, evidence_ids TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

-- 4) 算力规格标准库（供匹配/归一化）
CREATE TABLE IF NOT EXISTS compute_specifications (
  id TEXT PRIMARY KEY,
  gpu_model TEXT NOT NULL, vendor TEXT, form_factor TEXT,
  memory_gb INTEGER, memory_type TEXT, memory_bandwidth_gbps REAL,
  fp16_tflops REAL, tf32_tflops REAL, fp8_tflops REAL,
  interconnect TEXT, typical_cluster TEXT, power_kw_per_node REAL,
  notes TEXT, source TEXT
);

-- 5) 证据登记
CREATE TABLE IF NOT EXISTS evidence_registry (
  id TEXT PRIMARY KEY,
  subject_type TEXT NOT NULL,     -- COMPANY/DEMAND/SUPPLY/MATCH/CLAIM/OTHER
  subject_id TEXT,
  claim TEXT NOT NULL,
  source_title TEXT, url TEXT, publisher TEXT,
  published_at TEXT, retrieved_at TEXT,
  confidence TEXT NOT NULL DEFAULT 'UNVERIFIED',   -- HIGH/MEDIUM/LOW/UNVERIFIED
  cross_verified INTEGER NOT NULL DEFAULT 0,
  notes TEXT, created_at TEXT NOT NULL
);

-- 6) 供应商核验
CREATE TABLE IF NOT EXISTS supplier_verification (
  id TEXT PRIMARY KEY,
  supplier_company_id TEXT REFERENCES companies(id),
  checklist_json TEXT,
  legal_entity_ok INTEGER, resource_ownership_ok INTEGER, resale_right_ok INTEGER,
  capacity_evidence_ok INTEGER, overseas_service_ok INTEGER, export_control_declared INTEGER,
  non_exclusive_ok INTEGER, success_fee_ok INTEGER,
  verified_by TEXT, verified_at TEXT,
  status TEXT NOT NULL DEFAULT 'PENDING',   -- PENDING/IN_REVIEW/VERIFIED/REJECTED
  score INTEGER, gaps TEXT, notes TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

-- 7) 需求资格核验
CREATE TABLE IF NOT EXISTS demand_qualification (
  id TEXT PRIMARY KEY,
  demand_id TEXT REFERENCES demand_opportunities(id),
  decision_maker_confirmed INTEGER, budget_confirmed INTEGER, timeline_confirmed INTEGER,
  compliance_screened INTEGER, contracting_path_confirmed INTEGER, data_residency_ok INTEGER,
  qualified_by TEXT, qualified_at TEXT,
  status TEXT NOT NULL DEFAULT 'PENDING',   -- PENDING/IN_REVIEW/QUALIFIED/REJECTED
  score INTEGER, gaps TEXT, notes TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

-- 8) 匹配记录
CREATE TABLE IF NOT EXISTS matching_records (
  id TEXT PRIMARY KEY,
  demand_id TEXT NOT NULL, supply_id TEXT NOT NULL,
  score REAL, match_dimensions TEXT,       -- JSON: {dim:{score,max,reason}}
  why_match TEXT NOT NULL, why_not_match TEXT NOT NULL,
  risks TEXT, confidence TEXT,             -- LOW/MEDIUM/HIGH
  recommendation TEXT,                     -- ADVANCE/NEED_MORE_INFO/REJECT
  status TEXT NOT NULL DEFAULT 'DRAFT',    -- DRAFT/REVIEWED/CEO_PENDING/APPROVED/REJECTED
  analyst TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

-- 9) 采购分析报告
CREATE TABLE IF NOT EXISTS procurement_analyses (
  id TEXT PRIMARY KEY, demand_id TEXT,
  title TEXT NOT NULL, options_json TEXT, scoring_json TEXT,
  recommendation TEXT, risks TEXT, assumptions TEXT,
  status TEXT NOT NULL DEFAULT 'DRAFT',
  analyst TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

-- 10) 商业机会
CREATE TABLE IF NOT EXISTS commercial_opportunities (
  id TEXT PRIMARY KEY,
  demand_id TEXT, supply_id TEXT, match_id TEXT,
  title TEXT NOT NULL,
  stage TEXT NOT NULL DEFAULT 'OPEN',      -- OPEN/DISCLOSED/INTRODUCED/TERM_SHEET/CA/CLOSED_WON/CLOSED_LOST
  model_type TEXT,                          -- ADVISORY/INTRO/CHANNEL/JOINT/PMC
  fee_payer TEXT, fee_basis TEXT, fee_terms TEXT,   -- 逐案，禁止写死费率
  conflict_disclosed INTEGER NOT NULL DEFAULT 0,
  ceo_approval_status TEXT NOT NULL DEFAULT 'PENDING',
  next_step TEXT, owner TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

-- 11) 报价（真实值只进私有库；公开仓库仅模板/示例）
CREATE TABLE IF NOT EXISTS quotes (
  id TEXT PRIMARY KEY, opportunity_id TEXT,
  quote_type TEXT, currency TEXT, amount REAL, terms TEXT,
  status TEXT NOT NULL DEFAULT 'DRAFT', valid_until TEXT, approved_by TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

-- 12) 合同元数据（不存正文）
CREATE TABLE IF NOT EXISTS contracts_metadata (
  id TEXT PRIMARY KEY, opportunity_id TEXT,
  contract_type TEXT, counterparty_demand TEXT, counterparty_supply TEXT,
  term_sheet_ref TEXT,
  signature_status TEXT NOT NULL DEFAULT 'NOT_STARTED', -- NOT_STARTED/IN_REVIEW/SIGNED/TERMINATED
  effective_date TEXT, notes TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

-- 13) Agent 任务
CREATE TABLE IF NOT EXISTS agent_tasks (
  id TEXT PRIMARY KEY,
  agent_name TEXT NOT NULL, task_type TEXT, title TEXT NOT NULL,
  input_ref TEXT, output_path TEXT,
  priority TEXT NOT NULL DEFAULT 'P2',
  status TEXT NOT NULL DEFAULT 'QUEUED',   -- QUEUED/RUNNING/DONE/BLOCKED/FAILED/CANCELLED
  requires_approval INTEGER NOT NULL DEFAULT 0,
  started_at TEXT, finished_at TEXT, result_summary TEXT, error TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

-- 14) 项目活动（轻量时间线）
CREATE TABLE IF NOT EXISTS project_activities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL, actor TEXT, action TEXT,
  entity_type TEXT, entity_id TEXT, summary TEXT, detail TEXT
);

-- 15) 知识库
CREATE TABLE IF NOT EXISTS knowledge_records (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, category TEXT,
  content_md TEXT, tags TEXT, source TEXT,
  status TEXT NOT NULL DEFAULT 'DRAFT',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

-- 16) 审计日志（append-only）
CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL, actor TEXT, action TEXT, entity TEXT, entity_id TEXT,
  before_json TEXT, after_json TEXT, ip TEXT, note TEXT
);

-- 17) CEO 审批中心
CREATE TABLE IF NOT EXISTS approvals (
  id TEXT PRIMARY KEY, approval_type TEXT NOT NULL, subject TEXT NOT NULL,
  requested_by TEXT, requested_at TEXT, required_role TEXT NOT NULL DEFAULT 'CEO',
  payload_json TEXT,
  status TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING/APPROVED/REJECTED/RETURNED
  decided_by TEXT, decided_at TEXT, decision_note TEXT
);

-- 18) 备份记录
CREATE TABLE IF NOT EXISTS backup_records (
  id TEXT PRIMARY KEY, created_at TEXT NOT NULL, file_path TEXT NOT NULL,
  size_bytes INTEGER, sha256 TEXT, note TEXT
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_companies_type ON companies(company_type, status);
CREATE INDEX IF NOT EXISTS idx_demands_status ON demand_opportunities(status, lead_grade);
CREATE INDEX IF NOT EXISTS idx_supplies_status ON compute_supply_resources(status, verified);
CREATE INDEX IF NOT EXISTS idx_evidence_subject ON evidence_registry(subject_type, subject_id);
CREATE INDEX IF NOT EXISTS idx_match_demand ON matching_records(demand_id);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_logs(ts);
CREATE INDEX IF NOT EXISTS idx_activities_ts ON project_activities(ts);
```

## 2. 状态机（服务端必须校验）

**供应商（companies.status，company_type=SUPPLIER）：**
`LEAD → RESEARCHED → NEEDS_VERIFICATION → VERIFIED → QUALIFIED → ACTIVE`
异常态：`INSUFFICIENT_INFO`、`PAUSED`、`EXPIRED`、`REJECTED`、`CEO_PENDING`。
- `VERIFIED` 仅当存在 `supplier_verification.status=VERIFIED`。
- `QUALIFIED` 仅当 `supplier_verification.score>=70` 且 CEO 审批通过。
- `ACTIVE` 仅当 CEO 审批通过。
- 禁止从 `LEAD/RESEARCHED` 直接跳到 `VERIFIED` 及以后。

**需求（demand_opportunities.status）：**
`LEAD → RESEARCHED → NEEDS_VERIFICATION → VERIFIED → QUALIFIED → MATCHED → COMMERCIAL → WON/LOST`
异常态同上 + `NOT_MATCHED`。
- `VERIFIED` 仅当存在 `demand_qualification.status=QUALIFIED` 或 CEO 手工核验记录。
- `MATCHED` 仅当存在 `matching_records.recommendation=ADVANCE` 且已 REVIEWED。
- `WON/LOST` 仅 CEO 可置位。

**匹配：** `DRAFT → REVIEWED → CEO_PENDING → APPROVED/REJECTED`。
**核验：** `PENDING → IN_REVIEW → VERIFIED/REJECTED`。
**商机：** `OPEN → DISCLOSED → INTRODUCED → TERM_SHEET → CA → CLOSED_WON/CLOSED_LOST`。

## 3. 种子数据（backend 负责）

从历史交接资料导入，**全部保持未核实状态**：
- `company_type=SUPPLIER` 18 条：来自 `docs/handover-20261113/B-中国算力出海/01-供应侧档案/registry.csv`（SUP-20261102-001~007、SUP-20261112-001~011）。
- `company_type=DEMANDER` 9 条：来自 `02-海外需求侧档案/registry.csv`（DEM-20261102-001~009）。
- `matching_records` 3 条：来自 `03-匹配与解释/registry.csv`（MATCH-20261102-001~003），status=DRAFT，analyst=history-import。
- `evidence_registry`：从 `05-市场与竞争/证据表.md` 导入至少 B-E22、B-E23 等公开价目证据（若解析困难，至少导入 10 条并注明来源文件）。
- `compute_specifications`：内置 H100/H200/A100/A800/H800/昇腾910B/寒武纪590 等 8-12 条公开规格（来源写公开厂商页，标注「规格参考，非报价」）。
- `agent_tasks`：11 个 Agent 各 1 条初始任务（QUEUED），用于演示任务管理。
- `knowledge_records`：≥5 条（公司定位、线索分级规则、收费原则、核验标准、GitHub 敏感数据规则）。
- `approvals`：≥5 条 PENDING（对外话术批准、仓库改 Private、供应商首访、客户首访、介绍协议模板）。
- 所有种子记录的 `notes` 必须含 `seed:history-import` 或 `seed:demo` 标记；`lead_grade` 不高于 `PUBLIC_LEAD`。

## 4. 迁移与备份

- `schema.sql` 幂等（IF NOT EXISTS）；启动时自动建表。
- `POST /api/backup`：用 sqlite3 backup API 复制到 `backups/app-YYYYmmdd-HHMMSS.db`，写 `backup_records`。
- `POST /api/backup/restore {id, confirm:"RESTORE"}`：校验文件 sha256 后恢复（先备份当前库）。
- 默认保留最近 20 份备份。

## 5. 隐私分层

| 数据 | 位置 | 入仓 |
|------|------|------|
| 真实联系人 | `private/contacts.csv` | 否 |
| 真实报价 | `private/quotes.json` | 否 |
| 合同正文 | `private/contracts/` | 否 |
| 业务数据库 | `data/runtime/app.db` | 否 |
| 研究公开证据 | `data/research/*.csv` | 是（脱敏） |
| 导入模板/示例 | `data/import/*.csv` | 是 |
