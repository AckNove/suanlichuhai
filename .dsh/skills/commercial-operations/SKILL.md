---
name: commercial-operations
description: 商务运营：把已核验的匹配推进为商机，准备披露/引荐/条款/协议材料与 CEO 审批包，维护商机阶段与活动留痕；不对外联系、不报价、不签约、不收款。
version: 1.0
owner: Commercial Operations
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

# commercial-operations · 商务运营（商机推进/审批/协议准备）

> 适用场景：匹配结论为 ADVANCE 且需求/供给均已核验，需要建立商机、准备双方披露与引荐材料、走 CEO 审批时。
> 基线：PROJECT_BRIEF 第 6/8/9 节（6 类费用 R1–R6、双付披露、无资金托管）；`commercial_opportunities`、`quotes`、`contracts_metadata`、`approvals` 表。

## ① 输入

| 项 | 内容 | 来源 | 前置校验 |
|----|------|------|----------|
| 匹配结论 | match_id、ADVANCE、REVIEWED | `matching_records` | 非 ADVANCE/未 REVIEWED 不得建商机 |
| 双方状态 | 需求 VERIFIED+、供给 VERIFIED+ | `demand_opportunities`、`companies`/`compute_supply_resources` | 未核验不得进入对外披露 |
| 风险初筛 | 跨境/合规/数据驻留结论 | `cross-border-risk-screening` | 红线未排除不得推进 |
| 费用模式 | 6 类费用中拟采用的结构（R1–R6）、付费方、计费基础 | CEO 指示/商务策略 | 不写死费率；数字只进 `private/` |
| 审批与授权 | 当前可做的动作边界 | `approvals`、CEO 指示 | 无审批不得对外 |

## ② 操作步骤

1. **建商机**：`commercial_opportunities` 填 `demand_id/supply_id/match_id/title/stage=OPEN/model_type(ADVISORY/INTRO/CHANNEL/JOINT/PMC)/fee_payer/fee_basis/fee_terms(仅结构描述)/conflict_disclosed=0/ceo_approval_status=PENDING/next_step/owner`。
2. **利益冲突与双付披露**：核对是否存在双方收费、关联方、排他约束；在 `fee_terms` 写「拟双方收费，须事前书面披露」等结构条款；`conflict_disclosed=1` 仅在披露文本已获 CEO 批准后设置。
3. **分阶段推进**（严格遵守）：`OPEN → DISCLOSED → INTRODUCED → TERM_SHEET → CA → CLOSED_WON/CLOSED_LOST`；每步只做本阶段允许的内部材料，不跳级。
   - OPEN：内部立项、双方画像、价值假设、风险清单。
   - DISCLOSED：拟披露内容（脱敏）、双方披露同意书草案、披露范围清单（待 CEO 批准）。
   - INTRODUCED：引荐包（双方一页纸）、会议议程、问答准备；引荐动作由 CEO 执行。
   - TERM_SHEET：条款清单草案（服务范围、费用结构、双方责任、退出），标「草案·非报价」。
   - CA：协议准备清单、签约主体核验、用印流程、交付物清单；协议文本由律师/CEO 定稿。
4. **审批包**：写 `approvals`（`approval_type` 按动作：DISCLOSURE/INTRODUCTION/FEE_TERMS/CONTRACT/PAYMENT；`subject`、`payload_json` 含动作、对象、披露范围、费用结构、风险与建议；`required_role=CEO`），把商机 `ceo_approval_status` 置 PENDING。
5. **报价纪律**：`quotes` 只建 `DRAFT`（结构化：quote_type/currency/terms/valid_until），`amount` 未经 CEO 不得填写真实数字；首轮不报价；不得写「10%/8%」等固定费率。
6. **资金与合同边界**：不托管资金、不加价、不代收代付；`contracts_metadata` 只登记元数据（合同类型、对手方、条款清单引用、签署状态），不代拟法律条款。
7. **活动留痕**：每次推进写 `project_activities`（actor、action、entity、summary）与 `audit_logs`（before/after）；外部动作须记录「CEO 执行 + 时间 + 渠道」。
8. **复盘**：阶段停滞 >14 天写停滞原因与下一步；CLOSED_LOST 必须写失败原因（价格/信任/合规/竞争/无预算），沉淀到 `knowledge_records`。

异常与升级：对方要求直接报价 → 报 CEO，不口头承诺；发现利益冲突 → 立即暂停并报 CEO；合同条款超授权 → 退回律师/CEO；任何付款请求 → 转 CEO 与财务流程，Agent 不处理资金。

## ③ 工具要求

**本项目真实可用**：`web_search`、`web_fetch`（公开尽调）、`read`、`write`、`edit`、`python`（调用本地后端 API、生成审批包）、`sqlite3`（只读）、CSV、`git`（只读）。
**明确不可用**：浏览器自动化、MCP、邮件/私信/电话外联、电子签平台、支付/收款、CRM 商业系统、合同生成 SaaS。
所有对外动作（披露、引荐、报价、签约、收款）只能由 CEO 执行；Agent 只准备材料与记录。

## ④ 输出

| 产出 | 路径/表 | 字段 |
|------|---------|------|
| 商机 | `commercial_opportunities` | 全部字段，`stage` 按序推进，`ceo_approval_status=PENDING` |
| 报价草稿 | `quotes` | `status=DRAFT`，`amount` 未经批准不填 |
| 合同元数据 | `contracts_metadata` | 类型/对手方/条款引用/签署状态 |
| 审批 | `approvals` | `payload_json` 含动作/范围/费用结构/风险 |
| 商务材料 | `data/research/commercial-<opp>-<YYYYMMDD>.md` | 立项/披露/引荐/条款包（按阶段） |
| 留痕 | `project_activities`、`audit_logs`、`agent_tasks.result_summary` | 阶段变化与依据 |

## ⑤ 质量标准

- 阶段不跳级：无 DISCLOSED 记录不得 INTRODUCED；无 TERM_SHEET 不得 CA；WON/LOST 仅 CEO。
- 每阶段有对应审批记录或 CEO 指示编号；`ceo_approval_status` 与实际审批一致。
- 费用结构只写模式（R1–R6）+ 付费方 + 计费基础，不写固定费率、不写具体金额（除非 CEO 批准的 private 材料）。
- 双付/关联/排他必须在推进前披露；`conflict_disclosed=0` 不得进入 INTRODUCED。
- 商务材料不含未脱敏联系人、报价、合同全文；对外版与内部版分开存放。
- 活动日志完整可回溯：谁、何时、做了什么、依据哪条审批。

## ⑥ 权限边界

**可自主**：商机建档、阶段内材料准备、审批包起草、内部复盘、活动留痕、向 CEO 提交建议。
**必须 CEO 审批**：披露双方信息、引荐、报价、费用条款、合同签署、收款、付款、任何对外承诺。
**禁止**：联系客户/供应商、发送任何对外材料、口头报价、承诺成交/容量/价格、托管或代收资金、写死费率、代替律师拟条款、把商机写成已成交。
