# 脱敏演示数据（data/demo/）

> **性质：演示/开发用数据，不是真实业务数据。**
> 本目录由 CEO 于 2026-11-16 批准入库，用于让任何人克隆仓库后**无需重新抓取/录入**即可直接查看工作台的真实运行状态。

## 1. 内容

| 文件 | 说明 |
|---|---|
| `app-demo.db` | SQLite 演示库快照（19 个对象 = 18 张业务表 + `sqlite_sequence`），内容 = 历史交接种子（18 供给 / 9 需求 / 3 匹配）+ 第一轮公开研究导入（5 需求 / 3 供给 / 3 匹配 / 40 证据）+ 演示用规格/审批/知识/Agent 任务 |
| `agent_outputs/` | 11 个 Agent 任务的实际产物（6 类任务：data_audit / evidence_check / csv_ingest / match_compute / report_render / schema_validate） |
| `MANIFEST.json` | 生成时间、各表计数、每个文件的 sha256 与字节数 |

## 2. 数据边界（为什么可以公开）

- 全部实体均为**公开线索或种子演示数据**：供应商/需求方状态最高只到 `LEAD`，`verified=0`。
- **不含**：真实联系人姓名/邮箱/电话、真实报价、合同、采购预算、成交与回款、客户隐私。
- 入库前已扫描：**0 邮箱 / 0 手机号 / 0 本机绝对路径**（扫描脚本与结果见 `scripts/sensitive_scan.ps1` 与 `MANIFEST.json` 的 `sanitized` 字段）。
- 仍可能包含公开渠道可见的企业名称与公开报道信息（与 `docs/handover-20261113/` 历史资料一致）。

## 3. 如何使用

```powershell
cd D:\ChinaCompute\suanlichuhai
. .\scripts\setup_dev_env.ps1

# 方式 A：直接用演示库启动（会写 data/runtime/app.db，请先确认可覆盖）
Copy-Item data\demo\app-demo.db data\runtime\app.db -Force
python -m app.backend.server
# 浏览器打开 http://127.0.0.1:8770

# 方式 B：不覆盖本机库，只在临时库上跑
$env:CCGS_DB_PATH = "$env:TEMP\ccgs-demo.db"
Copy-Item data\demo\app-demo.db $env:CCGS_DB_PATH -Force
python -m app.backend.server
```

## 4. 如何重新生成

演示库可由仓库内容完全重建（不需要本目录）：

```powershell
python -m app.backend.db          # 建 18 张表
python -m app.backend.seed        # 历史交接种子（全部 LEAD）
python scripts\import_research.py # 第一轮研究导入（幂等）
python agents\runner.py run-all   # 复跑 11 个 Agent 任务，产物落 data/runtime/agent_outputs/
python scripts\build_demo_dataset.py  # 一次性重建 data/demo/（快照 + 产物 + 脱敏校验 + MANIFEST）
```

`build_demo_dataset.py` 会做四件事：sqlite3 backup 一致性快照 → 复制 Agent 产物并把本机绝对路径替换为相对路径 → 扫描演示库（邮箱/手机号/绝对路径必须为 0）→ 重写 `MANIFEST.json`（sha256 + 计数）。

## 5. 校验

```powershell
python -c "import hashlib,json,pathlib; m=json.loads(pathlib.Path('data/demo/MANIFEST.json').read_text(encoding='utf-8')); bad=[f['path'] for f in m['files'] if hashlib.sha256(pathlib.Path(f['path']).read_bytes()).hexdigest()!=f['sha256']]; print('files:',len(m['files']),'mismatch:',bad)"
```
