---
name: gpu-spec-normalization
description: GPU 规格标准化：把供应商/需求方口径不一的卡型、显存、互联、规模统一为可比较的规格记录（compute_specifications），产出映射表与可比性说明，不做性能承诺。
version: 1.0
owner: Compute Analyst
tools:
  - web_search
  - web_fetch
  - read
  - write
  - edit
  - python
  - sqlite3
  - csv
---

# gpu-spec-normalization · GPU 规格标准化

> 适用场景：供需双方卡型口径不一致（如「H100 等值」「A800/H800」「昇腾 910B」），需要建立可比口径再做匹配或采购分析时。
> 基线：`docs/07_ai_system/SPEC_DATABASE.md` compute_specifications 表；PROJECT_BRIEF 证据规则；匹配评分 gpu_model 维度。

## ① 输入

| 项 | 内容 | 来源 | 前置校验 |
|----|------|------|----------|
| 待标准化条目 | 原始卡型描述、显存、互联、集群规模 | `compute_supply_resources`、`demand_opportunities`、供应商材料 | 至少给型号或厂商 + 代际；纯「等值」描述标 TO_BE_CLARIFIED |
| 官方规格 | 厂商 datasheet/产品页 | `web_search`/`web_fetch`（NVIDIA/AMD/华为昇腾/寒武纪/海光等官网） | 只认厂商官方或权威文档；二手媒体仅交叉 |
| 既有规格库 | 已标准化的型号记录 | `compute_specifications` | 先查重：同型号同 form_factor 不重复建 |
| 历史映射 | 交接档案中的型号/规模描述 | `docs/handover-20261113/`、`data/research/` | 历史描述标「待复核」，不作为最终规格 |

## ② 操作步骤

1. **解析原始描述**：拆为「厂商 + 型号 + form_factor + 显存 + 互联 + 单节点卡数 + 集群规模 + 精度算力」七要素；缺失项标 `UNKNOWN`，不得猜。
2. **建规范名**：采用 `厂商 型号 form_factor`（如 `NVIDIA H100 SXM`、`NVIDIA A100 80GB PCIe`、`Huawei Ascend 910B`）；「H100 等值」「Blackwell 等值」不得作为规范名，只能写成 `notes` 中的换算口径并标 `equivalent=true`。
3. **填报规格**：`compute_specifications` 字段 `gpu_model(唯一规范名)/vendor/form_factor/memory_gb/memory_type/memory_bandwidth_gbps/fp16_tflops/tf32_tflops/fp8_tflops/interconnect/typical_cluster/power_kw_per_node/notes/source`；数值以官方 datasheet 为准，取不到就留空并在 `notes` 写「未获取」。
4. **互联与规模归一**：NVLink 代际/带宽、IB 200/400G、RoCE 25/100/200G 分别标注；节点内卡数（4/8）与集群卡数分开；带宽单位统一 Gbps，算力统一 TFLOPS（注明精度与是否稀疏）。
5. **生成映射表**：`data/research/gpu-spec-map-<YYYYMMDD>.csv`，列：原始描述、规范名、form_factor、显存、互联、单节点卡数、依据 URL、置信度、待确认项。
6. **可比较性说明**：写 `data/research/gpu-spec-notes-<YYYYMMDD>.md`，逐条说明「为何可比/不可比」；训练与推理用途分别给可比性结论。
7. **交接口径**：把规范名与可比性说明交给 `compute-matching` / `procurement-analysis`；发现系统性口径缺失（如全部供应商都不披露互联）→ 报 Lead 作为研究缺口。

异常与升级：官方规格与供应商自述冲突 → 以官方为准并在 `notes` 记录冲突；型号疑似改名/贴牌 → 标 `TO_BE_CLARIFIED` 并移交 `supplier-verification`；涉及受管制型号/阉割版 → 移交 `cross-border-risk-screening` 记录事实。

## ③ 工具要求

**本项目真实可用**：`web_search`、`web_fetch`、`read`、`write`、`edit`、`python`（计算换算、生成 CSV，可调用本地后端 API）、`sqlite3`（只读）、CSV、`git`（只读）。
**明确不可用**：浏览器自动化、MCP、付费基准测试数据库（MLPerf 结果可公开检索，但不得购买）、实测跑分环境（无 GPU 机器）、邮件外联。
换算计算（如「等值卡数」「总显存」）必须写清公式与假设，可由 `python` 复算。

## ④ 输出

| 产出 | 路径/表 | 字段 |
|------|---------|------|
| 规格记录 | `compute_specifications` | 全部字段，`source` 为官方 URL |
| 映射表 | `data/research/gpu-spec-map-<YYYYMMDD>.csv` | 原始→规范、依据、置信度、待确认 |
| 可比性说明 | `data/research/gpu-spec-notes-<YYYYMMDD>.md` | 可比/不可比结论与用途区分 |
| 证据 | `evidence_registry` | `subject_type=CLAIM`，claim 为单条规格事实 |
| 留痕 | `agent_tasks.result_summary`、`project_activities` | 新增/更新型号数 |

## ⑤ 质量标准

- 每个型号记录 `gpu_model` 唯一且符合命名规则；「等值/兼容/同代」不得进入 `gpu_model`。
- 数值字段必须有 `source`；无来源的算力/带宽数字不得填，只能留空并注「未获取」。
- 单位统一：带宽 Gbps、显存 GB、算力 TFLOPS（注明 FP16/BF16/FP8 与稀疏口径）、功率 kW。
- 映射表中每条原始描述都能落到一个规范名或明确 `TO_BE_CLARIFIED`，不得悬空。
- 可比性说明必须区分训练/推理，不得给「性能排名」或采购建议（属采购分析）。
- 同一型号多次出现时只维护一条主记录，其余引用其 `gpu_model`。

## ⑥ 权限边界

**可自主**：公开规格检索、规格库维护、换算与映射表、内部说明文档、向 Lead/其他 Agent 提供口径。
**必须 CEO 审批**：对外发布规格对比、向供应商质询规格、购买基准数据、任何报价相关表述。
**禁止**：编造 datasheet 数值、把估算当官方、做未标假设的性能承诺、把供应商自述规格写成已验证、泄露供应商非公开配置。
