---
name: procurement-analysis
description: 采购方案分析与报告：为需求方比较 2–5 个算力采购/租用方案（规格、交付、成本结构、合规、合同、退出），产出 procurement_analyses 记录与结构化对比报告，不报价、不替代客户决策。
version: 1.0
owner: Procurement Analyst
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

# procurement-analysis · 采购方案分析与报告

> 适用场景：需求已核验且存在 2 个以上可行供给方案，需要给客户/CEO 做内部决策材料时（C 线全球算力采购、A 线供给出海均适用）。
> 基线：`PRODUCT_SERVICE_CATALOG` D-05 方案比较；`docs/07_ai_system/SPEC_DATABASE.md` procurement_analyses；PROJECT_BRIEF 报价纪律（首轮不报价、逐案商议）。

## ① 输入

| 项 | 内容 | 来源 | 前置校验 |
|----|------|------|----------|
| 需求 | demand_id、规格/规模/时长/地点/驻留/预算口径 | `demand_opportunities`（VERIFIED 及以上） | 未核验需求只做「假设性方案比较」，结论标 DRAFT |
| 候选方案 | 2–5 个 supply/组合（自有+外部、单区域+多区域） | `matching_records`（REVIEWED 优先）、`compute_supply_resources` | 每个方案必须有对应 supply_id 与证据 |
| 规格口径 | 规范卡型、可比性说明 | `compute_specifications`、`gpu-spec-normalization` 输出 | 口径不一致先标准化再比较 |
| 成本信息 | 公开价目/结构性报价口径（非最终报价） | 公开价目、CEO 授权获取的材料 | 数字只进 `private/`；公开报告写「结构」不写金额 |
| 风险初筛 | 跨境/出口管制/数据驻留 | `cross-border-risk-screening` | 未初筛不得给 ADVANCE |

## ② 操作步骤

1. **定义评估维度与权重**：7 维——规格匹配 25、交付可行性 20、成本结构 20（只看计价模式与量级口径，不含对外报价）、合规与数据驻留 15、合同与退出 10、运维与 SLA 5、合作稳定性 5；权重在报告开头明示，可做敏感性分析。
2. **方案定义**：每方案写清供给侧、卡型/规模、地点、交付形态、时长、计价模式、关键假设；方案之间必须可区分（避免同质重复）。
3. **逐维打分**：0–5 分制换算为加权分；每维必须写理由与依据（证据 ID）；缺失信息按「未知」给中性分并在 `assumptions` 注明。
4. **成本结构分析**：按「按卡时/按节点/包年包月/预留+突发/代运营」分类，比较计价模式对需求方现金流与弹性的影响；金额仅用区间/指数化（如「方案 B 单价量级高于 A 约 15–25%」），并注明私下核价前不得外发。
5. **合规与合同**：跨境路径、数据驻留、出口管制自述、SLA 罚则、锁定期、扩容条款、终止与迁移成本；合规结论只写「已初筛/需律师意见」。
6. **推荐与分级**：输出 `ADVANCE / NEED_MORE_INFO / REJECT`；ADVANCE 必须同时满足「无红线 + 规格匹配 ≥20/25 + 成本结构可接受」；给出首选与备选，说明触发切换条件。
7. **落库**：写 `procurement_analyses`（`options_json` 数组、`scoring_json` 含权重与逐维分、`recommendation`、`risks`、`assumptions`、`status=DRAFT`、`analyst`）。
8. **报告**：`data/research/procurement-<demand>-<YYYYMMDD>.md`（含执行摘要、方案表、评分表、敏感性、风险、假设、下一步）+ 同名 CSV 评分明细；报告页脚标注「内部研判，非报价，非承诺，主体设立中」。
9. **复核**：交 Lead 复核后 status 可升 REVIEWED；对客户输出与任何商务动作须 CEO 审批。

异常与升级：候选不足 2 个 → 输出单方案 + 缺口清单，移交 `compute-matching`/供给研究；关键信息缺失（如交付周期未知）→ 该方案标 `NEED_MORE_INFO`，不得拍脑袋；发现红线 → 方案直接 REJECT 并写明，不得进入推荐。

## ③ 工具要求

**本项目真实可用**：`web_search`、`web_fetch`、`read`、`write`、`edit`、`python`（计算加权分、生成 CSV、调用本地后端 API）、`sqlite3`（只读）、CSV、`git`（只读）。
**明确不可用**：浏览器自动化、MCP、付费 API/付费行情、邮件/IM 外联、自动报价、财务模型 SaaS、外部 ERP。
成本数字与真实报价只能来自 CEO 授权材料，存放 `private/`；公开库只保留指数化口径。

## ④ 输出

| 产出 | 路径/表 | 字段 |
|------|---------|------|
| 分析记录 | `procurement_analyses` | `options_json`、`scoring_json`、`recommendation`、`risks`、`assumptions`、`status=DRAFT` |
| 报告 | `data/research/procurement-<demand>-<YYYYMMDD>.md` | 摘要/方案/评分/敏感性/风险/假设 |
| 评分明细 | `data/research/procurement-<demand>-<YYYYMMDD>.csv` | 方案 × 维度 × 分数 × 理由 |
| 证据 | `evidence_registry` | `subject_type=CLAIM/MATCH`，支撑关键判断 |
| 留痕 | `agent_tasks.result_summary`、`project_activities` | 方案数、推荐结果 |

## ⑤ 质量标准

- 方案 2–5 个且可区分；每个方案可追溯到 supply_id 与证据；单一方案必须说明原因。
- 权重公开、逐维可复算，总分 = 加权和；敏感性分析至少给「成本权重 ±10」与「合规从紧」两种情景。
- 公开报告不得出现具体报价数字/毛利率/佣金；只能写计价模式与指数化区间，并标「内部研判」。
- 推荐结论必须与红线规则一致：有红线不得 ADVANCE；NEED_MORE_INFO 必须列明缺什么。
- 假设清单可检验（「假设 2026Q2 前可交付」而非「假设顺利」）。
- 报告不得出现「保证最低价」「保证拿卡」等承诺性表述。

## ⑥ 权限边界

**可自主**：内部方案比较、评分、敏感性分析、报告撰写、DRAFT 记录、向 Lead/CEO 提交建议。
**必须 CEO 审批**：向客户/供应商披露方案或价格、正式报价、承诺交付/容量、商务谈判、对外发送报告、采购任何付费数据。
**禁止**：报价或写死费率、承诺成本优势、替客户做采购决定、公开真实报价与合同条款、把假设当事实、泄露其他客户/供应商信息。
