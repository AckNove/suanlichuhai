---
name: supplier-verification
description: 供应商核验：按 25 项 checklist 核验中国算力供应商的主体、授权、容量真实性、交付能力与商务合规，产出 supplier_verification 记录与核验报告；核验只给证据结论，升级与对外一律 CEO。
version: 1.0
owner: Supplier Verification
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

# supplier-verification · 供应商核验（25 项 checklist）

> 适用场景：供给线索进入 `NEEDS_VERIFICATION`，或 CEO/Lead 要求对指定供应商（优先登甲智能、天顿数据、硅基流动）做核验时。
> 基线：`docs/00_project_audit/PROJECT_BRIEF.md` 第 7、9、10 节；`docs/07_ai_system/SPEC_DATABASE.md` supplier_verification 表；交接档案 7 问清单。

## ① 输入

| 项 | 内容 | 来源 | 前置校验 |
|----|------|------|----------|
| 待核供应商 | company_id、公司全称、品牌名、官网、关联主体 | `companies`（SUPPLIER）、`compute_supply_resources` | 主体必须已建档；同名多主体先拆清关系 |
| 公开供给档案 | 卡型/规模/机房/海外服务自述 | `compute_supply_resources`、`evidence_registry` | 无证据的字段标「待核」，不得直接采信 |
| 证据包 | 官网、公告、年报、第三方报道、客户案例（公开） | `evidence_registry`（subject_type=SUPPLY/COMPANY） | 每条核验结论必须挂 evidence_id |
| 核验授权 | 是否允许联系供应商/索要材料/视频查验 | CEO 审批记录/Lead 任务单 | 未获批只能做公开信息核验（OFFLINE 模式） |
| 既有记录 | 上次核验结果与 gaps | `supplier_verification` | 先查最新一条：REJECTED 不得无新证据重开 |

## ② 操作步骤

1. **锁定主体**：工商全称、统一社会信用代码（公开可查部分）、股权/集团关系、销售主体与资源主体是否同一；不一致必须在 `gaps` 写明。
2. **按 25 项 checklist 逐项取证**（见下表），每项输出 `PASS / PARTIAL / FAIL / UNKNOWN` + `evidence_id` + 一句话理由。
3. **公开信息核验（默认模式）**：官网/公告/年报/招投标/新闻交叉比对；公司自述一律 `UNKNOWN`，除非有第三方可核证材料。
4. **受限材料核验（需 CEO 批准）**：向供应商发送统一 7 问（可售卡型/规模、机房与上架周期、网络时延专线、计费与最小起订、海外签约主体、数据驻留与出口管制自述、成功介绍费接受度）；所有回复原文存入 `private/` 或 `data/private/`，仅结论进公开库。
5. **评分**：每项 PASS=4、PARTIAL=2、FAIL/UNKNOWN=0，满分 100；硬门槛 A1/A4/B1/B3/D5 任一 FAIL → `REJECTED`；核心项（A2/A3/B2/B4/C1/C2/D1/D2）出现 UNKNOWN 且无替代证据 → `IN_REVIEW` 不得 VERIFIED。
6. **落库**：写 `supplier_verification`（`checklist_json` 含 25 项明细、8 个 boolean 按映射回填、`score`、`gaps`、`verified_by`、`verified_at`）；更新 `companies.trust_level`（最高到 MEDIUM，VERIFIED 需证据齐全）；资源侧 `compute_supply_resources.verified` 仅在容量证据通过时置 1。
7. **状态推进**：`PENDING→IN_REVIEW→VERIFIED/REJECTED`；公司 `NEEDS_VERIFICATION→VERIFIED` 仅在核验记录 VERIFIED 后由后端/CEO 执行；`QUALIFIED`（score≥70）与 `ACTIVE` 必须 CEO 审批，Agent 只创建 `approvals` 记录并置 `CEO_PENDING`。
8. **写报告**：`data/research/verification-<company>-<YYYYMMDD>.md`，含结论、25 项表、gaps、下一步与风险；向 CEO 提交审批前的决策要点（不代替 CEO 决策）。

### 25 项 checklist（A 主体与授权 6 / B 容量真实性 7 / C 交付与运营 5 / D 商务与合规 7）

| ID | 核验项 | 判定要点 | 映射列 |
|----|--------|----------|--------|
| A1 | 工商主体真实存续 | 全称/统一社会信用代码/存续状态可核 | legal_entity_ok |
| A2 | 股权与集团关系清晰 | 与母公司/上市主体关系可核，无冒名 | legal_entity_ok |
| A3 | 销售主体与资源主体一致或获授权 | 若不一致，有授权链说明 | legal_entity_ok |
| A4 | 资源所有权或合法转售权 | 自有/合营/代理三种形态明确，转售权有依据 | resale_right_ok |
| A5 | 非排他性约束 | 是否独家/区域排他，影响我方可售性 | non_exclusive_ok |
| A6 | 海外签约主体 | 是否有境外主体/可接受的签约路径 | legal_entity_ok |
| B1 | GPU 型号与代际真实 | 型号/代际与公开信息一致，非「等值」口径 | capacity_evidence_ok |
| B2 | 显存规格 | 显存容量/类型可核（如 80GB HBM3） | capacity_evidence_ok |
| B3 | 可售规模 vs 总规模 | 区分现网/可售/规划；规划不得当可售 | capacity_evidence_ok |
| B4 | 训练/推理能力 | 集群规模、互联、拓扑支持宣称负载 | capacity_evidence_ok |
| B5 | 互联方案 | NVLink/IB/RoCE 代际与带宽可核 | capacity_evidence_ok |
| B6 | 机房位置与权属 | 城市/园区/自有或第三方托管可核 | capacity_evidence_ok |
| B7 | 交付形态 | 裸金属/实例/集群/代运营，SLA 边界 | capacity_evidence_ok |
| C1 | 上架周期 | 从确认到可用的真实周期（非营销口径） | capacity_evidence_ok |
| C2 | 网络出口与时延 | 国际出口/专线/时延数据可核 | overseas_service_ok |
| C3 | SLA 与运维支持 | 可用性承诺、故障响应、驻场能力 | overseas_service_ok |
| C4 | 计费方式与最小起订 | 计费单位、最小起订、结算币种/账期结构 | success_fee_ok |
| C5 | 扩容与库存更新机制 | 扩容周期、库存可见性、锁单规则 | capacity_evidence_ok |
| D1 | 海外服务经验 | 可核验的海外客户/节点/案例（非自述） | overseas_service_ok |
| D2 | 报价口径与公开价 | 只记录结构；具体数字进 private，不进公开库 | success_fee_ok |
| D3 | 成功介绍费接受度 | 逐案商议，不写死费率；记录态度与前提 | success_fee_ok |
| D4 | 数据驻留自述 | 数据存放地、跨境路径、删除机制（自述记录） | overseas_service_ok |
| D5 | 出口管制自述 | 是否受管制/许可状态（只记录，不下法律结论） | export_control_declared |
| D6 | 第三方核验接受度 | 是否接受视频/截图/第三方确认/审计 | capacity_evidence_ok |
| D7 | 联系人与决策链 | 姓名/职务/权限（仅存 private，公开库只记「已建立/未建立」） | capacity_evidence_ok |

## ③ 工具要求

**本项目真实可用**：`web_search`、`web_fetch`、`read`、`write`、`edit`、`python`（含 requests，可调用本地后端 API）、`sqlite3`（只读）、CSV、`git`（只读）。
**明确不可用**：浏览器自动化、MCP 连接器、付费数据库/API、邮件/电话/IM 外联、供应商后台、网络爬虫绕过登录/验证码、视频会议录制工具。
核验材料获取方式：公开来源用 web_fetch；需供应商配合的材料只能由 CEO/授权人线下获取后放入 `private/`，Agent 只读整理。

## ④ 输出

| 产出 | 路径/表 | 字段 |
|------|---------|------|
| 核验记录 | `supplier_verification` | `checklist_json`（25 项）、8 个 boolean、`score`、`gaps`、`status`、`verified_by/at` |
| 公司信任度 | `companies.trust_level/status` | trust_level 最高 MEDIUM（VERIFIED 需证据齐全且 CEO 确认）|
| 供给核验位 | `compute_supply_resources.verified/status` | 容量证据通过才置 1；状态不越级 |
| 审批 | `approvals` | `approval_type=SUPPLIER_QUALIFICATION`、`payload_json` 含 score/gaps、`status=PENDING` |
| 报告 | `data/research/verification-<company>-<YYYYMMDD>.md` | 结论/25 项表/gaps/风险/下一步 |
| 留痕 | `project_activities`、`audit_logs`、`agent_tasks.result_summary` | 状态变化与依据 |

## ⑤ 质量标准

- 25 项一项不缺；`checklist_json` 每项必须有 `status`、`evidence_id`（UNKNOWN 可空但要写原因）、`note`。
- 任何 PASS 必须有公开可打开的 URL 或 CEO 授权获取的材料编号；自述不算 PASS。
- `score` 与 25 项逐项分数可复算一致；硬门槛 FAIL 必须 `REJECTED`，不得靠总分掩盖。
- `gaps` 必须可执行（缺什么、找谁、怎么补），不得写「进一步了解」。
- 核验结论不得出现「合规」「可合法出口」等法律判断；只写「自述/未见许可文件/需律师意见」。
- 联系人、报价、合同条款不得进入公开库或报告；报告只写「已建立联系渠道/未建立」。

## ⑥ 权限边界

**可自主**：公开信息核验、25 项打分、证据登记、核验报告、`supplier_verification` 草稿与 IN_REVIEW 推进、向 CEO 提交审批包。
**必须 CEO 审批**：联系供应商、索要敏感材料、视频/实地核验、把公司状态升到 VERIFIED/QUALIFIED/ACTIVE、任何对外表述、报价与费率讨论。
**禁止**：代替 CEO 决定合格供应商、把自述当已核验、对外承诺合作/价格、泄露其他供应商信息、把联系人/报价写入公开仓库。
