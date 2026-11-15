/* CCGS 前端 · 模块 11 商机 / 12 项目进度 / 13 Agent 任务 / 14 CEO 审批 / 15 知识库
 * 所有对外材料均为草案；审批只能人工点击，绝不自动批准。 */
var CCGS = window.CCGS || (window.CCGS = {});
(function () {
  'use strict';

  var U = CCGS.util, UI = CCGS.ui, API = CCGS.api, S = CCGS.schema;

  /* ---------------- 通用小工具 ---------------- */
  function txt(v) { return U.text(v, '待确认'); }
  function iso(v) { return U.isEmpty(v) ? '—' : U.dateTime(v); }
  function esc(v) { return U.esc(v); }
  function statusBadge(v) { return UI.badge(v, S.statusKind(v), { sm: true }); }
  function plain(v) { return U.isEmpty(v) ? '<span class="dash-text">—</span>' : esc(String(v)); }
  function pending(v) { return U.isEmpty(v) ? '<span class="pending-text">待确认</span>' : esc(String(v)); }
  function numText(v) {
    if (U.isEmpty(v)) return '<span class="dash-text">—</span>';
    var n = Number(v);
    return esc(isNaN(n) ? String(v) : String(n));
  }
  /* 空字符串可选字段 → null：避免空外键（'' 或 'undefined'）触发后端 FOREIGN KEY 失败 */
  function nullifyEmpty(values) {
    var out = {};
    Object.keys(values || {}).forEach(function (k) {
      var v = values[k];
      out[k] = (v === '') ? null : v;
    });
    return out;
  }
  function actionLabel(a) {
    var map = {
      CREATE: '新建', UPDATE: '更新', DELETE: '删除', STATUS_CHANGE: '状态变更', IMPORT: '导入',
      EXPORT: '导出', APPROVE: '批准', REJECT: '驳回', RETURN: '退回', RUN: '运行',
      BACKUP: '备份', RESTORE: '恢复', MATCH: '匹配', DECIDE: '审批决策', LOGIN: '登录'
    };
    return map[a] || a || '活动';
  }
  function actionKind(a) {
    var s = String(a || '').toUpperCase();
    if (/DELETE|REJECT|FAIL|CANCEL|LOST|WARN/.test(s)) return 'red';
    if (/CREATE|IMPORT|APPROVE|BUILD|RESTORE|SUCCESS|DONE/.test(s)) return 'green';
    return 'amber';
  }
  function statCard(label, value, hint, kind) {
    return '<div class="stat' + (kind ? ' stat--' + kind : '') + '">' +
      '<div class="stat-label">' + esc(label) + '</div>' +
      '<div class="stat-value">' + value + '</div>' +
      (hint ? '<div class="stat-hint">' + esc(hint) + '</div>' : '') + '</div>';
  }
  function fieldsFor(key) { return S.formFields ? S.formFields(key) : []; }
  function formUtil() { return CCGS.formUtil || null; }
  function patchSelectOptions(fields, key, options) {
    (fields || []).forEach(function (f) {
      if (f && f.key === key) {
        f.type = 'select';
        f.options = options;
      }
    });
  }
  function loadDemandOptions(fields, key) {
    var FU = formUtil();
    if (FU && FU.loadDemands) {
      try { var p = FU.loadDemands(fields, key); if (p && p.catch) p.catch(function () {}); } catch (e) {}
      return;
    }
    API.list('demands', { page_size: 200 }).then(function (res) {
      patchSelectOptions(fields, key, (res.items || []).map(function (d) {
        return { value: d.id, label: '#' + d.id + ' ' + txt(d.title) };
      }));
    }).catch(function () {});
  }
  function loadSupplyOptions(fields, key) {
    var FU = formUtil();
    if (FU && FU.loadSupplies) {
      try { var p = FU.loadSupplies(fields, key); if (p && p.catch) p.catch(function () {}); } catch (e) {}
      return;
    }
    API.list('supplies', { page_size: 200 }).then(function (res) {
      patchSelectOptions(fields, key, (res.items || []).map(function (s) {
        return { value: s.id, label: '#' + s.id + ' ' + txt(s.gpu_model) + ' × ' + (s.gpu_count === null || s.gpu_count === undefined ? '—' : s.gpu_count) };
      }));
    }).catch(function () {});
  }

  /* ============================================================
   * 模块 11 · 商机管理（阶段看板）
   * ============================================================ */
  var OPP_STAGES = ['OPEN', 'DISCLOSED', 'INTRODUCED', 'TERM_SHEET', 'CA', 'CLOSED_WON', 'CLOSED_LOST'];

  CCGS.views.opportunities = {
    title: '商机管理',
    subtitle: '按阶段推进商机；CEO 审批状态需人工处理，系统不会自动批准',
    mount: function (root) {
      root.innerHTML = '<div class="view">' +
        UI.draftRibbon('商机材料、费用条款与披露话术均为内部草案，未经 CEO 批准不得外发') +
        UI.tip('阶段推进与 CEO 审批状态只由人工点击完成，系统不会自动推进或批准；所有变更写入审计日志。' +
          '本页不生成正式报价、不签约、不收款。') +
        '<div class="toolbar">' +
          UI.button({ label: '新建商机', kind: 'primary', icon: 'plus', act: 'new-opp' }) +
          UI.button({ label: '刷新', kind: 'ghost', size: 'sm', icon: 'refresh', act: 'refresh-opps' }) +
          '<div class="toolbar-spacer"></div>' +
          '<span class="small muted">看板按阶段分组，点击卡片可查看详情、推进阶段或编辑</span>' +
        '</div>' +
        '<div id="opp-board" class="kanban"></div>' +
        '</div>';

      var board = U.byId('opp-board');
      var state = { items: [], loading: true, error: null };
      var oppFields = fieldsFor('opportunities');
      loadDemandOptions(oppFields, 'demand_id');
      loadSupplyOptions(oppFields, 'supply_id');

      function render() {
        if (state.loading) {
          board.innerHTML = '<div class="table-loading"><span class="spinner spinner--sm"></span> 加载商机…</div>';
          return;
        }
        if (state.error) {
          board.innerHTML = UI.errorState(state.error, true) +
            '<div style="margin-top:8px">' + UI.button({ label: '重试', size: 'sm', act: 'retry-opps', icon: 'refresh' }) + '</div>';
          return;
        }
        if (!state.items.length) {
          board.innerHTML = UI.empty({
            icon: 'flow',
            title: '暂无商机',
            text: '商机通常由已核验的匹配记录推进而来。可点击「新建商机」手工登记。',
            actions: UI.button({ label: '新建商机', kind: 'primary', size: 'sm', act: 'new-opp', icon: 'plus' })
          });
          return;
        }
        board.innerHTML = OPP_STAGES.map(function (stage) {
          var list = state.items.filter(function (o) { return o.stage === stage; });
          var cards = list.map(function (o) {
            return '<button class="kanban-card" type="button" data-opp-id="' + esc(String(o.id)) + '">' +
              '<span class="kc-title">' + esc(txt(o.title)) + '</span>' +
              '<span class="kc-meta">' +
                '<span class="kc-id">#' + esc(String(o.id)) + '</span>' +
                statusBadge(o.model_type) +
                UI.badge(o.ceo_approval_status, S.statusKind(o.ceo_approval_status), { sm: true }) +
                (o.fee_payer ? '<span>' + esc(o.fee_payer) + '</span>' : '') +
              '</span>' +
              (o.next_step ? '<span class="kc-meta">' + esc(o.next_step) + '</span>' : '') +
              '</button>';
          }).join('');
          return '<div class="kanban-col">' +
            '<div class="kanban-head"><span class="k-title">' + esc(S.label(stage)) + '</span>' +
            '<span class="k-count">' + list.length + '</span></div>' +
            '<div class="kanban-cards">' + (cards || '<div class="kanban-empty">暂无</div>') + '</div>' +
            '</div>';
        }).join('');
      }

      function load() {
        state.loading = true; state.error = null; render();
        API.list('commercial-opportunities', { page_size: 200, sort: '-updated_at' })
          .then(function (res) {
            state.items = (res && res.items) || [];
            state.loading = false;
            render();
          })
          .catch(function (err) {
            state.loading = false; state.error = err; render();
            if (err && err.status !== 0) UI.toast('error', UI.errorText(err), 5200);
          });
      }

      function findOpp(id) {
        for (var i = 0; i < state.items.length; i++) {
          if (String(state.items[i].id) === String(id)) return state.items[i];
        }
        return null;
      }

      function advanceOpp(o, target) {
        UI.confirm({
          title: '推进商机阶段',
          message: '将《' + txt(o.title) + '》从「' + S.label(o.stage) + '」推进为「' + S.label(target) + '」？',
          warn: '阶段推进只由人工确认；操作会写入审计日志，不会对外发送任何消息。',
          confirmText: '确认推进',
          danger: /LOST|CLOSED_LOST/.test(target)
        }).then(function (r) {
          if (!r.ok) return;
          API.update('commercial-opportunities', o.id, { stage: target })
            .then(function () { UI.toast('success', '阶段已推进为 ' + S.label(target)); load(); })
            .catch(function (err) { UI.toast('error', UI.errorText(err), 8000); });
        });
      }

      function openOppDetail(o) {
        var rows = [
          ['阶段', statusBadge(o.stage)],
          ['合作模式', statusBadge(o.model_type)],
          ['CEO 审批状态', statusBadge(o.ceo_approval_status)],
          ['关联需求', o.demand_id ? '<a href="#/demands">#' + esc(String(o.demand_id)) + '</a>' : '<span class="dash-text">—</span>'],
          ['关联供给', o.supply_id ? '<a href="#/supplies">#' + esc(String(o.supply_id)) + '</a>' : '<span class="dash-text">—</span>'],
          ['关联匹配记录', o.match_id ? '<a href="#/matching">#' + esc(String(o.match_id)) + '</a>' : '<span class="dash-text">—</span>'],
          ['付费方', pending(o.fee_payer)],
          ['计费基础', pending(o.fee_basis)],
          ['费用条款（草案，不外发）', pending(o.fee_terms)],
          ['利益冲突已披露', UI.boolBadge(o.conflict_disclosed)],
          ['下一步', pending(o.next_step)],
          ['负责人', pending(o.owner)],
          ['创建时间', esc(iso(o.created_at))],
          ['更新时间', esc(iso(o.updated_at))]
        ];
        var body = UI.draftRibbon('商机详情为内部草案，未经 CEO 批准不得外发；不构成正式报价或合同') +
          UI.kv(rows) +
          '<p class="help" style="margin-top:10px">CEO 审批状态只能由 CEO 审批中心人工处理；本页不会自动批准。</p>';
        var actions = [];
        var targets = (S.transitions['commercial-opportunities'] || {})[o.stage] || [];
        targets.forEach(function (t) {
          actions.push({
            label: '推进为 ' + S.label(t),
            kind: /LOST/.test(t) ? 'danger' : 'primary',
            onClick: function (h) { h.close(); advanceOpp(o, t); }
          });
        });
        actions.push({ label: '编辑', icon: 'edit', onClick: function (h) { h.close(); editOpp(o); } });
        actions.push({ label: '关闭', onClick: function (h) { h.close(); } });
        UI.openModal({
          title: '商机 #' + o.id,
          subtitle: txt(o.title),
          size: 'lg',
          body: body,
          actions: actions
        });
      }

      function openOppForm(item) {
        var values = {};
        if (item) {
          oppFields.forEach(function (f) { if (item[f.key] !== undefined) values[f.key] = item[f.key]; });
        } else {
          values = { stage: 'OPEN', model_type: 'ADVISORY', ceo_approval_status: 'PENDING', conflict_disclosed: 0, owner: 'local' };
        }
        UI.openForm({
          title: item ? ('编辑商机 #' + item.id) : '新建商机',
          subtitle: '商机为内部推进记录；不报价、不签约、不外发',
          fields: oppFields,
          values: values,
          original: item || null,
          submitText: item ? '保存修改' : '创建商机',
          onSubmit: function (payload) {
            payload = nullifyEmpty(payload);
            var p = item ? API.update('commercial-opportunities', item.id, payload)
                         : API.create('commercial-opportunities', payload);
            return p.then(function () {
              UI.toast('success', item ? '商机已更新' : '商机已创建');
              load();
            });
          }
        });
      }
      function editOpp(o) { openOppForm(o); }

      UI.on(root, 'click', '[data-act]', function (ev) {
        var btn = ev.target.closest('[data-act]');
        if (!btn || btn.disabled) return;
        var act = btn.getAttribute('data-act');
        if (act === 'new-opp') openOppForm(null);
        else if (act === 'refresh-opps' || act === 'retry-opps') load();
      });
      UI.on(root, 'click', '[data-opp-id]', function (ev) {
        var card = ev.target.closest('[data-opp-id]');
        if (!card) return;
        var o = findOpp(card.getAttribute('data-opp-id'));
        if (o) openOppDetail(o);
      });

      load();
      return function () {};
    }
  };

  /* ============================================================
   * 模块 12 · 项目进度（活动时间线 + 阶段漏斗）
   * ============================================================ */
  var PIPE_LABELS = {
    supplier: '供应商', suppliers: '供应商', supply: '供给', supplies: '供给',
    demand: '需求', demands: '需求', opportunity: '商机', opportunities: '商机'
  };
  var PIPE_ORDER = ['supplier', 'suppliers', 'demand', 'demands', 'opportunity', 'opportunities', 'supply', 'supplies'];

  CCGS.views.activities = {
    title: '项目进度',
    subtitle: 'project_activities 时间线与阶段漏斗（只读）',
    mount: function (root) {
      root.innerHTML = '<div class="view">' +
        UI.tip('本页数据来自 project_activities 与阶段汇总，只读；所有写操作在对应模块完成后自动留痕。') +
        '<div class="stat-grid" id="act-stats"></div>' +
        '<section class="card" style="margin-bottom:16px"><div class="card-head">' +
          '<div class="card-title">阶段漏斗</div><div class="card-sub">来自 /api/reports/pipeline，数据不足时明确提示</div></div>' +
          '<div class="card-body" id="act-funnel"></div></section>' +
        '<section class="card"><div class="card-head"><div class="card-title">活动时间线</div>' +
          '<div class="card-actions">' +
            UI.button({ label: '刷新', size: 'sm', kind: 'ghost', icon: 'refresh', act: 'refresh-act' }) +
          '</div></div>' +
          '<div class="toolbar">' +
            '<label class="search-field">' + U.icon('search', 15) +
              '<input type="search" id="act-q" placeholder="搜索活动摘要 / 操作者…" autocomplete="off"></label>' +
            '<label class="filter-label">实体</label>' +
            '<select class="select select--filter" id="act-entity"><option value="">全部实体</option></select>' +
            '<span class="toolbar-spacer"></span>' +
            '<label class="filter-label">显示</label>' +
            '<select class="select select--filter" id="act-limit">' +
              '<option value="50">最近 50 条</option><option value="100" selected>最近 100 条</option><option value="200">最近 200 条</option>' +
            '</select>' +
          '</div>' +
          '<div class="card-body"><div class="timeline" id="act-timeline"></div></div></section>' +
        '</div>';

      var el = {
        stats: U.byId('act-stats'),
        funnel: U.byId('act-funnel'),
        timeline: U.byId('act-timeline'),
        q: U.byId('act-q'),
        entity: U.byId('act-entity'),
        limit: U.byId('act-limit')
      };
      var state = { items: [], pipeline: [], loading: true, error: null };

      function normalizePipeline(doc) {
        if (!doc) return [];
        var src = doc.pipeline || doc.counts || doc;
        var used = {};
        var out = [];
        PIPE_ORDER.forEach(function (k) {
          if (used[k]) return;
          var group = src[k];
          if (!group || typeof group !== 'object' || Array.isArray(group)) return;
          var entries = Object.keys(group).filter(function (st) { return typeof group[st] === 'number'; });
          if (!entries.length) return;
          used[k] = true;
          out.push({ label: PIPE_LABELS[k] || k, raw: group });
        });
        return out;
      }

      function renderStats() {
        var today = U.dateOnly(U.nowIso());
        var todayCount = state.items.filter(function (a) { return a.ts && U.dateOnly(a.ts) === today; }).length;
        var types = {};
        state.items.forEach(function (a) { if (a.entity_type) types[a.entity_type] = true; });
        var last = state.items.length ? state.items[0].ts : null;
        el.stats.innerHTML = statCard('活动总数', esc(String(state.items.length)), '最近 200 条', 'accent') +
          statCard('今日活动', esc(String(todayCount)), '本地时间', 'good') +
          statCard('涉及实体类型', esc(String(Object.keys(types).length)), '供应商 / 需求 / 供给…') +
          statCard('最近活动', esc(last ? U.relTime(last) : '—'), last ? U.dateTime(last) : '暂无记录');
      }

      function renderFunnel() {
        var groups = state.pipeline.filter(function (g) {
          return g.raw && Object.keys(g.raw).some(function (k) { return typeof g.raw[k] === 'number'; });
        });
        if (!groups.length) {
          el.funnel.innerHTML = UI.empty({
            icon: 'filter',
            title: '漏斗数据不足',
            text: '后端返回 data_insufficient 或暂无阶段数据。录入供应商 / 需求 / 商机后会自动生成漏斗。'
          });
          return;
        }
        el.funnel.innerHTML = groups.map(function (g) {
          var values = Object.keys(g.raw).filter(function (k) {
            return typeof g.raw[k] === 'number';
          }).map(function (k) { return { st: k, n: Number(g.raw[k]) || 0 }; });
          var max = 1;
          values.forEach(function (v) { max = Math.max(max, v.n); });
          var total = values.reduce(function (a, b) { return a + b.n; }, 0);
          return '<div style="margin-bottom:14px">' +
            '<div class="section-title" style="margin:0 0 6px">' + esc(g.label) +
            '<span class="small muted"> · 共 ' + total + ' 条</span></div>' +
            '<div class="funnel">' + values.map(function (v, i) {
              var pct = max > 0 ? Math.max(3, Math.round(v.n / max * 100)) : 3;
              var cls = i === values.length - 1 ? 'green' : 'amber';
              return '<div class="funnel-row"><span class="funnel-label">' + esc(S.label(v.st)) + '</span>' +
                '<span class="funnel-track"><span class="funnel-fill funnel-fill--' + cls +
                '" style="width:' + pct + '%;display:block"></span></span>' +
                '<span class="funnel-val">' + v.n + '</span></div>';
            }).join('') + '</div></div>';
        }).join('');
      }

      function renderTimeline() {
        var q = (el.q.value || '').trim().toLowerCase();
        var ent = el.entity.value;
        var limit = Number(el.limit.value) || 100;
        var list = state.items.filter(function (a) {
          if (ent && a.entity_type !== ent) return false;
          if (!q) return true;
          return [a.summary, a.action, a.actor, a.entity_type, a.entity_id, a.detail]
            .map(function (x) { return String(x === null || x === undefined ? '' : x).toLowerCase(); })
            .join(' ').indexOf(q) >= 0;
        }).slice(0, limit);
        if (state.loading) {
          el.timeline.innerHTML = '<div class="table-loading"><span class="spinner spinner--sm"></span> 加载活动…</div>';
          return;
        }
        if (state.error) { el.timeline.innerHTML = UI.errorState(state.error, true); return; }
        if (!list.length) {
          el.timeline.innerHTML = UI.empty({
            icon: 'clock',
            title: '暂无活动记录',
            text: '写操作（新建 / 更新 / 审批 / 匹配 / 导入）会自动写入 project_activities。'
          });
          return;
        }
        el.timeline.innerHTML = list.map(function (a) {
          var meta = [a.actor || 'local'];
          if (a.entity_type) meta.push(a.entity_type + (a.entity_id !== null && a.entity_id !== undefined ? ' #' + a.entity_id : ''));
          return '<div class="tl-item"><span class="tl-dot tl-dot--' + actionKind(a.action) + '"></span>' +
            '<div class="tl-head"><span class="tl-summary">' + esc(actionLabel(a.action)) + ' · ' + esc(txt(a.summary)) + '</span>' +
            '<span class="tl-meta">' + esc(meta.join(' · ')) + '</span>' +
            '<span class="tl-date">' + esc(U.dateTime(a.ts)) + '</span></div>' +
            (a.detail ? '<div class="tl-detail">' + esc(a.detail) + '</div>' : '') + '</div>';
        }).join('');
      }

      function renderEntityOptions() {
        var types = {};
        state.items.forEach(function (a) { if (a.entity_type) types[a.entity_type] = true; });
        var cur = el.entity.value;
        el.entity.innerHTML = '<option value="">全部实体</option>' +
          Object.keys(types).sort().map(function (t) {
            return '<option value="' + esc(t) + '"' + (cur === t ? ' selected' : '') + '>' + esc(t) + '</option>';
          }).join('');
      }

      function load() {
        state.loading = true; state.error = null;
        renderTimeline();
        var pActivities = API.list('activities', { page_size: 200, sort: '-ts' }).then(function (res) {
          state.items = (res && res.items) || [];
        }).catch(function (err) { state.items = []; state.error = err; });
        var pPipe = API.reportPipeline().catch(function () { return null; });
        var pDash = API.dashboard().catch(function () { return null; });
        Promise.all([pActivities, pPipe, pDash]).then(function (out) {
          state.loading = false;
          state.pipeline = [];
          if (out[1]) state.pipeline = normalizePipeline(out[1]);
          if (!state.pipeline.length && out[2] && out[2].pipeline) {
            state.pipeline = normalizePipeline(out[2]);
          }
          renderStats(); renderEntityOptions(); renderFunnel(); renderTimeline();
          if (state.error) UI.toast('warn', UI.errorText(state.error), 5200);
        });
      }

      UI.on(root, 'input', '#act-q', function () { renderTimeline(); });
      UI.on(root, 'change', '#act-entity', function () { renderTimeline(); });
      UI.on(root, 'change', '#act-limit', function () { renderTimeline(); });
      UI.on(root, 'click', '[data-act="refresh-act"]', function () { load(); });

      load();
      return function () {};
    }
  };

  /* ============================================================
   * 模块 13 · Agent 任务管理
   * ============================================================ */
  CCGS.views.agents = {
    title: 'Agent 任务',
    subtitle: '11 个本地 Agent 定义与任务队列；运行只在本机，不自动外发',
    mount: function (root) {
      root.innerHTML = '<div class="view">' +
        UI.tip('Agent 任务只在本机运行，可能调用 Web 搜索 / 网页读取；不会发送邮件、私信或对外报价。' +
          '需要 CEO 审批的任务会在审批中心由人工处理。') +
        '<section class="card" style="margin-bottom:16px"><div class="card-head">' +
          '<div class="card-title">Agent 阵容</div>' +
          '<div class="card-sub" id="agent-sub">来自 /api/agents</div>' +
          '<div class="card-actions">' + UI.button({ label: '刷新', size: 'sm', kind: 'ghost', icon: 'refresh', act: 'refresh-agents' }) + '</div>' +
          '</div><div class="card-body"><div class="agent-grid" id="agent-grid"></div></div></section>' +
        '<section class="card"><div class="card-body" id="agent-tasks-slot"></div></section>' +
        '</div>';

      var grid = U.byId('agent-grid');
      var sub = U.byId('agent-sub');
      var slot = U.byId('agent-tasks-slot');
      var taskFields = fieldsFor('agentTasks');
      var taskCtx = null;

      function agentCard(a) {
        var name = a.name || a.agent_name || a.id || 'Agent';
        var role = a.role || a.title || a.category || a.stage || '';
        var desc = a.description || a.purpose || a.desc || a.responsibility || a.summary || '';
        var tags = a.skills || a.capabilities || a.tags || [];
        if (typeof tags === 'string') tags = tags.split(/[,，;；、]+/).filter(Boolean);
        if (!Array.isArray(tags)) tags = [];
        var initialText = /^[A-Za-z]/.test(String(name)) ? String(name).charAt(0).toUpperCase() : String(name).charAt(0);
        return '<div class="agent-card">' +
          '<div class="agent-head"><span class="agent-avatar">' + esc(initialText) + '</span>' +
          '<div><div class="agent-name">' + esc(name) + '</div>' +
          (role ? '<div class="agent-role">' + esc(role) + '</div>' : '') + '</div></div>' +
          (desc ? '<div class="agent-desc">' + esc(desc) + '</div>' : '') +
          (tags.length ? '<div class="agent-tags">' + tags.slice(0, 6).map(function (t) {
            return '<span class="tag">' + esc(typeof t === 'object' ? (t.name || t.label || JSON.stringify(t)) : t) + '</span>';
          }).join('') + '</div>' : '') +
          '</div>';
      }

      function loadAgents() {
        grid.innerHTML = '<div class="table-loading"><span class="spinner spinner--sm"></span> 加载 Agent 定义…</div>';
        return API.agents()
          .then(function (data) {
            var list = Array.isArray(data) ? data : ((data && (data.items || data.agents)) || []);
            if (!list.length) {
              grid.innerHTML = UI.empty({ icon: 'grid', title: '暂无 Agent 定义', text: '后端 /api/agents 返回为空。' });
              return;
            }
            sub.textContent = '共 ' + list.length + ' 个 Agent · 来自 /api/agents';
            grid.innerHTML = list.map(agentCard).join('');
            var names = list.map(function (a) { return a.name || a.agent_name || a.id; }).filter(Boolean);
            patchSelectOptions(taskFields, 'agent_name', names.map(function (n) { return { value: n, label: n }; }));
            if (taskCtx) taskCtx.reload();
          })
          .catch(function (err) {
            grid.innerHTML = UI.errorState(err, true);
            sub.textContent = 'Agent 定义加载失败';
          });
      }

      function taskTitle(row) { return txt(row.title) + ' · ' + txt(row.agent_name); }

      function runTask(task, ctx) {
        var go = function () {
          UI.toast('info', '已触发 Agent 任务 #' + task.id + '，正在本地运行…');
          API.runAgentTask(task.id).then(function (res) {
            var st = (res && res.status) || 'DONE';
            var body = '<div class="runner-actions" style="margin-bottom:10px">' +
              UI.badge(st, S.statusKind(st), { sm: false }) +
              (res && res.task_id ? '<span class="small muted">task #' + esc(String(res.task_id)) + '</span>' : '') +
              '</div>' +
              (res && res.result ? '<div class="detail-block"><h4>运行结果</h4><pre>' + esc(typeof res.result === 'string' ? res.result : U.jsonPretty(res.result)) + '</pre></div>' : '<p class="help">后端未返回 result 字段。</p>') +
              (res && res.output_path ? '<div class="kv"><div class="kv-row"><div class="kv-key">输出路径</div><div class="kv-val">' + esc(res.output_path) + '</div></div></div>' : '') +
              '<p class="help" style="margin-top:10px">结果仅保存在本地；不会自动外发。</p>';
            UI.openModal({ title: 'Agent 运行结果', subtitle: taskTitle(task), size: 'lg', body: body, actions: [{ label: '关闭', onClick: function (h) { h.close(); } }] });
            if (ctx && ctx.reload) ctx.reload();
          }).catch(function (err) {
            UI.toast('error', UI.errorText(err), 8000);
          });
        };
        UI.confirm({
          title: '触发 Agent 任务',
          message: '将在本机运行 Agent 任务 #' + task.id + '（' + txt(task.agent_name) + '）。',
          warn: '运行可能调用 Web 搜索 / 网页读取；不会自动发送邮件、私信或生成正式报价。',
          confirmText: '运行任务'
        }).then(function (r) { if (r.ok) go(); });
      }

      function mountTasks() {
        taskCtx = UI.listPage(slot, {
          resource: 'agent-tasks',
          title: '任务队列',
          subtitle: '状态筛选与运行；运行结果仅本地展示',
          singular: '任务',
          create: { label: '新建任务', title: '新建 Agent 任务', subtitle: '任务默认 QUEUED，需手动运行' },
          form: { fields: taskFields, wide: true, buildPayload: nullifyEmpty },
          defaultSort: '-created_at',
          pageSize: 25,
          filters: [{ param: 'status', label: '状态', options: S.opts(S.options.taskStatus) }],
          columns: [
            { key: 'id', label: 'ID', sortable: true, className: 'cell--id' },
            { key: 'agent_name', label: 'Agent', sortable: true, className: 'cell--mono' },
            { key: 'title', label: '任务', sortable: true, render: function (r) { return '<span class="cell-link">' + esc(txt(r.title)) + '</span>' + (r.task_type ? '<span class="cell-sub">' + esc(r.task_type) + '</span>' : ''); } },
            { key: 'priority', label: '优先级', sortable: true, render: function (r) { return statusBadge(r.priority); } },
            { key: 'status', label: '状态', sortable: true, render: function (r) { return statusBadge(r.status); } },
            { key: 'requires_approval', label: '需审批', sortable: true, render: function (r) { return UI.boolBadge(r.requires_approval, '是', '否'); } },
            { key: 'created_at', label: '创建时间', sortable: true, className: 'cell--mono', render: function (r) { return esc(iso(r.created_at)); } }
          ],
          rowActions: function (row) {
            var html = '<div class="row-actions">';
            if (row.status !== 'RUNNING') {
              html += UI.button({ label: '运行', size: 'sm', kind: 'primary', icon: 'play', act: 'run-task', data: { id: row.id } });
            }
            html += UI.button({ label: '详情', size: 'sm', act: 'detail', data: { id: row.id } });
            html += '</div>';
            return html;
          },
          onAction: function (act, actEl, ctx) {
            if (act === 'run-task') {
              var id = actEl.getAttribute('data-id');
              var row = null;
              (ctx.state.items || []).forEach(function (it) { if (String(it.id) === String(id)) row = it; });
              if (row) runTask(row, ctx);
              return true;
            }
            return false;
          },
          detail: {
            size: 'lg',
            title: function (r) { return '任务 #' + r.id; },
            keys: [
              ['Agent', 'agent_name'], ['任务类型', 'task_type'], ['标题', 'title'], ['优先级', 'priority'],
              ['状态', 'status'], ['需要审批', 'requires_approval'], ['输入引用', 'input_ref'],
              ['输出路径', 'output_path'], ['开始时间', 'started_at'], ['结束时间', 'finished_at'],
              ['创建时间', 'created_at'], ['更新时间', 'updated_at']
            ],
            body: function (r) {
              var extra = '';
              if (!U.isEmpty(r.result_summary)) extra += UI.detailBlock('结果摘要', r.result_summary);
              if (!U.isEmpty(r.error)) extra += UI.detailBlock('错误信息', r.error);
              if (!extra) extra = '<p class="help">暂无运行结果。</p>';
              return extra + '<p class="help" style="margin-top:10px">任务只在本机运行；需要审批的任务会进入 CEO 审批中心。</p>';
            },
            actions: function (r, ctx) {
              if (r.status === 'RUNNING') return [];
              return [{ label: '运行任务', kind: 'primary', icon: 'play', onClick: function (h) { h.close(); runTask(r, ctx); } }];
            }
          }
        });
      }

      UI.on(root, 'click', '[data-act="refresh-agents"]', function () { loadAgents(); });

      mountTasks();
      loadAgents();
      return function () {};
    }
  };

  /* ============================================================
   * 模块 14 · CEO 审批中心
   * ============================================================ */
  CCGS.views.approvals = {
    title: 'CEO 审批中心',
    subtitle: '待审批事项只能由人工点击处理；系统绝不自动批准',
    mount: function (root) {
      root.innerHTML = '<div class="view">' +
        UI.tip('<strong>只能人工点击审批</strong>：本页不会自动批准任何事项，也不会对外发送通知。' +
          '驳回与退回必须填写原因；批准备注建议填写。所有决策写入审计日志。') +
        '<section class="card" style="margin-bottom:16px"><div class="card-head">' +
          '<div class="card-title">待审批</div><div class="card-sub" id="ap-pending-sub">加载中…</div>' +
          '<div class="card-actions">' + UI.button({ label: '刷新', size: 'sm', kind: 'ghost', icon: 'refresh', act: 'refresh-ap' }) + '</div>' +
          '</div><div class="card-body" id="ap-pending"></div></section>' +
        '<section class="card"><div class="card-head"><div class="card-title">审批历史</div>' +
          '<div class="card-sub">最近 20 条 · 只读</div></div>' +
          '<div class="card-body" id="ap-history"></div></section>' +
        '</div>';

      var el = { pending: U.byId('ap-pending'), sub: U.byId('ap-pending-sub'), history: U.byId('ap-history') };
      var state = { pending: [], history: [], loading: true, error: null };

      function renderPending() {
        if (state.loading) { el.pending.innerHTML = '<div class="table-loading"><span class="spinner spinner--sm"></span> 加载待审批事项…</div>'; return; }
        if (state.error) {
          el.pending.innerHTML = UI.errorState(state.error, true) +
            '<div style="margin-top:8px">' + UI.button({ label: '重试', size: 'sm', act: 'retry-ap', icon: 'refresh' }) + '</div>';
          return;
        }
        if (!state.pending.length) {
          el.pending.innerHTML = UI.empty({
            icon: 'check',
            title: '没有待审批事项',
            text: 'CEO 审批队列为空。所有审批只能由人工在本地逐条点击处理，系统不会自动批准。'
          });
          return;
        }
        el.pending.innerHTML = '<div class="approval-list">' + state.pending.map(function (a) {
          var payload = a.payload_json || a.payload || null;
          return '<div class="approval-card">' +
            '<div class="approval-head">' +
              '<span class="approval-type">' + esc(txt(a.approval_type)) + '</span>' +
              '<span class="approval-subject">' + esc(txt(a.subject)) + '</span>' +
              '<span class="toolbar-spacer"></span>' +
              '<span class="badge badge--amber badge--sm">待审批</span>' +
            '</div>' +
            '<div class="approval-meta">申请人 ' + esc(txt(a.requested_by)) + ' · ' + esc(iso(a.requested_at)) +
              ' · 需要角色 ' + esc(txt(a.required_role)) + '</div>' +
            (payload !== null ? '<div class="approval-payload">' + UI.prettyJson(payload) + '</div>' : '') +
            '<div class="approval-foot">' +
              UI.button({ label: '批准', size: 'sm', kind: 'primary', act: 'decide', data: { id: a.id, decision: 'APPROVED' } }) +
              UI.button({ label: '驳回', size: 'sm', kind: 'danger', act: 'decide', data: { id: a.id, decision: 'REJECTED' } }) +
              UI.button({ label: '退回补充', size: 'sm', kind: 'ghost', act: 'decide', data: { id: a.id, decision: 'RETURNED' } }) +
              '<span class="hint">需人工决策 · 不会自动批准</span>' +
            '</div>' +
            '</div>';
        }).join('') + '</div>';
      }

      function renderHistory() {
        var list = state.history || [];
        if (!list.length) {
          el.history.innerHTML = UI.empty({ icon: 'clock', title: '暂无审批历史', text: '处理审批后，决策记录会出现在这里。' });
          return;
        }
        var rows = list.map(function (a) {
          return '<tr>' +
            '<td class="cell--id">' + esc(a.id) + '</td>' +
            '<td>' + esc(txt(a.approval_type)) + '</td>' +
            '<td>' + esc(txt(a.subject)) + '</td>' +
            '<td>' + statusBadge(a.status) + '</td>' +
            '<td>' + esc(txt(a.decided_by)) + '</td>' +
            '<td class="cell--mono">' + esc(iso(a.decided_at)) + '</td>' +
            '<td>' + esc(txt(a.decision_note)) + '</td>' +
            '</tr>';
        }).join('');
        el.history.innerHTML = '<div class="table-wrap"><table class="data-table"><thead><tr>' +
          '<th>ID</th><th>类型</th><th>事项</th><th>状态</th><th>决策人</th><th>决策时间</th><th>备注</th>' +
          '</tr></thead><tbody>' + rows + '</tbody></table></div>';
      }

      function load() {
        state.loading = true; state.error = null;
        renderPending();
        var p1 = API.pendingApprovals().then(function (res) {
          state.pending = (res && (res.items || res)) || [];
          if (!Array.isArray(state.pending)) state.pending = [];
        }).catch(function (err) { state.pending = []; state.error = err; });
        var p2 = API.list('approvals', { page_size: 20, sort: '-requested_at' })
          .then(function (res) { state.history = (res && res.items) || []; })
          .catch(function () { state.history = []; });
        Promise.all([p1, p2]).then(function () {
          state.loading = false;
          el.sub.textContent = state.pending.length + ' 项待人工决策';
          renderPending(); renderHistory();
          if (state.error) UI.toast('warn', UI.errorText(state.error), 5200);
        });
      }

      function decide(a, decision, btn) {
        var isApprove = decision === 'APPROVED';
        var isReject = decision === 'REJECTED';
        var cfg = {
          title: isApprove ? '批准审批事项' : (isReject ? '驳回审批事项' : '退回补充'),
          message: (isApprove ? '批准' : (isReject ? '驳回' : '退回')) + '「' + txt(a.subject) + '」？',
          warn: isApprove
            ? '批准只代表本地审批结论，不会自动外发邮件/私信，也不会自动生成正式报价。'
            : '该决定会记录审批备注并写入审计日志，不会自动通知外部。',
          danger: isReject,
          note: true,
          noteLabel: isApprove ? '审批备注（建议填写）' : (isReject ? '驳回理由（必填）' : '退回原因（必填）'),
          notePlaceholder: isApprove ? '如：同意推进，注意合规复核…' : '请说明原因，便于申请人补充…',
          noteRequired: !isApprove,
          confirmText: isApprove ? '确认批准' : (isReject ? '确认驳回' : '确认退回')
        };
        UI.confirm(cfg).then(function (r) {
          if (!r.ok) return;
          if (btn) btn.disabled = true;
          API.decideApproval(a.id, decision, r.note || '').then(function () {
            UI.toast('success', isApprove ? '已批准（人工操作）' : (isReject ? '已驳回' : '已退回补充'));
            load();
          }).catch(function (err) {
            if (btn) btn.disabled = false;
            UI.toast('error', UI.errorText(err), 8000);
          });
        });
      }

      UI.on(root, 'click', '[data-act="decide"]', function (ev) {
        var btn = ev.target.closest('[data-act="decide"]');
        if (!btn || btn.disabled) return;
        var id = btn.getAttribute('data-id');
        var decision = btn.getAttribute('data-decision');
        var a = null;
        state.pending.forEach(function (it) { if (String(it.id) === String(id)) a = it; });
        if (a) decide(a, decision, btn);
      });
      UI.on(root, 'click', '[data-act="refresh-ap"], [data-act="retry-ap"]', function () { load(); });

      load();
      return function () {};
    }
  };

  /* ============================================================
   * 模块 15 · 知识库（Markdown）
   * ============================================================ */
  CCGS.views.knowledge = {
    title: '知识库',
    subtitle: '内部 Markdown 资料；默认 DRAFT，未经 CEO 批准不得外发',
    mount: function (root) {
      var fields = fieldsFor('knowledge');
      UI.listPage(root, {
        resource: 'knowledge',
        title: '知识库',
        subtitle: '内部资料 · 简单 Markdown 渲染',
        singular: '文档',
        draft: true,
        searchPlaceholder: '搜索标题 / 分类 / 标签 / 内容…',
        create: { label: '新建文档', title: '新建知识文档', subtitle: '内容支持简单 Markdown：标题 / 列表 / 引用 / 代码 / 表格' },
        form: { fields: fields, wide: true, editTitle: '编辑知识文档', buildPayload: nullifyEmpty },
        defaultSort: '-updated_at',
        pageSize: 25,
        filters: [{ param: 'status', label: '状态', options: S.opts(S.options.knowledgeStatus) }],
        columns: [
          { key: 'id', label: 'ID', sortable: true, className: 'cell--id' },
          { key: 'title', label: '标题', sortable: true, render: function (r) {
              return '<span class="cell-link">' + esc(txt(r.title)) + '</span>' +
                '<span class="cell-sub">' + esc(txt(r.category)) + '</span>';
            } },
          { key: 'tags', label: '标签', sortable: true, render: function (r) { return UI.tags(r.tags); } },
          { key: 'status', label: '状态', sortable: true, render: function (r) { return statusBadge(r.status); } },
          { key: 'updated_at', label: '更新时间', sortable: true, className: 'cell--mono', render: function (r) { return esc(iso(r.updated_at)); } }
        ],
        detail: {
          size: 'lg',
          title: function (r) { return txt(r.title); },
          keys: [['分类', 'category'], ['状态', 'status'], ['来源', 'source'], ['更新时间', 'updated_at']],
          body: function (r) {
            var meta = '<div class="runner-actions" style="margin-bottom:10px">' +
              statusBadge(r.status) + ' ' + UI.tags(r.tags) +
              (r.source ? '<span class="small muted">来源：' + esc(r.source) + '</span>' : '') + '</div>';
            return UI.draftRibbon('知识库内容为内部资料草稿，未经 CEO 批准不得外发') +
              meta + UI.markdown(r.content_md) +
              '<p class="help" style="margin-top:10px">内容仅存本地数据库，不对外发布。</p>';
          }
        }
      });
      return function () {};
    }
  };
})();
