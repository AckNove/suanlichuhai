---
name: evidence-management
description: 证据登记与交叉验证：把每条企业/容量/需求/报价/规则主张登记为可追溯的 evidence_registry 记录，做来源分级、交叉验证、重复与缺口审计，维护证据链完整性。
version: 1.0
owner: Data Manager
tools:
  - web_search
  - web_fetch
  - read
  - write
  - edit
  - python
  - sqlite3
  - csv
---

# evidence-management · 证据登记与交叉验证

> 适用场景：任何 Agent 写入实体/数字/结论前后；每周证据健康检查；交接档案 31 条证据（B-E01~B-E31）迁移与复核时。
> 基线：`PROJECT_BRIEF.md` 第 10 节证据规则；`SPEC_DATABASE.md` evidence_registry 表；`evidence_check` 任务类型。

## ① 输入

| 项 | 内容 | 来源 | 前置校验 |
|----|------|------|----------|
| 待登记主张 | 单条可判定真伪的陈述（谁/什么/多少/何时） | 研究简报、供应商/需求材料、Agent 产出 | 必须原子化：一条记录只放一条主张；不得复合多事实 |
| 来源信息 | 标题、URL、发布者、发布时间、获取时间 | 原始页面/文档 | URL 可打开；付费墙/登录页须注明「不可直接访问」 |
| 归属对象 | subject_type + subject_id | `companies/demands/supplies/matches` | subject_id 必须存在；跨对象主张用 CLAIM |
| 既有证据 | 同主题历史记录 | `evidence_registry` | 先查重：同 claim 同 URL 不重复登记 |
| 历史证据表 | 31 条交接证据 | `docs/handover-20261113/` | 迁移时保留原编号（B-E01 等）于 notes |

## ② 操作步骤

1. **拆分主张**：把一段话拆成原子 claim；例如「该公司有 1000 张 H100 且已服务中东客户」拆成两条。
2. **定 subject**：企业事实→COMPANY；需求→DEMAND；供给→SUPPLY；匹配结论→MATCH；规则/行业/第三方事实→CLAIM；其他→OTHER。
3. **填来源字段**：`source_title/url/publisher/published_at(未知写「未标注」)/retrieved_at(ISO-8601)`；`notes` 记录访问限制、原文关键句、口径说明。
4. **评信任度** `confidence`：HIGH＝一手官方/原始文件且已打开核对；MEDIUM＝权威二手（主流媒体、律所公开文章、上市公司公告转载）或多源一致；LOW＝单一弱来源/自媒体/公司营销页；UNVERIFIED＝仅线索、未打开、来源不明。默认 UNVERIFIED，不得凭感觉升级。
5. **交叉验证**：`cross_verified=1` 需 ≥2 个**相互独立**来源（非互相转载）且结论一致；来源冲突时 `cross_verified=0`，在 `notes` 记录冲突并保留双方。
6. **回填链接**：把 evidence id 写入 `demand_opportunities.evidence_ids`、`compute_supply_resources.evidence_ids` 或匹配/分析的说明字段；一条实体至少 1 条证据，关键数字至少 2 条。
7. **缺口审计**：按实体列出「无证据字段」「单一来源关键数字」「UNVERIFIED 超 30 天」「url 为空」「交叉验证覆盖率」；输出 `data/research/evidence-gaps-<YYYYMMDD>.md`。
8. **维护**：证据过期（>180 天或规则变更）标 `notes` 加「待复核」；原文消失时保留 URL 并在 notes 写「链接失效，留档快照在 private/」；不得删除历史证据，只能新增更正记录。

异常与升级：找不到公开来源 → 记录「无公开来源」并请 CEO 决定是否通过授权渠道获取，不得编造；来源内容与既有记录冲突 → 保留双记录并报 Lead；涉及报价/合同/联系人 → 只登记「存在该材料」的元信息，敏感内容进 `private/`。

## ③ 工具要求

**本项目真实可用**：`web_search`、`web_fetch`、`read`、`write`、`edit`、`python`（批量校验、统计、调用本地后端 API）、`sqlite3`（只读）、CSV、`git`（只读）。
**明确不可用**：浏览器自动化、MCP、付费 API/付费墙绕过、网页快照商业服务、邮件/IM 外联、截图 OCR 工具链（pytesseract 未安装）。
URL 无法访问时可保留公开元数据并注明，不得用「记忆中的内容」充当证据。

## ④ 输出

| 产出 | 路径/表 | 字段 |
|------|---------|------|
| 证据记录 | `evidence_registry` | 全部字段，`claim` 原子化，`confidence` 默认 UNVERIFIED |
| 实体回填 | `demand_opportunities/compute_supply_resources.evidence_ids` | 逗号/JSON 形式证据 ID |
| 缺口报告 | `data/research/evidence-gaps-<YYYYMMDD>.md` + `.csv` | 无证据/单一来源/过期/未交叉验证清单 |
| 证据备份 | `data/research/evidence-export-<YYYYMMDD>.csv` | UTF-8，公开字段 |
| 留痕 | `project_activities`、`audit_logs`、`agent_tasks.result_summary` | 新增/更正/缺口统计 |

## ⑤ 质量标准

- 每条记录 claim 单一、可判定、不含「可能/据说」等模糊词；模糊判断改写为「X 声称 Y」。
- `url` 或 `source_title` 至少其一非空；两者都空仅允许「内部材料编号」并注明存放位置（private）。
- `confidence=HIGH` 必须有官方/原始来源且已打开核对；`cross_verified=1` 必须 ≥2 独立来源。
- 同一实体关键数字（容量/规模/预算）证据不足 2 条时，在缺口报告中列为高风险。
- 迁移历史证据保留原编号并标注「迁移复核状态」，不覆盖原结论。
- 证据登记不改变实体状态机；不允许「补了证据就自动升级」。

## ⑥ 权限边界

**可自主**：证据登记/更正、来源分级、交叉验证、缺口审计、证据导出（公开字段）、向各 Agent 提供 evidence_id。
**必须 CEO 审批**：通过授权渠道获取非公开材料、使用付费数据库、对外引用证据、把敏感材料复制出 `private/`。
**禁止**：编造 URL/来源/发布时间、删除历史证据、把 UNVERIFIED 写成 HIGH、把公司自述当一手证据、在公开仓库保留联系人/报价原文。
