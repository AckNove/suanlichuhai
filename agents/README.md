# CCGS Agents · 能力边界与运行方式

> 本目录是「中国算力国际化项目」（CCGS）的 Agent 注册表与确定性任务运行器。
> 配套文档：`docs/07_ai_system/AGENT_SKILLS_SPEC.md`（Agent × Skill × 工具 × 数据 × 产物 × 权限矩阵）。

## 1. Agent 不是「只有提示词」

一个 Agent 的真实能力 = **注册表声明的工具** ∩ **runner 可执行的确定性任务** ∩ **对应 Skill 流程**。三者缺一，能力即不成立：

| 组成 | 文件 | 作用 | 缺失后果 |
|------|------|------|----------|
| 角色注册 | `agents/registry.json` | 声明 11 个 Agent 的职责、输入、真实工具、Skill、产物、读写范围、审批要求、可执行 task_type | 无法审计「它能做什么、不能做什么」 |
| Skill 流程 | `.dsh/skills/<name>/SKILL.md` | 每项能力的输入校验、编号步骤、工具要求、输出字段、质量标准、权限边界 | Agent 只有一句描述，无法复现执行 |
| 确定性任务 | `agents/runner.py` | 6 类无需 LLM 的任务：数据体检、证据缺口、CSV 校验、匹配评分、报告渲染、schema 校验；负责产物落盘与状态回写 | 无法自动产出可验收产物，只能人工操作 |
| LLM 推理 | DSH Agent 会话 | 研究判断、写作、方案比较、风险识别等需要语言推理的工作 | runner 不做推理、不联网、不写业务数据 |

**分工原则**：
- **LLM（DSH Agent 会话）** 承担研究、分析、写作、判断与工具编排，按 Skill 的六节流程执行。
- **runner（Python 3.9 stdlib）** 只承担确定性、可重复、可校验的任务：读库统计、评分计算、格式化输出、落盘与状态回写。
- **runner 不执行任何外部网络请求、不发消息、不改业务数据**；它只读业务表，写自己的 `agent_tasks` 状态与 `data/runtime/agent_outputs/` 产物（该目录已被 `.gitignore` 忽略）。

## 2. 运行方式

```powershell
# 0. 先准备数据库（二选一）
#    a) 启动后端自动建表 + 种子：python -m app.backend.server
#    b) 运行 scripts/init_db.ps1

# 1. 校验注册表 + Skills 完整性（不依赖 DB）
python -m agents.runner validate

# 2. 查看 Agent / 任务
python -m agents.runner list
python -m agents.runner show "Matching Engine"

# 3. 创建并运行确定性任务
python -m agents.runner create --agent "Data Manager" --type data_audit --title "全库数据体检"
python -m agents.runner run 1

# 4. 批量运行 QUEUED 任务
python -m agents.runner run-all --status QUEUED
```

- 数据库路径：环境变量 `CCGS_DB_PATH`，默认 `data/runtime/app.db`。不存在时 runner 会优雅报错，提示先启动后端或运行初始化脚本。
- 产物目录：`data/runtime/agent_outputs/`（JSON/Markdown，运行时生成，不入仓）。
- 状态流转：`agent_tasks` 中 `QUEUED → RUNNING → DONE / BLOCKED / FAILED`，写 `started_at/finished_at/result_summary/output_path`；同时尽力写 `project_activities` 与 `audit_logs`（表不存在则跳过并在结果中记录）。

## 3. task_type（确定性任务）

| task_type | 作用 | 产物 | 写库 |
|-----------|------|------|------|
| `data_audit` | 各表行数、线索分级/状态分布、非法状态值、无证据实体清单 | `<task_id>_data_audit.json` | 只写任务状态/留痕 |
| `evidence_check` | url 为空、信任度缺失、未交叉验证的证据待补清单 | `<task_id>_evidence_check.json` | 只写任务状态/留痕 |
| `csv_ingest` | 校验 `data/import/*.csv` 字段与枚举，报告问题（不写库） | `<task_id>_csv_ingest.json` | 不写业务表 |
| `match_compute` | 调 `app.backend.matching`（若可导入），否则内置等价 8 维评分；输出标注实现来源 | `<task_id>_match_compute.json` | 不落匹配记录 |
| `report_render` | 把漏斗/匹配/核验数据渲染成 Markdown 报告 | `<task_id>.md` | 只写任务状态/留痕 |
| `schema_validate` | 对比 `app/data/schema.sql`、`SPEC_DATABASE.md` 与真实 DB 的表/索引/行数 | `<task_id>_schema_validate.json` | 只读 |

## 4. 权限与审批

- **可自主执行**：公开信息研究、写作、内部分析、本地数据库只读统计、确定性任务、产物落盘。
- **必须 CEO 审批**：对外联系/披露/引荐/报价/签约/收款/法律与合规结论/预算；线索等级升级（如 PUBLIC_LEAD → POTENTIAL 以上）、公司 QUALIFIED/ACTIVE、商机条款。
- **禁止**：自动发邮件/私信/拨号、自动报价或承诺成交、托管或代收资金、编造容量/报价/联系人/预算、规避出口管制、把公开线索写成合格客户。

`registry.json` 中 `approval_required=true` 表示该 Agent 的关键产出在**对外或升级**前必须经 CEO 审批，不代表它不能做内部分析。

## 5. 新增或修改 Agent

1. 在 `registry.json` 增加对象，字段齐全（name/display_name_zh/role/objective/inputs/tools/skills/outputs/permissions/approval_required/task_types/status/notes）。
2. 在 `.dsh/skills/<name>/SKILL.md` 写对应 Skill（frontmatter + 六节），Skill 名与 registry 的 `skills` 字段一致。
3. 如需新的确定性任务，在 `agents/runner.py` 的 `TASK_TYPES` 与处理器注册表中实现，并补 `tests/test_agents_runner.py`。
4. 运行 `python -m agents.runner validate` 与单元测试，全部通过后再提交。
