# 商务澄清清单 — MATCH-20261102-001

> **内部草稿 · 不对客自动发出。**  
> 脱敏版。含联系方式或报价数字的问答原文 → `99-敏感商务_仅本项目/COMM-…`。外发澄清邮件须 Arthur 确认。
>
> 性质：公开线索上的**内部方法样例**，非可成交订单。澄清完成前**暂不商务试探 / 不外联**。

- 日期：2026-11-03（Asia/Shanghai）
- 对象侧：供应侧 SUP-20261102-001（阿里云）× 需求侧 DEM-20261102-009（GoTo Group）
- 关联 ID：MATCH-20261102-001；证据 B-E04 / B-E06 / B-E19

## 必须澄清（阻塞成交）
1. 需求侧是否存在可独立切分的 GPU / 推理容量需求，还是纯 PaaS / SaaS 迁移？（DEM-009 未披露 GPU 规格）
2. 公开战略合作是否排他，第三方撮合 / 介绍是否可介入？（平台不得假设有中介空间）
3. 印尼数据驻留与本地交付约束是否写进公开采购或合同口径？

## 重要但非阻塞
1. 供应侧东南亚节点对第三方客户的可售形态（容量表 / 专线 / 合规声明）是否有公开文档可摘录？
2. B-E19 新闻稿之外，是否有可核验的交付里程碑（不含报价）？

## 已确认（脱敏摘要）
- 区域与产品线表面贴合：东南亚 + 云 / AI 服务采购叙事（见 MATCH 解释与档案字段）
- 无敏感联系人 / 报价字段入库；敏感指针：无

## 下次跟进
- 日期：2026-11-04（Asia/Shanghai）公开补搜已完成（见下文）；仍禁外联
- 动作：默认保持「候选 / 暂不推进」；可选由 Arthur 决定是否对其余 MATCH 复用同法
- 负责人：中国算力出海（内部）；外发须 Arthur 确认


## 公开补搜结论（2026-11-04 Asia/Shanghai，禁外联）

> 仅用公开网页/新闻稿回填阻塞项；未联系任何一方；仍非可成交订单。

### 阻塞项回答

1. **GPU/推理容量 vs PaaS/SaaS**  
   - 事实：Alibaba Cloud 新闻稿（B-E19）列明服务为 cloud computing、cloud-native database、networking、security、data analytics 等，**未披露 GPU 型号、集群规模或裸金属规格**。  
   - 事实：2025-06 Alibaba Cloud / GoTo 新闻稿称 GoTo Financial 已迁至 **Jakarta 本地数据中心**；技术栈公开叙述为 Landing Zone / Terraform IaC、微服务、MaxCompute、PolarDB 等（PaaS/数据平台迁移），仍无 GPU 规格。  
   - 推断（单独标出）：公开叙事主线是**存量云与金融基础设施迁移**，不能当作已确认的可切分 GPU 租约需求。  
   - 来源：https://www.alibabacloud.com/en/press-room/alibaba-and-goto-group-announce-strategic-partners?_p_lc=1 ；https://www.alibabacloud.com/en/press-room/goto-and-alibaba-cloud-complete-cloud-migration?_p_lc=1 ；Computer Weekly 客户面板报道 https://www.computerweekly.com/news/366626981/How-GoTos-high-stakes-cloud-shift-is-powering-Its-AI-future

2. **是否排他 / 第三方撮合可否介入**  
   - 事实：公开稿**未写 exclusive / sole provider**。  
   - 事实：DCD 报道 GoTo **同期另签五年期 Tencent Cloud**（PaaS 等），说明至少不是「只跟阿里」的单一排他叙事。  
   - 事实：稿件强调 Alibaba 作为股东维持持股承诺；**未提及中介、介绍人或第三方撮合席位**。  
   - 结论：公开材料**不能支持**「平台可介入介绍」；继续禁止假设有中介空间。  
   - 来源：https://www.datacenterdynamics.com/en/news/goto-group-signs-five-year-cloud-deals-with-tencent-and-alibaba-cloud/

3. **印尼数据驻留与本地交付**  
   - 事实：GoTo Financial 迁移公开声明「all data held within the country's borders / data sovereignty」，落点为 Alibaba Cloud **印尼（Jakarta）数据中心**（阿里云称在印尼有 3 个本地 DC）。  
   - 事实（法规背景，非本案合同原文）：印尼 PDP 法一般无全面本地化；但金融/支付等部门有本地机房与灾备要求（OJK 等），与「金融臂迁本地」公开叙事一致。  
   - 结论：对本案公开已完成的金融迁移，**本地交付是硬约束**；海外第三方机房介入空间公开材料为 0。  
   - 来源：同上 GoTo Financial 迁移稿；Alibaba Cloud Indonesia trust center https://www.alibabacloud.com/en/trust-center/indonesia?_p_lc=1

### 裁定（内部）

- 三条阻塞项用公开源可答到「规格缺口 + 无中介证据 + 本地交付」；**仍无法变成可报价 GPU 供需**。  
- **保持候选 / 暂不推进商务试探**；本条继续作为方法样例，不升级为可成交线索。  
- 未新建敏感联系人/报价字段。

### 下次跟进

- 默认：不再空追本案 GPU 规格；有新一手公开披露再开。  
- 可选（须 Arthur 点头）：把同方法用到其他 MATCH，或从 DEM/SUP 另选更像「可切分容量」的公开线索。
