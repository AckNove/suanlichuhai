---
name: demand-qualification
description: 需求资格核验：按决策人、预算、时间窗、合规、签约路径、数据驻留六维核验需求，产出 demand_qualification 记录与资格结论，只有一手核实才允许升级线索等级。
version: 1.0
owner: Compute Analyst
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

# demand-qualification · 需求资格核验

> 适用场景：需求线索从 `NEEDS_VERIFICATION` 向 `VERIFIED/QUALIFIED` 推进前，或采购方案分析前需要确认「这是不是真需求」时。
> 基线：`docs/00_project_audit/PROJECT_BRIEF.md` 线索分级（PUBLIC_LEAD→INFERRED→POTENTIAL→VERIFIED→QUALIFIED）；`demand_qualification` 表。

## ① 输入

| 项 | 内容 | 来源 | 前置校验 |
|----|------|------|----------|
| 待核需求 | demand_id、公司、负载类型、规模、时间窗、数据驻留要求 | `demand_opportunities`、`companies`（DEMANDER） | 需求已建档；`budget_range` 默认 UNKNOWN，不得先填数字 |
| 现有证据 | 需求相关公开证据、来源与信任度 | `evidence_registry`（subject_type=DEMAND/COMPANY） | 每条重大判断挂证据；无证据字段标「未证实」 |
| 既有资格记录 | 上次核验结果、gaps | `demand_qualification` | 先查最新记录；REJECTED 需新证据才能重开 |
| 核验授权 | 是否允许接触客户/转介渠道/索取需求文件 | CEO 审批或 Lead 任务单 | 未获批只能公开信息核验；不得暗示已有接触 |
| 合规初筛结果 | 跨境/出口管制/数据驻留风险点 | `cross-border-risk-screening` 输出 | 无初筛则先移交该 Skill，不得跳过 |

## ② 操作步骤

1. **六维逐项判定**：对 `decision_maker_confirmed / budget_confirmed / timeline_confirmed / compliance_screened / contracting_path_confirmed / data_residency_ok` 各输出 `PASS / PARTIAL / FAIL / UNKNOWN` + 依据 + evidence_id。
2. **判真伪**：区分「公开信号」（招聘、融资、扩产、公开招标）与「已确认需求」；公开信号最多支持 `POTENTIAL`，不得写 `VERIFIED`。
3. **决策人核验**：只有可核实的岗位/姓名/沟通记录才算 PASS；仅媒体引用「某负责人」为 PARTIAL，未提及为 UNKNOWN。
4. **预算核验**：`budget_confirmed` 仅在客户书面/口头明确预算区间或采购计划时 PASS；公开报道的「投资额」不等于采购预算，最多 PARTIAL 并注明口径。
5. **时间窗核验**：明确上线/招标/签约时间点 PASS；「计划 2026 年」类模糊表述 PARTIAL；无信息 UNKNOWN。
6. **签约路径核验**：明确签约主体、合同类型、采购流程（直签/招标/代理）PASS；只知「通过某云厂商采购」为 PARTIAL。
7. **数据驻留与合规**：数据存放地、是否出境、数据类型、客户合规要求四项齐全 PASS；涉及中国境内处理境外数据或反之，必须移交 `cross-border-risk-screening`，本 Skill 只记录事实不下法律结论。
8. **评分与结论**：六项 PASS=满分（决策人 25、预算 25、时间窗 15、合规 20、签约路径 15，数据驻留作为硬门槛）；`score` 0–100；硬门槛：决策人 + 签约路径任一非 PASS → 不得 QUALIFIED；合规或数据驻留 FAIL → `REJECTED`。
9. **落库**：写 `demand_qualification`（六列、`score`、`gaps`、`qualified_by/at`、`status`）；`status` 仅 PENDING→IN_REVIEW→QUALIFIED/REJECTED；需求 `lead_grade` 与 `status` 的升级由后端规则/CEO 执行，Agent 不越级。
10. **写核验备忘录**：`data/research/demand-qual-<demand>-<YYYYMMDD>.md`；给 CEO/Lead 明确「可推进 / 需补信息 / 建议放弃」三选一建议及理由。

异常与升级：必需信息缺失 → `IN_REVIEW` + `gaps` 列明缺什么、从哪获取、谁可获取；客户要求保密 → 只记录「已确认/未确认」，敏感细节进 `private/`；发现疑似骗局/空壳 → 标 `REJECTED` 并写明依据，报 Lead。

## ③ 工具要求

**本项目真实可用**：`web_search`、`web_fetch`、`read`、`write`、`edit`、`python`（含 requests，可调用本地后端 API）、`sqlite3`（只读）、CSV、`git`（只读）。
**明确不可用**：浏览器自动化、MCP、付费 API/付费企业库、邮件/电话/IM 外联、自动拨号、CRM 登录、验证码绕过。
客户侧材料只能经 CEO/授权人获取后进入 `private/`；Agent 只读整理，不直接对外沟通。

## ④ 输出

| 产出 | 路径/表 | 字段 |
|------|---------|------|
| 资格记录 | `demand_qualification` | 6 个 boolean、`score`、`gaps`、`status`、`qualified_by/at`、`notes` |
| 需求更新建议 | `demand_opportunities.lead_grade/status` | 只提交建议（VERIFIED 需一手核实或 CEO 手工核验）|
| 合规初筛联动 | `demand_opportunities.compliance_notes` | 记录初筛结论与待律师确认项 |
| 证据 | `evidence_registry` | `subject_type=DEMAND`，每条判断可追溯 |
| 备忘录 | `data/research/demand-qual-<demand>-<YYYYMMDD>.md` | 六维表/gaps/三选一建议 |
| 留痕 | `project_activities`、`audit_logs`、`agent_tasks.result_summary` | 状态变化与依据 |

## ⑤ 质量标准

- 六维判定必须有依据；UNKNOWN 不得当成 PASS，也不得静默省略。
- `budget_confirmed=1` 必须有明确预算/采购计划来源；媒体投资额不算。
- 未经一手核实，`lead_grade` 最高 `POTENTIAL`；严禁把 `PUBLIC_LEAD` 直接写成 `QUALIFIED`。
- 合规结论只写「已初筛，待律师/CEO 确认」，不得写「合规」「可执行」。
- `gaps` 可执行：缺什么、找谁、何时前补；不得写「继续跟进」。
- 备忘录不得包含客户联系人隐私、报价、未授权信息。

## ⑥ 权限边界

**可自主**：公开信息核验、六维打分、资格记录草稿/IN_REVIEW、合规初筛转介、内部备忘录、向 CEO/Lead 提交建议。
**必须 CEO 审批**：接触客户/需求方、索取预算与采购文件、承诺响应时间、把需求升级到 VERIFIED/QUALIFIED/MATCHED、任何对外表述。
**禁止**：编造决策人/预算/时间窗、代替客户确认需求、跳过合规初筛、对外承诺能力或价格、把未证实信息写成已确认。
