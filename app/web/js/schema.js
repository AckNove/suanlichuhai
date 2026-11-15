/* CCGS 内部工作台 · schema.js
 * 字段元数据、状态枚举与徽标映射、状态机允许迁移、常用表单字段定义。
 * 仅做前端展示与输入辅助；后端为权威校验方（非法迁移返回 409）。
 * 加载顺序：core.js → api.js → ui.js → schema.js → views/*.js → app.js
 */
var CCGS = window.CCGS || (window.CCGS = {});

(function () {
  'use strict';

  var S = CCGS.schema = {};

  /* ============================================================
   * 值 → 中文标签
   * ============================================================ */
  var LABELS = {
    /* 公司/通用状态 */
    LEAD: '线索',
    RESEARCHED: '已研究',
    NEEDS_VERIFICATION: '待核验',
    VERIFIED: '已核验',
    QUALIFIED: '已确认资格',
    ACTIVE: '合作中',
    INSUFFICIENT_INFO: '信息不足',
    PAUSED: '暂停',
    EXPIRED: '已过期',
    REJECTED: '已拒绝',
    CEO_PENDING: '待 CEO 审批',
    MATCHED: '已匹配',
    COMMERCIAL: '商务推进中',
    WON: '已成交',
    LOST: '已丢单',
    NOT_MATCHED: '未匹配',
    PENDING: '待处理',
    IN_REVIEW: '审核中',
    APPROVED: '已批准',
    RETURNED: '已退回',
    DRAFT: '草稿',
    REVIEWED: '已复核',
    QUEUED: '排队中',
    RUNNING: '运行中',
    DONE: '已完成',
    BLOCKED: '受阻',
    FAILED: '失败',
    CANCELLED: '已取消',
    OPEN: '开放',
    DISCLOSED: '已披露',
    INTRODUCED: '已引荐',
    TERM_SHEET: '条款清单',
    CA: '协议谈判',
    CLOSED_WON: '已关闭（赢单）',
    CLOSED_LOST: '已关闭（输单）',
    NOT_STARTED: '未开始',
    SIGNED: '已签署',
    TERMINATED: '已终止',
    PUBLISHED: '已发布',
    ARCHIVED: '已归档',
    /* 匹配建议 */
    ADVANCE: '建议推进',
    NEED_MORE_INFO: '需补充信息',
    REJECT: '建议拒绝',
    /* 通用程度 */
    HIGH: '高',
    MEDIUM: '中',
    LOW: '低',
    UNVERIFIED: '未核验',
    /* 工作负载 */
    TRAINING: '训练',
    FINETUNE: '微调',
    INFERENCE: '推理',
    RENDERING: '渲染',
    SIMULATION: '仿真',
    MIXED: '混合',
    /* 公司类型 */
    SUPPLIER: '供应商',
    DEMANDER: '需求方',
    PARTNER: '合作伙伴',
    BOTH: '兼具',
    /* 线索等级 */
    PUBLIC_LEAD: '公开线索',
    INFERRED: '推断线索',
    POTENTIAL: '潜在线索',
    /* 其它 */
    COMPANY: '公司',
    DEMAND: '需求',
    SUPPLY: '供给',
    MATCH: '匹配',
    CLAIM: '主张',
    OTHER: '其他',
    ADVISORY: '顾问服务',
    INTRO: '引荐服务',
    CHANNEL: '渠道合作',
    JOINT: '联合方案',
    PMC: '项目管理',
    P0: 'P0 紧急',
    P1: 'P1 高',
    P2: 'P2 普通',
    P3: 'P3 低',
    CS: '客户成功',
    UNKNOWN: '未知'
  };

  var KINDS = {
    LEAD: 'blue', RESEARCHED: 'blue', NEEDS_VERIFICATION: 'amber', VERIFIED: 'green',
    QUALIFIED: 'green', ACTIVE: 'green', INSUFFICIENT_INFO: 'gray', PAUSED: 'gray',
    EXPIRED: 'red', REJECTED: 'red', CEO_PENDING: 'amber', MATCHED: 'blue',
    COMMERCIAL: 'purple', WON: 'green', LOST: 'red', NOT_MATCHED: 'gray',
    PENDING: 'amber', IN_REVIEW: 'amber', APPROVED: 'green', RETURNED: 'amber',
    DRAFT: 'blue', REVIEWED: 'blue', QUEUED: 'blue', RUNNING: 'cyan', DONE: 'green',
    BLOCKED: 'amber', FAILED: 'red', CANCELLED: 'gray', OPEN: 'blue',
    DISCLOSED: 'purple', INTRODUCED: 'purple', TERM_SHEET: 'purple', CA: 'purple',
    CLOSED_WON: 'green', CLOSED_LOST: 'red', NOT_STARTED: 'gray', SIGNED: 'green',
    TERMINATED: 'red', PUBLISHED: 'green', ARCHIVED: 'gray',
    ADVANCE: 'green', NEED_MORE_INFO: 'amber', REJECT: 'red',
    HIGH: 'green', MEDIUM: 'amber', LOW: 'red', UNVERIFIED: 'gray',
    PUBLIC_LEAD: 'gray', INFERRED: 'amber', POTENTIAL: 'blue',
    P0: 'red', P1: 'amber', P2: 'blue', P3: 'gray'
  };

  S.label = function (value) {
    if (value === null || value === undefined || value === '') return '—';
    return LABELS[String(value)] || String(value);
  };

  S.statusKind = function (value) {
    if (value === null || value === undefined) return 'gray';
    return KINDS[String(value)] || 'gray';
  };

  S.leadGradeLabel = function (value) {
    if (value === 'VERIFIED') return '一手已核线索';
    if (value === 'QUALIFIED') return '已确认资格线索';
    return S.label(value);
  };
  S.leadGradeKind = function (value) {
    if (value === 'VERIFIED') return 'green';
    if (value === 'QUALIFIED') return 'green';
    if (value === 'POTENTIAL') return 'blue';
    if (value === 'INFERRED') return 'amber';
    return 'gray';
  };

  /* 字段中文名（详情/表头可用） */
  var FIELD_LABELS = {
    id: 'ID', name: '名称', name_en: '英文名', company_type: '公司类型', country: '国家',
    region: '地区', website: '官网', parent: '母公司', listed_code: '上市代码',
    business_summary: '业务简介', status: '状态', trust_level: '信任度', owner: '负责人',
    tags: '标签', notes: '备注', created_at: '创建时间', updated_at: '更新时间',
    company_id: '公司', title: '标题', workload_type: '负载类型', gpu_models: 'GPU 型号',
    min_gpu_count: '最少卡数', max_gpu_count: '最多卡数', duration_months: '时长（月）',
    cluster_requirements: '集群要求', network_requirements: '网络要求',
    location_preference: '位置偏好', data_residency: '数据驻留', compliance_notes: '合规备注',
    timeline: '时间窗', budget_range: '预算范围', decision_maker: '决策人',
    lead_grade: '线索等级', next_action: '下一步动作', evidence_ids: '证据 ID',
    location_country: '所在国家', location_city: '所在城市', datacenter: '数据中心',
    gpu_model: 'GPU 型号', gpu_count: 'GPU 总数', sellable_gpu_count: '可售卡数',
    gpu_memory_gb: '单卡显存（GB）', interconnect: '互联方式', cluster_topology: '集群拓扑',
    training_capable: '训练能力', inference_capable: '推理能力',
    network_bandwidth: '网络带宽', storage: '存储', delivery_lead_time: '交付周期',
    price_indication: '价格线索', pricing_model: '计费模式', overseas_service: '海外服务',
    verified: '已核验', vendor: '厂商', form_factor: '形态', memory_gb: '显存（GB）',
    memory_type: '显存类型', memory_bandwidth_gbps: '显存带宽（GB/s）',
    fp16_tflops: 'FP16 TFLOPS', tf32_tflops: 'TF32 TFLOPS', fp8_tflops: 'FP8 TFLOPS',
    typical_cluster: '典型集群', power_kw_per_node: '单节点功耗（kW）', source: '来源',
    subject_type: '主体类型', subject_id: '主体 ID', claim: '证据主张',
    source_title: '来源标题', url: '来源 URL', publisher: '发布方',
    published_at: '发布时间', retrieved_at: '获取时间', confidence: '置信度',
    cross_verified: '交叉验证', supplier_company_id: '供应商公司', checklist_json: '核验清单',
    legal_entity_ok: '主体合法', resource_ownership_ok: '资源所有权',
    resale_right_ok: '转售权', capacity_evidence_ok: '容量证据',
    overseas_service_ok: '海外服务能力', export_control_declared: '出口管制声明',
    non_exclusive_ok: '非排他', success_fee_ok: '成功费条款', verified_by: '核验人',
    verified_at: '核验时间', score: '评分', gaps: '缺口 / 待补证据',
    demand_id: '需求', decision_maker_confirmed: '决策人确认', budget_confirmed: '预算确认',
    timeline_confirmed: '时间窗确认', compliance_screened: '合规初筛',
    contracting_path_confirmed: '签约路径确认', data_residency_ok: '数据驻留确认',
    qualified_by: '核验人', qualified_at: '核验时间', supply_id: '供给',
    match_dimensions: '维度得分', why_match: '匹配理由', why_not_match: '不匹配理由',
    risks: '风险', recommendation: '建议', analyst: '分析师',
    options_json: '方案对比', scoring_json: '评分明细', assumptions: '假设',
    stage: '阶段', model_type: '合作模式', fee_payer: '付费方', fee_basis: '计费基础',
    fee_terms: '费用条款', conflict_disclosed: '利益冲突已披露',
    ceo_approval_status: 'CEO 审批', next_step: '下一步', match_id: '匹配记录',
    agent_name: 'Agent', task_type: '任务类型', input_ref: '输入引用',
    output_path: '输出路径', priority: '优先级', requires_approval: '需要审批',
    started_at: '开始时间', finished_at: '完成时间', result_summary: '结果摘要',
    error: '错误信息', ts: '时间', actor: '操作者', action: '动作',
    entity_type: '实体类型', entity_id: '实体 ID', summary: '摘要', detail: '详情',
    category: '分类', content_md: '内容（Markdown）', approval_type: '审批类型',
    subject: '审批主题', requested_by: '申请人', requested_at: '申请时间',
    required_role: '所需角色', payload_json: '审批载荷', decided_by: '决策人',
    decided_at: '决策时间', decision_note: '决策备注', before_json: '变更前',
    after_json: '变更后', ip: '来源 IP', file_path: '文件路径', size_bytes: '大小',
    sha256: 'SHA256', total: '总数', page: '页码', page_size: '每页条数',
    insert: '新增', updated: '更新', skipped: '跳过', errors: '错误'
  };

  S.fieldLabel = function (key) { return FIELD_LABELS[key] || key; };

  /* ============================================================
   * 枚举选项
   * ============================================================ */
  S.options = {
    companyTypes: [
      { value: 'SUPPLIER', label: '供应商' }, { value: 'DEMANDER', label: '需求方' },
      { value: 'PARTNER', label: '合作伙伴' }, { value: 'BOTH', label: '兼具' }
    ],
    companyStatus: ['LEAD', 'RESEARCHED', 'NEEDS_VERIFICATION', 'VERIFIED', 'QUALIFIED', 'ACTIVE', 'CEO_PENDING', 'INSUFFICIENT_INFO', 'PAUSED', 'EXPIRED', 'REJECTED'],
    trustLevels: ['HIGH', 'MEDIUM', 'LOW', 'UNVERIFIED'],
    demandStatus: ['LEAD', 'RESEARCHED', 'NEEDS_VERIFICATION', 'VERIFIED', 'QUALIFIED', 'MATCHED', 'COMMERCIAL', 'WON', 'LOST', 'NOT_MATCHED', 'CEO_PENDING', 'INSUFFICIENT_INFO', 'PAUSED', 'EXPIRED', 'REJECTED'],
    supplyStatus: ['LEAD', 'RESEARCHED', 'NEEDS_VERIFICATION', 'VERIFIED', 'QUALIFIED', 'ACTIVE', 'PAUSED', 'EXPIRED', 'REJECTED'],
    workloadTypes: ['TRAINING', 'FINETUNE', 'INFERENCE', 'RENDERING', 'SIMULATION', 'MIXED'],
    leadGrades: ['PUBLIC_LEAD', 'INFERRED', 'POTENTIAL', 'VERIFIED', 'QUALIFIED'],
    evidenceSubjectTypes: ['COMPANY', 'DEMAND', 'SUPPLY', 'MATCH', 'CLAIM', 'OTHER'],
    confidence: ['HIGH', 'MEDIUM', 'LOW', 'UNVERIFIED'],
    verificationStatus: ['PENDING', 'IN_REVIEW', 'VERIFIED', 'REJECTED'],
    matchStatus: ['DRAFT', 'REVIEWED', 'CEO_PENDING', 'APPROVED', 'REJECTED'],
    recommendation: ['ADVANCE', 'NEED_MORE_INFO', 'REJECT'],
    opportunityStages: ['OPEN', 'DISCLOSED', 'INTRODUCED', 'TERM_SHEET', 'CA', 'CLOSED_WON', 'CLOSED_LOST'],
    modelTypes: ['ADVISORY', 'INTRO', 'CHANNEL', 'JOINT', 'PMC'],
    ceoApproval: ['PENDING', 'APPROVED', 'REJECTED'],
    taskStatus: ['QUEUED', 'RUNNING', 'DONE', 'BLOCKED', 'FAILED', 'CANCELLED'],
    taskPriority: ['P0', 'P1', 'P2', 'P3'],
    knowledgeStatus: ['DRAFT', 'PUBLISHED', 'ARCHIVED'],
    signatureStatus: ['NOT_STARTED', 'IN_REVIEW', 'SIGNED', 'TERMINATED'],
    approvalDecisions: ['APPROVED', 'REJECTED', 'RETURNED'],
    quoteStatus: ['DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED', 'EXPIRED']
  };

  /* 便捷：字符串数组 → {value,label} */
  S.opts = function (list) {
    return (list || []).map(function (v) { return { value: v, label: S.label(v) }; });
  };
  S.leadGradeOpts = function () {
    return S.options.leadGrades.map(function (v) { return { value: v, label: S.leadGradeLabel(v) }; });
  };

  /* ============================================================
   * 状态机允许迁移（前端仅用于展示可推进按钮；后端 409 为权威）
   * 结构：transitions[resource][当前状态] = [允许目标状态...]
   * ============================================================ */
  S.transitions = {
    companies: {
      LEAD: ['RESEARCHED', 'PAUSED', 'EXPIRED'],
      RESEARCHED: ['NEEDS_VERIFICATION', 'INSUFFICIENT_INFO', 'PAUSED', 'REJECTED'],
      NEEDS_VERIFICATION: ['VERIFIED', 'REJECTED', 'INSUFFICIENT_INFO'],
      VERIFIED: ['QUALIFIED', 'CEO_PENDING', 'PAUSED'],
      QUALIFIED: ['ACTIVE', 'PAUSED', 'EXPIRED'],
      ACTIVE: ['PAUSED', 'EXPIRED'],
      CEO_PENDING: ['ACTIVE', 'REJECTED'],
      INSUFFICIENT_INFO: ['RESEARCHED', 'PAUSED', 'REJECTED'],
      PAUSED: ['RESEARCHED', 'ACTIVE', 'EXPIRED'],
      EXPIRED: ['RESEARCHED'],
      REJECTED: ['RESEARCHED']
    },
    demands: {
      LEAD: ['RESEARCHED', 'PAUSED', 'EXPIRED'],
      RESEARCHED: ['NEEDS_VERIFICATION', 'INSUFFICIENT_INFO', 'PAUSED'],
      NEEDS_VERIFICATION: ['VERIFIED', 'REJECTED', 'INSUFFICIENT_INFO'],
      VERIFIED: ['QUALIFIED', 'PAUSED'],
      QUALIFIED: ['MATCHED', 'NOT_MATCHED', 'PAUSED'],
      MATCHED: ['COMMERCIAL', 'NOT_MATCHED', 'PAUSED'],
      COMMERCIAL: ['WON', 'LOST', 'PAUSED'],
      NOT_MATCHED: ['MATCHED', 'PAUSED', 'EXPIRED'],
      CEO_PENDING: ['COMMERCIAL', 'REJECTED'],
      INSUFFICIENT_INFO: ['RESEARCHED', 'PAUSED'],
      PAUSED: ['RESEARCHED', 'QUALIFIED', 'EXPIRED'],
      EXPIRED: ['RESEARCHED'],
      WON: [],
      LOST: ['RESEARCHED'],
      REJECTED: ['RESEARCHED']
    },
    'supplier-verifications': {
      PENDING: ['IN_REVIEW', 'REJECTED'],
      IN_REVIEW: ['VERIFIED', 'REJECTED'],
      VERIFIED: [],
      REJECTED: ['PENDING']
    },
    'demand-qualifications': {
      PENDING: ['IN_REVIEW', 'REJECTED'],
      IN_REVIEW: ['QUALIFIED', 'REJECTED'],
      QUALIFIED: [],
      REJECTED: ['PENDING']
    },
    matches: {
      DRAFT: ['REVIEWED', 'REJECTED'],
      REVIEWED: ['CEO_PENDING', 'DRAFT', 'REJECTED'],
      CEO_PENDING: ['APPROVED', 'REJECTED', 'REVIEWED'],
      APPROVED: [],
      REJECTED: ['DRAFT']
    },
    'commercial-opportunities': {
      OPEN: ['DISCLOSED', 'CLOSED_LOST'],
      DISCLOSED: ['INTRODUCED', 'CLOSED_LOST'],
      INTRODUCED: ['TERM_SHEET', 'CLOSED_LOST'],
      TERM_SHEET: ['CA', 'CLOSED_WON', 'CLOSED_LOST'],
      CA: ['CLOSED_WON', 'CLOSED_LOST'],
      CLOSED_WON: [],
      CLOSED_LOST: []
    },
    'agent-tasks': {
      QUEUED: ['RUNNING', 'CANCELLED'],
      RUNNING: ['DONE', 'BLOCKED', 'FAILED', 'CANCELLED'],
      BLOCKED: ['QUEUED', 'CANCELLED'],
      FAILED: ['QUEUED'],
      DONE: [],
      CANCELLED: []
    },
    knowledge: {
      DRAFT: ['PUBLISHED', 'ARCHIVED'],
      PUBLISHED: ['ARCHIVED', 'DRAFT'],
      ARCHIVED: ['DRAFT']
    },
    approvals: {
      PENDING: ['APPROVED', 'REJECTED', 'RETURNED'],
      APPROVED: [],
      REJECTED: [],
      RETURNED: ['PENDING']
    }
  };

  /* ============================================================
   * 表单字段定义（供 views 引用；动态下拉的 options 由视图填充）
   * ============================================================ */
  function text(key, label, extra) {
    return Object.assign({ key: key, label: label, type: 'text' }, extra || {});
  }
  function num(key, label, extra) {
    return Object.assign({ key: key, label: label, type: 'number', step: 'any' }, extra || {});
  }
  function area(key, label, extra) {
    return Object.assign({ key: key, label: label, type: 'textarea', span: true }, extra || {});
  }
  function sel(key, label, options, extra) {
    return Object.assign({ key: key, label: label, type: 'select', options: options }, extra || {});
  }
  function check(key, label, extra) {
    return Object.assign({ key: key, label: label, type: 'checkbox' }, extra || {});
  }

  var F = S.forms = {};

  F.companies = [
    text('name', '公司名称', { required: true, span: true }),
    text('name_en', '英文名'),
    sel('company_type', '公司类型', S.options.companyTypes, { required: true, default: 'SUPPLIER' }),
    sel('status', '状态', S.opts(S.options.companyStatus), { default: 'LEAD' }),
    text('country', '国家'),
    text('region', '地区'),
    text('website', '官网', { type: 'url', span: true }),
    text('parent', '母公司'),
    text('listed_code', '上市代码'),
    sel('trust_level', '信任度', S.opts(S.options.trustLevels), { default: 'UNVERIFIED' }),
    text('owner', '负责人'),
    text('tags', '标签（逗号分隔）', { span: true }),
    area('business_summary', '业务简介', { rows: 3 }),
    area('notes', '备注', { rows: 3 })
  ];

  F.demands = [
    text('title', '需求标题', { required: true, span: true }),
    sel('company_id', '需求公司', [], { help: '从需求方公司中选择；留空表示公司待确认' }),
    sel('workload_type', '负载类型', S.opts(S.options.workloadTypes), { default: 'MIXED' }),
    sel('lead_grade', '线索等级', S.leadGradeOpts(), { default: 'PUBLIC_LEAD' }),
    sel('status', '状态', S.opts(S.options.demandStatus), { default: 'LEAD' }),
    text('gpu_models', 'GPU 型号（逗号分隔）', { span: true }),
    num('min_gpu_count', '最少卡数'),
    num('max_gpu_count', '最多卡数'),
    num('duration_months', '时长（月）'),
    text('timeline', '时间窗'),
    sel('budget_range', '预算范围', ['UNKNOWN', '待确认', '<100万', '100-500万', '500-2000万', '>2000万'], {}),
    text('location_preference', '位置偏好'),
    text('data_residency', '数据驻留要求'),
    text('decision_maker', '决策人'),
    area('cluster_requirements', '集群要求', { rows: 2 }),
    area('network_requirements', '网络要求', { rows: 2 }),
    area('compliance_notes', '合规备注', { rows: 2 }),
    area('next_action', '下一步动作', { rows: 2 }),
    text('evidence_ids', '证据 ID（逗号分隔）', { span: true })
  ];

  F.supplies = [
    sel('company_id', '供给公司', [], { help: '从供应商公司中选择' }),
    text('gpu_model', 'GPU 型号', { required: true }),
    num('gpu_count', 'GPU 总数'),
    num('sellable_gpu_count', '可售卡数'),
    num('gpu_memory_gb', '单卡显存（GB）'),
    text('location_country', '所在国家'),
    text('location_city', '所在城市'),
    text('datacenter', '数据中心'),
    text('interconnect', '互联方式'),
    text('cluster_topology', '集群拓扑'),
    check('training_capable', '支持训练'),
    check('inference_capable', '支持推理'),
    text('network_bandwidth', '网络带宽'),
    text('storage', '存储'),
    text('delivery_lead_time', '交付周期'),
    text('price_indication', '价格线索（内部参考）'),
    text('pricing_model', '计费模式'),
    check('overseas_service', '可提供海外服务'),
    sel('status', '状态', S.opts(S.options.supplyStatus), { default: 'LEAD' }),
    check('verified', '已核验'),
    area('next_action', '下一步动作', { rows: 2 }),
    text('evidence_ids', '证据 ID（逗号分隔）', { span: true })
  ];

  F.specs = [
    text('gpu_model', 'GPU 型号', { required: true }),
    text('vendor', '厂商'),
    text('form_factor', '形态（SXM / PCIe / 整机…）'),
    num('memory_gb', '显存（GB）'),
    text('memory_type', '显存类型'),
    num('memory_bandwidth_gbps', '显存带宽（GB/s）'),
    num('fp16_tflops', 'FP16 TFLOPS'),
    num('tf32_tflops', 'TF32 TFLOPS'),
    num('fp8_tflops', 'FP8 TFLOPS'),
    text('interconnect', '互联方式'),
    text('typical_cluster', '典型集群规模'),
    num('power_kw_per_node', '单节点功耗（kW）'),
    text('source', '规格来源'),
    area('notes', '备注', { rows: 3 })
  ];

  F.evidence = [
    sel('subject_type', '主体类型', S.opts(S.options.evidenceSubjectTypes), { required: true, default: 'COMPANY' }),
    text('subject_id', '主体 ID'),
    area('claim', '证据主张（这条证据能证明什么）', { required: true, rows: 3 }),
    text('source_title', '来源标题', { span: true }),
    text('url', '来源 URL', { type: 'url', span: true, placeholder: 'https://…' }),
    text('publisher', '发布方'),
    text('published_at', '发布时间', { type: 'date' }),
    text('retrieved_at', '获取时间', { type: 'date' }),
    sel('confidence', '置信度', S.opts(S.options.confidence), { default: 'UNVERIFIED' }),
    check('cross_verified', '已交叉验证'),
    area('notes', '备注', { rows: 2 })
  ];

  F.supplierVerifications = [
    sel('supplier_company_id', '供应商公司', [], { required: true, help: '从 company_type=SUPPLIER 的公司中选择' }),
    sel('status', '核验结论', S.opts(S.options.verificationStatus), { default: 'PENDING' }),
    num('score', '总分（0–100）', { min: 0, max: 100 }),
    text('verified_by', '核验人'),
    text('verified_at', '核验时间', { type: 'date' }),
    {
      key: 'checklist', type: 'checks', label: '核验清单（逐项确认，勾选=通过）', span: true,
      items: [
        { key: 'legal_entity_ok', label: '主体合法（可查工商/注册信息）' },
        { key: 'resource_ownership_ok', label: '资源所有权 / 自营可证明' },
        { key: 'resale_right_ok', label: '具备转售 / 分销权' },
        { key: 'capacity_evidence_ok', label: '容量证据充分（合同/上架/现场）' },
        { key: 'overseas_service_ok', label: '具备海外服务能力' },
        { key: 'export_control_declared', label: '出口管制已声明' },
        { key: 'non_exclusive_ok', label: '非排他条款可接受' },
        { key: 'success_fee_ok', label: '成功费条款可接受' }
      ]
    },
    area('gaps', '缺口 / 待补证据', { rows: 3 }),
    area('notes', '备注', { rows: 2 })
  ];

  F.demandQualifications = [
    sel('demand_id', '需求', [], { required: true }),
    sel('status', '资格结论', S.opts(S.options.verificationStatus), { default: 'PENDING' }),
    num('score', '总分（0–100）', { min: 0, max: 100 }),
    text('qualified_by', '核验人'),
    text('qualified_at', '核验时间', { type: 'date' }),
    {
      key: 'checklist', type: 'checks', label: '资格核验（勾选=已确认）', span: true,
      items: [
        { key: 'decision_maker_confirmed', label: '决策人已确认' },
        { key: 'budget_confirmed', label: '预算已确认' },
        { key: 'timeline_confirmed', label: '时间窗已确认' },
        { key: 'compliance_screened', label: '合规已初筛（数据出境/管制）' },
        { key: 'contracting_path_confirmed', label: '签约路径已确认' },
        { key: 'data_residency_ok', label: '数据驻留要求可满足' }
      ]
    },
    area('gaps', '缺口 / 待确认项', { rows: 3 }),
    area('notes', '备注', { rows: 2 })
  ];

  F.opportunities = [
    text('title', '商机名称', { required: true, span: true }),
    sel('demand_id', '关联需求', []),
    sel('supply_id', '关联供给', []),
    text('match_id', '关联匹配记录 ID', { type: 'number' }),
    sel('stage', '阶段', S.opts(S.options.opportunityStages), { default: 'OPEN' }),
    sel('model_type', '合作模式', S.opts(S.options.modelTypes), { default: 'ADVISORY' }),
    sel('ceo_approval_status', 'CEO 审批状态', S.opts(S.options.ceoApproval), { default: 'PENDING' }),
    text('fee_payer', '付费方'),
    text('fee_basis', '计费基础'),
    text('fee_terms', '费用条款（草案，不外发）'),
    check('conflict_disclosed', '利益冲突已披露'),
    text('owner', '负责人'),
    area('next_step', '下一步', { rows: 2 })
  ];

  F.procurement = [
    sel('demand_id', '需求', [], { required: false }),
    text('title', '分析报告标题', { required: true, span: true }),
    sel('status', '状态', ['DRAFT', 'REVIEWED', 'CEO_PENDING', 'APPROVED', 'REJECTED'].map(function (v) { return { value: v, label: S.label(v) }; }), { default: 'DRAFT' }),
    text('recommendation', '建议方案（摘要）', { span: true }),
    text('analyst', '分析师'),
    area('risks', '风险', { rows: 3 }),
    area('assumptions', '假设与前提', { rows: 3 })
  ];

  F.agentTasks = [
    sel('agent_name', 'Agent', [], { required: true }),
    text('task_type', '任务类型'),
    text('title', '任务标题', { required: true, span: true }),
    text('input_ref', '输入引用'),
    sel('priority', '优先级', S.opts(S.options.taskPriority), { default: 'P2' }),
    sel('status', '状态', S.opts(S.options.taskStatus), { default: 'QUEUED' }),
    check('requires_approval', '需要 CEO 审批'),
    text('output_path', '输出路径'),
    area('result_summary', '结果摘要', { rows: 2 }),
    area('error', '错误信息', { rows: 2 })
  ];

  F.knowledge = [
    text('title', '标题', { required: true, span: true }),
    text('category', '分类'),
    sel('status', '状态', S.opts(S.options.knowledgeStatus), { default: 'DRAFT' }),
    text('tags', '标签（逗号分隔）', { span: true }),
    text('source', '来源'),
    area('content_md', '内容（Markdown）', { required: true, rows: 14, code: true, placeholder: '# 标题\n\n正文…' })
  ];

  /* 表单字段提取时只保留存在的字段，避免 undefined 报错 */
  S.formFields = function (entityKey) {
    return (S.forms[entityKey] || []).slice();
  };
})();
