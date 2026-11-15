---
name: global-demand-research
description: 海外 AI 算力需求发现与研究：从公开信号定位目标区域/客群的算力需求，产出带证据链的结构化需求线索与《需求研究简报》，不接触客户、不升级线索等级。
version: 1.0
owner: Global Demand Intelligence
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

# global-demand-research · 海外需求发现与研究

> 适用场景：需要回答「哪个区域/哪类客户缺什么算力」并为 `demand_opportunities` 增加新线索时。
> 基线：`docs/00_project_audit/PROJECT_BRIEF.md` 第 2、8、10 节；`docs/07_ai_system/SPEC_DATABASE.md` 第 1、2 节。

## ① 输入

| 项 | 内容 | 来源 | 前置校验 |
|----|------|------|----------|
| 研究范围 | 目标区域（国家/城市）、工作负载（TRAINING/FINETUNE/INFERENCE/RENDERING/SIMULATION/MIXED）、时间窗 | CEO 或 Lead 的研究任务单（`agent_tasks.title/input_ref`） | 范围不得为空；不得以「全球」为单一范围启动，必须拆区域 |
| 已有线索 | 需求线索清单、负责人、区域、状态 | `demand_opportunities`、`companies`（company_type=DEMANDER） | 先查重：公司名/主体英文名/域名重复则不新建，走补充证据 |
| 历史研究 | 东南亚/中东/欧美的既有结论与缺口 | `docs/handover-20261113/`、`docs/05_research/`、`data/research/*.csv` | 引用历史结论必须标注来源路径；过期信息标「待复核」 |
| 证据规则 | 每条主张的来源/发布时间/信任度要求 | `docs/00_project_audit/PROJECT_BRIEF.md` 第 10 节 | 无来源的主张不得写入表 |
| 公开线索基线 | 现有 9 条需求线索（ByteDance、Alibaba、Tencent、DeepSeek、HUMAIN、G42、Sea Limited、Nebius、GoTo Group） | 交接档案 | 这些线索**全部未核验**，仅作研究起点 |

## ② 操作步骤

1. **拆研究问题**：写清区域 × 负载类型 × 规模区间（GPU 张数/集群 MW）× 时间窗四要素；每个组合一条研究假设。
2. **检索公开信号**（只用 `web_search` / `web_fetch`）：招标公告、政府采购、公司官网/财报、行业媒体、会议议程、云厂商区域公告、IDC 与智算园区新闻；记录 URL、发布者、发布时间、获取时间。
3. **信号分级**：区分「需求事实」（签约/采购/招标）与「需求推断」（扩产、融资、招聘、区域布局）；推断必须标 `INFERRED`。
4. **结构化落档**：按 `demand_opportunities` 字段填写 `company_id/title/workload_type/gpu_models/min_gpu_count/max_gpu_count/duration_months/cluster_requirements/network_requirements/location_preference/data_residency/timeline/budget_range(默认 UNKNOWN)/decision_maker(未证实留空)`；`lead_grade` 初始只能是 `PUBLIC_LEAD`；`status=LEAD`。
5. **证据登记**：每条关键主张写入 `evidence_registry`（`subject_type=DEMAND`，`subject_id=<demand_id>`），并将证据 ID 回填 `evidence_ids`；≥2 个独立来源才可置 `cross_verified=1`。
6. **写研究简报**：`data/research/demand-<区域>-<YYYYMMDD>.md` + 同结构 CSV；含结论、证据表、不确定性、下一步建议（下一步只写「建议 CEO 核实/授权接触」，不得写已接触）。
7. **提交复核**：向 Lead 报告新增条数、分级分布、缺口；不自行提交 CEO 接触申请以外的外部动作。

异常与升级：检索受限（付费墙/403）→ 在简报写明「一手不可得」并按二手来源降级；无法判断区域合规风险 → 移交 `cross-border-risk-screening`；发现疑似真实采购需求 → 只报 Lead，不联系。

## ③ 工具要求

**本项目真实可用**：`web_search`、`web_fetch`、`read`、`write`、`edit`、`python`（含 requests/urllib，可调用本地后端 API `127.0.0.1:8770`）、`sqlite3`（只读查询）、CSV、`git`（只读 log/diff/show）。
**明确不可用**：浏览器自动化（Playwright/Selenium）、MCP 连接器、付费数据 API、邮件/私信发送、自动拨号、付费数据库订阅、验证码绕过。
写库方式：优先 `python` 调用本地后端 `POST/PATCH /api/demands`、`/api/evidence`（审计留痕）；不要直连 sqlite3 写业务表。

## ④ 输出

| 产出 | 路径/表 | 字段 |
|------|---------|------|
| 需求线索 | `demand_opportunities` | 全部字段，`lead_grade=PUBLIC_LEAD/INFERRED`，`status=LEAD` |
| 证据 | `evidence_registry` | `subject_type=DEMAND`、`claim`、`url`、`publisher`、`published_at`、`retrieved_at`、`confidence`、`cross_verified` |
| 研究简报 | `data/research/demand-<region>-<YYYYMMDD>.md` | 结论 / 证据表 / 不确定性 / 下一步 |
| 结构化数据 | `data/research/demand-<region>-<YYYYMMDD>.csv` | 一行一需求，含 evidence_ids |
| 任务留痕 | `agent_tasks.result_summary`、`project_activities` | 摘要 + 计数 |

## ⑤ 质量标准

- 每条主张必须能在 `evidence_registry` 找到对应记录；无证据的数字（容量、预算、客户意向）不得出现。
- `lead_grade` 不得高于实际核实程度：无一手核实不得写 `VERIFIED`/`QUALIFIED`；不得把 `PUBLIC_LEAD` 升级为合格客户。
- 来源必须至少包含 URL + 发布者 + 获取时间；`published_at` 未知写「未标注」。
- 声明与推断分开：简报中「事实 / 判断 / 建议 / 待确认」四类标签齐全。
- 同一公司不重复建档；重复线索合并到既有 ID 并在 `notes` 记录合并原因。
- 研究简报不含任何未批准对外话术，不含联系人手机号/邮箱。

## ⑥ 权限边界

**可自主**：公开信息检索与阅读、结构化建档（仅 PUBLIC_LEAD/INFERRED）、证据登记、内部简报写作、本地 CSV/Markdown 产出、向 Lead 汇报。
**必须 CEO 审批**：对外联系/邮件/私信、提交报价、签署任何文件、对外发布研究结论、购买付费数据源、跨境数据传输。
**禁止**：捏造客户意向/预算/决策人、把公开线索写成已签约、使用未批准话术外发、绕过 `data/private/` 规则保存联系人、直接修改业务库状态机。
