# Git 同步记录（GIT SYNC LOG）

**分支规则：** 所有开发在 `ai-build-20261116`；`main` 不覆盖；禁止 force push；不删除历史分支。
**远程：** `https://github.com/AckNove/suanlichuhai`（**当前 Public**，只推代码与脱敏文档）
**记录规则：** 每阶段 = 测试 → 文件检查 → `git add` → `commit` → `push` → 校验远程 SHA → 登记本文件。

## 1. 分阶段提交记录（对应 CEO 任务书 7 个阶段）

| CEO 阶段 | Commit SHA | 推送状态（`git ls-remote`） | 内容摘要 |
|---|---|---|---|
| `00_PROJECT_AUDIT` | `2789a797d90e10a2ba93b35f3a5ec4ab826b004e` | ✅ `origin/ai-build-20261116` 一致 | 项目/环境/GitHub 审计、执行基线、DB/API 契约、工具清单、`.gitignore`、安全脚本、README |
| `01_COMPANY_STRATEGY` | `d06898b29323f82a4f50f007a8970a79d9388901` | ✅ 一致 | 公司战略 6 份（docs/01_strategy）+ 经营体系 6 份（docs/06_operations）+ SYSTEM_ARCHITECTURE；修复 PowerShell 脚本 UTF-8 BOM |
| `02_COMMERCIAL_SYSTEM` | `07e4abbd0c0f93101989d8e62c86d5018289c2aa` | ✅ 一致 | 商务体系 5 份（docs/02_commercial）+ 商务条款 3 份（docs/04_contracts）+ RUNBOOK |
| `03_SALES_AND_PARTNERS` | 同 `07e4abbd…`（与 02 合并为一次推送，内容完整包含） | ✅ 一致 | 中英双语销售工具包 21 文件（docs/03_sales：10 组 zh/en + README），全部标注草案未经 CEO 批准不得外发 |
| `04_DATABASE_AND_BACKEND` | `872ea77b05261f7adcf32836783866b007d6b947` | ✅ 一致 | 后端 9 模块、18 表 schema、历史种子导入、可解释匹配引擎、CSV 导入导出、备份恢复、89 个测试 |
| `05_FRONTEND_AND_AGENTS` | `c49121bbc7e0e052dcf77bd0ac35f7c4074eb860` | ✅ 一致 | 18 模块前端工作台、11 Agent 注册表 + 确定性运行器、10 个项目 Skills、研究导入工具脚本、备份/能力口径校正 |
| `06_FINAL_ACCEPTANCE`（研究） | `260d2a08e38d271d857baa56250c385fc66deab1` | ✅ 一致 | 第一轮真实公开研究（需求 5 / 供给 3 / 匹配 3 / 证据 40 + 4 个 CSV）、文档终校（战略/商务/条款/经营修订） |
| `06_FINAL_ACCEPTANCE`（验收） | `15f0797ac8b1097c703ff6e5392225176eb3c8f6` | ✅ 一致 | MVP 验收报告、最终交接、CEO 下一步、本同步记录（含 00–05 全部 SHA） |

> 说明：CEO 要求的 7 个阶段均已覆盖；其中 02 与 03 因同一批次交付合并为一次提交推送，已在表中注明。研究阶段按任务书时间线并入 06 收尾。

## 2. 提交前检查清单（每次）

- [x] `python -m unittest discover -s tests -v` → 89 tests OK（exit 0）
- [x] `powershell -ExecutionPolicy Bypass -File scripts/sensitive_scan.ps1` → 高危 0 / 中危 0 / 历史二进制 7 项豁免 / 通过
- [x] `git status` 无意外文件（数据库/备份/敏感目录均被 `.gitignore` 排除）
- [x] `git diff --cached --stat` 核对变更范围
- [x] `git push` 后 `git ls-remote` 校验远程 SHA 与本地 HEAD 一致（每阶段均执行）

## 3. 失败与例外记录

| 时间（Asia/Shanghai） | 现象 | 处理 |
|---|---|---|
| 2026-11-16 00:49 | PowerShell 5.1 将无 BOM 的 UTF-8 `.ps1` 按 ANSI 解析，`sensitive_scan.ps1` 中文乱码 ParserError | 全部 `.ps1` 重写为 UTF-8 BOM；后续 edit 后均重新补 BOM |
| 2026-11-16 00:50 | `git ls-files` 默认 quotepath 引号转义中文路径，扫描报「路径非法字符」 | 脚本内启用 UTF-8 输出 + `git -c core.quotepath=false` |
| 2026-11-16 01:05 | 集成校验 23/24 失败：脚本断言 `total_score` 而实际字段为 `score` | 修正校验脚本与 `smoke_test.ps1`；后端字段以 SPEC 为准保持 `score` |
| 2026-11-16 01:07 | 全量测试 3 项失败：`_run_match(persist=...)` 与函数签名 `persist_default` 不一致 | 后端改为位置参数调用，复跑 89 tests OK |
| 2026-11-16 01:19 | 前端自测误删种子匹配 `MATCH-20261102-001`，按审计日志以新 ID 恢复 | 重跑幂等 seed 恢复原 ID，删除重复恢复件；`data/runtime/app.db` 计数已核对（matches=6 含 3 条研究匹配） |
| 2026-11-16 01:21 | `scripts/run_tests.ps1` 用 `2>&1` 管道触发 NativeCommandError | 改用 `Start-Process` 重定向输出并回读 |
| 2026-11-16 01:22 | `backup.py` 无 CLI，原文档 `python -m app.backend.backup` 无效 | 文档改为 `backup.create_backup()` + `POST /api/backup[/restore]`，路径统一 `backups\app-*.db` |
| 2026-11-16 01:24 | 本机无 PowerShell 7（`pwsh` 不在 PATH） | 文档与脚本用法统一改为 `powershell -ExecutionPolicy Bypass -File` |

## 4. 未推送/未提交文件说明

- `data/runtime/**`：运行时数据库、备份、Agent 产物（`.gitignore` 排除，设计如此）。
- `data/private/**`、`private/**`、`backups/**`：私有/敏感/备份目录（`.gitignore` 排除）。
- `docs/handover-20261113/` 中的历史二进制（jpg、zip）：保留历史，已提交；敏感扫描对其实施「历史豁免」并逐项列出。
- 历史分支 `cursor/handover-20261113-5b36`：未合并、未删除，作为历史存档保留（远程仍在）。
- `main`：未改动（仍为初始提交 `d0a9a30d61285471a0cfd0264fdc4b1015256f86`）。

## 5. 远程核对命令（可复现）

```powershell
git branch -vv
git log --oneline -10
git ls-remote origin
# 期望：refs/heads/ai-build-20261116 指向本地 HEAD
```

## 6. 最终核对快照

- 远程默认分支 `main`：`d0a9a30d61285471a0cfd0264fdc4b1015256f86`（未改动）。
- 历史分支 `cursor/handover-20261113-5b36`：`ca825a581135f9fadb3786fd240581be398587cd`（未删除、未合并）。
- 开发分支 `origin/ai-build-20261116`：含 checkpoint-00 ~ 06 全部提交；每次推送后 `git ls-remote` 核对远程 SHA 与本地 HEAD 一致（无 force push）。
- 本文件最后由「docs 同步提交」更新（SHA 见 `git log -1 --format=%H`）；该提交仅更新本记录，包含最终远程 HEAD。
- 仓库仍为 **Public**（匿名 `ls-remote` 可访问已验证）；**待 CEO 授权后改为 Private**，未经授权未自行修改。改权限后建议 `git remote set-url` 不变，仅访问控制变化。
- 敏感数据检查：最近一次 `sensitive_scan.ps1` 覆盖全部受控文件，高危 0 / 未确认中危 0；历史交接二进制 7 项按「不得删除历史文件」要求豁免并列出路径。
