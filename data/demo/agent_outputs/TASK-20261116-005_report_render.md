# GPU 规格归一化对照表（公开规格）

> 由 `agents/runner.py` 生成（确定性任务，无 LLM 推理、无网络请求）。

| 项目 | 值 |
|------|----|
| 生成时间 | 2026-11-16T01:00:18 |
| 任务 ID | TASK-20261116-005 |
| Agent | Compute Analyst |
| task_type | report_render |
| 数据库 | `data/runtime/app.db` |

## 1. 数据概览

| 表 | 行数 |
|----|------|
| companies | 27 |
| demand_opportunities | 9 |
| compute_supply_resources | 18 |
| compute_specifications | 10 |
| evidence_registry | 31 |
| supplier_verification | 0 |
| demand_qualification | 0 |
| matching_records | 3 |
| procurement_analyses | 0 |
| commercial_opportunities | 0 |
| quotes | 0 |
| contracts_metadata | 0 |
| agent_tasks | 11 |
| project_activities | 15 |
| knowledge_records | 6 |
| audit_logs | 15 |
| approvals | 7 |
| backup_records | 0 |

## 2. 需求漏斗

- 状态分布：LEAD=9
- 线索分级：PUBLIC_LEAD=9

## 3. 供给状态

- 状态分布：LEAD=18

## 4. 匹配候选

- 建议分布：(NULL)=3
- 记录状态：DRAFT=3

| id | demand | supply | score | recommendation | status | confidence |
|----|--------|--------|-------|----------------|--------|------------|
| MATCH-20261102-001 | DEM-20261102-009 | SUP-20261102-001 | None | None | DRAFT | LOW |
| MATCH-20261102-002 | DEM-20261102-001 | SUP-20261102-007 | None | None | DRAFT | LOW |
| MATCH-20261102-003 | DEM-20261102-005 | SUP-20261102-004 | None | None | DRAFT | LOW |

## 5. 核验覆盖

- 供应商核验：（无数据）
- 需求资格核验：（无数据）

## 6. 商机与审批

- 商机阶段：（无数据）
- 待 CEO 审批：7

## 7. 证据健康

- 证据信任度：MEDIUM=18，HIGH=13

## 8. Agent 任务

- 任务状态：DONE=7，QUEUED=3，RUNNING=1

## 9. 最近活动

| 时间 | 执行者 | 动作 | 对象 | 摘要 |
|------|--------|------|------|------|
| 2026-11-16T01:00:18 | agents.runner/Compute Analyst | agent_task.start | agent_task:TASK-20261116-005 | 开始执行任务：GPU 规格归一化对照表（公开规格） |
| 2026-11-16T01:00:18 | agents.runner/Data Manager | agent_task.finish | agent_task:TASK-20261116-010 | schema 校验：SPEC 18 表 / 运行库 18 表；问题 0 项；警告 0 项 |
| 2026-11-16T01:00:18 | agents.runner/Data Manager | agent_task.start | agent_task:TASK-20261116-010 | 开始执行任务：数据库 schema 与 SPEC 一致性校验 |
| 2026-11-16T01:00:18 | agents.runner/Cross-border Research | agent_task.finish | agent_task:TASK-20261116-008 | 证据体检：共 31 条；缺 URL/来源 0；信任度缺失或非法 0；未交叉验证 8 |
| 2026-11-16T01:00:18 | agents.runner/Cross-border Research | agent_task.start | agent_task:TASK-20261116-008 | 开始执行任务：跨境合规公开信息初筛清单 |
| 2026-11-16T01:00:18 | agents.runner/Matching Engine | agent_task.finish | agent_task:TASK-20261116-006 | 匹配评分：需求 DEM-20261102-001，供给 18 条，实现来源 app.backend.matching.score_match；最高分 35.0（supply SUP-20261102-001，REJECT） |
| 2026-11-16T01:00:18 | agents.runner/Matching Engine | agent_task.start | agent_task:TASK-20261116-006 | 开始执行任务：首条公开需求线索的确定性匹配试算 |
| 2026-11-16T01:00:18 | agents.runner/Supplier Verification | agent_task.finish | agent_task:TASK-20261116-004 | 证据体检：共 31 条；缺 URL/来源 0；信任度缺失或非法 0；未交叉验证 8 |
| 2026-11-16T01:00:18 | agents.runner/Supplier Verification | agent_task.start | agent_task:TASK-20261116-004 | 开始执行任务：三家优先供应商核验清单准备 |
| 2026-11-16T01:00:18 | agents.runner/China Supply Intelligence | agent_task.finish | agent_task:TASK-20261116-003 | 证据体检：共 31 条；缺 URL/来源 0；信任度缺失或非法 0；未交叉验证 8 |

## 10. 已知限制

- 本报告是数据库快照，不包含 LLM 研究判断、预测或对外话术。
- 种子数据与未核验线索不代表真实商机；不得直接用于对外材料。
- 分数 / 状态均为系统内部记录，对外使用须经人工复核与 CEO 审批。
