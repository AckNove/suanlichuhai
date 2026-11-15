# CCGS 运行手册（RUNBOOK）

**版本：** v1.0（2026-11-16）
**适用：** CEO / 运营人员 / 后续维护者在本机（Windows）运行 AI 经营工作台。
**前置：** 项目根目录 `D:\ChinaCompute\suanlichuhai`，Python 3.9+，无需联网、无需安装额外服务。

---

## 1. 首次准备（只做一次）

打开 PowerShell（Windows PowerShell 5.1 或 PowerShell 7 均可），执行：

```powershell
cd D:\ChinaCompute\suanlichuhai
. .\scripts\setup_dev_env.ps1
```

该脚本只对**当前进程**生效，把缓存与临时目录指向 D 盘：

| 变量 | 值 |
|---|---|
| `TEMP` / `TMP` | `D:\ChinaCompute\temp` |
| `PIP_CACHE_DIR` | `D:\ChinaCompute\cache\pip` |
| `UV_CACHE_DIR` | `D:\ChinaCompute\cache\uv` |
| `npm_config_cache` | `D:\ChinaCompute\cache\npm` |

并创建 `private\`、`data\private\`、`data\runtime\`、`backups\` 目录。**不修改系统环境变量。**

> 每个新开的 PowerShell 窗口都要先执行一次 `. .\scripts\setup_dev_env.ps1`（或把 `verify_env.ps1` 作为第一条命令）。

---

## 2. 环境自检

```powershell
. .\scripts\setup_dev_env.ps1
. .\scripts\verify_env.ps1
```

检查：D/C 盘容量、python/git/node 版本、Python 依赖（flask/sqlalchemy/pandas/openpyxl/requests/bs4/lxml/yaml/fitz/PyPDF2/pydantic/jinja2）、Git 分支与远程、TEMP 等是否指向 D 盘、工具能力清单。
**只读，不修改任何东西。**

---

## 3. 初始化数据库

```powershell
. .\scripts\setup_dev_env.ps1
python -m app.backend.seed
```

（等价方式：`pwsh -File scripts/init_db.ps1`；若脚本尚未提供，使用上面的 Python 命令。）
首次运行会：创建 `data/runtime/ccgs.db` → 建 18 张表 → 导入历史线索种子（18 供给 / 9 需求 / 3 匹配，全部 `LEAD`/`PUBLIC_LEAD`/`verified=0`）→ 写入演示用的规格、证据、Agent 任务、知识库、审批记录。

> 种子数据在 `notes` 字段标注 `seed:history-import` 或 `seed:demo`，可用于区分「历史导入线索」与「演示数据」。

---

## 4. 启动工作台

```powershell
. .\scripts\setup_dev_env.ps1
python -m app.backend.server
```

- 地址：**http://127.0.0.1:8770**
- 监听 127.0.0.1（仅本机可访问），无登录鉴权；**不要**绑定 0.0.0.0 或暴露到公网。
- 前端为同源静态文件（Flask 托管），不需要第二个服务、不需要 `npm install`。
- 停止：在运行窗口按 `Ctrl+C`。

### 4.1 前端单独调试（可选）

若只想改前端样式，可临时启动静态服务器（注意 API 请求会失败并提示「后端未连接」）：

```powershell
cd app\web
python -m http.server 8899
```

访问 http://127.0.0.1:8899/ —— 仅用于样式检查，正常业务一律走 8770。

---

## 5. 日常操作路径（对应 18 个模块）

| 想做 | 页面（hash 路由） | 说明 |
|---|---|---|
| 看经营全貌 | `#/dashboard` | 计数、漏斗、评分分布、核验状态、提醒 |
| 录入/查看需求 | `#/demands` | 新建即 LEAD；不复选「已核验」 |
| 录入/查看供应商 | `#/suppliers` | 供应商主体 + 供给资源 |
| 管理 GPU 资源 | `#/supplies` | 卡型、数量、可售量、位置、交付 |
| 登记证据 | `#/evidence` | URL/标题/发布者/发布时间/获取时间/信任度 |
| 供应商核验 | `#/verify-supplier` | 25 项 checklist 打分；≥70 才可 QUALIFIED（需 CEO 审批） |
| 需求资格核验 | `#/qualify-demand` | 决策人/预算/时间窗/合规/签约/数据驻留 |
| 规格标准化 | `#/specs` | 统一卡型口径，便于比较 |
| 供需匹配 | `#/matching` | 选 demand + supply → 8 维评分 → 记录 + 解释 |
| 采购分析 | `#/analyses` | 2–5 方案对比，不生成报价 |
| 商机管理 | `#/opportunities` | L1–L6 阶段；双方收费须披露 |
| 项目活动 | `#/activities` | 每一步操作留痕 |
| Agent 任务 | `#/agents`、`#/tasks` | 查看 11 个 Agent 与任务执行记录 |
| CEO 审批 | `#/approvals` | 批量查看待批，逐项批准/驳回（仅 CEO） |
| 知识库 | `#/knowledge` | 方法论、口径、FAQ |
| CSV 导入导出 | 各页按钮 / `#/settings` | 用模板导入，避免字段错位 |
| 备份 | `#/settings` 或命令行 | 见 §7 |
| 审计日志 | `#/audit` | 只读，不可删除 |

**操作纪律：**
1. 先有证据，再升级线索；公开线索永不动自动变「合格」。
2. 任何对外发送前，材料状态必须是「CEO 已批准」。
3. 报价、签约、收款不在系统内进行。

---

## 6. 测试

```powershell
. .\scripts\setup_dev_env.ps1
python -m unittest discover -s tests -v
```

或 `pwsh -File scripts\run_tests.ps1`。
覆盖：数据库建表/种子、API CRUD 与状态机校验、匹配评分边界、CSV 导入导出、备份恢复、Agent runner。

**冒烟测试**（起服务→打端点→关服务）：

```powershell
. .\scripts\setup_dev_env.ps1
. .\scripts\smoke_test.ps1
```

预期：11 个端点全部 200，匹配返回 `total_score` 与 `recommendation`。

---

## 7. 数据备份与恢复

见 `docs/07_ai_system/BACKUP_RESTORE.md`。最短路径：

```powershell
# 备份（生成 data/runtime/backups/ccgs-YYYYMMDD-HHMMSS.db + .sha256）
python -m app.backend.backup

# 查看备份
Get-ChildItem data\runtime\backups\

# 恢复（需先在 UI 输入 RESTORE 或命令行确认）
python -m app.backend.backup --restore data\runtime\backups\<file>.db --confirm RESTORE
```

**恢复前先备份当前库。** 备份文件不入 Git。

---

## 8. Agent 与 Skills

```powershell
# 列出 11 个 Agent
python agents\runner.py list

# 校验注册表结构
python agents\runner.py validate

# 执行所有可自动任务（数据审计/证据检查/CSV 导入/匹配/报告/Schema 校验）
python agents\runner.py run-all

# 查看单个 Agent
python agents\runner.py show matching-engine
```

产物写入 `data/runtime/agent_outputs/`（不入 Git）。
10 个 Skill 位于 `.dsh/skills/`，供 AI 操作者按 `SKILL.md` 流程执行；Skill 不授予外联/报价/签约权限。

---

## 9. 提交与同步（仅维护者）

```powershell
. .\scripts\setup_dev_env.ps1
. .\scripts\sensitive_scan.ps1      # 必须通过（高危 0、违规二进制 0）
git add -A
git commit -m "type(scope): message (checkpoint-NN)"
git push origin ai-build-20261116
```

规则：不直接推 `main`、不 force push、不删除历史分支/文件；每次推送后 `git ls-remote` 核对远程 SHA，并登记到 `docs/00_project_audit/GIT_SYNC_LOG.md`。

---

## 10. 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 页面提示「后端未连接」 | 后端没起 / 端口被占 | 确认 `python -m app.backend.server` 运行；换端口 `--port 8771` |
| `ModuleNotFoundError: flask` | 用了错误 Python | `python -V` 应为 3.9+；用 `setup_dev_env.ps1` 后的同一窗口运行 |
| 409 状态迁移被拒 | 状态机不允许该跳转 | 按提示的允许目标先补核验/审批记录 |
| `database is locked` | 多个进程同时写 | 关闭多余实例；SQLite 单写者 |
| 控制台中文乱码 | PS 5.1 编码 | 脚本已保存为 UTF-8 BOM；如仍乱码执行 `chcp 65001` |
| 扫描误报邮箱/手机号 | 文档含示例联系方式 | 改成 `name@example.com` 或标注「示例」 |
| Git push 401 | PAT 过期 | 更新 Windows 凭据管理器的 `git:https://github.com` 凭据（CEO 授权后） |

---

## 11. 运行边界（必须遵守）

- 系统**不联网**发起外部请求、**不发邮件/私信/拨号**、**不报价**、**不签约**、**不收款**。
- 无多用户鉴权：只在本机运行；如需远程访问，必须先加认证与 HTTPS（当前 UNVERIFIED）。
- 所有对外沟通与商务动作由 CEO 人工执行。
