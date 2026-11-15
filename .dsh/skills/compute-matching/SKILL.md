---
name: compute-matching
description: 供需匹配：按 8 维确定性评分（GPU 型号 30/规模 20/负载 15/位置 10/交付 10/网络 5/合规 5/信任 5）生成可解释匹配记录，红线封顶 39 分；匹配只是候选，一律不外发。
version: 1.0
owner: Matching Engine
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

# compute-matching · 供需匹配（维度评分与解释）

> 适用场景：有已研究的需求与供给候选，需要产出可解释的匹配候选与推荐结论时。
> 基线：`docs/07_ai_system/SPEC_API.md` POST /api/match/run 与 /api/match/score；`matching_records` 表；PROJECT_BRIEF 第 4 节匹配纪律。

## ① 输入

| 项 | 内容 | 来源 | 前置校验 |
|----|------|------|----------|
| 需求 | demand_id、GPU 型号/数量、负载类型、地点偏好、时限、数据驻留、合规要求 | `demand_opportunities` | 关键字段缺失要标 UNKNOWN 并在结论说明；不得自行假设 |
| 供给候选 | supply_id 列表、卡型、可售数量、位置、能力、交付、合规自述、状态 | `compute_supply_resources`、`companies` | 优先取 `verified=1`；未核验供给必须降权并标注 |
| 规格口径 | 规范卡型与可比性 | `compute_specifications` | 口径冲突先走 `gpu-spec-normalization` |
| 资格状态 | 需求/供给核验进度 | `demand_qualification`、`supplier_verification` | 未核验不阻止「技术匹配」，但结论必须标 NEED_MORE_INFO 或低置信 |
| 红线事实 | 无合法转售权、未筛查跨境合规、数据驻留冲突 | 核验记录/合规初筛 | 任一命中，`why_not_match` 必须写明 |

## ② 操作步骤

1. **确定候选集**：按需求选择 1–10 个供给（可全量批量）；每条记录 `demand_id/supply_id` 唯一。
2. **调用确定性评分**：优先 `python` 调 `POST /api/match/score`（不落库试算）或直接调用 `agents.runner` 的 `match_compute`（离线等价实现，输出必须标 `implementation_source`）；不得手改分数。
3. **八维评分（合计 100）**：gpu_model 30（精确 30/同代兼容 20/可替代 10/不兼容 0）、scale 20（`sellable_gpu_count>=min` 满分，每缺 10% 扣 2，未知 5）、workload 15（训练看 training_capable、推理看 inference_capable，不满足 0）、location 10（国家 10/区域 6/未知 4）、delivery 10（≤需求时限 10/未知 5/超期 0）、network 5（有描述 5/未知 2）、compliance 5（已筛查 5/未筛查 2/红线 0）、trust 5（VERIFIED 5/NEEDS_VERIFICATION 3/LEAD 1）。
4. **红线封顶**：命中「无合法转售权 / 未筛查跨境合规 / 数据驻留冲突」任一，总分最高 39 且 `why_not_match` 必须包含风险说明；`recommendation` 不得 ADVANCE。
5. **生成解释**：`why_match`（≥2 条硬理由 + 分数构成）、`why_not_match`（缺口与风险）、`risks`（商务/合规/交付）、`confidence`（LOW/MEDIUM/HIGH，取决于两侧核验程度）。
6. **落库**：写 `matching_records`（`score`、`match_dimensions` JSON `{dim:{score,max,reason}}`、`recommendation`、`status=DRAFT`、`analyst`）；不得写 `MATCHED` 需求状态。
7. **复核**：ADVANCE 的匹配交 Lead 复核后 `status=REVIEWED`；对外的 `CEO_PENDING/APPROVED` 与需求 `MATCHED` 只能由 CEO/后端推进。
8. **产出对比**：`data/research/matches-<demand>-<YYYYMMDD>.csv` + Markdown 摘要（候选排名、维度差异、待补信息），报告中注明「技术匹配候选，非订单、非承诺」。

异常与升级：无候选满足硬约束 → 输出 `REJECT` 并给「缺口清单」（卡型/规模/区域/时限），移交研究侧补供给；评分与实际直觉冲突 → 检查输入字段（尤其可售量与交付周期），不得手调；两侧状态未核验 → 结论一律 NEED_MORE_INFO。

## ③ 工具要求

**本项目真实可用**：`web_search`、`web_fetch`、`read`、`write`、`edit`、`python`（调用本地后端 API `POST /api/match/run|score`，或运行 `python -m agents.runner run <task_id>`）、`sqlite3`（只读）、CSV、`git`（只读）。
**明确不可用**：浏览器自动化、MCP、付费 API、外部 GPU 性能实测、邮件/IM 外联、自动报价。
若 `app.backend.matching` 不可导入，用 runner 内置等价实现并标注来源；禁止两种实现混用后不标注。

## ④ 输出

| 产出 | 路径/表 | 字段 |
|------|---------|------|
| 匹配记录 | `matching_records` | `score`、`match_dimensions`(JSON)、`why_match`、`why_not_match`、`risks`、`confidence`、`recommendation`、`status=DRAFT` |
| 试算结果 | API 响应/`agent_outputs/<task_id>.json` | 含 `implementation_source` |
| 对比材料 | `data/research/matches-<demand>-<YYYYMMDD>.csv/.md` | 排名、维度差异、待补信息 |
| 任务留痕 | `agent_tasks.result_summary`、`project_activities` | 候选数、ADVANCE 数、红线数 |

## ⑤ 质量标准

- 分数必须可由八维明细复算；`match_dimensions` 每维含 `score/max/reason`。
- 红线命中时总分 ≤39，且 `why_not_match` 含风险条目；不得出现红线 + ADVANCE。
- 未核验供给/需求 → `confidence` 不得 HIGH；`ADVANCE` 需两侧至少 `NEEDS_VERIFICATION` 且关键字段齐全。
- 结论术语统一：ADVANCE / NEED_MORE_INFO / REJECT；不得写「已成交」「已锁定」「客户已同意」。
- 同一 (demand_id, supply_id) 不重复建 DRAFT；重跑更新原记录并在 `notes` 记原因。
- 报告必须声明「匹配为技术候选，商务与合规需 CEO 决策」。

## ⑥ 权限边界

**可自主**：评分试算、匹配记录 DRAFT、解释与对比材料、向 Lead 提交复核、给研究侧列缺口。
**必须 CEO 审批**：把匹配转为对外推荐、接触供需双方、披露对方身份、承诺价格/容量/交付、把需求推进到 MATCHED/COMMERCIAL。
**禁止**：泄漏供需双方敏感信息、编造可售量/交付周期、绕过红线规则、直接对外发送匹配结果、代替 CEO 拍板 ADVANCE。
