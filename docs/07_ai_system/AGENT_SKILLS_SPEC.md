# CCGS Agent × Skills 体系规格

| 项目 | 内容 |
| --- | --- |
| 文档编号 | AGENT_SKILLS_SPEC |
| 版本 | 1.0 |
| 状态 | ACTIVE（随实现同步维护） |
| 负责人 | Agent & Skills 体系负责人 |
| 权威基线 | `docs/00_project_audit/PROJECT_BRIEF.md`、`docs/07_ai_system/SPEC_DATABASE.md`、`docs/07_ai_system/SPEC_API.md` |
| 实现位置 | `agents/registry.json`、`agents/runner.py`、`.dsh/skills/*/SKILL.md`、`tests/test_agents_runner.py` |

> 一句话：**Agent 不等于提示词。** 一个 Agent 的真实能力边界 = 注册表声明的工具 ∩ runner 可执行的确定性任务 ∩ 对应 Skill 的可执行流程。LLM 推理由 DSH Agent 会话承担；runner 只做确定性执行、校验与产物落盘，不调用任何大模型。

---

## 0. 文档定位与阅读方式

本文回答四个问题：

1. 10 个 Skill 各自的输入、步骤、工具、输出、质量标准与权限边界是什么（§2）；
2. 11 个 Agent 分别能用哪些 Skill/工具、读写哪些数据、产出什么、哪些动作必须审批（§3）；
3. 多 Agent 协作时的标准调用顺序（§4：需求研究、供应商核验、匹配到商机三套工作流）；
4. 权限红线、CEO 审批点与已知限制（§5、§6）。

配套事实源：

- Skill 原文：`.dsh/skills/<name>/SKILL.md`（YAML frontmatter + 六节正文）；
- Agent 注册表：`agents/registry.json`（数组，11 个对象）；
- 确定性执行器：`agents/runner.py`（Python 3.9，仅标准库）；
- 自测：`tests/test_agents_runner.py`（unittest，临时库，不触碰 `data/runtime` 真实库）。

术语沿用英文原名：PUBLIC_LEAD / INFERRED / POTENTIAL / VERIFIED / QUALIFIED，LEAD / RESEARCHED / NEEDS_VERIFICATION / VERIFIED / QUALIFIED / ACTIVE，ADVANCE / NEED_MORE_INFO / REJECT，DRAFT / REVIEWED / CEO_PENDING / APPROVED / REJECTED。

---

## 1. 体系总览：三层能力模型

```
┌──────────────────────────────────────────────────────────────┐
│ 第 3 层：DSH Agent 会话（LLM）                                │
│   读 Skill 流程 → 调 web_search/web_fetch → 写作 → 分派/复核   │
├──────────────────────────────────────────────────────────────┤
│ 第 2 层：确定性执行器 agents/runner.py（无 LLM、无网络）       │
│   data_audit / evidence_check / csv_ingest / match_compute /  │
│   report_render / schema_validate → 读写 agent_tasks + 产物    │
├──────────────────────────────────────────────────────────────┤
│ 第 1 层：数据与规则基座                                       │
│   18 张表（SQLite，TEXT 主键）+ 状态机 + 证据规则 + 权限边界    │
└──────────────────────────────────────────────────────────────┘
```

三条硬约束：

1. **能力真实性**：Skill 和 Agent 只能声明本环境真实可用的工具。可用：`web_search`、`web_fetch`、`read`、`write`、`edit`、`python`、`sqlite3`、`csv`、`git`（只读）、`backend_api`（`http://127.0.0.1:8770`）、`runner`；浏览器自动化仅限本机 Chrome + CDP 的本地自测（Agent 不得用于外部登录/外联）。不可用：MCP（0 个）、付费 API（无密钥）、PPTX 生成（python-pptx 未安装）、pytest（未安装）、邮件/私信/电话外联。
2. **确定性可复现**：凡是「统计、校验、评分、渲染」类工作，必须能由 runner 在无 LLM 条件下重跑；LLM 只负责判断、写作与解释。
3. **证据优先**：任何对外或对内的结论都必须落到 `evidence_registry`；没有证据的容量、报价、预算、意向一律不得写入。

另：`data/runtime/` 与 `backups/` 已被 `.gitignore` 排除；runner 产物只写入 `data/runtime/agent_outputs/`。公开仓库只提交脱敏内容，`private/` 与敏感商务材料不入库。

---

## 2. 10 个 Skills：六要素对照表

> 路径约定：`S` = `.dsh/skills/<name>/SKILL.md`。所有 Skill 的 frontmatter 均含 `name`、`description`、`version: 1.0`、`owner`、`tools`，正文固定六节：`## ① 输入`、`## ② 操作步骤`、`## ③ 工具要求`、`## ④ 输出`、`## ⑤ 质量标准`、`## ⑥ 权限边界`。

| # | Skill | ① 输入（字段/来源/前置校验） | ② 操作步骤（编号摘要） | ③ 工具要求 | ④ 输出（文件/表/字段） | ⑤ 质量标准（可验证） | ⑥ 权限边界 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `global-demand-research` | 研究区域/客群/负载类型；`data/research/` 基线；`docs/handover-20261113/需求侧 registry.csv`（9 条线索）；证据规则 | 1 拆研究问题 2 公开检索（官网/公告/财报/招聘/新闻）3 建 `demand_opportunities` 草案 4 逐条登记 `evidence_registry` 5 出需求研究简报 6 自检 | `web_search`、`web_fetch`、`read`、`write`、`edit`、`python`、`sqlite3`、`csv`、`git`(只读) | `demand_opportunities`（`lead_grade` 初始 PUBLIC_LEAD）；`companies`；`evidence_registry`；`data/research/demand-<region>-<YYYYMMDD>.md` | 每条主张有 `evidence_registry`；budget 未知写 `UNKNOWN`；`lead_grade` 不得擅自升级；9 条基线线索必须逐条有下落 | 可自主研究/建档；不得接触客户、不得代发消息、不得把公开线索写成合格客户 |
| 2 | `china-compute-supply-research` | 18 条供给线索（`SUP-20261102-001~007`、`SUP-20261112-001~011`）；`compute_supply_resources`；`compute_specifications`；证据表 | 1 盘点线索 2 官网/公告检索 3 区分现网/可售/规划 4 写供给记录（`verified=0`、`price_indication=待确认`）5 登记证据 6 出供给简报 | 同上 | `compute_supply_resources`；`companies`；`evidence_registry`；`data/research/supply-<topic>-<YYYYMMDD>.md` | 公开价目不得写成报价；规划容量不得写成可售；每条供给至少 1 条来源 URL；优先核验登甲/天顿/硅基流动 | 可自主研究；不得对外询价/访谈；`price_indication` 只能保留原文或「待确认」 |
| 3 | `supplier-verification` | 供应商档案；25 项 checklist（A 主体与授权 A1–A6、B 容量真实性 B1–B7、C 交付运营 C1–C5、D 商务合规 D1–D7）；`evidence_registry` | 1 锁定对象 2 按 25 项逐项取证 3 填 `checklist_json` 与 8 个 boolean 4 评分（PASS=4/PARTIAL=2/FAIL=0）5 判硬门槛（A1/A4/B1/B3/D5 任一 FAIL→REJECTED）6 出核验报告与缺口清单 | 同上 + `backend_api` | `supplier_verification`（`status` PENDING→IN_REVIEW→VERIFIED/REJECTED，`score`、`gaps`）；`compute_supply_resources.verified`（仅核验 VERIFIED 后）；核验报告 Markdown | 25 项逐项有证据或标「无法取得」；8 个 boolean 与 checklist 不矛盾；VERIFIED 必须 8 项全过且无硬门槛 FAIL；公司状态不得跳级 | 可自主取证/写核验记录；面试/电话/邮件需 CEO；公司升级 QUALIFIED/ACTIVE 必须 CEO 审批 |
| 4 | `gpu-spec-normalization` | 供应商/需求方原始卡型描述；公开规格资料；`compute_specifications` 现有记录 | 1 解析型号/厂商/形态/显存/带宽/算力/互联/功耗 2 统一单位 3 规范名「厂商 型号 form_factor」4 写 `compute_specifications` 5 出映射表与可比性说明 6 标注未知项 | `web_search`、`web_fetch`、`read`、`write`、`edit`、`python`、`sqlite3`、`csv` | `compute_specifications`（`gpu_model` NOT NULL，`vendor`、`memory_gb`、`interconnect`、`typical_cluster` 等）；`data/research/spec-normalization-<YYYYMMDD>.md` | 每个规格有 `source`；未知写「未披露」不猜；同型号多来源冲突必须并列；单位统一（GB/GB·s⁻¹/TFLOPS/kW） | 可自主查公开规格；不做性能承诺、不给未公开参数估值、不替代供应商规格书 |
| 5 | `demand-qualification` | 需求档案；`demand_qualification`；决策人/预算/时间窗/合规/签约路径/数据驻留证据 | 1 六维核验（决策人 25/预算 25/时间窗 15/合规 20/签约 15+数据驻留硬门槛）2 公开投资额折算需剔除 3 填 boolean 与 `score` 4 给 QUALIFIED/IN_REVIEW/REJECTED 建议 5 出缺口清单 | `web_search`、`web_fetch`、`read`、`write`、`edit`、`python`、`sqlite3`、`csv` | `demand_qualification`（`decision_maker_confirmed`、`budget_confirmed`、`timeline_confirmed`、`compliance_screened`、`contracting_path_confirmed`、`data_residency_ok`、`score`、`gaps`）；资格报告 | 六维逐项有证据；「公开宣布投资额」不能当作 `budget_confirmed`；`lead_grade` 未经一手核实最高 POTENTIAL；数据驻留冲突必须判红线 | 可自主核验/写记录；不得擅自把需求升 VERIFIED/QUALIFIED；对外确认需求意向须 CEO |
| 6 | `compute-matching` | `demand_opportunities`、`compute_supply_resources`、`supplier_verification`、`demand_qualification`；`POST /api/match/score` | 1 校验需求必填（卡型/最小规模/负载/位置/时限）2 逐对调用 `/api/match/score`（离线用 runner `match_compute` 等价实现）3 八维打分（30/20/15/10/10/5/5/5）4 红线封顶 39 5 写 `matching_records` DRAFT 6 附 why_match/why_not_match | `web_fetch`、`read`、`write`、`python`、`sqlite3`、`backend_api`、`runner` | `matching_records`（`score`、`match_dimensions`、`why_match`、`why_not_match`、`risks`、`confidence`、`recommendation`、`status=DRAFT`）；runner 产物 JSON | 八个维度合计 100；每维有 reason；命中红线（无转售权/未筛查跨境合规/数据驻留冲突）最高 39 且 `why_not_match` 必含风险；`>=70 ADVANCE`、`40–69 NEED_MORE_INFO`、`<40 REJECT`；标注实现来源 | 可自主计算/写 DRAFT；匹配结果不外发、不构成订单；`REVIEWED` 及之后状态由人工/CEO |
| 7 | `procurement-analysis` | 需求档案；2–5 个候选供给；`matching_records`；`procurement_analyses` | 1 确定比较口径 2 选 2–5 方案 3 七维评分（规格 25/交付 20/成本结构 20/合规 15/合同 10/退出 5/信任 5）4 写 `options_json`/`scoring_json` 5 给推荐与风险假设 6 出报告 | `web_search`、`web_fetch`、`read`、`write`、`python`、`sqlite3`、`csv` | `procurement_analyses`（`options_json`、`scoring_json`、`recommendation`、`risks`、`assumptions`、`status=DRAFT`）；`data/research/procurement-<demand>-<YYYYMMDD>.md` | 成本只写计价模式与指数化区间，不写具体金额；每个假设可证伪；方案差异必须量化；不替客户决策 | 可自主分析；不报价、不承诺交付、不替代客户决策；对外版本须 CEO 审批 |
| 8 | `cross-border-risk-screening` | 场景（外数中算/中算出海）；主体与数据流；证据表 B-E01 等公开法规解读 | 1 画数据流与主体 2 六类风险筛查（数据出境/出口管制/制裁名单/数据驻留/行业监管/合同责任）3 区分事实与风险 4 列待律师确认问题 5 红线→CEO 6 出风险登记 | `web_search`、`web_fetch`、`read`、`write`、`edit`、`python`、`sqlite3` | `evidence_registry`；`approvals`（`approval_type=CROSS_BORDER_RISK`）；`data/research/risk-<subject>-<YYYYMMDD>.md` | 只陈述公开事实，不写「合规/不合规」结论；每条风险有来源或标「待确认」；红线必须 CEO_PENDING | 可自主研究/写风险登记；**不提供法律意见**；红线结论须 CEO+律师复核；不得与客户讨论法律结论 |
| 9 | `evidence-management` | 任意主张（企业/容量/报价/需求/规则）；已有 `evidence_registry` | 1 把主张原子化 2 采集来源（URL/标题/发布者/发布时间/获取时间）3 分级 HIGH/MEDIUM/LOW/UNVERIFIED 4 交叉验证（≥2 独立来源才 `cross_verified=1`）5 登记/去重 6 出缺口清单 | `web_search`、`web_fetch`、`read`、`write`、`edit`、`python`、`sqlite3`、`csv` | `evidence_registry`（`subject_type`、`subject_id`、`claim`、`source_title`、`url`、`publisher`、`published_at`、`retrieved_at`、`confidence`、`cross_verified`） | 每条 claim 一条记录；`url` 为空必须标 LOW/UNVERIFIED 待补；发布时间未知写「未标注」；`cross_verified=1` 必须有 ≥2 独立来源；不删除历史证据 | 可自主登记/分级；不修改他人结论、不删证据；`HIGH` 判定需一手来源且已打开验证 |
| 10 | `commercial-operations` | 已核验匹配；`matching_records`；`commercial_opportunities`；费用模式 R1–R6；`approvals` | 1 校验匹配 `recommendation=ADVANCE` 且 `status=REVIEWED` 2 建商机（stage=OPEN）3 阶段推进（OPEN→DISCLOSED→INTRODUCED→TERM_SHEET→CA→CLOSED_WON/LOST）4 准备披露/引荐/条款/协议材料 5 组审批包 6 活动留痕 | `web_search`、`web_fetch`、`read`、`write`、`edit`、`python`、`sqlite3`、`csv`、`backend_api` | `commercial_opportunities`（`stage`、`model_type`、`fee_payer`、`fee_basis`、`fee_terms`、`conflict_disclosed`、`ceo_approval_status`）；`quotes`（DRAFT）；`contracts_metadata`；`approvals` | 阶段不跳级；费用只写 R1–R6 模式不写费率；双付须事前书面披露；冲突披露 `conflict_disclosed=1`；每个阶段变更留 `project_activities` | 仅内部准备；**不联系客户/供应商、不报价、不签约、不收款、不托管资金**；披露/引荐/条款/合同/收款全部 CEO 执行 |

### 2.1 Skill 共用的工具事实

| 类别 | 工具 | 说明 |
| --- | --- | --- |
| 检索 | `web_search`、`web_fetch` | 仅 DSH Agent 会话可用；runner 不联网。私有/付费墙内容需标注「仅二手」 |
| 文件 | `read`、`write`、`edit` | 写入范围受 Agent 权限约束；产物默认写 `data/runtime/agent_outputs/` |
| 数据 | `python`、`sqlite3`、`csv` | 仅标准库；SQLite 单机文件，业务库 `data/runtime/app.db`（`CCGS_DB_PATH` 可覆盖） |
| 只读 | `git` | 只允许 `status`/`log`/`diff` 等只读命令；禁止 commit/push/切分支 |
| 接口 | `backend_api` | `http://127.0.0.1:8770`，与前端共用；不得绕过 API 改业务表 |
| 执行 | `runner` | `python -m agents.runner ...` 或 `python agents\runner.py ...` |
| 不可用 | MCP、付费 API、邮件/短信/电话、PPTX、pytest；浏览器自动化不得用于外部登录/外联 | Skill 中不得出现「自动发邮件」「自动成交」「自动报价」等承诺 |

---

## 3. 11 个 Agent：能力与权限矩阵

> `approval_required` 来自注册表：`true` 表示该 Agent 的关键升级动作需 CEO/Lead 审批；日常只读研究与草稿写入可自主。

| Agent | 何时使用 | Skills | 读 | 写 | 可执行 task_type | 产物 | 审批 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Research Director（研究总监） | 多线研究启动、任务分派、简报合并、证据质量把关 | global-demand-research、china-compute-supply-research、evidence-management | 全部业务表 + `docs/` + `data/research/` | `data/research/`、`agent_outputs/`、`knowledge_records` | data_audit、report_render | 研究计划、合并简报、knowledge_records | 是 |
| Global Demand Intelligence（全球需求情报） | 发现/补充海外需求线索 | global-demand-research、demand-qualification、evidence-management | companies、demands、evidence、demand_qualification、`docs/` | companies、demands、evidence、`data/research/` | report_render、evidence_check | 需求草案、需求简报 | 否（升级需审批） |
| China Supply Intelligence（中国算力供给情报） | 盘点 18 条供给线索、区分现网/可售/规划 | china-compute-supply-research、gpu-spec-normalization、evidence-management | companies、supplies、specs、evidence、`docs/` | companies、supplies、evidence、`data/research/` | report_render、evidence_check | 供给记录、供给简报 | 否（升级需审批） |
| Supplier Verification（供应商核验） | 25 项 checklist 取证与核验结论 | supplier-verification、evidence-management、cross-border-risk-screening | companies、supplies、specs、evidence、supplier_verification | supplier_verification、evidence、supplies | evidence_check、report_render | 核验记录、缺口清单、核验报告 | 是（VERIFIED+） |
| Compute Analyst（算力分析师） | GPU 规格统一、口径纠偏、技术可行性 | gpu-spec-normalization、china-compute-supply-research、compute-matching | specs、supplies、demands、evidence | compute_specifications、supplies、`data/research/` | csv_ingest、report_render | 规格记录、映射表、技术说明 | 否 |
| Matching Engine（匹配引擎） | 需求×供给打分与解释 | compute-matching、supplier-verification、demand-qualification | demands、supplies、verifications、qualifications、matches | matching_records、`agent_outputs/` | match_compute、report_render | 匹配记录（DRAFT）、匹配报告 | 否（ADVANCE 后人工复核） |
| Procurement Analyst（采购分析师） | 2–5 方案比较与采购报告 | procurement-analysis、cross-border-risk-screening、commercial-operations | demands、supplies、matches、procurement、verifications、qualifications | procurement_analyses、`data/research/` | report_render、csv_ingest | 采购分析（DRAFT）、对比报告 | 是（对外版本） |
| Cross-border Research（跨境合规研究） | 数据出境/出口管制/制裁/合同风险初筛 | cross-border-risk-screening、evidence-management | demands、supplies、evidence、`docs/` | evidence、`data/research/`、`approvals` | evidence_check、report_render | 风险登记、律师问题清单、CROSS_BORDER_RISK 审批项 | 是 |
| Commercial Operations（商务运营） | 匹配转商机、阶段推进、审批包 | commercial-operations、demand-qualification、supplier-verification | matches、demands、supplies、opportunities、quotes、contracts、approvals | commercial_opportunities、quotes、contracts_metadata、approvals、`data/research/` | report_render、data_audit | 商机、DRAFT 报价单、协议元数据、审批包 | 是（对外动作） |
| Data Manager（数据管理员） | 数据体检、证据缺口、CSV 校验、schema 一致性 | evidence-management、gpu-spec-normalization | 全 18 表 + `data/import/` + `app/data/schema.sql` | agent_tasks、project_activities、audit_logs、`agent_outputs/`、`data/research/` | data_audit、evidence_check、csv_ingest、schema_validate | 体检 JSON、证据缺口清单、导入校验报告 | 否 |
| QA（质量保证） | 注册表/技能/产物/状态机/红线复核 | evidence-management、compute-matching、commercial-operations | `agents/`、`.dsh/skills/`、`tests/`、`docs/`、全表只读 | agent_tasks、`data/research/`、`agent_outputs/` | schema_validate、data_audit、evidence_check、csv_ingest | QA 报告、问题清单 | 否（P0 立即上报） |

### 3.1 Research Director（研究总监）

- **何时用**：一天/一周研究周期开始时；多条线索需要合并；简报结论互相冲突；证据缺口需要统一分派。
- **输入从哪来**：`PROJECT_BRIEF`（目标与红线）、`docs/handover-20261113/`（历史 18+9 线索与证据表）、当前 `demand_opportunities`/`compute_supply_resources`/`evidence_registry` 状态、前端看板 `/api/dashboard`。
- **产出到哪**：`data/research/research-plan-<YYYYMMDD>.md`、`data/research/brief-<topic>-<YYYYMMDD>.md`、`knowledge_records`；任务通过 `runner create` 进入 `agent_tasks`。
- **失败如何升级**：任务连续 BLOCKED/FAILED、证据冲突无法裁决、发现红线 → 升级 Lead/CEO；不自行改变研究结论的等级。

### 3.2 Global Demand Intelligence（全球需求情报）

- **何时用**：需要新增/更新海外需求线索；某区域（中东、东南亚、欧洲）出现新算力投资信号。
- **输入从哪来**：`docs/handover-20261113/需求侧 registry.csv` 9 条基线（ByteDance、Alibaba、Tencent、DeepSeek、HUMAIN、G42、Sea Limited、Nebius、GoTo Group）；`data/research/` 旧简报；公开官网/公告/财报/招聘页。
- **产出到哪**：`demand_opportunities`（`lead_grade` 初始 PUBLIC_LEAD，`status=LEAD`，`budget_range=UNKNOWN`）、`companies`、`evidence_registry`、需求简报。
- **失败如何升级**：来源付费墙/无法打开 → 标 MEDIUM/UNVERIFIED 并写缺口；需要联系决策人 → 交 CEO，绝不自行外联；禁止把 PUBLIC_LEAD 升级为合格客户。

### 3.3 China Supply Intelligence（中国算力供给情报）

- **何时用**：供给库需要补卡型/规模/机房信息；某供应商发布新集群或新平台。
- **输入从哪来**：18 条供给线索（7 条云厂商 + 11 条 20261112 批次）；供应商官网/公众号/公告；`compute_specifications` 已有规格。
- **产出到哪**：`compute_supply_resources`（`verified=0`、`price_indication=待确认`）、`companies`、`evidence_registry`、供给简报。
- **失败如何升级**：只能拿到规划容量 → 标注「规划/未投产」并保持 LEAD；发现历史纠错（天顿 `01396.HK`、量子湃、TArk 元舟）→ 先修正档案再写新结论；需要商务询价 → 交 CEO。

### 3.4 Supplier Verification（供应商核验）

- **何时用**：某条供给线索准备进入匹配或商机；收到供应商自述材料；需要回答「这家能不能用」。
- **输入从哪来**：`compute_supply_resources` 档案、`companies` 主体信息、公开工商/官网/公告、人工验证清单 7 问（可售卡型/规模、机房与上架周期、网络时延专线、计费与最小起订、海外签约主体、数据驻留与出口管制自述、成功介绍费接受度）。
- **产出到哪**：`supplier_verification`（25 项 `checklist_json`、8 个 boolean、`score`、`gaps`、`status`）、`evidence_registry`、核验报告；核验 VERIFIED 后才允许 `compute_supply_resources.verified=1`。
- **失败如何升级**：关键项无法取证 → 保持 IN_REVIEW/NEEDS_VERIFICATION；任一硬门槛 FAIL → REJECTED 并写原因；公司升 QUALIFIED/ACTIVE、要求供应商承诺成功费 → CEO。

### 3.5 Compute Analyst（算力分析师）

- **何时用**：需求方问「H100 与 H200 怎么比」；供应商描述「80G 显存卡」但未写型号；匹配前需要统一口径。
- **输入从哪来**：`compute_specifications`、`compute_supply_resources`、`demand_opportunities`、公开规格文档（NVIDIA/厂商官网）。
- **产出到哪**：`compute_specifications`（规范名、显存、互联、典型集群、功率、来源）、规格映射表、技术说明。
- **失败如何升级**：参数缺失且不能公开取得 → 写「未披露」，不猜；同型号冲突 → 并列标注来源并升级研究总监；涉及供应商私有参数 → 不承诺、不外推。

### 3.6 Matching Engine（匹配引擎）

- **何时用**：一批需求与供给需要初筛；匹配结果需要解释给内部决策者。
- **输入从哪来**：`demand_opportunities`（工作负载、最小规模、位置、时限）、`compute_supply_resources`（可售卡数、能力、交付）、核验/资格记录、`POST /api/match/score` 或 runner `match_compute`。
- **产出到哪**：`matching_records`（`score`、八维 `match_dimensions`、`why_match`、`why_not_match`、`risks`、`recommendation`、`status=DRAFT`）；runner JSON 产物。
- **失败如何升级**：需求字段缺失 → 先补 `demand-qualification`；后端不可用 → 用 runner 内置等价实现并在输出标 `implementation_status=UNVERIFIED`；评分接近阈值或红线冲突 → 人工复核；`REVIEWED`/`ADVANCE` 不构成对外承诺。

### 3.7 Procurement Analyst（采购分析师）

- **何时用**：需求方要求「给几个方案对比」；内部需要判断哪条供给路径最稳。
- **输入从哪来**：需求档案、2–5 个候选供给、匹配记录、核验/资格记录、公开成本结构（不写具体金额）。
- **产出到哪**：`procurement_analyses`（`options_json`、`scoring_json`、`recommendation`、`risks`、`assumptions`、`status=DRAFT`）、采购对比报告。
- **失败如何升级**：候选不足 2 个 → 退回匹配；成本只能拿到公开标价 → 用指数化区间并标「参考」；报告对外或涉及费用 → CEO 审批。

### 3.8 Cross-border Research（跨境合规研究）

- **何时用**：场景涉及数据出境、海外训练、跨境远程访问、受管制芯片或受制裁主体。
- **输入从哪来**：数据流与主体清单、`evidence_registry`、公开法规与律所解读（B-E01 中伦文章等）、供应商/需求方合规自述。
- **产出到哪**：`evidence_registry`、`data/research/risk-<subject>-<YYYYMMDD>.md`、`approvals`（`approval_type=CROSS_BORDER_RISK`）。
- **失败如何升级**：出现红线（规避出口管制、违法数据出境、受制裁主体）→ 立即 CEO_PENDING；法律定性问题 → 交 CEO 与外部律师；**任何情况下不给法律意见**。

### 3.9 Commercial Operations（商务运营）

- **何时用**：匹配已 REVIEWED/APPROVED，准备进入商机推进；需要准备披露、引荐、条款或协议材料。
- **输入从哪来**：`matching_records`（ADVANCE）、`commercial_opportunities`、`supplier_verification`/`demand_qualification`、费用模式 R1–R6、`approvals`。
- **产出到哪**：`commercial_opportunities`（阶段、模式、付费方、费用条款、冲突披露）、`quotes`（DRAFT）、`contracts_metadata`、审批包、活动留痕。
- **失败如何升级**：匹配未 REVIEWED → 退回匹配引擎；费用/双付/冲突 → CEO；对外披露、引荐、条款、签约、收款全部 CEO 执行，Agent 只准备材料。

### 3.10 Data Manager（数据管理员）

- **何时用**：每日/每周数据体检；导入 CSV 前；证据缺口需要清单；schema 与 SPEC 可能漂移。
- **输入从哪来**：`data/runtime/app.db`、`app/data/schema.sql`、`docs/07_ai_system/SPEC_DATABASE.md`、`data/import/*.csv`。
- **产出到哪**：`data/runtime/agent_outputs/`（JSON/Markdown）、`agent_tasks`、`project_activities`、`audit_logs`、证据缺口清单。
- **失败如何升级**：DB 缺失/表缺失 → 提示启动后端或 `scripts/init_db.ps1`；schema 不一致 → BLOCKED 并报 Lead/后端；导入字段不合法 → 只出报告不写库。

### 3.11 QA（质量保证）

- **何时用**：每次交付前、每次 registry/skills 变更后、每周质量抽检。
- **输入从哪来**：`agents/registry.json`、`.dsh/skills/*/SKILL.md`、`tests/test_agents_runner.py`、数据库、SPEC 文档。
- **产出到哪**：`data/research/qa-report-<YYYYMMDD>.md`、runner 产物、`agent_tasks` 问题单。
- **失败如何升级**：P0（数据损坏、状态跳级、红线动作、对外承诺）立即报 Lead/CEO；P1/P2 进问题清单并给出修复建议；不直接修改他人写入范围。

---

## 4. 确定性任务运行器（`agents/runner.py`）

### 4.1 CLI

```powershell
python -m agents.runner list [--status QUEUED] [--agent "Data Manager"] [--limit 100]
python -m agents.runner show "Supplier Verification"
python -m agents.runner create --agent "Data Manager" --type data_audit --title "每日数据体检" --priority P1
python -m agents.runner run TASK-20261116-001
python -m agents.runner run-all [--status QUEUED] [--agent "Data Manager"] [--limit 50]
python -m agents.runner validate
```

- `run`：任务 DONE → 退出码 0；BLOCKED → 3；FAILED → 4；参数/DB/任务错误 → 2。
- `validate`：registry + skills 全部通过 → 0，否则 1；DB 缺失只给 note，不判失败。
- 等价的 `python agents\runner.py ...` 也可用（脚本内部把仓库根加入 `sys.path`，以便 `import app.backend.matching`）。

### 4.2 task_type 与行为

| task_type | 执行内容 | 产物 | 状态语义 |
| --- | --- | --- | --- |
| `data_audit` | 18 表行数、需求/供给/公司等分布、非法枚举值、公司/需求/供给无证据清单、孤儿证据 | `<task_id>_data_audit.json` | 有非法项仍 DONE，但报告列出；表缺失→BLOCKED |
| `evidence_check` | 缺 url/source_title、confidence 非法或缺失、未交叉验证、缺 retrieved_at 的待补清单 | `<task_id>_evidence_check.json` | DONE（问题入清单） |
| `csv_ingest` | 读 `data/import/*.csv`，识别实体、缺列、空必填、重复主键、非法枚举；显式 `wrote_database: false` | `<task_id>_csv_ingest.json` | DONE；目录不存在→BLOCKED |
| `match_compute` | 优先 `app.backend.matching`，失败用内置 8 维等价实现；红线封顶 39；输入支持 JSON 或 `demand_id=... supply_ids=...`，仅给需求 ID 时对全部非 REJECTED 供给做只读评分；标注 `implementation_source` 与 `implementation_status` | `<task_id>_match_compute.json` | 输入无效→BLOCKED；DONE 不落 `matching_records`（`persisted=false`） |
| `report_render` | 10 节 Markdown：概览/需求漏斗/供给/匹配/核验/商机审批/证据/任务/最近活动/已知限制 | `<task_id>.md` | DONE |
| `schema_validate` | 解析 `app/data/schema.sql` 与 `SPEC_DATABASE.md` 的 ```sql 块，对比 18 表/7 索引与运行库 | `<task_id>_schema_validate.json` | 不一致→BLOCKED |

### 4.3 状态回写与审计

- 运行前：`agent_tasks.status` RUNNING，写 `started_at`；
- 运行后：DONE/BLOCKED/FAILED，写 `finished_at`、`result_summary`（≤500 字）、`output_path`、`error`；
- 尽力写 `project_activities` 与 `audit_logs`（表不存在则跳过并在结果中记录 `audit_skipped`），不因审计失败而回滚任务；
- 所有产物写入 `data/runtime/agent_outputs/`（已被 `.gitignore` 排除），JSON 内附 `output_sha256`。

### 4.4 环境变量

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `CCGS_DB_PATH` | `data/runtime/app.db` | 业务库；相对路径按仓库根解析 |
| `CCGS_AGENT_OUTPUT_DIR` | `data/runtime/agent_outputs` | runner 产物目录（自动创建） |
| `CCGS_IMPORT_DIR` | `data/import` | CSV 导入校验目录 |

---

## 5. Skills 调用顺序示例

### 5.1 需求研究工作流

```text
global-demand-research
  → evidence-management          （每条需求主张登记/分级）
  → demand-qualification         （六维核验，给资格建议）
  → runner: create --type report_render / evidence_check
  → runner: run <task_id>        （简报与缺口清单落盘）
  → Research Director 合并简报   （冲突升级 CEO）
```

规则：Lead 阶段只产出 PUBLIC_LEAD/INFERRED/POTENTIAL；没有一手证据不得升 VERIFIED；`demand_qualification` 结果需人工/CEO 复核。

### 5.2 供应商核验工作流

```text
china-compute-supply-research   （锁定 1–3 家优先对象：登甲/天顿/硅基流动）
  → gpu-spec-normalization      （卡型/显存/互联/规模统一）
  → supplier-verification       （25 项 checklist，8 boolean）
  → evidence-management         （25 项逐项取证与交叉验证）
  → cross-border-risk-screening （数据出境/出口管制/制裁/合同初筛）
  → runner: create --type evidence_check
  → runner: run <task_id>       （待补清单）
  → Supplier Verification 出报告；公司 VERIFIED/QUALIFIED 分别由核验结论与 CEO 决定
```

规则：硬门槛 A1/A4/B1/B3/D5 任一 FAIL → REJECTED；对供应商的访谈/询价必须 CEO 发起，Agent 只准备问题清单。

### 5.3 匹配到商机工作流

```text
compute-matching                （八维 0–100，红线封顶 39，matching_records=DRAFT）
  → Procurement Analyst         （2–5 方案对比，procurement_analyses=DRAFT）
  → evidence-management         （匹配/成本/风险主张补证）
  → 人工复核：matching_records REVIEWED → CEO_PENDING → APPROVED
  → commercial-operations       （商机 OPEN→DISCLOSED→…，审批包）
  → CEO：披露/引荐/条款/签约/收款
  → runner: create --type match_compute / report_render → run
```

规则：匹配分数只是候选，不是订单；`ADVANCE` 不构成对外承诺；商机阶段不得跳级；任何对外动作由 CEO 执行。

### 5.4 日常数据体检工作流

```text
Data Manager / QA：
  runner validate                    （registry + skills + DB 表/索引）
  runner create --agent "Data Manager" --type data_audit
  runner run <task_id> → data/runtime/agent_outputs/*.json
  runner create --type evidence_check → run
  runner create --type schema_validate → run
  → 有问题：QA 报告 → Lead；P0 直接 CEO
```

---

## 6. 权限边界与 CEO 审批点

### 6.1 Agent 可自主完成

- 公开信息检索与研究（`web_search`、`web_fetch`）；
- 内部写作、Markdown/CSV/JSON 产物（写入被授权的目录或表）；
- 确定性任务执行（runner 六类任务）与数据体检；
- 证据登记、分级、缺口清单；
- 内部草稿：需求/供给档案、匹配记录 DRAFT、采购分析 DRAFT、商机材料草稿、审批包草稿；
- 本地开发与测试（不 push）。

### 6.2 必须 CEO 审批（Agent 只能准备材料）

| 审批点 | 触发条件 | 落库位置 |
| --- | --- | --- |
| 对外联系 | 邮件/私信/电话/会议/访谈/询价 | `approvals`（`required_role=CEO`） |
| 报价与费用 | 任何数额、费率、费用模式对外表述；首轮报价 | `quotes` DRAFT → `approvals` |
| 披露与引荐 | 向一方披露另一方身份/需求/供给信息 | `approvals` |
| 签约/合同 | 条款清单、CA、合同签署 | `contracts_metadata` + `approvals` |
| 收款/资金 | 收款账户、资金托管（一律不做） | `approvals` |
| 供应商升级 | 公司 QUALIFIED（需 score≥70）/ACTIVE | `supplier_verification` + `approvals` |
| 需求升级 | `demand_opportunities` VERIFIED（需资格 QUALIFIED 或 CEO 手工核验） | `demand_qualification` + 审计 |
| 匹配推进 | `matching_records` REVIEWED→CEO_PENDING→APPROVED；需求 MATCHED | `matching_records` + `approvals` |
| 跨境红线 | 数据出境/出口管制/制裁/受制裁主体 | `approvals(approval_type=CROSS_BORDER_RISK)` |
| 对外发布 | 任何对外材料、公开仓库内容、对外话术 | `approvals` |
| 预算/采购 | 付费工具、数据、服务 | `approvals` |

### 6.3 绝对禁止（任何 Agent 均不得做）

- 自营机房、自购 GPU、Token 零售、转售未授权芯片；
- 规避出口管制、违法跨境数据、资金托管、加价倒卖；
- 提供法律意见或合规结论；
- 把 PUBLIC_LEAD 直接写成 VERIFIED/QUALIFIED 客户；
- 伪造容量、报价、联系人、预算、成交意向；
- 执行 `git commit/push`、修改 Secret、修改仓库权限（由人工/Lead 执行）；
- 对外发送任何未经 CEO 批准的内容。

---

## 7. 已知限制（必须如实告知使用方）

1. **runner 无 LLM**：六类任务只做统计、校验、确定性评分与模板渲染；不做语义判断、不写研究结论、不自动升级线索等级。
2. **浏览器仅限本地自测**：本机 Chrome + CDP 可用于渲染自测/截图，但不得自动登录、填表、发帖或对外联络；JS 渲染页面仍以 `web_fetch` 单页文本为主，登录墙与验证码无法处理。
3. **无付费 API**：无付费数据源、无企业工商 API、无邮件/短信/电话通道；联系人与敏感信息只能依赖公开来源或人工提供。
4. **无 MCP、无 PPTX、无 pytest**：交付以 Markdown/CSV/JSON/SQLite 为主；测试框架为 unittest。
5. **匹配 fallback 未与后端逐例对拍**：`app.backend.matching` 可用时优先其后端实现；不可用时 runner 内置等价实现标注 `UNVERIFIED`，不能当作与后端完全一致。
6. **25 项 checklist 需人工取证**：大量项目依赖供应商回复或人工访谈，Agent 只能准备问题清单与公开证据，不能代替商务沟通。
7. **单机 SQLite**：并发写入有限；多人同时跑 runner 可能竞争，当前按「单人/单任务队列」设计。
8. **数据真实性基线**：截至最近审计，供给线索 18 条、需求线索 9 条全部未核验；已核验合格供给/需求为 0，成交/回款为 0；任何产出不得隐含「已有订单/客户」。
9. **主体未设立**：对外材料必须标注「主体设立中/待确认」，不得使用未批准的对外话术。

---

## 8. 校验与测试

```powershell
# 注册表 + 技能 + （可选）数据库校验
python -m agents.runner validate

# 查看 11 个 Agent
python -m agents.runner list

# 执行队列（需要可用的业务库）
python -m agents.runner run-all

# 单元测试（临时库，不依赖 data/runtime）
python -m unittest tests.test_agents_runner -v
```

测试覆盖（23 个用例）：

- registry：UTF-8 数组、恰好 11 个、字段齐全、name 唯一、tools 在白名单、task_types 合法、无禁止性承诺；
- skills：10 个目录存在、frontmatter 五个字段、六节标题齐全、只声明真实可用工具；
- runner：`validate_all`、`list`（seed 11 条）、`show`、`create`（TEXT 主键 + 审计）、六类任务执行、`run_all`、重跑报错、CLI 五个子命令、缺库优雅报错；
- 产物：JSON/Markdown 落盘、`output_sha256`、状态回写 DONE/BLOCKED/FAILED、`project_activities`/`audit_logs` 记录。

---

## 9. 版本与维护

- 本文件版本 1.0，与 `agents/registry.json`、10 个 `SKILL.md`、`agents/runner.py` 同批交付。
- 新增 Agent/Skill/task_type 时，必须同步更新：注册表 → Skill 文件 → runner 常量（`EXPECTED_AGENTS`/`EXPECTED_SKILLS`/`TASK_TYPES`）→ 测试 → 本文档，否则 `runner validate` 与测试会失败。
- 术语、状态机、线索分级如与 `PROJECT_BRIEF`、`SPEC_DATABASE` 冲突，以两份基线文档为准，并在本文档中记录差异。
