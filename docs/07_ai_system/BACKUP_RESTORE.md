# 数据备份与恢复（BACKUP & RESTORE）

**版本：** v1.0（2026-11-16）
**对象：** 本地 SQLite 经营数据库 `data/runtime/app.db`
**原则：** 备份文件**永不入库**（`.gitignore` 已排除 `*.db*`、`backups/`）；Git 只承载代码与脱敏文档，不承载真实业务数据。

---

## 1. 什么被备份 / 什么不被备份

| 内容 | 是否备份 | 说明 |
|---|---|---|
| `data/runtime/app.db`（18 表全部业务数据） | ✅ 自动备份 | 主数据库 |
| `backup_records` 表 | ✅ 随库 | 记录每次备份的路径、sha256、大小、时间、操作者 |
| `data/research/**`、`app/data/seed/**` | ❌ 不需 | 已入 Git，可从仓库恢复 |
| `data/private/**`、`private/**`（真实报价/合同/联系人） | ⚠️ 手动另备 | 高敏数据，需加密离线备份，不进本系统自动备份范围 |
| Git 仓库本身 | ❌ 不需 | GitHub 远程即版本存档 |
| `data/runtime/agent_outputs/**` | ⚠️ 可选 | 可再生，建议每月手动留一份 |

---

## 2. 备份方式

### 2.1 命令行（推荐）

```powershell
cd D:\ChinaCompute\suanlichuhai
. .\scripts\setup_dev_env.ps1
python -m app.backend.backup                 # 立即备份一次
python -m app.backend.backup --list          # 列出已有备份
```

产物：`backups\app-YYYYMMDD-HHMMSS.db`（重复秒级自动追加 `-02`）。sha256 不落独立文件，记录在 `backup_records.sha256`，恢复时由 API 自动校验。
实现要求（见 `SPEC_DATABASE.md`）：使用 `sqlite3` 的 `Connection.backup()` 热备 API（运行中也可备份，不锁库）、计算 sha256、登记 `backup_records`、**保留最近 20 份**（超出按时间删除最旧）。

### 2.2 界面

`#/backup` → 「立即备份」按钮 → POST `/api/backup`；列表来自 `GET /api/backup`；恢复按钮要求输入 `RESTORE`。

### 2.3 建议频率

| 场景 | 频率 |
|---|---|
| 日常录入期 | 每日 1 次（下班前） |
| 批量导入/大规模改状态前 | **先备份再操作** |
| 重要商务节点（提交核验、生成商机、CEO 审批前） | 立即备份并手工复制一份到 `D:\ChinaCompute\backup-offline\`（加密） |

> 备份与数据库在同一块盘上，只能防误操作，防不了磁盘故障。**每周至少一次**把最新备份复制到另一块盘/移动硬盘/加密云盘（CEO 决定是否启用云）。

---

## 3. 恢复流程

### 3.1 安全前置（必须）

1. **先备份当前库**（哪怕它已损坏）：`python -c "from app.backend import db, backup; c = db.ensure_schema(); print(backup.create_backup(c, note='pre-restore'))"`；若库打不开，先整文件复制 `data/runtime/app.db` 到 `data/runtime/app-broken-<时间>.db`。
2. 停止后端服务（`Ctrl+C`），确保没有进程写库。
3. 恢复 API 会自动按 `backup_records.sha256` 校验文件完整性（无需手工比对）；如需手工核对：

```powershell
cd D:\ChinaCompute\suanlichuhai
$f = "backups\app-20261116-010203.db"
$actual = (Get-FileHash $f -Algorithm SHA256).Hash.ToLower()
python -c "from app.backend import db; c=db.ensure_schema(); print([r['sha256'] for r in [dict(x) for x in c.execute('SELECT sha256 FROM backup_records')]])"
# 与数据库中记录的 sha256 比对，不一致则禁止恢复
```

### 3.2 执行恢复

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8770/api/backup/restore -ContentType 'application/json' -Body '{"file_path":"backups\\app-20261116-010203.db","confirm":"RESTORE"}'
```

- 必须显式确认字符串 `RESTORE`（界面同理，输入 `RESTORE` 才执行）。
- 恢复动作会：先把当前库另存为 `backups\app-YYYYMMDD-HHMMSS.db`（note=`restore 前自动安全备份`）→ 用备份覆盖 `data/runtime/app.db` → 写 `audit_logs`（BACKUP/RESTORE 动作）→ 校验表数量与关键计数。

### 3.3 恢复后验证

```powershell
python -m app.backend.server
# 另开窗口
curl http://127.0.0.1:8770/api/health
curl http://127.0.0.1:8770/api/health/db
curl http://127.0.0.1:8770/api/dashboard
```

预期：`health` ok；`health/db` 返回 18 张表齐全、integrity_check=ok；`dashboard` 计数与恢复点一致。再抽查 1 条需求与 1 条供给的 `updated_at` 与状态。

---

## 4. 灾难恢复（整机/目录丢失）

1. 确认 D 盘路径 `D:\ChinaCompute\suanlichuhai` 存在（不存在则创建）。
2. 克隆仓库并切到开发分支：
   ```powershell
   cd D:\ChinaCompute
   git clone https://github.com/AckNove/suanlichuhai.git
   cd suanlichuhai
   git checkout ai-build-20261116
   ```
3. 运行 `. .\scripts\setup_dev_env.ps1` 与 `. .\scripts\init_db.ps1`（或 `python -m app.backend.seed`）——**注意：这一步会生成种子库，不是你的真实业务库**。
4. 把离线备份的最新 `app-*.db` 放回 `backups\`，按 §3 恢复。
5. 从 `docs/handover-20261113/` 与 `data/research/` 可重建历史线索与研究证据（它们已在仓库）。
6. 执行冒烟：`. .\scripts\smoke_test.ps1`。

---

## 5. 保留策略与清理

| 项 | 策略 |
|---|---|
| 自动备份 | 最近 20 份（超出自动删除最旧） |
| pre-restore 备份 | 保留最近 5 份 |
| 离线备份 | 每周 1 份，保留 8 周（CEO 定） |
| 删除方式 | 只允许通过 `backup.py --prune` 或手工删除**备份目录内**文件；禁止删除 `app.db` 本体（除非恢复流程） |

---

## 6. 责任与审计

- 备份/恢复是**写操作**，必须写 `audit_logs`（`action=backup|restore`，含文件路径、sha256、操作者、结果）。
- `X-Actor` 头缺省为 `system`；人工操作建议 `X-Actor: CEO` 或姓名。
- 恢复属于高风险动作：执行前须 CEO 口头/书面同意（矩阵 A-xx 待登记到 `CEO_APPROVAL_MATRIX.md`）。

---

## 7. 已知限制

1. 无自动定时备份（Windows 计划任务可后续加，当前 PLANNED）。
2. 备份未加密；若含 L2/L3 数据，复制到离线介质前应使用 BitLocker/VeraCrypt 加密卷（PLANNED）。
3. 不支持跨库合并（只支持整体覆盖恢复）。
4. SQLite 备份为单文件，无法做增量；数据量大时可改用 `VACUUM INTO`（同等效果，仍为全量）。
