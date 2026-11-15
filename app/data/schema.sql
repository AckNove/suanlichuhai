-- CCGS · 中国算力国际化项目 本地业务库 DDL（v1.0）
-- 权威契约：docs/07_ai_system/SPEC_DATABASE.md（逐字实现，幂等）
-- 真实业务库位于 data/runtime/app.db（gitignore），公开仓库不含真实数据。

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
