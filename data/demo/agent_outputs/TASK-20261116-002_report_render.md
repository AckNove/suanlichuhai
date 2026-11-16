# 海外需求研究简报（公开信号版）

> 由 `agents/runner.py` 生成（确定性任务，无 LLM 推理、无网络请求）。

| 项目 | 值 |
|------|----|
| 生成时间 | 2026-11-16T01:00:18 |
| 任务 ID | TASK-20261116-002 |
| Agent | Global Demand Intelligence |
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
| project_activities | 3 |
| knowledge_records | 6 |
| audit_logs | 3 |
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

- 任务状态：QUEUED=9，RUNNING=1，DONE=1

## 9. 最近活动

| 时间 | 执行者 | 动作 | 对象 | 摘要 |
|------|--------|------|------|------|
| 2026-11-16T01:00:18 | agents.runner/Global Demand Intelligence | agent_task.start | agent_task:TASK-20261116-002 | 开始执行任务：海外需求研究简报（公开信号版） |
| 2026-11-16T01:00:18 | agents.runner/Research Director | agent_task.finish | agent_task:TASK-20261116-001 | 数据体检：18 张表有数据；非法状态值 0 项；无证据实体：公司 27 / 需求 9 / 供给 18 |
| 2026-11-16T01:00:18 | agents.runner/Research Director | agent_task.start | agent_task:TASK-20261116-001 | 开始执行任务：研究线数据体检与研究计划维护 |

## 10. 已知限制

- 本报告是数据库快照，不包含 LLM 研究判断、预测或对外话术。
- 种子数据与未核验线索不代表真实商机；不得直接用于对外材料。
- 分数 / 状态均为系统内部记录，对外使用须经人工复核与 CEO 审批。
