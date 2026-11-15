---
name: china-compute-supply-research
description: 中国算力供给研究：发现并结构化中国智算中心/GPU 云/运营商的公开供给线索（卡型、规模、位置、交付形态、海外服务自述），产出带证据链的供给线索与《供给研究简报》。
version: 1.0
owner: China Supply Intelligence
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

# china-compute-supply-research · 中国算力供给研究

> 适用场景：为 A 线（中国智算供给出海）补充合格供给候选，或复核现有 18 条供给线索的公开信息。
> 基线：`docs/00_project_audit/PROJECT_BRIEF.md` 第 2、7、10 节；`docs/handover-20261113/B-中国算力出海/01-供应侧档案/`。

## ① 输入

| 项 | 内容 | 来源 | 前置校验 |
|----|------|------|----------|
| 研究目标 | 卡型/区域/规模/交付形态要求 | Lead 任务单或匹配缺口清单 | 至少一项明确；不得无目标泛扫 |
| 现有供给线索 | 18 条 LEGACY 线索（阿里云、腾讯、华为、移动/电信/联通、Aolani、创世华彩、中数通、广东越动、壹通道、华胜天成、智子芯元、蜂助手、点动数字、天顿数据、登甲智能、硅基流动） | `compute_supply_resources`、`companies`（SUPPLIER） | 先查重（公司名/域名/集团关系），重复不新建 |
| 公开规格库 | GPU 型号规格参考 | `compute_specifications` | 规格只作参考，标注「非报价」 |
| 证据规则 | URL/发布者/时间/信任度要求 | `PROJECT_BRIEF.md` 第 10 节 | 无来源不得落库 |
| 优先级提示 | 优先验证：登甲智能、天顿数据、硅基流动（词元跨境更敏感） | `PROJECT_BRIEF.md` 第 7 节 | 尊重优先顺序，但不预设结论 |

## ② 操作步骤

1. **明确缺口**：从匹配记录/Lead 任务单提取需要的卡型、显存、规模、互联、地点、交付形态；写研究假设。
2. **公开检索**：官网产品页/价目页、上市公司公告与年报、港交所/交易所披露、信通院与政府项目新闻、行业会议报道、云厂商区域节点页；记录 URL、发布者、发布时间、获取时间。
3. **区分「自述」与「可核验」**：官网自称容量/海外节点/客户占比一律标 `UNVERIFIED`，只有第三方独立来源或可核验公示才可升级信任度。
4. **结构化落档**：`compute_supply_resources` 填写 `company_id/location_country/location_city/datacenter/gpu_model/gpu_count/sellable_gpu_count/gpu_memory_gb/interconnect/cluster_topology/training_capable/inference_capable/network_bandwidth/storage/delivery_lead_time/price_indication(默认「待确认」)/pricing_model/overseas_service`；`status=LEAD`、`verified=0`；公司记录 `status=RESEARCHED` 仅在公开研究完成时。
5. **证据登记**：每条型号/规模/位置/海外节点主张写 `evidence_registry`（`subject_type=SUPPLY`），回填 `evidence_ids`；同一数字只引用一次主证据，转述源做交叉。
6. **写简报**：`data/research/supply-<主题>-<YYYYMMDD>.md` + CSV；列出「已公开可核 / 仅公司自述 / 完全缺失」三档，并给下一轮待澄清问题（移交 `supplier-verification`）。
7. **报告**：向 Lead 汇报新增/更新条数、证据缺口、排序建议；不接触供应商。

异常与升级：同一公司存在多个法人/品牌 → 在 `notes` 写明关系并移交核验，不合并主体；发现疑似违规宣传（虚构容量）→ 降级信任度并标「待核验」；涉及出口管制/跨境节点表述 → 移交 `cross-border-risk-screening`。

## ③ 工具要求

**本项目真实可用**：`web_search`、`web_fetch`、`read`、`write`、`edit`、`python`（含 requests，可调用本地后端 API）、`sqlite3`（只读）、CSV、`git`（只读）。
**明确不可用**：浏览器自动化、MCP 连接器、付费 API/付费数据库、邮件/电话外联、供应商后台账号、验证码绕过、爬取登录后付费内容。
写库走本地后端 API（`POST/PATCH /api/supplies`、`/api/companies`、`/api/evidence`）；runner 不写业务数据。

## ④ 输出

| 产出 | 路径/表 | 字段 |
|------|---------|------|
| 供给资源 | `compute_supply_resources` | 全部字段，`status=LEAD`、`verified=0`、`price_indication=待确认` |
| 供给公司 | `companies`（company_type=SUPPLIER） | `name/name_en/country/region/website/parent/status=RESEARCHED/RESEARCHED 仅公开研究完成/trust_level` |
| 证据 | `evidence_registry` | `subject_type=SUPPLY/COMPANY`，URL/publisher/时间/信任度 |
| 简报 | `data/research/supply-<topic>-<YYYYMMDD>.md` + `.csv` | 三档证据状态、待澄清清单 |
| 任务留痕 | `agent_tasks.result_summary`、`project_activities` | 摘要 + 计数 |

## ⑤ 质量标准

- 可售数量必须写「现网/可售/规划」中的哪一种；官网营销口径（千卡/万 P）不得直接当可售量，必须标「公司自述」。
- `verified=0` 时 `price_indication` 只能为「待确认」，不得写价格；任何价格数字不得进入公开仓库。
- `overseas_service=1` 需有公开可核证的海外节点/服务说明，否则填 0 并在 `notes` 写「自述，未核」。
- 每条记录至少 1 条 `evidence_registry` 记录；`trust_level` 不得高于证据强度。
- 简报四类标签齐全（事实/判断/建议/待确认）；不得出现「已合作」「已授权」等未证实表述。

## ⑥ 权限边界

**可自主**：公开信息检索、供应商公开档案结构化、证据登记、内部简报、本地数据分析、向 Lead 汇报。
**必须 CEO 审批**：联系供应商、询问报价/容量、索取证明材料、视频/实地查验、对外发布任何供给信息、购买付费数据。
**禁止**：承诺供应商资源、代表供应商对外表述、把自述容量写成已验证、将真实联系人/报价写入公开仓库（只进 `private/` 或 `data/private/`）、修改状态机至 VERIFIED 及以后。
