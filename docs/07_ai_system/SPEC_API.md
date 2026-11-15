# SPEC · API 契约（v1.0，权威）

> 服务：Flask（Python 3.9），默认监听 `127.0.0.1:8770`。前端同源调用 `/api/*`。
> 统一 JSON；时间 ISO-8601；分页参数 `page`(默认1)、`page_size`(默认50，最大200)。
> 请求头 `X-Actor` 标识操作者（默认 `local`），写入 audit_logs。
> 本地无鉴权（仅绑定 127.0.0.1），文档中明确标注为本地单用户工作台。

## 1. 通用响应

```json
// 列表
{"items":[...], "total": 123, "page": 1, "page_size": 50}
// 单条
{"item": {...}}
// 错误
{"error": {"code": "VALIDATION_ERROR|NOT_FOUND|CONFLICT|FORBIDDEN|INTERNAL", "message": "..."}}
```

HTTP 码：200/201/204/400/404/409/403/500。

## 2. 资源路由（通用 CRUD）

| 前缀 | 表 | 可写字段 |
|------|----|----------|
| `/api/companies` | companies | 全部（id 自动生成 `C-YYYYmmdd-NNN`，若传入则用传入） |
| `/api/demands` | demand_opportunities | 全部 |
| `/api/supplies` | compute_supply_resources | 全部 |
| `/api/specs` | compute_specifications | 全部 |
| `/api/evidence` | evidence_registry | 全部 |
| `/api/supplier-verifications` | supplier_verification | 全部 |
| `/api/demand-qualifications` | demand_qualification | 全部 |
| `/api/matches` | matching_records | 全部 |
| `/api/procurement-analyses` | procurement_analyses | 全部 |
| `/api/commercial-opportunities` | commercial_opportunities | 全部 |
| `/api/quotes` | quotes | 全部 |
| `/api/contracts` | contracts_metadata | 全部 |
| `/api/agent-tasks` | agent_tasks | 全部 |
| `/api/activities` | project_activities | 只读（由系统写） |
| `/api/knowledge` | knowledge_records | 全部 |
| `/api/approvals` | approvals | 全部 |
| `/api/audit-logs` | audit_logs | 只读 |
| `/api/backups` | backup_records | 只读（POST /api/backup 创建） |

通用参数：`q`（模糊搜索 name/title/summary 等文本字段）、`status`、`lead_grade`、`company_type`、`sort`（`field` 或 `-field`）、`page`、`page_size`。

- `GET /api/<res>` → 列表
- `GET /api/<res>/<id>` → 单条
- `POST /api/<res>` → 创建（201）
- `PUT /api/<res>/<id>` → 全量更新（200）
- `PATCH /api/<res>/<id>` → 局部更新（200）
- `DELETE /api/<res>/<id>` → 删除（204，写审计；关联数据存在时 409）

## 3. 专用端点

### GET /api/health
```json
{"status":"ok","version":"1.0.0","db":"data/runtime/app.db","time":"...","tables":18}
```

### GET /api/dashboard
```json
{
 "counts": {"companies":27,"suppliers":18,"demanders":9,"supplies":18,"demands":9,
            "evidence":30,"matches":3,"opportunities":0,"agent_tasks":11,
            "pending_approvals":5,"knowledge":5},
 "pipeline": {"supplier":{"LEAD":18},"demand":{"LEAD":9},"opportunity":{}},
 "grades": {"PUBLIC_LEAD":27,"INFERRED":0,"POTENTIAL":0,"VERIFIED":0,"QUALIFIED":0},
 "verification": {"verified":0,"needs_verification":18,"rejected":0},
 "recent_activities":[...],
 "alerts":[{"level":"WARN","code":"PUBLIC_REPO","message":"GitHub 仓库仍为 Public，建议 CEO 授权改 Private"},
           {"level":"WARN","code":"NO_LEGAL_ENTITY","message":"公司主体未设立，签约与收款为 BLOCKED"}]
}
```

### POST /api/match/run
请求：`{"demand_id":"DEM-...", "supply_ids":["SUP-..."], "persist":true}`
- 缺省 supply_ids 时对全部 `status>=NEEDS_VERIFICATION` 或全部供给评分。
- 确定性评分（0–100），回写 `matching_records`（persist=true 时），返回：
```json
{"demand_id":"...","results":[{"supply_id":"...","score":78.5,
  "dimensions":{"gpu_model":{"score":28,"max":30,"reason":"..."},
                "scale":{"score":18,"max":20,"reason":"..."},
                "workload":{"score":15,"max":15,"reason":"..."},
                "location":{"score":6,"max":10,"reason":"..."},
                "delivery":{"score":7,"max":10,"reason":"..."},
                "network":{"score":4,"max":5,"reason":"..."},
                "compliance":{"score":3,"max":5,"reason":"..."},
                "trust":{"score":2,"max":5,"reason":"..."}},
  "why_match":"...","why_not_match":"...","confidence":"MEDIUM",
  "recommendation":"ADVANCE|NEED_MORE_INFO|REJECT","id":"MATCH-..."}]}
```
评分规则（必须可解释，禁止随机）：
- GPU 型号匹配 30：精确匹配 30；同代/同级别兼容 20；可替代 10；不兼容 0。
- 规模 20：supply.sellable_gpu_count>=demand.min_gpu_count 得满分，每缺 10% 扣 2；未知 5。
- 负载能力 15：训练需求且 training_capable=1 得 15；推理需求且 inference_capable=1 得 15；不满足 0。
- 地点/数据驻留 10：国家匹配 10；区域匹配 6；未知 4。
- 交付周期 10：<=需求时限 10；未知 5；明显超期 0。
- 网络 5：有互联/带宽描述 5；未知 2。
- 合规 5：跨境合规已筛查 5；未筛查 2；命中红线 0。
- 信任 5：VERIFIED 5；NEEDS_VERIFICATION 3；LEAD 1。
- `recommendation`：>=70 ADVANCE；40–69 NEED_MORE_INFO；<40 REJECT。
- 若命中红线（无合法转售权/未筛查跨境合规/数据驻留冲突），最高分封顶 39 且 why_not_match 必含风险原因。

### POST /api/match/score
同上但不落库（`persist` 忽略）。

### GET /api/export?entity=<res>&format=csv
返回 `text/csv; charset=utf-8`，UTF-8 BOM 前缀便于 Excel；文件名 `<entity>-YYYYmmdd.csv`。entity 取值同资源路由（用短名：companies/demands/supplies/specs/evidence/supplier-verifications/demand-qualifications/matches/procurement-analyses/commercial-opportunities/quotes/contracts/agent-tasks/knowledge/approvals）。

### POST /api/import?entity=<res>&mode=upsert|insert
- `multipart/form-data` 字段 `file`，或 `Content-Type: text/csv` 原始 body。
- 返回 `{"inserted":n,"updated":n,"skipped":n,"errors":[{"row":2,"error":"..."}]}`
- upsert 依据主键 id；缺 id 自动生成。只允许白名单字段，未知字段忽略并报告。
- 导入前校验：敏感字段（手机号/邮箱/微信）不得进入 companies 表的公开备注；发现则返回 warnings。

### POST /api/backup
`{"note":"..."}` → `{"id":"B-...","file_path":"backups/app-....db","size_bytes":...,"sha256":"..."}`

### GET /api/backups
列表（按时间倒序）。

### POST /api/backup/restore
`{"id":"B-...","confirm":"RESTORE"}` → 恢复并返回 `{"restored":true,"safety_backup":"B-..."}`

### GET /api/search?q=<keyword>&limit=20
跨 companies/demands/supplies/evidence/knowledge 搜索，返回：
```json
{"results":[{"type":"company","id":"C-...","title":"...","snippet":"...","score":1.0}]}
```

### GET /api/agents
返回 `agents/registry.json` 内容（11 个 Agent 定义）。

### GET /api/skills
列出 `.dsh/skills/*/SKILL.md` 的 name/description/inputs/tools/outputs（解析 frontmatter 或标题）。

### POST /api/agent-tasks/<id>/run
调用本地 runner（`agents/runner.py` 的 run_task 函数）执行确定性任务；适用于 task_type ∈ {data_audit, evidence_check, csv_ingest, match_compute, report_render, schema_validate}。返回 `{"task_id":..., "status":"DONE|BLOCKED|FAILED", "result":{...}, "output_path":...}`。

### GET /api/approvals/pending
待审批列表（status=PENDING）。

### POST /api/approvals/<id>/decide
`{"decision":"APPROVED|REJECTED|RETURNED","decided_by":"CEO","note":"..."}` → 状态更新 + 审计。**仅 CEO 本人使用；系统不自动批准。**

### GET /api/reports/pipeline
漏斗统计：按状态计数 + 转化率（无历史时返回 `null` 并注明 data_insufficient）。

### GET /api/reports/fee-scenarios
返回收费情景示例（明确 `example_only:true`，不写死费率）。

### GET /api/state/transitions
返回允许的状态迁移表（前端下拉用）。

### GET /api/health/db
表清单 + 各表行数 + 最近备份。

## 4. 审计规则

- 所有 POST/PUT/PATCH/DELETE 写入 `audit_logs`（含 before/after，截断至 2000 字符）与 `project_activities`（摘要）。
- 默认 actor 取 `X-Actor`，缺省 `local`。
- 不允许删除 `audit_logs`。
- 状态非法迁移返回 409 `CONFLICT` 并在 message 中给出允许的目标状态。

## 5. 前端模块与 API 对应

| # | 模块 | 路由 | 主 API |
|---|------|------|--------|
| 1 | 经营总览 | #/dashboard | dashboard, reports/pipeline |
| 2 | 需求管理 | #/demands | demands |
| 3 | 供应商管理 | #/suppliers | companies?company_type=SUPPLIER |
| 4 | GPU 资源管理 | #/supplies | supplies |
| 5 | 证据来源管理 | #/evidence | evidence |
| 6 | 供应商核验 | #/supplier-verifications | supplier-verifications |
| 7 | 需求资格核验 | #/demand-qualifications | demand-qualifications |
| 8 | 算力规格标准化 | #/specs | specs |
| 9 | 供需智能匹配 | #/matching | match/run, matches |
| 10 | 采购分析报告 | #/procurement | procurement-analyses |
| 11 | 商机管理 | #/opportunities | commercial-opportunities |
| 12 | 项目进度 | #/activities | activities, reports/pipeline |
| 13 | Agent 任务管理 | #/agents | agent-tasks, agents |
| 14 | CEO 审批中心 | #/approvals | approvals |
| 15 | 知识库 | #/knowledge | knowledge |
| 16 | CSV 导入导出 | #/data | export, import |
| 17 | 数据备份 | #/backup | backup, backups |
| 18 | 审计日志 | #/audit | audit-logs |

## 6. 运行方式

```powershell
# 启动（默认 127.0.0.1:8770）
python -m app.backend.server
# 或
powershell -File scripts/run_server.ps1
```
首次启动自动建表 + 导入种子数据（可用 `CCGS_SEED=0` 关闭）。
