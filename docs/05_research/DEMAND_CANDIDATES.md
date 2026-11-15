# 海外 AI 算力需求候选（第一轮）

- 项目：中国算力国际化项目（CCGS）
- 文件编号：DEMAND-R1
- 编制：海外需求与中国供给研究组
- 编制日期：2026-11-16（Asia/Shanghai）
- 证据获取时间：2026-11-16
- 覆盖范围：5 个海外需求候选（DEM-R1-001 至 DEM-R1-005）
- 配套数据：`data/research/demand_candidates.csv`、`data/research/evidence_registry.csv`
- 重要声明：本文件全部内容来自公开信息，**不构成任何采购意向、合作授权或报价**。文中「推断」字样均为研究假设，不得作为对外表述。

## 0. 分级与证据规则（本轮执行口径）

| 分级 | 定义 | 本轮是否可升级 |
|---|---|---|
| 公开线索 | 有公开信息表明该主体存在与算力相关的需求或扩张动作，但未核实其采购意向与决策链 | 否 |
| 推断需求 | 需求由公开动作间接推断（如已运营 GPU 云、公开模型训练计划），缺少直接的扩容/采购公开信息 | 否 |
| 潜在机会 | 在公开线索基础上叠加我方供给能力与地缘/合规判断形成的可跟进机会 | 否 |
| 已核实需求 | 由一手联系人/正式文件确认 | 本轮无 |
| 已合格商机 | 经资格核验并获 CEO 授权 | 本轮无 |

本轮 5 个候选均停留于「公开线索 / 推断需求」。任何对外接触、报价、签约、收款均由 CEO 保留。

## 1. 候选总览

| 编号 | 公司 | 地区 | 类型 | 需求信号强度 | 线索分级 | 与我方相关性 |
|---|---|---|---|---|---|---|
| DEM-R1-001 | Mistral AI | 法国巴黎 | 前沿大模型公司 | 强（自建数据中心） | 公开线索 | 低 |
| DEM-R1-002 | Yotta Data Services | 印度孟买 | AI 云/数据中心 | 强（万卡部署、扩张、IPO） | 公开线索 | 中低 |
| DEM-R1-003 | Cassava Technologies | 英国伦敦（泛非运营，待核） | 数字基础设施/GPUaaS | 中（埃及 AI factory） | 公开线索 | 中 |
| DEM-R1-004 | Lintasarta | 印尼雅加达 | 运营商系 ICT/GPUaaS | 中（GPU Merdeka 已上线，扩容为推断） | 推断需求 | 高 |
| DEM-R1-005 | Sarvam AI | 印度班加罗尔 | 主权大模型公司 | 中（万亿参数计划） | 推断需求 | 低 |

---

## 2. DEM-R1-001 Mistral AI

### 2.1 基本信息

- 候选编号：DEM-R1-001
- 公司名：Mistral AI
- 官网：https://mistral.ai
- 总部/地区：法国巴黎
- 业务描述：欧洲前沿大模型公司，开发 Mistral 系列开放权重/商用大模型，提供 API、企业部署与定制模型服务。

### 2.2 需求信号

1. **自建 AI 数据中心**：2026-02-11，Mistral AI 与北欧数据中心运营商 EcoDataCenter 联合宣布，将在瑞典 Borlänge 建设 AI 数据中心，投资额约 **12 亿欧元**，计划 **2027 年开放**，部署 **NVIDIA 最新 Vera Rubin GPU**。该中心被表述为 Mistral 在法国以外的首个 AI 基础设施投资，数据将存储在欧洲（EV-R1-001）。
2. **媒体二次报道**：Bloomberg 同日报道「Mistral 投资 12 亿欧元建设瑞典 AI 数据中心」（EV-R1-002，标题可见、正文付费墙）；AI Business 报道规模约 14 亿美元（EV-R1-003，页面未能打开）。
3. **派生信号**：自建数据中心意味着长期 GPU 采购、机房运维、电力与网络采购需求；但公开信息未披露 GPU 数量、采购方式（自购/租赁/融资租赁）与供应商名单。

### 2.3 线索分级：公开线索

理由：公司主动公开了资本开支、选址与代际选择，需求真实存在；但尚无任何证据显示其会向第三方（尤其中国供应商）采购算力或服务。**不得升级**。

### 2.4 可能的需求规格（全部为推断）

| 维度 | 推断内容 | 说明 |
|---|---|---|
| 卡型 | NVIDIA Vera Rubin 世代（GB300/Rubin 级） | 来自官方新闻稿明确表述 |
| 规模 | 未披露；按 12 亿欧元资本开支推断为「数十 MW 级」AI 工厂 | 不换算卡数，避免编造 |
| 负载 | 训练 + 推理混合 | 前沿模型公司通常两者兼有 |
| 地点 | 瑞典 Borlänge（2027） | 官方信息 |
| 数据驻留 | 欧洲境内 | 官方表述与欧盟监管环境 |
| 采购形态 | 自建（可能含融资租赁/能源合同） | 推断 |

### 2.5 证据

| 证据编号 | 来源标题 | URL | 发布者 | 发布时间 | 信任度 |
|---|---|---|---|---|---|
| EV-R1-001 | Mistral AI and EcoDataCenter Partner to Build AI-focused Data Center in Sweden | https://ecodatacenter.tech/press/mistral-ai-and-ecodatacenter-partner-to-build-ai-focused-data-center-in-sweden-3431886 | EcoDataCenter | 2026-02-11 | HIGH |
| EV-R1-002 | Mistral Invests €1.2 Billion in Swedish AI Data Center Buildout | https://www.bloomberg.com/news/articles/2026-02-11/mistral-invests-1-2-billion-in-swedish-ai-data-center-buildout | Bloomberg | 2026-02-11 | MEDIUM |
| EV-R1-003 | Mistral Cites Euro Vision With $1.4B for Swedish AI Data Center | https://prod.aibusiness.com/generative-ai/mistral-cites-euro-vision-with-1-4b-for-swedish-ai | AI Business | 未标注 | LOW |

独立来源数：2 条可核（EV-001 一手、EV-002 标题级），满足「≥2 条独立证据」的最低要求但仅限「投资建设」这一主张；「采购需求」本身仍为推断。

### 2.6 待确认事项

1. 数据中心的 IT 负载、GPU 数量、机柜功率是否已确定？是否已下订单？
2. 采购主体是 Mistral、EcoDataCenter，还是双方合资的项目公司（SPV）？
3. 是否只接受 NVIDIA 平台？对非 NVIDIA 推理是否有降本诉求？
4. 是否有第三方推理/token 服务外包需求（非训练）？
5. 项目是否受欧盟补贴、美国出口管制或「欧洲主权 AI」条件的约束？
6. 2027 年开放前的采购窗口与招标方式（直采/EPC/融资租赁）？

### 2.7 推荐下一步

- 列为**观察级（P4）**，不主动接触。
- 跟踪其 2027 年前的资本开支披露、数据中心运维/GPU 采购招聘、与 EcoDataCenter 的合同结构。
- 若其推理侧出现明显成本压力，再评估「欧洲境外训练 + 欧洲境内推理」的合规切分，但优先级最低。

### 2.8 与我方服务的相关性：**低**

理由：①欧洲主权 AI 叙事与数据驻留要求指向「欧洲境内、NVIDIA 平台」；②Mistral 的技术栈与融资结构高度绑定美国芯片生态；③中国供应商进入其训练侧在出口管制与政治接受度上均不可行；④仅在「非敏感推理 token 转售」层面存在理论空间，但与数据驻留直接冲突，短期不建议投入。

---

## 3. DEM-R1-002 Yotta Data Services

### 3.1 基本信息

- 候选编号：DEM-R1-002
- 公司名：Yotta Data Services（Hiranandani 集团旗下）
- 官网：https://yotta.com
- 总部/地区：印度孟买；数据中心位于印度境内（具体园区与 GPU 云产品以官网为准）
- 业务描述：印度数据中心与云服务商，运营 Shakti Cloud GPU 云，面向印度主权 AI 与企业 AI 提供算力。

### 3.2 需求信号

1. **万卡级 GPU 部署**：Yotta 官网新闻稿称「Yotta Deploys 20,000+ NVIDIA Blackwell GPUs in India」（EV-R1-004）。该页面正文被导航内容淹没，仅标题与主题可核，属**官网自述**。
2. **大规模扩张计划**：ET EnterpriseAI 2026-06-23 报道「Yotta scales up AI bet with $6 billion expansion plan」（EV-R1-005，正文抓取失败、标题可核）。
3. **资本动作**：Bloomberg 2026-08-28 报道「Yotta Plans IPO 'Very Soon' to Keep Up With AI Demand」（标题见搜索结果；链接未留存，故未单列为证据）。Yotta 设有投资者关系页（EV-R1-006），定位「Building India's Sovereign AI & Cloud Infrastructure」。
4. **派生信号**：若 2 万卡部署与 60 亿美元扩张属实，则其持续需要 GPU、机房、电力、网络与运维；但采购对象与是否开放第三方供给无公开信息。

### 3.3 线索分级：公开线索

理由：扩张与资本开支公开，需求方向明确；但「向中国供应商采购」无任何公开证据，且其现有栈为 NVIDIA。**不得升级**。

### 3.4 可能的需求规格（全部为推断）

| 维度 | 推断内容 | 说明 |
|---|---|---|
| 卡型 | NVIDIA Blackwell（GB200/GB300 级）为主 | 官网标题与行业惯例 |
| 规模 | 万卡级（官网称 20,000+，未核） | 官网自述，未取得正文细节 |
| 负载 | 训练 + 推理（Shakti Cloud 对外售卖） | 业务模式推断 |
| 地点 | 印度境内（孟买/大诺伊达等，待核） | 数据中心业务 |
| 数据驻留 | 印度境内 | 主权 AI 定位 |
| 采购形态 | 自购 + 融资/IPO 资金 | 推断 |

### 3.5 证据

| 证据编号 | 来源标题 | URL | 发布者 | 发布时间 | 信任度 |
|---|---|---|---|---|---|
| EV-R1-004 | Yotta Deploys 20,000+ NVIDIA Blackwell GPUs in India | https://yotta.com/press-releases/yotta-to-deploy-20000-nvidia-blackwell-ultra-gpus/ | Yotta | 未标注 | MEDIUM |
| EV-R1-005 | Yotta scales up AI bet with $6 billion expansion plan | https://enterpriseai.economictimes.indiatimes.com/news/industry/yotta-to-invest-6-billion-in-ai-infrastructure-expansion/131906932 | ET EnterpriseAI | 2026-06-23 | MEDIUM |
| EV-R1-006 | Yotta Data Services – Investor Relations / Building India's Sovereign AI & Cloud Infrastructure | https://yotta.com/ir/index.html | Yotta | 未标注 | MEDIUM |

独立来源数：3 条（均为标题级/自述级），满足数量要求；但「20,000+ 卡是否已交付」未被独立核实，标注为**未核实**。

### 3.6 待确认事项

1. 20,000+ Blackwell 是已交付、已下单还是规划目标？分批时间表？
2. 60 亿美元扩张的资金来源（IPO/债务/战投）与时间表？
3. 是否全部锁定 NVIDIA？是否评估 AMD 或非美系芯片用于推理？
4. IPO 后是否披露供应链与客户集中度？
5. 是否服务印度以外客户（中东/东南亚/非洲）？跨境数据规则如何？
6. 电力与并网是否构成瓶颈？是否有自备电厂/绿电？
7. 采购决策链（Yotta 本身 vs Hiranandani 集团）？

### 3.7 推荐下一步

- 列为**观察级（P3）**，不主动接触。
- 跟踪其 IPO 招股书/年报披露的资本开支、GPU 供应商与客户结构。
- 若其公开表示需要「非 NVIDIA 推理补充」或「海外节点」，再评估合作可能。

### 3.8 与我方服务的相关性：**中低**

理由：①印度对中资科技企业审查趋严（需律师确认），整机/芯片进入难度高；②Yotta 自身是算力供给方，且已深度绑定 NVIDIA；③其 IPO 与扩张可能带来边缘机会（如非敏感推理、海外节点转售），但短期不具备可操作性；④印度市场体量大，值得作为长期观察对象而非首轮目标。

---

## 4. DEM-R1-003 Cassava Technologies

### 4.1 基本信息

- 候选编号：DEM-R1-003
- 公司名：Cassava Technologies
- 官网：https://www.cassavatechnologies.com
- 总部/地区：公开资料常表述为英国伦敦总部、泛非运营（**总部所在地待核**）；业务覆盖非洲多国
- 业务描述：泛非数字基础设施集团，业务含光纤网络、数据中心、云与 AI 服务；据第三方报道为非洲首家 NVIDIA 云合作伙伴。

### 4.2 需求信号

1. **埃及首个国家 AI factory**：2026-09，Cassava 与 Vodafone Business 在埃及启动「埃及首个国家 AI factory」，通过 NVIDIA 加速计算提供全栈 AI 基础设施，以 **GPU-as-a-Service** 模式面向政府与企业，**数据驻留埃及**（EV-R1-007 一手、EV-R1-008 独立报道）。
2. **投资规模**：Engineering News 报道 Vodafone 埃及本财年投资超 **EGP 200 亿**、28 年累计超 **EGP 1,250 亿**（EV-R1-008）；该数字为 Vodafone 侧投资，不直接等于 Cassava 采购额。
3. **非洲 AI 基础设施布局**：Cassava 官网另有《The Supercomputers Shaping Africa's AI Future》一文（EV-R1-009，页面未能打开），显示其持续建设 AI 算力叙事。
4. **派生信号**：GPUaaS 运营方需要持续扩容 GPU、机房与网络；但 Cassava 与 NVIDIA 的合作深度、是否排他、采购主体均未公开。

### 4.3 线索分级：公开线索

理由：项目已公开启动，需求（GPU 容量）真实；但采购来源、规模、时间表未公开。**不得升级**。

### 4.4 可能的需求规格（全部为推断）

| 维度 | 推断内容 | 说明 |
|---|---|---|
| 卡型 | NVIDIA 加速计算（具体代际未披露） | 官方表述「NVIDIA accelerated computing」 |
| 规模 | 未披露（国家 AI factory 级，推断为数十至数百卡起步） | 不编造数字 |
| 负载 | GPUaaS：推理为主 + 训练 | 业务模式推断 |
| 地点 | 埃及（首个），可能扩展至南非等 | 官方信息 |
| 数据驻留 | 埃及境内 | 官方明确 |
| 采购形态 | 与 Vodafone/NVIDIA 联合建设，可能含融资 | 推断 |

### 4.5 证据

| 证据编号 | 来源标题 | URL | 发布者 | 发布时间 | 信任度 |
|---|---|---|---|---|---|
| EV-R1-007 | Launch of Egypt's First National AI Factory in Partnership with Vodafone Business | https://www.cassavatechnologies.com/launch-of-egypt-first-national-ai-factory-in-partnership-with-vodafone-business/ | Cassava Technologies | 2026-09 | HIGH |
| EV-R1-008 | Cassava, Vodafone launch Egypt's first national AI factory | https://www.engineeringnews.co.za/article/cassava-vodafone-launch-egypts-first-national-ai-factory-2026-09-11 | Engineering News（Natasha Odendaal） | 2026-09-11 | HIGH |
| EV-R1-009 | The Supercomputers Shaping Africa's AI Future | https://www.cassavatechnologies.com/the-supercomputers-shaping-africas-ai-future/ | Cassava Technologies | 未标注 | MEDIUM |

独立来源数：2 条（一手 + 独立第三方），满足要求。

### 4.6 待确认事项

1. 埃及 AI factory 的 IT 负载、GPU 数量与分批交付时间？
2. Cassava 是运营方、集成商还是转售方？采购合同主体是哪家实体？
3. 与 NVIDIA 的合作是否排他？是否允许非 NVIDIA 卡用于非敏感负载？
4. 埃及数据驻留的具体规则（境内存储/处理/跨境审批）？
5. 项目融资结构（Vodafone/非洲开发银行/出口信贷）是否限制供应商来源？
6. 是否有南非/肯尼亚等后续节点计划？
7. 对中国设备/服务的政策接受度与安全审查要求？

### 4.7 推荐下一步

- 列为**非洲区域重点观察（P2）**，不主动接触。
- 核验 Cassava 与 NVIDIA 合作协议性质、埃及项目采购主体与融资条款。
- 评估「埃及/南非二线节点 + 中国推理卡/整机」的理论空间，但须先过合规与政治风险筛查。

### 4.8 与我方服务的相关性：**中**

理由：①非洲市场对成本敏感、对中国技术接受度相对较高；②数据中心运营商天然需要多源供给；③但 Cassava 的 NVIDIA 合作伙伴身份、数据驻留要求、以及西方融资/伙伴结构构成硬约束；④其自身支付能力与项目规模未核，短期只适合观察与补证。

---

## 5. DEM-R1-004 Lintasarta

### 5.1 基本信息

- 候选编号：DEM-R1-004
- 公司名：Lintasarta（PT Aplikanusa Lintasarta）
- 官网：https://www.lintasarta.net
- 总部/地区：印尼雅加达
- 母公司：Indosat Ooredoo Hutchison（印尼电信集团）旗下 ICT 服务商
- 业务描述：印尼企业 ICT、连接、云与数据中心服务商，2024 年起以「GPU Merdeka」进入 GPU 云市场。

### 5.2 需求信号

1. **GPU Merdeka 已上线**：2024-08-21，Lintasarta 推出 GPU Merdeka——基于 NVIDIA Sovereign AI Cloud 的 GPU-as-a-Service，**8×H100 SXM/服务器、单机架 20kW、3.2Tbps InfiniBand**，全部基础设施位于印尼（EV-R1-010，国家通讯社 ANTARA）。
2. **主权 AI 定位**：Lintasarta 官网推出「AI Merdeka」项目，强调赋能印尼 AI 主权（EV-R1-011）。
3. **与 NVIDIA 合作**：官网另有与 NVIDIA 合作加速印尼 AI 采用的报道（EV-R1-012，未打开）。
4. **派生信号（推断）**：作为 GPUaaS 运营商，其商业模式依赖持续扩容与利用率；但公开信息只有首批产品参数，**没有二期扩容、采购量或招标公告**，因此「扩容需求」属推断。

### 5.3 线索分级：推断需求

理由：Lintasarta 是算力**供给方**，其自身对 GPU 的采购需求只能从其运营模式与主权 AI 定位推断；公开信息未给出扩容时间表、规模或采购方式。**不得升级**。

### 5.4 可能的需求规格（全部为推断）

| 维度 | 推断内容 | 说明 |
|---|---|---|
| 卡型 | 现有 H100 SXM；扩容可能为 H200/Blackwell 或国产/AMD 降本方案 | 推断，无公开信息 |
| 规模 | 首批产品规模未披露；扩容推断为「数十至数百卡」级 | 不编造数字 |
| 负载 | GPUaaS：训练 + 推理，政府/企业客户 | 产品定位 |
| 地点 | 印尼境内（雅加达等） | 官方明确「全部基础设施在印尼」 |
| 数据驻留 | 印尼境内 | 主权 AI 叙事 |
| 采购形态 | 设备采购/租赁/联合运营 | 推断 |

### 5.5 证据

| 证据编号 | 来源标题 | URL | 发布者 | 发布时间 | 信任度 |
|---|---|---|---|---|---|
| EV-R1-010 | Lintasarta Luncurkan GPU Merdeka | https://megapolitan.antaranews.com/berita/304967/lintasarta-luncurkan-gpu-merdeka | ANTARA | 2024-08-21 | HIGH |
| EV-R1-011 | Lintasarta Introduced "AI Merdeka" to Empowering Indonesia's AI Sovereignty | https://www.lintasarta.net/en/news/lintasarta-introduced-ai-merdeka-to-empowering-indonesias-ai-sovereignty/ | Lintasarta | 未标注 | MEDIUM |
| EV-R1-012 | Kolaborasi Lintasarta dan NVIDIA untuk Percepat Adopsi AI di Indonesia | https://www.lintasarta.net/berita/kolaborasi-lintasarta-dan-nvidia-untuk-percepat-adopsi-ai-di-indonesia/ | Lintasarta | 未标注 | LOW |

独立来源数：3 条（其中 1 条国家级通讯社、2 条官网），满足要求；但均为 2024 年信息，2025–2026 年扩容动态缺失。

### 5.6 待确认事项

1. GPU Merdeka 当前实际装机量、利用率与客户结构？
2. 是否有二期扩容计划、时间表与预算？
3. 采购决策链在 Lintasarta 还是 Indosat Ooredoo Hutchison 集团？
4. 是否接受非 NVIDIA 卡（昇腾/AMD/其他）用于推理或训练？
5. 印尼数据驻留与跨境规则对「境外算力 + 境内数据」的具体要求？
6. 对中国供应商/设备的政策接受度与安全审查流程？
7. 合同主体、结算币种、付款条件与融资安排？

### 5.7 推荐下一步

- **优先级最高（P1）**，但仅限内部研究与补证，不对外接触。
- 补全 2025–2026 年 Lintasarta/Indosat 的 AI 基础设施公开动态（年报、发布会、招聘）。
- 由 CEO 决定是否经合规渠道进行试探性接触；接触前准备「印尼本地节点 + 多代际 GPU 推理」的方案假设（非报价）。

### 5.8 与我方服务的相关性：**高**

理由：①东南亚地理邻近、成本敏感、区域 GPU 云需求增长；②Lintasarta 已有 GPUaaS 运营经验与主权 AI 叙事，作为需求方（扩容）与我方供给（卡时/整机/Token）能力互补；③印尼对中国技术接受度总体高于印度/欧洲；④主要风险是其现有栈为 NVIDIA H100 + InfiniBand，迁移成本与合规审查需核验。

---

## 6. DEM-R1-005 Sarvam AI

### 6.1 基本信息

- 候选编号：DEM-R1-005
- 公司名：Sarvam AI
- 官网：https://www.sarvam.ai
- 总部/地区：印度班加罗尔
- 业务描述：印度主权大模型公司，面向 14 亿人的多语言基础模型与应用，获印度政府与 NVIDIA 支持。

### 6.2 需求信号

1. **万亿参数模型计划**：Financial Express 报道 Sarvam 计划在 6 个月内训练万亿参数 AI 模型（EV-R1-014，正文抓取失败、标题可核）。
2. **NVIDIA 投资**：India Today 2026-08-05 报道「Sarvam AI gets Nvidia funding, days after announcing plans to make 1 trillion parameter AI model」（EV-R1-015，标题可核）。
3. **政府支持**：ET Morning Dispatch 报道「Sarvam gets state backing」（EV-R1-016，标题可核）。
4. **NVIDIA 案例**：NVIDIA 官网将 Sarvam 列为「Sovereign AI for 1.4 Billion People」案例（EV-R1-013，正文截断）。
5. **派生信号（推断）**：万亿参数训练需要万卡级算力；但公开信息显示其供应高度绑定 NVIDIA，是否寻求非 NVIDIA 降本无公开证据。

### 6.3 线索分级：推断需求

理由：「训练算力需求」由公开的模型计划推断，且供应方向已明显偏向 NVIDIA；没有公开的采购/扩容/招标信息。**不得升级**。

### 6.4 可能的需求规格（全部为推断）

| 维度 | 推断内容 | 说明 |
|---|---|---|
| 卡型 | NVIDIA（受投资方影响）；推理可能多芯片 | 推断 |
| 规模 | 万亿参数训练 → 万卡级（推断） | 不换算具体数字 |
| 负载 | 训练 + 大规模多语言推理 | 业务模式 |
| 地点 | 印度境内 | 主权 AI 要求 |
| 数据驻留 | 印度境内 | 主权 AI 要求 |
| 采购形态 | NVIDIA 投资 + 政府支持 + 云租用 | 推断 |

### 6.5 证据

| 证据编号 | 来源标题 | URL | 发布者 | 发布时间 | 信任度 |
|---|---|---|---|---|---|
| EV-R1-013 | Sovereign AI for 1.4 Billion People（Sarvam 案例） | https://www.nvidia.com/en-us/case-studies/sarvam-sovereign-ai/ | NVIDIA | 未标注 | MEDIUM |
| EV-R1-014 | Sarvam plans trillion-parameter AI model in 6 months | https://www.financialexpress.com/life/technology/sarvam-plans-trillion-parameter-ai-model/4306841/ | Financial Express | 未标注 | MEDIUM |
| EV-R1-015 | Sarvam AI gets Nvidia funding, days after announcing plans to make 1 trillion parameter AI model | https://www.indiatoday.in/technology/news/story/sarvam-gets-nvidia-funding-days-after-announcing-plans-to-make-1-trillion-parameter-ai-model-2964057-2026-08-05 | India Today | 2026-08-05 | MEDIUM |
| EV-R1-016 | Sarvam gets state backing; Andy Jassy's India visit | https://m.economictimes.com/tech/newsletters/morning-dispatch/sarvam-gets-state-backing-andy-jassys-india-visit/amp_articleshow/131980088.cms | Economic Times | 未标注 | LOW |

独立来源数：4 条（均为标题级/案例级），数量满足；但「训练是否已启动、算力从何而来」未被独立核实。

### 6.6 待确认事项

1. 万亿参数模型是否已启动？训练集群位于何处、规模多大？
2. NVIDIA 投资是否附带算力供应条款/排他条款？
3. 是否接受非 NVIDIA 芯片用于推理或微调？
4. 印度「主权 AI」采购规则是否排除中国供应商？
5. 数据驻留与跨境传输的具体要求？
6. 政府支持的形式（补贴/算力/数据）与附加条件？

### 6.7 推荐下一步

- **不推进（P5）**，仅作为「印度主权 AI 需求大但合规壁垒最高」的样本保留。
- 跟踪其模型发布与融资条款；若印度政策或供应结构变化，再评估推理侧合作。

### 6.8 与我方服务的相关性：**低**

理由：①NVIDIA 投资 + 主权 AI 定位使供应绑定；②印度对中国科技企业审查趋严（需律师确认）；③数据驻留与「印度境内训练」要求与中国算力跨境服务直接冲突；④训练侧基本无空间，推理侧亦受合规限制。

---

## 7. 未纳入候选的观察对象（及原因）

| 对象 | 观察到的信号 | 未纳入原因 |
|---|---|---|
| Manus（新加坡） | 2025 年初将总部从中国迁至新加坡以使用 H100/H200 集群；2025 年底 Meta 宣布收购（EV-R1-030） | 已被收购、主体归属不清；且「为算力迁址」本身是重要教训，但不再是独立需求方 |
| Luma AI（美国） | 官网称生产推理跑在 AMD + TensorWave 上（EV-R1-031，页面未能打开）；Semafor 报道视频 AI 公司把算力转向沙特（EV-R1-032，页面未能打开） | 信息不足，无法形成可核需求；列入下一轮观察 |
| HUMAIN（沙特）、G42（阿联酋）、Sea Limited（新加坡）、Nebius（欧洲）、GoTo（印尼） | 历史档案线索（未核） | 本轮未复核；下一轮优先补证（尤其 HUMAIN/G42 的主权 AI 采购） |
| TensorWave（美国） | 2026-06 完成 3.5 亿美元 B 轮、估值 15.5 亿美元，AMD 算力（EV-R1-033） | 是算力供给方而非需求方；作为「非 NVIDIA 算力」市场信号观察 |

---

## 8. 本轮结论

1. 海外需求真实存在，但**中国供应商可进入的窗口集中在东南亚、中东、非洲的区域性 GPUaaS/主权 AI 运营商**，而非欧洲前沿模型公司或印度主权 AI 旗舰。
2. 5 个候选中，只有 **Lintasarta（印尼）** 具备「需求可推断 + 地缘可进入 + 产品形态互补」三项同时成立的条件，应作为首轮唯一重点。
3. **Cassava（非洲）** 值得作为第二观察对象，但需先解决 NVIDIA 绑定与数据驻留两个硬约束。
4. **Yotta、Sarvam、Mistral** 短期均不具备可操作性：Yotta 是供给方且绑定 NVIDIA，Sarvam 受印度主权 AI 与 NVIDIA 投资约束，Mistral 受欧洲数据驻留与地缘约束。
5. 所有候选的「采购意向、预算、决策人、时间窗」均未核实；本轮不产生任何对外动作。

## 9. 证据与数据一致性

- 本文件引用的全部证据编号见 `EVIDENCE_REGISTRY.md` 与 `data/research/evidence_registry.csv`。
- 需求候选结构化数据见 `data/research/demand_candidates.csv`。
- 证据信任度分级：HIGH（一手官方或独立权威媒体，已打开全文）/ MEDIUM（标题级、转载、官网自述）/ LOW（页面未能打开、仅搜索标题）。
