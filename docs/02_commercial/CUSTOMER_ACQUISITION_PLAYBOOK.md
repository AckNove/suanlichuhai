# 海外客户开发手册（Customer Acquisition Playbook）

> 项目：中国算力国际化项目（CCGS）· 中国算力出海
> 版本：v1.0 ｜ 日期：2026-11-16 ｜ 状态：内部草案，待 CEO 审批
> 性质声明：本文是商业流程与话术设计，**不是法律文本、不构成法律意见，也不构成对外报价或合作承诺**；涉及数据保护、跨境传输、出口管制的具体问题须由律师逐案判断。正式合同须律师审核。
> 密级：内部。所有对外联系须 CEO 本人批准并执行，本文不授权任何自动外联。
> 依据：`docs/00_project_audit/PROJECT_BRIEF.md`；历史参考 `docs/handover-20261113/B-中国算力出海/07-项目管理/经营框架-开口到收款.md`。

---

## 0. 一分钟读懂本文

- **目标**：从公开信号出发，找到真实、可核实的海外 AI 算力需求，做成「合格需求」再谈匹配。
- **当前真实状态**：已核验合格需求 **0**；需求侧公开线索均为公开信息，未接触、未核实（BRIEF §7）。**不得把公开线索写成「客户」「意向」「在谈」。**
- **三条铁律**：
  1. **先有信号、再接触；先核实、再介绍**。
  2. **首轮不谈费率**；只讲对方能获得什么（按规格筛过的可交付供给短名单 + 为什么配/不配）。
  3. **不虚构案例、不承诺合规、不承诺价格更低**；主体设立中，不得暗示已具备签约与收款能力。

---

## 1. 客户分类与优先级

| # | 客户类型 | 典型画像 | 典型算力需求 | 我方切入点 | 优先级 |
|---|----------|----------|--------------|------------|--------|
| 1 | AI 创业公司（种子轮—B 轮） | 小团队、融资后扩训练/推理 | 训练集群短租、推理弹性扩容 | 快速给出可交付短名单与交付周期对比 | **P0** |
| 2 | 模型训练公司 | 预训练/微调/RL，长周期大集群 | 数十至数百卡、稳定长租、IB 集群 | 中国供给的价格与交付窗口；跨境方案 | **P0** |
| 3 | 推理服务商/API 平台 | 按调用量扩容，成本敏感 | 推理卡、弹性实例、低时延节点 | 推理成本优化与多区域供给 | **P0** |
| 4 | 视频生成/3D AI | 高显存、高并发、GPU 密集型 | H100/H200 级、长时间批量渲染 | 大显存卡型与批量任务排期 | P1 |
| 5 | 机器人/仿真 | 仿真训练、合成数据、边缘推理 | 中等规模训练 + 边缘节点 | 训练/推理组合方案 | P1 |
| 6 | AI 基础设施（平台/工具/中间件） | 自身不买卡，但服务大量用卡客户 | 为其客户提供算力选项 | 渠道合作、白标供给 | P2 |
| 7 | 主权 AI/政府项目 | 国家级/区域级 AI 计划，合规极重 | 本地化、数据驻留、长期框架 | 仅做研究与合规路径梳理，不承诺可执行 | P2（研究优先） |
| 8 | 区域云与渠道 | 本地云厂商、系统集成商、代理 | 批量采购、转售、区域交付 | 供给分销与联合方案 | P1 |

**优先级规则**：P0 先跑通「信号 → 接触 → 12 问 → 合格需求」闭环；P1 建档并准备场景化材料；P2 只研究、不主动接触，除非 CEO 点名。主权 AI 方向必须遵守 BRIEF §2-B：**未经专业法律审核前，不得对外承诺合法、合规或可执行。**

---

## 2. 需求信号识别（先找信号，再找人）

| 信号 | 在哪看 | 具体操作 | 记录字段 | 时效 |
|------|--------|----------|----------|------|
| 招聘 JD 中的 GPU/infra 岗位 | 公司招聘页、LinkedIn Jobs、YC Work at a Startup | 搜 `"GPU cluster"`、`"distributed training"`、`"inference infrastructure"`、`"ML platform"`；JD 里写「build GPU cluster from scratch」= 强信号 | 岗位、发布时间、JD 原文链接、推断需求 | 高（2 周内） |
| 融资公告 | 公司博客、TechCrunch、Crunchbase、官方 X/LinkedIn | 关注「用新资金扩展算力和团队」的表述 | 轮次、金额、用途、日期 | 高（1 个月内） |
| 模型发布 | Hugging Face、公司博客、arXiv、X | 新模型/新参数规模 → 训练或推理扩容推断 | 模型规模、发布方、技术博客链接 | 中 |
| 算力短缺公开表态 | 创始人访谈、播客、X、财报电话会 | 关键词 `"compute constrained"`、`"GPU shortage"`、`"waitlist"` | 原话、来源、日期 | 高 |
| 扩容新闻 | 官网新闻、数据中心合作公告、云厂商案例 | 「签约新数据中心」「部署新集群」 | 合作方、地点、规模 | 中 |
| 公开采购 | 政府/企业招标平台、公共采购公告 | 搜 `"GPU"`、`"AI compute"`、`"H100"` + 国家/机构 | 预算、交付要求、截止日 | 高（有截止日） |
| 会议演讲 | NeurIPS/ICML/ICLR/CVPR、GTC、AI Engineer、区域 AI 峰会 | 从议程找「Infrastructure/Scaling」主题讲者与公司 | 讲者、公司、主题 | 中 |
| GitHub/技术博客 | 开源项目 README、工程博客 | 项目自述「需要更多 GPU」「训练受限于算力」；issue 中讨论扩容 | 项目、需求线索、链接 | 中 |

**信号 → 线索 → 潜在机会的升级规则**（BRIEF §8）：单条信号只能标「推断需求」；同一公司出现 2 条以上独立信号、且有明确决策岗位，才可升「潜在机会」；接触并核实后才可升「已核实需求」。

---

## 3. 决策人岗位与切入方式

| 岗位 | 关心什么 | 开场说什么 | 决策角色 |
|------|----------|------------|----------|
| CTO / VP Engineering | 交付确定性、总体成本、技术风险 | 「我们只介绍核验过的供给，并写清为什么配/不配」 | 决策/技术否决 |
| Head of Infrastructure / Head of Platform | 集群可用性、网络、交付周期 | 「按卡型、地点、网络、交付期做短名单」 | 关键推动者 |
| Head of ML / 训练负责人 | 卡型、互联、训练效率 | 「先确认工作负载与集群要求，再匹配供给」 | 需求定义者 |
| Procurement / 采购 | 价格、合同条款、供应商资质 | 「双方直接签约，我们不托管资金、不加价」 | 流程把关 |
| CEO / Founder（早期公司） | 速度、现金流、能否撑过训练窗口 | 「帮你在 1–2 周内把可交付选项摆上桌」 | 最终决策 |

**原则**：先找「有痛点的人」（Infra/ML），再找「能签字的人」（CTO/CEO/Procurement）；不要一上来只找 CEO，除非公司小于 50 人。

---

## 4. 客户发现渠道（具体操作法与检索式）

| 渠道 | 具体操作 | 检索式/动作示例 | 产出 |
|------|----------|------------------|------|
| LinkedIn | 按岗位 + 公司 + 地区搜索；看公司页「近期动态」与员工增长 | `("Head of Infrastructure" OR "Head of ML" OR "VP Engineering") AND ("AI" OR "LLM" OR "foundation model")`；`("GPU" AND "cluster")`；筛选国家/地区 | 目标人 + 公司 + 信号 |
| LinkedIn Sales Navigator | 建 Account List（按行业/规模/地区/融资）；保存 Lead 搜索；开启「Hiring on LinkedIn」提醒 | Account filters: Industry=AI, Employee size 10–500, Geography=目标市场；Lead filters: Title contains Infrastructure/ML/CTO | 账户清单 + 提醒 |
| Y Combinator 目录 | ycombinator.com/companies 按 Industry=AI、Batch 筛选；逐家公司看官网/招聘页 | 筛 `AI`、`B2B`、近 2 年批次；导出公司名、简介、创始人 | 初创客户清单 |
| Hugging Face Organizations | 看组织页、模型卡、Inference Providers、讨论区 | 搜组织名 → 看模型发布频率与推理部署方式 | 技术需求线索 |
| 企业官网 | /careers、/about、/newsroom、/blog 四个页面固定扫 | 招聘页找 GPU 岗位；博客找「scaling」「training run」 | 信号与联系人路径 |
| 官方招聘页 | 直接看 JD 关键词与团队规模 | `"build our GPU cluster"`、`"manage 1000+ GPUs"`、`"CUDA"`、`"Kubernetes GPU"` | 需求强度判断 |
| AI 产业会议 | 议程 + 展商 + 讲者名单；会后按讲者公司建档 | NeurIPS/ICML/ICLR/CVPR、GTC、AI Engineer World's Fair；检索 speaker list | 高意向公司清单 |
| 合作伙伴网络 | 云厂商、IDC、VC/加速器、猎头、行业群 | 请合作方引荐「正在扩算力的被投企业」 | 转介绍线索 |

**渠道纪律**：每个线索必须记录来源 URL、获取日期、信任等级；渠道只用于「找到公开的商务联系方式」，不得使用爬虫批量抓取个人数据，不得购买联系人数据库。

---

## 5. 联系方式获取的合规边界

- **只使用公开渠道**：公司官网 contact/about、公开的商务邮箱、LinkedIn 公开资料、会议公开名片/讲者页。
- **不购买个人数据**，不使用来源不明的联系人列表，不抓取私人手机号/私人邮箱。
- **最小化**：只记录完成商务沟通所必需的字段（姓名、岗位、公司、公开商务联系方式、来源）。
- **可拒绝与可删除**：对方要求停止联系时立即停止并标记 `DO_NOT_CONTACT`；对方要求删除时按内部流程处理。
- **GDPR / PDPA 提示**（不构成法律意见）：向欧盟/英国/新加坡等司法辖区联系人发送商业邮件前，应确认适用规则（合法基础、商业邮件同意要求、退订机制、数据保留期限、跨境传输限制）；正式外联前由律师/合规顾问确认模板与流程。**本文不构成任何合规结论。**
- **记录**：所有联系记录仅存内部系统（含 `private/` 敏感区），不进公开仓库。

---

## 6. 初次联系话术（英文为主 + 中文注释，不谈费率）

> 使用前提：CEO 批准外联；主体状态如实披露（设立中）。以下均为**待批准草案**，不得直接群发。

### 版本 A：Cold Email（冷邮件）

**Subject:** China GPU capacity for your training / inference workload — sourcing help

> Hi [First Name],
>
> I'm [Your Name], working on compute sourcing at CCGS. We help AI teams compare verified GPU capacity — including China-based data centers and GPU clouds — and we coordinate the commercial introduction.
>
> Two things we do differently:
> 1) We verify availability, card type, delivery timeline and network before introducing anything.
> 2) The capacity contract is signed directly between you and the supplier. We don't resell capacity, don't mark up your price, and don't hold funds.
>
> If you're evaluating additional capacity in the next 1–2 quarters, would a 20-minute call be useful? I can share what's realistically deliverable for your workload — and tell you plainly what doesn't fit.
>
> [Your Name] · CCGS (entity in formation) · [public email]

**中文注释**：①先自报身份与目的，不绕弯；②用「verified / don't resell / don't mark up」建立差异，但不承诺价格更低；③给出低门槛 CTA（20 分钟）；④签名如实标注主体设立中；⑤全篇无费率、无案例、无客户名。

### 版本 B：LinkedIn DM

> Hi [First Name] — I saw [company] is hiring for [GPU/infra role] / recently announced [signal]. We help AI teams source verified GPU capacity, including China-based providers, and coordinate the intro. Contract stays between you and the supplier; we don't resell or mark up. Open to a 15-min call this week or next?

**中文注释**：①首句必须引用对方**公开的**具体信号（招聘/融资/发布），证明不是群发；②一句话说清商业模式；③只问「是否愿意聊」，不附文件、不报费率；④不超过 300 字符。

### 版本 C：会议开场（30–60 秒）

> "Hi, I'm [Name] from CCGS. We work on the supply side of AI compute — specifically, sourcing and verifying GPU capacity from China-based providers for teams outside China. We're not a reseller and we don't mark up capacity; we prepare a shortlist and explain why it fits or doesn't. I noticed [company] is [signal] — is capacity planning on your roadmap this year? Happy to compare notes for 10 minutes."

**中文注释**：①10 秒内说清「我们不是谁」比说「我们是谁」更有效；②引用现场信息或公开信号；③以「交换信息」而非「推销」收尾；④遇到追问「你们收多少」→ 标准答复见第 7 节反对意见 #4。

---

## 7. 需求访谈流程（12 问，逐条记录）

> 目标：把模糊的「需要 GPU」变成可匹配的需求。对方答不上来的标「待确认」，不替对方假设。

1. **工作负载是什么？** 预训练、微调、RL、推理、视频生成、仿真？具体框架与并行方式？
2. **需要哪些卡型？** H100/H200/A100/其他？显存与互联要求？是否接受国产卡/混合集群？
3. **规模多大？** 卡数、集群规模、是否需要多节点？峰值与稳态各多少？
4. **训练还是推理？** 训练时长/频率；推理的 QPS、时延、上下文长度？
5. **时间要求？** 何时必须上架？是短租（周/月）还是长租（年）？有没有硬截止日？
6. **地点要求？** 必须在哪个国家/区域？是否接受中国境内或第三地交付？
7. **网络要求？** 带宽、时延、专线、公网出口、IP 资源、跨境链路？
8. **数据驻留与合规要求？** 数据能否出境？是否涉及个人信息/重要数据/行业监管？是否需要本地实体签约？
9. **预算量级？** 年度/项目预算范围（量级即可）、计价偏好（卡时/包月/年包）、账期要求？
10. **决策链？** 谁发起、谁评估、谁签字、预算谁批？采购流程与周期？
11. **现有供应商？** 现在用谁、为什么考虑更换/补充、最不满意什么？
12. **成功标准？** 交付时间、稳定性、成本、支持响应——哪个是第一优先？

**合格需求判定（至少满足）**：明确卡型/规模或可换算容量、训练/推理、时间窗、地点与网络、数据驻留要求、有决策人或明确转介路径（源：经营框架-开口到收款.md §3）。不达标的，只保留为「潜在机会」，不进入匹配。

---

## 8. 反对意见应答（8 条）

| # | 反对意见 | 应答原则 | 英文应答（可直接照读） | 中文注释 |
|---|----------|----------|------------------------|----------|
| 1 | 你们是谁？没听过 | 诚实 + 具体，不吹规模 | "We're a new, specialized team focused on China-side GPU supply for overseas demand. We're not a marketplace or a reseller. Our value is verification and coordination — you can judge us on the shortlist we produce." | 不装大公司；不编客户；用「你可以用产出判断我们」转移信任问题。 |
| 2 | 你们没有案例 | 承认现状 + 给过程保障 | "Fair — we're early and don't have public case studies yet. What we can offer is a transparent process: verified specs, written comparison, and no fee unless a deal closes on agreed terms." | 绝不虚构案例；用流程与条款降低对方风险。 |
| 3 | 为什么通过你们，不直接找供应商？ | 讲筛选与协调价值 | "You can absolutely go direct. What we add is a pre-filtered shortlist, side-by-side delivery/network comparison, and coordination across time zones — so your team spends hours, not weeks." | 不贬低直采；强调省时间与减少信息不对称。 |
| 4 | 价格会不会更贵？ | 明确不加价 + 收费方披露 | "No. Your capacity price is set directly with the supplier — we don't mark it up. Our fee, if any, is agreed in writing with the paying party before introduction, and we disclose it if both sides pay." | 不报具体比例；明确「不加价」与「书面约定」。 |
| 5 | 数据安全怎么保证？ | 不承诺，讲边界与转交 | "We don't handle your data or workloads. Data residency and security are agreed between you and the operator, and we flag the questions to ask. For regulated data, we'd bring in counsel before proceeding." | 我方不碰数据；不宣称「安全合规」。 |
| 6 | 跨境合规怎么办？ | 只提示、不结论 | "Cross-border compute and data flows have legal constraints we don't opine on. We map the questions, identify what needs local counsel, and won't push a structure that looks problematic." | 严守 BRIEF：不承诺合法/合规/可执行。 |
| 7 | 交付风险怎么控制？ | 用核验与合同条款回答 | "We verify availability and delivery timelines before introduction, and we recommend milestone-based contract terms. We don't guarantee delivery — the operator does, in the contract." | 不替供应商担保；把风险落回合同。 |
| 8 | 和直接找供应商有什么不同？ | 一句话差异 + 退出机制 | "We do the verification and comparison work up front, and we tell you when something doesn't fit. If our shortlist adds nothing, you've lost one call." | 低承诺、可退出；不纠缠。 |

---

## 9. 商务跟进流程与 CRM 字段

**跟进节奏**：首触后 24h 内发资料（一页纸，待批准版）→ 72h 内约访谈 → 7 天内完成 12 问 → 14 天内给出匹配判断（配/不配 + 原因）→ 30 天内进入商务阶段或关闭。每次跟进记录渠道、摘要、对方承诺、下一步、证据链接。

**需求阶段流转**（BRIEF §9）：`LEAD → RESEARCHED → NEEDS_VERIFICATION → VERIFIED → QUALIFIED → MATCHED → COMMERCIAL → WON/LOST`；另有 `INSUFFICIENT_INFO / PAUSED / EXPIRED / NOT_MATCHED / CEO_PENDING`。禁止跳级。

### 表 1：`demand_opportunities`（需求机会）核心字段

| 字段 | 说明 |
|------|------|
| opportunity_id | 需求编号 |
| company_name / website | 公司名称与官网 |
| country_region | 国家/地区 |
| segment | 客户类型（第 1 节八类） |
| signal_type / signal_source_url / signal_date | 信号类型、来源链接、日期 |
| inferred_need | 推断需求（一句话） |
| workload_type | 训练/推理/混合/视频/仿真 |
| gpu_preference | 卡型偏好与可否替代 |
| scale | 卡数/集群规模/调用量 |
| timeline | 上架时间窗与租期 |
| location_requirement | 地点要求 |
| network_requirement | 带宽/时延/专线 |
| data_residency | 数据驻留与合规要求 |
| budget_range | 预算量级（非精确报价） |
| decision_maker_role / decision_chain | 决策人岗位与链路 |
| current_supplier | 现有供应商 |
| success_criteria | 成功标准 |
| stage | BRIEF §9 状态 |
| trust_level | HIGH/MEDIUM/LOW/UNVERIFIED |
| owner / next_action / next_due | 负责人、下一步、截止日 |
| source_urls / evidence_note | 证据链 |

### 表 2：`commercial_opportunities`（商业机会）核心字段

| 字段 | 说明 |
|------|------|
| commercial_id | 商业机会编号 |
| demand_id / supply_id | 关联需求与供给 |
| match_reason | 为什么配（必填，写清规格/地点/时限/网络/合规） |
| mismatch_reason | 为什么不配（如适用） |
| proposed_model | A/B/C/D/E 合作模式（见 COOPERATION_MODELS.md） |
| fee_type_hypothesis | 费用类型假设（不写死比例） |
| approval_status / ceo_decision | CEO 审批状态与结论 |
| contract_status | 无/起草/律师审核/已签 |
| trigger_event | 合同签署或首笔付款（孰早） |
| settlement_status | 未触发/待开票/已开票/已收款 |
| conflict_disclosure | 双付费/利益冲突披露记录 |
| next_action / owner | 下一步与负责人 |

**记录纪律**：CRM 中不写未经证实的猜测；不确定写「待确认」；对外发送前必须经 CEO 批准；敏感联系人/报价/合同只进 `private/`。

---

## 10. 红线清单

- ❌ 把公开线索写成「客户」「在谈」「意向明确」。
- ❌ 编造案例、客户名、成交额、团队规模、合作背书。
- ❌ 首轮报价或承诺具体费率。
- ❌ 承诺「价格更低」「保证交付」「合规没问题」。
- ❌ 购买个人数据、群发未经批准的邮件、使用爬虫抓取联系人。
- ❌ 未获 CEO 批准擅自发送任何对外材料。
- ✅ 正确姿势：信号 → 建档 → 核验 → 12 问 → 匹配判断 → 协议 → CEO 介绍 → 跟进留痕。

## 11. 变更记录

| 版本 | 日期 | 变更 | 审批 |
|------|------|------|------|
| v1.0 | 2026-11-16 | 初稿建立；对齐 PROJECT_BRIEF v1.0、CEO 2026-11-16 任务书 | 待 CEO 审批 |

> 配套：`SUPPLIER_ACQUISITION_PLAYBOOK.md`（供给端）、`COOPERATION_MODELS.md`（模式）、`PRICING_AND_FEE_FRAMEWORK.md`（收费）、`docs/03_sales/`（双语材料，均待批准）。
