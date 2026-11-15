# GitHub 仓库审计（2026-11-16 00:37–00:50 Asia/Shanghai）

## 1. 远程仓库

| 项 | 值 |
|----|----|
| URL | https://github.com/AckNove/suanlichuhai |
| 默认分支 | `main`（`origin/HEAD -> origin/main`） |
| 可见性 | **Public**（匿名 `git -c credential.helper= ls-remote` 可读取，已实测） |
| 访问 | HTTPS；push 凭据已存在（Windows Credential Manager：username=AckNove，token 长度 40） |
| 推送测试 | `git push --dry-run origin ai-build-20261116` 成功（exit 0） |

## 2. 分支清单（远程实测）

| 分支 | HEAD SHA | 说明 |
|------|----------|------|
| `refs/heads/main` | `d0a9a30d61285471a0cfd0264fdc4b1015256f86` | Initial commit（仅 README 等骨架） |
| `refs/heads/cursor/handover-20261113-5b36` | `ca825a581135f9fadb3786fd240581be398587cd` | **最新业务资料分支**（2026-11-13 交接快照） |
| `refs/pull/1/head` / `merge` | `ca825a5…` / `5f2bd1c…` | PR #1（handover 分支 → main，未合并） |

本地已有分支：`main`（d0a9a30）、`ai-build-20261116`（ca825a5，跟踪 handover 分支）。**本地 `ai-build-20261116` 尚未推送到远程。**

## 3. 权威版本判定（按内容而非分支名）

- `cursor/handover-20261113-5b36` 含 75 份业务资料、证据表、供应/需求档案、匹配样例、对外话术修订稿 —— 这是**最新业务资料**。
- `main` 仅 Initial commit 骨架 —— 不是业务版本。
- 本地 `ai-build-20261116` 已基于 `ca825a5`（handover HEAD），因此以它为开发基线正确。
- 远程不存在真实代码分支（无应用代码）；「哪个分支含真实代码」= 无，本项目代码从零建。

## 4. 仓库内容现状

```
README.md                   4 KB   交接快照说明（无软件实现，明确声明）
ALL-TEXT.md                 268 KB 全部 .md/.csv/.txt 原文拼接（阅读器友好）
docs/handover-20261113/     75 份历史业务资料（含证据表 registry、海报裁图 jpg）
downloads/…zip              8.9 MB 历史交接压缩包
scripts/setup_dev_env.ps1   2 KB   D 盘开发环境脚本（未提交）
.gitignore                  1.2 KB 敏感数据忽略规则（未提交，编码损坏需重写）
```

## 5. 隐私与安全评估

**风险：仓库为 Public。** 当前仓库内容仅为交接文档与海报裁图（无联系人、无报价、无合同、无密钥），历史资料本身标明「99-敏感商务_仅本项目」目录只有空模板。但本项目后续产生真实客户/供应商数据、报价、合同元数据，**绝不能进入 Public 仓库**。

处置（本次执行）：
1. 建立分级目录：`private/`、`data/private/`（gitignore，永不入仓）。
2. 公开仓库只推：代码、脱敏文档、公开研究证据、模板、示例数据。
3. 真实联系人、报价、合同、密钥、真实业务数据库一律本地私有。
4. **不自行修改仓库可见性**（CEO 保留权限）。已在 `CEO_NEXT_ACTIONS.md` 列为第一优先决策项：建议改为 Private。
5. 提交前执行敏感信息扫描（脚本 + 人工复核），记录结果。

## 6. Git 操作规则（本次执行）

- 开发分支：`ai-build-20261116`（基于 `origin/cursor/handover-20261113-5b36`）。
- 禁止：force push、直接覆盖 `main`、删除历史分支或历史文件。
- 分阶段提交：`00_PROJECT_AUDIT` / `01_COMPANY_STRATEGY` / `02_COMMERCIAL_SYSTEM` / `03_SALES_AND_PARTNERS` / `04_DATABASE_AND_BACKEND` / `05_FRONTEND_AND_AGENTS` / `06_FINAL_ACCEPTANCE`。
- 每次推送后核对远程 SHA，记录到 `FINAL_HANDOVER.md`。
- 若推送失败：如实报告原因，不伪造同步。

## 7. 结论

- GitHub 可读写，基线正确，分支策略清晰。
- 唯一需 CEO 授权的风险项：Public → Private。
- 技术资料与历史资料均已就位，可以开始 00/01 阶段。
