/* CCGS 内部工作台 · views/entities.js
 * 模块 2–8：需求 / 供应商与需求方 / GPU 资源 / 证据 / 供应商核验 / 需求资格核验 / 算力规格
 * 约定：列表统一走 UI.listPage；表单字段来自 CCGS.schema.forms；动态下拉在挂载后填充。
 */
var CCGS = window.CCGS || (window.CCGS = {});

(function () {
  'use strict';

  var U = CCGS.util, UI = CCGS.ui, API = CCGS.api, S = CCGS.schema;
  var V = CCGS.views = CCGS.views || {};

  /* ---------- 共享表单工具（后续 views 复用） ---------- */
  var FU = CCGS.formUtil = CCGS.formUtil || {};

  FU.find = function (fields, key) {
    for (var i = 0; i < fields.length; i++) if (fields[i].key === key) return fields[i];
    return null;
  };
  FU.fill = function (fields, key, options) {
    var f = FU.find(fields, key);
    if (!f) return;
    f.options = options;
    f.type = 'select';
    if (f.help && f.help.indexOf('无法加载') >= 0) f.help = '';
  };
  FU.textFallback = function (fields, key, message) {
    var f = FU.find(fields, key);
    if (!f) return;
    f.type = 'text';
    f.options = null;
    f.help = message;
    if (!f.placeholder) f.placeholder = '可手工填写 ID';
  };
  FU.loadCompanies = function (fields, key, companyType) {
    var params = { page_size: 200 };
    if (companyType) params.company_type = companyType;
    return API.list('companies', params).then(function (res) {
      FU.fill(fields, key, (res.items || []).map(function (c) {
        return { value: c.id, label: (c.name || ('公司 #' + c.id)) + (c.country ? ' · ' + c.country : '') };
      }));
    }).catch(function () {
      FU.textFallback(fields, key, '无法加载公司列表（后端未连接），可手工填写公司 ID');
    });
  };
  FU.loadDemands = function (fields, key) {
    return API.list('demands', { page_size: 200, sort: '-updated_at' }).then(function (res) {
      FU.fill(fields, key, (res.items || []).map(function (d) {
        return { value: d.id, label: (d.title || ('需求 #' + d.id)) + (d.gpu_models ? ' · ' + d.gpu_models : '') };
      }));
    }).catch(function () {
      FU.textFallback(fields, key, '无法加载需求列表（后端未连接），可手工填写需求 ID');
    });
  };
  FU.loadSupplies = function (fields, key) {
    return API.list('supplies', { page_size: 200, sort: '-updated_at' }).then(function (res) {
      FU.fill(fields, key, (res.items || []).map(function (s) {
        var bits = [s.gpu_model || ('供给 #' + s.id)];
        if (s.location_city || s.location_country) bits.push([s.location_city, s.location_country].filter(Boolean).join(' '));
        if (s.gpu_count) bits.push(s.gpu_count + ' 卡');
        return { value: s.id, label: bits.join(' · ') };
      }));
    }).catch(function () {
      FU.textFallback(fields, key, '无法加载供给列表（后端未连接），可手工填写供给 ID');
    });
  };
  FU.loadAgents = function (fields, key) {
    return API.agents().then(function (list) {
      var arr = Array.isArray(list) ? list : ((list && list.items) || []);
      FU.fill(fields, key, arr.map(function (a) {
        var name = a.agent_name || a.name || a.id || a.key || '';
        return { value: name, label: name + (a.role ? ' · ' + a.role : '') };
      }));
    }).catch(function () {
      FU.textFallback(fields, key, '无法加载 Agent 列表（后端未连接），可手工填写 Agent 名称');
    });
  };

  /* ---------- 通用渲染小工具 ---------- */
  function sub(main, extra) {
    return main + (extra ? '<div class="cell-sub">' + U.esc(extra) + '</div>' : '');
  }
  function statusBadge(v) { return UI.badge(v, S.statusKind(v), { sm: true }); }
  function badge(v, kind) { return UI.badge(v, kind, { sm: true }); }
  function companyTypeBadge(v) {
    var kind = v === 'SUPPLIER' ? 'cyan' : v === 'DEMANDER' ? 'purple' : v === 'BOTH' ? 'blue' : 'gray';
    return badge(S.label(v), kind);
  }
  function leadGradeBadge(v) { return UI.badge(v, S.leadGradeKind(v), { sm: true }); }
  function numText(v) { return U.isEmpty(v) ? '<span class="dash-text">—</span>' : U.esc(String(v)); }
  function pendingText(v) {
    return U.isEmpty(v) ? '<span class="pending-text">待确认</span>' : U.escText(v);
  }
  function linkHtml(url, label) {
    if (!url) return '<span class="dash-text">—</span>';
    return UI.link(url, label || '打开来源');
  }
  function dateText(v) { return U.isEmpty(v) ? '<span class="dash-text">—</span>' : U.esc(U.dateTime(v)); }
  function daysHint(n) { return U.isEmpty(n) ? '—' : n + ' 个月'; }

  /* 空字符串的可选字段转成 null：否则空的值会被当成外键值（如 company_id='')
   * 发送给后端，触发 FOREIGN KEY constraint failed。 */
  function nullifyEmpty(values) {
    var out = {};
    Object.keys(values || {}).forEach(function (k) {
      var v = values[k];
      out[k] = (v === '') ? null : v;
    });
    return out;
  }

  function matrixHint(row, statusField, okThreshold, badThreshold) {
    var score = Number(row.score);
    if (isNaN(score)) return '';
    var st = row[statusField];
    var box = function (msg) {
      return '<div class="tip-box" style="border-color:rgba(243,183,63,.45);color:#f3b73f;margin-bottom:12px;">⚠ ' + msg + '</div>';
    };
    if ((st === 'VERIFIED' || st === 'QUALIFIED') && score < okThreshold) {
      return box('评分与结论不一致：结论为「' + U.esc(S.label(st)) + '」，但总分 ' + score +
        ' 低于建议门槛 ' + okThreshold + '。建议补足证据或下调结论。');
    }
    if (st === 'REJECTED' && score >= badThreshold) {
      return box('评分与结论不一致：结论为「已拒绝」，但总分 ' + score +
        ' 高于拒绝参考线 ' + badThreshold + '。请在缺口/备注中说明拒绝原因。');
    }
    return '';
  }

  function checklistBlock(row, fieldKey) {
    var list = S.forms[fieldKey] || [];
    var checks = null;
    for (var i = 0; i < list.length; i++) if (list[i].type === 'checks') checks = list[i];
    if (!checks) return '';
    var body = '<div class="check-grid">' + checks.items.map(function (it) {
      var ok = Number(row[it.key]) === 1;
      return '<div class="check-item"><span class="badge badge--sm badge--' + (ok ? 'green' : 'gray') + '">' +
        (ok ? '通过' : '未通过') + '</span> ' + U.esc(it.label) + '</div>';
    }).join('') + '</div>';
    return '<div class="detail-block"><h4>' + U.esc(checks.label || '核验清单') + '</h4>' + body + '</div>';
  }

  /* ---------- 公司映射（把 company_id 显示成名称） ---------- */
  var companyNames = null;
  function loadCompanyNames() {
    if (companyNames) return Promise.resolve(companyNames);
    return API.list('companies', { page_size: 200 }).then(function (res) {
      var map = {};
      (res.items || []).forEach(function (c) { map[c.id] = c.name || ('公司 #' + c.id); });
      companyNames = map;
      return map;
    }).catch(function () { companyNames = {}; return companyNames; });
  }
  function companyName(id) {
    if (U.isEmpty(id)) return '<span class="dash-text">—</span>';
    if (companyNames && companyNames[id]) return U.esc(companyNames[id]);
    return '公司 #' + U.esc(id);
  }

  /* ============================================================
   * 2. 需求管理
   * ============================================================ */
  var demandFields = null;

  function demandDetailBody(row) {
    var html = (row.status === 'MATCHED' || row.status === 'COMMERCIAL')
      ? UI.tip('该需求已进入匹配/商务阶段。对外沟通须引用已核验证据，不得使用未确认字段。')
      : '';
    html += UI.kv([
      ['需求标题', '<strong>' + U.escText(row.title) + '</strong>'],
      ['需求公司', companyName(row.company_id)],
      ['负载类型', badge(S.label(row.workload_type), 'blue')],
      ['线索等级', leadGradeBadge(row.lead_grade)],
      ['状态', statusBadge(row.status)],
      ['GPU 型号', pendingText(row.gpu_models)],
      ['卡数范围', (U.isEmpty(row.min_gpu_count) && U.isEmpty(row.max_gpu_count)) ? pendingText('') :
        U.esc(String(row.min_gpu_count === null || row.min_gpu_count === undefined ? '—' : row.min_gpu_count) + ' ~ ' +
          String(row.max_gpu_count === null || row.max_gpu_count === undefined ? '—' : row.max_gpu_count)) + ' 卡'],
      ['时长', U.isEmpty(row.duration_months) ? pendingText('') : U.esc(String(row.duration_months)) + ' 个月'],
      ['时间窗', pendingText(row.timeline)],
      ['预算范围', pendingText(row.budget_range)],
      ['决策人', pendingText(row.decision_maker)],
      ['位置偏好', pendingText(row.location_preference)],
      ['数据驻留', pendingText(row.data_residency)],
      ['证据 ID', pendingText(row.evidence_ids)],
      ['创建时间', dateText(row.created_at)],
      ['更新时间', dateText(row.updated_at)]
    ]);
    html += UI.detailBlock('集群要求', row.cluster_requirements);
    html += UI.detailBlock('网络要求', row.network_requirements);
    html += UI.detailBlock('合规备注', row.compliance_notes);
    html += UI.detailBlock('下一步动作', row.next_action);
    return html;
  }

  V.demands = {
    title: '需求管理',
    subtitle: '需求线索 · 资格核验 · 匹配',
    mount: function (root) {
      if (!demandFields) {
        demandFields = S.formFields('demands');
      }
      var ctx = UI.listPage(root, {
        resource: 'demands',
        title: '需求管理',
        subtitle: '线索等级与状态均为内部记录；对外须以证据为准',
        singular: '需求',
        columns: [
          { key: 'title', label: '需求', render: function (r) { return sub('<strong>' + U.escText(r.title) + '</strong>', r.gpu_models || ''); } },
          { key: 'company_id', label: '需求公司', render: function (r) { return companyName(r.company_id); } },
          { key: 'workload_type', label: '负载', render: function (r) { return badge(S.label(r.workload_type), 'gray'); } },
          { key: 'lead_grade', label: '线索等级', render: function (r) { return leadGradeBadge(r.lead_grade); } },
          { key: 'min_gpu_count', label: '卡数', sortable: false, className: 'cell--num', render: function (r) {
            if (U.isEmpty(r.min_gpu_count) && U.isEmpty(r.max_gpu_count)) return '<span class="dash-text">—</span>';
            return U.esc((U.isEmpty(r.min_gpu_count) ? '?' : r.min_gpu_count) + '–' + (U.isEmpty(r.max_gpu_count) ? '?' : r.max_gpu_count));
          } },
          { key: 'status', label: '状态', render: function (r) { return statusBadge(r.status); } },
          { key: 'updated_at', label: '更新时间', render: function (r) { return dateText(r.updated_at); } }
        ],
        filters: [
          { param: 'status', label: '状态', options: S.opts(S.options.demandStatus) },
          { param: 'lead_grade', label: '线索等级', options: S.leadGradeOpts() },
          { param: 'workload_type', label: '负载', options: S.opts(S.options.workloadTypes) }
        ],
        create: { label: '新建需求', defaults: { status: 'LEAD', lead_grade: 'PUBLIC_LEAD', workload_type: 'MIXED' } },
        form: { fields: demandFields, editTitle: '编辑需求', buildPayload: nullifyEmpty },
        advance: { entity: 'demands' },
        detail: { keys: [], body: demandDetailBody, size: 'lg' },
        defaultSort: '-updated_at',
        emptyTitle: '暂无需求',
        emptyText: '当前没有需求线索。新建需求时，未确认的预算、时间窗、决策人等字段请留空，界面会显示「待确认」。'
      });
      loadCompanyNames().then(function () { ctx.reload(); });
      FU.loadCompanies(demandFields, 'company_id');
      return ctx;
    }
  };

  /* ============================================================
   * 3. 供应商 / 需求方（companies）
   * ============================================================ */
  var companyFields = null;

  function openCompanyCreate(ctx, defaultType) {
    var fields = S.formFields('companies');
    UI.openForm({
      title: '新建公司档案',
      subtitle: defaultType === 'DEMANDER' ? '需求方' : '供应商',
      fields: fields,
      values: { company_type: defaultType || 'SUPPLIER', status: 'LEAD', trust_level: 'UNVERIFIED' },
      wide: true,
      submitText: '创建',
      onSubmit: function (payload) {
        return API.create('companies', nullifyEmpty(payload)).then(function (item) {
          UI.toast('success', '已创建公司：' + (item.name || ''));
          ctx.reload();
        });
      }
    });
  }

  function companyDetailBody(row) {
    var html = UI.kv([
      ['公司名称', '<strong>' + U.escText(row.name) + '</strong>'],
      ['英文名', U.isEmpty(row.name_en) ? '<span class="dash-text">—</span>' : U.escText(row.name_en)],
      ['公司类型', companyTypeBadge(row.company_type)],
      ['状态', statusBadge(row.status)],
      ['信任度', badge(S.label(row.trust_level), S.statusKind(row.trust_level))],
      ['国家/地区', U.esc([row.country, row.region].filter(Boolean).join(' / ') || '—')],
      ['官网', linkHtml(row.website, row.website)],
      ['母公司', pendingText(row.parent)],
      ['上市代码', pendingText(row.listed_code)],
      ['负责人', pendingText(row.owner)],
      ['标签', pendingText(row.tags)],
      ['创建时间', dateText(row.created_at)],
      ['更新时间', dateText(row.updated_at)]
    ]);
    html += UI.detailBlock('业务简介', row.business_summary);
    html += UI.detailBlock('备注', row.notes);
    return html;
  }

  V.companies = {
    title: '供应商 / 需求方',
    subtitle: '企业档案 · SUPPLIER / DEMANDER',
    mount: function (root) {
      if (!companyFields) companyFields = S.formFields('companies');
      var ctx = UI.listPage(root, {
        resource: 'companies',
        title: '企业与供应商管理',
        subtitle: '供应商默认只看 company_type=SUPPLIER；可切换需求方 tab',
        singular: '公司',
        tabs: {
          param: 'company_type',
          items: [
            { value: 'SUPPLIER', label: '供应商' },
            { value: 'DEMANDER', label: '需求方' },
            { value: '', label: '全部' }
          ]
        },
        columns: [
          { key: 'name', label: '公司', render: function (r) { return sub('<strong>' + U.escText(r.name) + '</strong>', r.name_en || ''); } },
          { key: 'company_type', label: '类型', render: function (r) { return companyTypeBadge(r.company_type); } },
          { key: 'country', label: '国家/地区', render: function (r) { return U.esc([r.country, r.region].filter(Boolean).join(' / ') || '—'); } },
          { key: 'trust_level', label: '信任度', render: function (r) { return badge(S.label(r.trust_level), S.statusKind(r.trust_level)); } },
          { key: 'status', label: '状态', render: function (r) { return statusBadge(r.status); } },
          { key: 'updated_at', label: '更新时间', render: function (r) { return dateText(r.updated_at); } }
        ],
        filters: [
          { param: 'trust_level', label: '信任度', options: S.opts(S.options.trustLevels) },
          { param: 'status', label: '状态', options: S.opts(S.options.companyStatus) }
        ],
        create: false,
        headActions: UI.button({ label: '新建公司', act: 'new-company', kind: 'primary', icon: 'plus' }),
        onAction: function (act, el, c) {
          if (act === 'new-company') {
            openCompanyCreate(c, c.state.tab === 'DEMANDER' ? 'DEMANDER' : 'SUPPLIER');
            return true;
          }
          return false;
        },
        form: { fields: companyFields, editTitle: '编辑公司档案', buildPayload: nullifyEmpty },
        advance: { entity: 'companies' },
        detail: { keys: [], body: companyDetailBody, size: 'lg' },
        defaultSort: 'name',
        emptyTitle: '暂无公司档案',
        emptyText: '供应商与需求方共用 companies 表。请先新建公司，或在「数据」页导入 CSV。'
      });
      return ctx;
    }
  };

  /* ============================================================
   * 4. GPU 资源管理（supplies）
   * ============================================================ */
  var supplyFields = null;

  function supplyDetailBody(row) {
    return UI.kv([
      ['GPU 型号', '<strong>' + U.escText(row.gpu_model) + '</strong>'],
      ['供给公司', companyName(row.company_id)],
      ['GPU 总数', numText(row.gpu_count)],
      ['可售卡数', numText(row.sellable_gpu_count)],
      ['单卡显存', U.isEmpty(row.gpu_memory_gb) ? '<span class="dash-text">—</span>' : U.esc(String(row.gpu_memory_gb)) + ' GB'],
      ['位置', U.esc([row.location_city, row.location_country].filter(Boolean).join(' / ') || '—')],
      ['数据中心', pendingText(row.datacenter)],
      ['互联方式', pendingText(row.interconnect)],
      ['集群拓扑', pendingText(row.cluster_topology)],
      ['支持训练', UI.boolBadge(row.training_capable, '是', '否')],
      ['支持推理', UI.boolBadge(row.inference_capable, '是', '否')],
      ['网络带宽', pendingText(row.network_bandwidth)],
      ['存储', pendingText(row.storage)],
      ['交付周期', pendingText(row.delivery_lead_time)],
      ['价格线索', '<span class="pending-text">' + U.escText(row.price_indication || '待确认') + '</span>（内部参考，不对外报价）'],
      ['计费模式', pendingText(row.pricing_model)],
      ['海外服务', UI.boolBadge(row.overseas_service, '可提供', '未确认')],
      ['状态', statusBadge(row.status)],
      ['核验', UI.boolBadge(row.verified, '已核验', '未核验')],
      ['更新时间', dateText(row.updated_at)]
    ]) + UI.detailBlock('下一步动作', row.next_action) + UI.detailBlock('证据 ID', row.evidence_ids);
  }

  V.supplies = {
    title: 'GPU 资源',
    subtitle: '算力供给 · 容量与交付线索',
    mount: function (root) {
      if (!supplyFields) supplyFields = S.formFields('supplies');
      var ctx = UI.listPage(root, {
        resource: 'supplies',
        title: 'GPU 资源管理',
        subtitle: '所有容量/价格为公开线索或自述，未经核验不得对外承诺',
        singular: '供给',
        columns: [
          { key: 'gpu_model', label: 'GPU 型号', render: function (r) { return sub('<strong>' + U.escText(r.gpu_model) + '</strong>', companyNames && companyNames[r.company_id] ? companyNames[r.company_id] : ''); } },
          { key: 'gpu_count', label: '卡数/可售', sortable: false, className: 'cell--num', render: function (r) {
            return numText(r.gpu_count) + ' <span class="faint">/</span> ' + numText(r.sellable_gpu_count);
          } },
          { key: 'location_city', label: '位置', render: function (r) {
            return U.esc([r.location_city, r.location_country].filter(Boolean).join(' / ') || '—') +
              (r.datacenter ? '<div class="cell-sub">' + U.esc(r.datacenter) + '</div>' : '');
          } },
          { key: 'delivery_lead_time', label: '交付周期', render: function (r) { return pendingText(r.delivery_lead_time); } },
          { key: 'price_indication', label: '价格线索', render: function (r) { return '<span class="pending-text">' + U.escText(r.price_indication || '待确认') + '</span>'; } },
          { key: 'status', label: '状态', render: function (r) { return statusBadge(r.status); } },
          { key: 'verified', label: '核验', render: function (r) { return UI.boolBadge(r.verified, '已核验', '未核验'); } },
          { key: 'updated_at', label: '更新', render: function (r) { return dateText(r.updated_at); } }
        ],
        filters: [
          { param: 'status', label: '状态', options: S.opts(S.options.supplyStatus) },
          { param: 'verified', label: '核验', options: [{ value: '1', label: '已核验' }, { value: '0', label: '未核验' }] }
        ],
        create: { label: '新建供给', defaults: { status: 'LEAD' } },
        form: { fields: supplyFields, editTitle: '编辑 GPU 资源', buildPayload: nullifyEmpty },
        detail: { keys: [], body: supplyDetailBody, size: 'lg' },
        defaultSort: '-updated_at',
        emptyTitle: '暂无 GPU 资源',
        emptyText: '登记供应商可提供的 GPU 型号、卡数、位置与交付周期。未核验的容量不得对外承诺。'
      });
      FU.loadCompanies(supplyFields, 'company_id');
      loadCompanyNames().then(function () { ctx.reload(); });
      return ctx;
    }
  };

  /* ============================================================
   * 5. 证据来源管理（evidence）
   * ============================================================ */
  var evidenceFields = null;

  function evidenceDetailBody(row) {
    return '<div class="detail-block"><h4>证据主张</h4><div class="detail-text">' + U.escText(row.claim) + '</div></div>' +
      (U.isEmpty(row.url) ? '' : '<div class="detail-block"><h4>来源链接</h4>' + linkHtml(row.url, row.url) + '</div>') +
      UI.kv([
        ['主体类型', badge(S.label(row.subject_type), 'blue')],
        ['主体 ID', pendingText(row.subject_id)],
        ['来源标题', pendingText(row.source_title)],
        ['发布方', pendingText(row.publisher)],
        ['发布时间', dateText(row.published_at)],
        ['获取时间', dateText(row.retrieved_at)],
        ['置信度', badge(S.label(row.confidence), S.statusKind(row.confidence) === 'gray' ? 'gray' : S.statusKind(row.confidence))],
        ['交叉验证', UI.boolBadge(row.cross_verified, '已交叉验证', '未交叉验证')],
        ['创建时间', dateText(row.created_at)]
      ]) + UI.detailBlock('备注', row.notes);
  }

  V.evidence = {
    title: '证据来源',
    subtitle: '来源 · 置信度 · 交叉验证',
    mount: function (root) {
      if (!evidenceFields) evidenceFields = S.formFields('evidence');
      return UI.listPage(root, {
        resource: 'evidence',
        title: '证据来源管理',
        subtitle: '每条主张都必须可追溯；未交叉验证的证据不得作为对外材料依据',
        singular: '证据',
        columns: [
          { key: 'claim', label: '证据主张', render: function (r) { return sub(U.esc(U.summarize(r.claim, 70)), r.source_title || ''); } },
          { key: 'subject_type', label: '主体', render: function (r) { return badge(S.label(r.subject_type), 'blue') + (U.isEmpty(r.subject_id) ? '' : ' <span class="small faint">#' + U.esc(r.subject_id) + '</span>'); } },
          { key: 'publisher', label: '发布方', render: function (r) { return pendingText(r.publisher); } },
          { key: 'url', label: '来源', sortable: false, render: function (r) { return linkHtml(r.url, '打开来源'); } },
          { key: 'confidence', label: '置信度', render: function (r) { return badge(S.label(r.confidence), S.statusKind(r.confidence)); } },
          { key: 'cross_verified', label: '交叉验证', render: function (r) { return UI.boolBadge(r.cross_verified, '已交叉', '未交叉'); } },
          { key: 'retrieved_at', label: '获取时间', render: function (r) { return dateText(r.retrieved_at); } }
        ],
        filters: [
          { param: 'subject_type', label: '主体类型', options: S.opts(S.options.evidenceSubjectTypes) },
          { param: 'confidence', label: '置信度', options: S.opts(S.options.confidence) }
        ],
        create: { label: '登记证据', defaults: { subject_type: 'COMPANY', confidence: 'UNVERIFIED' } },
        form: { fields: evidenceFields, editTitle: '编辑证据', buildPayload: nullifyEmpty },
        detail: { keys: [], body: evidenceDetailBody, size: 'lg' },
        defaultSort: '-retrieved_at',
        emptyTitle: '暂无证据',
        emptyText: '把每条可追溯的公开信息登记为证据：填写主张、来源 URL、发布方与获取时间，并标记是否交叉验证。'
      });
    }
  };

  /* ============================================================
   * 6. 供应商核验（supplier-verifications）
   * ============================================================ */
  var verificationFields = null;

  function verificationDetailBody(row) {
    var html = matrixHint(row, 'status', 70, 40);
    html += UI.kv([
      ['供应商公司', companyName(row.supplier_company_id)],
      ['核验结论', statusBadge(row.status)],
      ['总分', '<strong>' + numText(row.score) + '</strong> <span class="small faint">/ 100</span>'],
      ['核验人', pendingText(row.verified_by)],
      ['核验时间', dateText(row.verified_at)],
      ['创建时间', dateText(row.created_at)],
      ['更新时间', dateText(row.updated_at)]
    ]);
    html += checklistBlock(row, 'supplierVerifications');
    html += UI.detailBlock('缺口 / 待补证据', row.gaps);
    html += UI.detailBlock('备注', row.notes);
    html += UI.tip('结论提示：建议总分 ≥ 70 且关键项通过才标记 VERIFIED；总分 &lt; 40 时建议 REJECTED。核验只给证据结论，升级与对外一律 CEO 审批。');
    return html;
  }

  V.supplierVerifications = {
    title: '供应商核验',
    subtitle: '核验清单 · 评分 · 结论',
    mount: function (root) {
      if (!verificationFields) verificationFields = S.formFields('supplierVerifications');
      var ctx = UI.listPage(root, {
        resource: 'supplier-verifications',
        title: '供应商核验',
        subtitle: '核验只依据证据；结论与评分不一致时会在详情中提示',
        singular: '核验记录',
        columns: [
          { key: 'supplier_company_id', label: '供应商', render: function (r) { return sub(companyName(r.supplier_company_id), '核验 #' + U.esc(r.id)); } },
          { key: 'status', label: '结论', render: function (r) { return statusBadge(r.status); } },
          { key: 'score', label: '总分', render: function (r) { return '<strong>' + numText(r.score) + '</strong>'; } },
          { key: 'verified_by', label: '核验人', render: function (r) { return pendingText(r.verified_by); } },
          { key: 'verified_at', label: '核验时间', render: function (r) { return dateText(r.verified_at); } },
          { key: 'updated_at', label: '更新', render: function (r) { return dateText(r.updated_at); } }
        ],
        filters: [
          { param: 'status', label: '结论', options: S.opts(S.options.verificationStatus) }
        ],
        create: { label: '新建核验', subtitle: '逐项确认后给出评分与结论', defaults: { status: 'PENDING' } },
        form: {
          fields: verificationFields,
          editTitle: '编辑核验记录',
          buildPayload: function (values) {
            var payload = nullifyEmpty(values);
            delete payload.checklist;
            return payload;
          }
        },
        advance: { entity: 'supplier-verifications' },
        detail: { keys: [], body: verificationDetailBody, size: 'lg' },
        defaultSort: '-updated_at',
        emptyTitle: '暂无核验记录',
        emptyText: '选择供应商，逐项确认主体、授权、容量证据、海外服务与商务条款，给出评分与结论。'
      });
      FU.loadCompanies(verificationFields, 'supplier_company_id', 'SUPPLIER');
      loadCompanyNames().then(function () { ctx.reload(); });
      return ctx;
    }
  };

  /* ============================================================
   * 7. 需求资格核验（demand-qualifications）
   * ============================================================ */
  var qualificationFields = null;

  function qualificationDetailBody(row) {
    var html = matrixHint(row, 'status', 70, 40);
    html += UI.kv([
      ['需求', U.isEmpty(row.demand_id) ? '<span class="dash-text">—</span>' : '需求 #' + U.esc(row.demand_id)],
      ['资格结论', statusBadge(row.status)],
      ['总分', '<strong>' + numText(row.score) + '</strong> <span class="small faint">/ 100</span>'],
      ['核验人', pendingText(row.qualified_by)],
      ['核验时间', dateText(row.qualified_at)],
      ['创建时间', dateText(row.created_at)],
      ['更新时间', dateText(row.updated_at)]
    ]);
    html += checklistBlock(row, 'demandQualifications');
    html += UI.detailBlock('缺口 / 待确认项', row.gaps);
    html += UI.detailBlock('备注', row.notes);
    html += UI.tip('只有一手核实（决策人/预算/时间窗/合规/签约路径/数据驻留）才允许升级线索等级；未经 CEO 批准不得对外承诺。');
    return html;
  }

  V.demandQualifications = {
    title: '需求资格核验',
    subtitle: '六维核验 · 评分 · 结论',
    mount: function (root) {
      if (!qualificationFields) qualificationFields = S.formFields('demandQualifications');
      var ctx = UI.listPage(root, {
        resource: 'demand-qualifications',
        title: '需求资格核验',
        subtitle: '核验需求是否具备推进条件；未确认项会保留为缺口',
        singular: '资格核验',
        columns: [
          { key: 'demand_id', label: '需求', render: function (r) { return sub(U.isEmpty(r.demand_id) ? '<span class="dash-text">—</span>' : '需求 #' + U.esc(r.demand_id), '核验 #' + U.esc(r.id)); } },
          { key: 'status', label: '结论', render: function (r) { return statusBadge(r.status); } },
          { key: 'score', label: '总分', render: function (r) { return '<strong>' + numText(r.score) + '</strong>'; } },
          { key: 'qualified_by', label: '核验人', render: function (r) { return pendingText(r.qualified_by); } },
          { key: 'qualified_at', label: '核验时间', render: function (r) { return dateText(r.qualified_at); } },
          { key: 'updated_at', label: '更新', render: function (r) { return dateText(r.updated_at); } }
        ],
        filters: [
          { param: 'status', label: '结论', options: S.opts(S.options.verificationStatus) }
        ],
        create: { label: '新建资格核验', defaults: { status: 'PENDING' } },
        form: { fields: qualificationFields, editTitle: '编辑资格核验', buildPayload: nullifyEmpty },
        advance: { entity: 'demand-qualifications' },
        detail: { keys: [], body: qualificationDetailBody, size: 'lg' },
        defaultSort: '-updated_at',
        emptyTitle: '暂无资格核验',
        emptyText: '选择需求，确认决策人、预算、时间窗、合规、签约路径与数据驻留六项。'
      });
      FU.loadDemands(qualificationFields, 'demand_id');
      return ctx;
    }
  };

  /* ============================================================
   * 8. 算力规格标准化（specs）
   * ============================================================ */
  var specFields = null;

  function specDetailBody(row) {
    return UI.kv([
      ['GPU 型号', '<strong>' + U.escText(row.gpu_model) + '</strong>'],
      ['厂商', pendingText(row.vendor)],
      ['形态', pendingText(row.form_factor)],
      ['显存', U.isEmpty(row.memory_gb) ? '<span class="dash-text">—</span>' : U.esc(String(row.memory_gb)) + ' GB'],
      ['显存类型', pendingText(row.memory_type)],
      ['显存带宽', U.isEmpty(row.memory_bandwidth_gbps) ? '<span class="dash-text">—</span>' : U.esc(String(row.memory_bandwidth_gbps)) + ' GB/s'],
      ['FP16', U.isEmpty(row.fp16_tflops) ? '<span class="dash-text">—</span>' : U.esc(String(row.fp16_tflops)) + ' TFLOPS'],
      ['TF32', U.isEmpty(row.tf32_tflops) ? '<span class="dash-text">—</span>' : U.esc(String(row.tf32_tflops)) + ' TFLOPS'],
      ['FP8', U.isEmpty(row.fp8_tflops) ? '<span class="dash-text">—</span>' : U.esc(String(row.fp8_tflops)) + ' TFLOPS'],
      ['互联方式', pendingText(row.interconnect)],
      ['典型集群', pendingText(row.typical_cluster)],
      ['单节点功耗', U.isEmpty(row.power_kw_per_node) ? '<span class="dash-text">—</span>' : U.esc(String(row.power_kw_per_node)) + ' kW'],
      ['来源', pendingText(row.source)]
    ]) + UI.detailBlock('备注', row.notes);
  }

  V.specs = {
    title: '算力规格',
    subtitle: '规格参考库 · 口径统一',
    mount: function (root) {
      if (!specFields) specFields = S.formFields('specs');
      return UI.listPage(root, {
        resource: 'specs',
        title: '算力规格标准化',
        subtitle: '把供应商/需求方口径统一的参考库；不做性能承诺',
        singular: '规格',
        columns: [
          { key: 'gpu_model', label: 'GPU 型号', render: function (r) { return sub('<strong>' + U.escText(r.gpu_model) + '</strong>', [r.vendor, r.form_factor].filter(Boolean).join(' · ')); } },
          { key: 'memory_gb', label: '显存', className: 'cell--num', render: function (r) { return U.isEmpty(r.memory_gb) ? '<span class="dash-text">—</span>' : U.esc(String(r.memory_gb)) + ' GB'; } },
          { key: 'fp16_tflops', label: 'FP16', className: 'cell--num', render: function (r) { return numText(r.fp16_tflops); } },
          { key: 'interconnect', label: '互联', render: function (r) { return pendingText(r.interconnect); } },
          { key: 'typical_cluster', label: '典型集群', render: function (r) { return pendingText(r.typical_cluster); } },
          { key: 'source', label: '来源', render: function (r) { return pendingText(r.source); } }
        ],
        create: { label: '新增规格', defaults: {} },
        form: { fields: specFields, editTitle: '编辑规格', buildPayload: nullifyEmpty },
        detail: { keys: [], body: specDetailBody, size: 'lg' },
        defaultSort: 'gpu_model',
        emptyTitle: '暂无规格记录',
        emptyText: '新增 GPU 规格（显存、带宽、算力、互联等），用于把不同口径的供给与需求标准化比较。'
      });
    }
  };
})();
