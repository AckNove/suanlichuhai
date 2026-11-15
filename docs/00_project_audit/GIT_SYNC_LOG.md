# Git 同步记录（GIT SYNC LOG）

**分支规则：** 所有开发在 `ai-build-20261116`；`main` 不覆盖；禁止 force push；不删除历史分支。
**远程：** `https://github.com/AckNove/suanlichuhai`（**当前 Public**，只推代码与脱敏文档）
**记录规则：** 每阶段 = 测试 → 文件检查 → `git add` → `commit` → `push` → 校验远程 SHA → 登记本文件。

| 阶段 | 时间（Asia/Shanghai） | Commit SHA | 远程分支 | 校验 | 内容摘要 |
|---|---|---|---|---|---|
| checkpoint-00 | 2026-11-16 00:5x | `2789a797d90e10a2ba93b35f3a5ec4ab826b004e` | `origin/ai-build-20261116` | ✅ `git ls-remote` 一致 | 项目审计、环境审计、GitHub 审计、执行基线、DB/API 契约、工具清单、安全脚本、.gitignore、README |
| checkpoint-01 | 待提交 | — | — | — | 公司战略与商业体系（docs/01_strategy 6 份 + docs/06_operations 6 份） |
| checkpoint-02 | 待提交 | — | — | — | 供应商/客户开发手册、合作模式、收费框架、双语销售包、商务条款 |
| checkpoint-03 | 待提交 | — | — | — | 数据库、后端 API、种子数据、测试 |
| checkpoint-04 | 待提交 | — | — | — | 前端工作台 18 模块 |
| checkpoint-05 | 待提交 | — | — | — | 10 Skills、11 Agents、运行器 |
| checkpoint-06 | 待提交 | — | — | — | 第一轮真实市场研究、验收报告、交接文档 |

## 提交前检查清单（每次）

- [ ] `python -m unittest discover -s tests -v` 通过
- [ ] `pwsh -File scripts/sensitive_scan.ps1` 无高危命中
- [ ] `git status` 无意外文件（数据库/备份/敏感目录未入库）
- [ ] `git diff --cached --stat` 核对变更范围
- [ ] `git push` 后 `git ls-remote` 校验远程 SHA 与本地 HEAD 一致

## 失败与例外记录

| 时间 | 现象 | 处理 |
|---|---|---|
| — | 暂无 | — |

## 未推送/未提交文件说明

- `data/runtime/**`：运行时数据库、备份、Agent 产物（.gitignore 排除，设计如此）。
- 历史分支 `cursor/handover-20261113-5b36`：未合并、未删除，作为历史存档保留。
- `main`：未改动。
