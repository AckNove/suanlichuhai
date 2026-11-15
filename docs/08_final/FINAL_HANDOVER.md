# 项目交接总览（Final Handover）

- 项目：中国算力国际化项目（China Compute Globalization Services，CCGS）
- 交接日期：2026-11-16（Asia/Shanghai）
- 交接对象：CEO Arthur
- 仓库：https://github.com/AckNove/suanlichuhai
- 开发分支：`ai-build-20261116`（远程同名分支）
- 本地目录：`D:\ChinaCompute\suanlichuhai`
- 本文件性质：内部交接说明；**不含**、也不得被解读为任何业绩、客户、合作或资质证明

---

## 1. 这个项目现在是什么

一句话：**一套「中国算力出海」的 AI 原生经营底座**——60 份文档（战略 6、商务 5、双语销售 21、合同条款 3、研究 5、经营 6、系统 7、审计 4、验收 3）+ 一个本地可运行的 18 模块经营工作台 + 11 个 Agent/10 个 Skills + 第一轮 9 个真实公开信息研究产出。

它的定位是「服务商」：连接中国可商业化智算与全球 AI 算力需求，收服务费，**不自营机房、不囤卡、不托管客户资金、不做未授权交易**（详见 `docs/01_strategy/COMPANY_POSITIONING.md`）。

它目前的真实业务状态：**0 家已核验供应商、0 个已核验需求方、0 份协议、0 成交、0 回款**。系统里所有企业记录都是「公开线索/推断需求」，不允许自动升级。

---

## 2. 五分钟上手

```powershell
cd D:\ChinaCompute\suanlichuhai
. .\scripts\setup_dev_env.ps1          # 进程级设置：TEMP/TMP、pip/uv/npm 缓存全部指向 D 盘
python -m app.backend.seed             # 建库（18 表）+ 装历史种子，幂等可重复执行
python -m app.backend.server           # 启动工作台：http://127.0.0.1:8770
```

浏览器打开 `http://127.0.0.1:8770/` 即进入经营工作台（账号体系无，本地单用户；顶部有「不外发/不报价」诚实横幅）。

验证环境与质量：

```powershell
python -m unittest discover -s tests     # 期望：Ran 89 tests, OK
powershell -File scripts\smoke_test.ps1  # 期望：13 个端点 + 匹配引擎全 OK
python agents\runner.py validate         # 期望：11 agents / 10 skills / 0 problems
```

更多命令与排错见 `docs/07_ai_system/RUNBOOK.md`。

---

## 3. 交付物索引

### 3.1 商业体系（`docs/`）

| 目录 | 内容 | 份数 |
|---|---|---|
| `00_project_audit/` | 项目基线、环境审计、GitHub 审计、Git 同步记录 | 4 |
| `01_strategy/` | 公司定位、商业模式、产品目录、价值主张、竞争定位、目标客户 | 6 |
| `02_commercial/` | 供应商开发手册、客户开发手册、合作模式、收费框架、材料索引 | 5 |
| `03_sales/` | 双语销售工具包（公司/供应商/客户介绍、首联话术、问卷、One Pager、采购方案样例、核验清单、跟进模板） | 21 |
| `04_contracts/` | 成功介绍协议、采购顾问服务、渠道合作条款清单（商务条款设计，非律师合同） | 3 |
| `05_research/` | 第一轮真实研究：需求 5 / 供给 3 / 匹配 3 / 市场总结 / 40 条证据 | 5 |
| `06_operations/` | 经营手册、交易管道、CEO 审批矩阵、风险登记、公司设立清单、跨境风险流程 | 6 |
| `07_ai_system/` | 数据库契约、API 契约、系统架构、工具清单、运行手册、备份恢复、Agent/Skills 规格 | 7 |
| `08_final/` | 本交接文档、验收报告、CEO 下一步行动 | 3 |

### 3.2 软件（`app/`、`agents/`、`.dsh/`）

- `app/backend/`：db / repo / api / matching / seed / csv_io / backup / server（Flask + SQLite，仅标准库+Flask）
- `app/web/`：零依赖前端（10 个 JS + 单页 shell），18 模块 hash 路由
- `app/data/`：`schema.sql`（18 表 7 索引）+ 4 份种子 CSV
- `agents/`：`registry.json`（11 Agent）、`runner.py`（6 类确定性任务）、README
- `.dsh/skills/`：10 个项目 Skill（各含输入/步骤/工具/输出/质量标准/权限边界）
- `tests/`：89 个测试（后端 66 + Agent 23）
- `scripts/`：环境、初始化、启动、测试、冒烟、敏感扫描

### 3.3 数据

- 运行库：`data/runtime/app.db`（**被 .gitignore 排除，不进仓库**；由 `python -m app.backend.seed` 生成）
- 演示种子数据：公司 27 / 供给 18 / 需求 9 / 证据 31 / 匹配 3 / 规格 10 / Agent 任务 11 / 审批 7 / 知识 6
- 研究数据：`data/research/*.csv`（5 需求 + 3 供给 + 3 匹配 + 40 证据），已脱敏、无个人联系方式

---

## 4. GitHub 版本记录

| 阶段 | commit | 说明 |
|---|---|---|
| checkpoint-00 | `2789a797d90e10a2ba93b35f3a5ec4ab826b004e` | 审计与基线 |
| checkpoint-01 | `d06898b29323f82a4f50f007a8970a79d9388901` | 战略与经营体系 |
| checkpoint-02 | `07e4abbd0c0f93101989d8e62c86d5018289c2aa` | 商务、双语销售、合同条款 |
| checkpoint-03 | `872ea77b05261f7adcf32836783866b007d6b947` | 数据库与后端 |
| checkpoint-04 | `c49121bbc7e0e052dcf77bd0ac35f7c4074eb860` | 前端工作台 + Agent/Skills |
| checkpoint-05 | `260d2a08e38d271d857baa56250c385fc66deab1` | 第一轮研究 + 文档终校 |
| checkpoint-06 | 见 `docs/00_project_audit/GIT_SYNC_LOG.md`（验收提交） | 验收与交接 |

**分支规则**：只在 `ai-build-20261116` 开发；`main` 未被覆盖；历史 branch `cursor/handover-20261113-5b36` 保留；禁止 force push。

**⚠ 隐私待办**：仓库当前仍是 **Public**。建议 CEO 改为 Private。在改动前，仓库只含代码与脱敏文档；真实客户信息、报价、合同、联系人、数据库一律不得入库（`.gitignore` 已阻断常见路径）。

---

## 5. 系统能做什么 / 不能做什么（交接重点）

**能**（已实测）：

- 管理公司/需求/供给/规格/证据/核验/匹配/采购分析/商机/报价元数据/合同元数据/任务/活动/知识/审计/审批/备份 18 类实体；
- 8 维确定性匹配评分（可解释、含 why_match/why_not_match/红线），并把结果落库；
- CSV 导入导出、数据库备份与恢复（需输入 `RESTORE` 确认）；
- Agent 任务实跑：数据审计、证据检查、CSV 装载、匹配计算、报告渲染、schema 校验；
- 全量审计日志与项目活动留痕（所有写操作）。

**不能**（设计如此，不是缺陷）：

- 不发送邮件/私信、不拨号、不对外联系（CEO 保留联系权）；
- 不生成正式报价、不签约、不收款、不托管资金；
- 不自动把公开线索升级为合格供应商/客户（需核验记录与 CEO 审批）；
- 不做法律/合规结论（只做风险识别与待律师确认清单）；
- 不支持多用户/远程访问（本地单用户 Flask 开发服务器）。

---

## 6. 下一任接手者须知

1. **先读**：`docs/00_project_audit/PROJECT_BRIEF.md`（执行基线）→ 本文件 → `MVP_ACCEPTANCE_REPORT.md`。
2. **再跑**：第 2 节命令，确认 89 测试与冒烟全绿后再改任何代码。
3. **改代码前**：`app/backend` 改动必须同步跑 `tests/`；`app/web` 改动必须过 `node --check`；任何提交前跑 `scripts/sensitive_scan.ps1`。
4. **数据规则**：历史 handover 资料是只读输入（`docs/handover-20261113/`），不得删除或改写；新研究入库必须带证据编号。
5. **不确定先问 CEO**：任何涉及对外表述、报价、合作、合规的内容，一律先给 CEO 批准。

---

## 7. 风险与已知限制

| 风险 | 影响 | 处置 |
|---|---|---|
| 仓库 Public | 商业文档可能被外部看到 | CEO 改 Private；当前已只推脱敏内容 |
| 无公司主体/账户 | 无法签约收款 | CEO 决策注册与开户（见 `COMPANY_SETUP_CHECKLIST.md`） |
| 供应商证据不足 | 无法对外承诺 | 下一步线下核验（9 问清单+25 项 checklist） |
| 研究证据 14 条仅标题级 | 结论强度有限 | 已在证据表标 LOW/未打开，不得升级 |
| 前端回归以人工 + 本机 Chrome 无头自测为主 | 已跑 18 路由渲染与 CDP 交互 | 未引入 Playwright 自动化回归；后续可补 |
| Python 3.9 / Flask 开发服务器 | 仅本机单用户 | 生产化需 WSGI + 账号体系（PLANNED） |
| LLM 不在系统内 | Agent 不是自主智能体 | 推理由 DSH 会话承担，runner 只做确定性任务 |

---

## 8. 交接签署

- 代码与文档：已提交并推送到 `origin/ai-build-20261116`，远程 SHA 与本地一致。
- 数据：真实业务数据为空（0 核验/0 协议/0 成交）；演示种子可重建。
- 待 CEO 动作：见 `docs/08_final/CEO_NEXT_ACTIONS.md`（只列一个需要今天回答的问题）。
