/* CCGS 前端 · 模块 9 供需智能匹配 / 模块 10 采购分析报告
 * 匹配为内部候选，一律不外发；评分 100 分制，红线封顶 39。 */
var CCGS = window.CCGS || (window.CCGS = {});
(function () {
  'use strict';

  var U = CCGS.util, UI = CCGS.ui, API = CCGS.api, S = CCGS.schema;

  var DIMS = [
    ['gpu_model', 'GPU 型号', 30],
    ['scale', '规模', 20],
    ['workload', '负载匹配', 15],
    ['location', '位置', 10],
    ['delivery', '交付', 10],
    ['network', '网络', 5],
    ['compliance', '合规', 5],
    ['trust', '信任', 5]
  ];

  function txt(v) { return U.text(v, '待确认'); }
  function iso(v) { return U.isEmpty(v) ? '—' : U.dateTime(v); }
  function scoreNum(v) {
    var n = Number(v);
    return isNaN(n) ? 0 : n;
  }
  function scoreText(v) {
    var n = scoreNum(v);
    return n % 1 === 0 ? String(n) : n.toFixed(1);
  }
  function parseJson(v) {
    if (v === null || v === undefined || v === '') return null;
    if (typeof v === 'object') return v;
    return U.safeParse(v);
  }
  function recBadge(v) { return UI.badge(v, S.statusKind(v), { sm: true }); }
  function confBadge(v) { return UI.badge(v, S.statusKind(v), { sm: true }); }
  function statusBadge(v) { return UI.badge(v, S.statusKind(v), { sm: true }); }
  function workload(v) { return U.text(S.label(v), '待确认'); }

  /* 空字符串可选字段 → null：避免空外键（如 demand_id=''）触发后端 FOREIGN KEY 失败 */
  function nullifyEmpty(values) {
    var out = {};
    Object.keys(values || {}).forEach(function (k) {
      var v = values[k];
      out[k] = (v === '') ? null : v;
    });
    return out;
  }

  function dimsHtml(raw) {
    var dims = raw && typeof raw === 'object' ? raw : parseJson(raw);
    if (!dims || typeof dims !== 'object') return '<div class="dash-text">暂无维度明细</div>';
    var rows = DIMS.map(function (d) {
      var key = d[0], label = d[1], max = d[2];
      var item = dims[key];
      if (!item) return '';
      var score = scoreNum(item.score);
      var full = scoreNum(item.max) || max;
      var pct = full > 0 ? Math.max(0, Math.min(100, (score / full) * 100)) : 0;
      var kind = pct >= 80 ? 'high' : (pct >= 50 ? 'mid' : 'low');
      var reason = item.reason ? '<div class="dim-reason">' + U.esc(item.reason) + '</div>' : '';
      return '<div class="dim-row">' +
        '<span class="dim-label">' + U.esc(label) + '</span>' +
        '<span class="dim-bar"><span class="dim-fill dim-fill--' + kind + '" style="width:' + pct.toFixed(1) + '%;display:block"></span></span>' +
        '<span class="dim-num">' + scoreText(score) + '/' + full + '</span>' +
        reason +
        '</div>';
    }).join('');
    if (!rows) return '<div class="dash-text">暂无维度明细</div>';
    return '<div class="dim-grid">' + rows + '</div>';
  }

  function whyHtml(whyMatch, whyNot) {
    var m = U.isEmpty(whyMatch) ? '（未提供匹配理由）' : String(whyMatch);
    var n = U.isEmpty(whyNot) ? '（未提供不匹配理由）' : String(whyNot);
    return '<div class="why-grid">' +
      '<div class="why why--match"><h5>匹配理由</h5>' + U.esc(m) + '</div>' +
      '<div class="why why--not"><h5>不匹配 / 风险</h5>' + U.esc(n) + '</div>' +
      '</div>';
  }

  function resultCard(r, supplyMap) {
    var sid = r.supply_id;
    var sup = supplyMap[String(sid)] || {};
    var gpu = sup.gpu_model || '';
    var loc = [sup.location_city, sup.location_country].filter(Boolean).join(' · ');
    var sub = [];
    if (gpu) sub.push(gpu + (sup.gpu_count ? ' × ' + sup.gpu_count : ''));
    if (loc) sub.push(loc);
    if (sup.delivery_lead_time) sub.push('交付 ' + sup.delivery_lead_time);
    var total = scoreNum(r.score);
    var saved = r.id ? '<span class="badge badge--green badge--sm">已保存 #' + U.esc(String(r.id)) + '</span>' : '<span class="badge badge--gray badge--sm">未保存</span>';
    return '<article class="match-card">' +
      '<div class="match-card-head">' +
      '<div class="match-title">供给 #' + U.esc(String(sid)) +
      '<span class="mono">' + U.esc(sub.join(' · ') || '—') + '</span></div>' +
      '<span class="match-total"><span class="num">' + scoreText(total) + '</span><span class="of">/ 100</span></span>' +
      '</div>' +
      '<div class="match-body">' +
      '<div class="runner-actions" style="margin-bottom:9px">' +
      recBadge(r.recommendation) + ' ' + saved +
      '<span class="badge badge--blue badge--sm">置信度 ' + U.esc(S.label(r.confidence) || '待确认') + '</span>' +
      '</div>' +
      dimsHtml(r.dimensions) +
      whyHtml(r.why_match, r.why_not_match) +
      '<div class="match-foot"><span>匹配记录状态：DRAFT（内部候选）</span>' +
      '<span class="mf-id">' + (r.id ? 'record #' + U.esc(String(r.id)) : '尚未落库') + '</span></div>' +
      '</div></article>';
  }

  CCGS.views.matching = {
    title: '供需智能匹配',
    subtitle: '选择需求与供给，运行 8 维确定性评分；结果为内部候选，一律不外发',
    mount: function (root) {
      root.innerHTML = '<div class="view">' +
        UI.draftRibbon() +
        UI.tip('评分口径：GPU 型号 30 / 规模 20 / 负载 15 / 位置 10 / 交付 10 / 网络 5 / 合规 5 / 信任 5，合计 100；红线项封顶 39 分。' +
          '≥70 建议推进（ADVANCE），40–69 需补充信息（NEED_MORE_INFO），&lt;40 建议拒绝（REJECT）。匹配结果只是候选，不构成对外承诺。') +
        '<div class="match-runner" style="margin-bottom:16px">' +
          '<section class="picker">' +
            '<div class="picker-head"><span>1. 选择需求</span><span class="picker-count" id="m-demand-count">加载中…</span></div>' +
            '<div class="picker-search"><input id="m-demand-search" type="search" placeholder="搜索需求标题 / GPU / 地点…" autocomplete="off"></div>' +
            '<div class="picker-list" id="m-demand-list"></div>' +
          '</section>' +
          '<div class="runner-side">' +
            '<section class="picker" style="max-height:240px">' +
              '<div class="picker-head"><span>2. 选择供给（可多选）</span><span class="picker-count" id="m-supply-count">加载中…</span></div>' +
              '<div class="picker-search"><input id="m-supply-search" type="search" placeholder="搜索 GPU / 城市 / 数据中心…" autocomplete="off"></div>' +
              '<div class="picker-list" id="m-supply-list"></div>' +
              '<div class="picker-actions">' +
                UI.button({ label: '全选当前', size: 'sm', icon: 'check', act: 'select-all' }) +
                UI.button({ label: '清空', size: 'sm', kind: 'ghost', act: 'clear-supplies' }) +
              '</div>' +
            '</section>' +
            '<div class="demand-preview" id="m-demand-preview"><span class="dash-text">尚未选择需求</span></div>' +
            '<div class="runner-actions">' +
              UI.button({ label: '运行匹配', kind: 'primary', icon: 'play', act: 'run' }) +
              UI.button({ label: '刷新供需池', kind: 'ghost', size: 'sm', icon: 'refresh', act: 'reload-pools' }) +
            '</div>' +
            '<p class="runner-hint">后端未连接时此处会给出明确提示与重试按钮，页面不会白屏。</p>' +
          '</div>' +
        '</div>' +
        '<section class="card" style="margin-bottom:16px">' +
          '<div class="card-head"><div class="card-title">匹配结果</div>' +
          '<div class="card-sub" id="m-result-sub">尚未运行</div>' +
          '<div class="card-actions" id="m-result-actions"></div></div>' +
          '<div class="card-body"><div class="match-results" id="m-results">' +
          UI.empty({ icon: 'flow', title: '尚未运行匹配', text: '在左侧选择 1 个需求，再在右侧勾选 1 个或多个供给，点击「运行匹配」。' }) +
          '</div></div>' +
        '</section>' +
        '<section class="card"><div class="card-body" id="m-history-slot"></div></section>' +
        '</div>';

      var el = {
        demandList: U.byId('m-demand-list'),
        supplyList: U.byId('m-supply-list'),
        demandCount: U.byId('m-demand-count'),
        supplyCount: U.byId('m-supply-count'),
        demandSearch: U.byId('m-demand-search'),
        supplySearch: U.byId('m-supply-search'),
        preview: U.byId('m-demand-preview'),
        results: U.byId('m-results'),
        resultSub: U.byId('m-result-sub'),
        resultActions: U.byId('m-result-actions'),
        historySlot: U.byId('m-history-slot')
      };

      var state = {
        demands: [],
        supplies: [],
        demandId: null,
        selected: {},
        results: [],
        running: false,
        saved: false,
        loadError: null
      };
      var supplyMap = {};
      var historyCtx = null;

      function demandMatches(d) {
        var q = (el.demandSearch.value || '').trim().toLowerCase();
        if (!q) return true;
        return [d.title, d.gpu_models, d.location_preference, d.workload_type, d.data_residency, d.company_id]
          .map(function (x) { return String(x === null || x === undefined ? '' : x).toLowerCase(); })
          .join(' ').indexOf(q) >= 0;
      }
      function supplyMatches(s) {
        var q = (el.supplySearch.value || '').trim().toLowerCase();
        if (!q) return true;
        return [s.gpu_model, s.location_city, s.location_country, s.datacenter, s.company_id, s.interconnect, s.delivery_lead_time]
          .map(function (x) { return String(x === null || x === undefined ? '' : x).toLowerCase(); })
          .join(' ').indexOf(q) >= 0;
      }

      function renderDemands() {
        var list = state.demands.filter(demandMatches);
        el.demandCount.textContent = state.demands.length + ' 项';
        if (!list.length) {
          el.demandList.innerHTML = '<div class="picker-empty">' +
            (state.loadError ? '需求加载失败：' + U.esc(UI.errorText(state.loadError)) : '没有匹配的需求') + '</div>';
          return;
        }
        el.demandList.innerHTML = list.map(function (d) {
          var sub = ['#' + d.id, workload(d.workload_type), U.text(d.gpu_models, 'GPU 待确认')];
          var counts = []; if (d.min_gpu_count || d.max_gpu_count) counts.push((d.min_gpu_count || '?') + '–' + (d.max_gpu_count || '?') + ' 卡');
          if (counts.length) sub.push(counts[0]);
          if (d.location_preference) sub.push(d.location_preference);
          return '<label class="picker-item"><input type="radio" name="m-demand" value="' + U.esc(String(d.id)) + '"' +
            (String(state.demandId) === String(d.id) ? ' checked' : '') + '>' +
            '<span class="pi-main">' + U.esc(txt(d.title)) + ' ' + statusBadge(d.status) +
            '<span class="pi-sub">' + U.esc(sub.filter(Boolean).join(' · ')) + '</span></span></label>';
        }).join('');
      }

      function renderSupplies() {
        var list = state.supplies.filter(supplyMatches);
        var selCount = Object.keys(state.selected).length;
        el.supplyCount.textContent = list.length + ' / ' + state.supplies.length + ' 项 · 已选 ' + selCount;
        if (!list.length) {
          el.supplyList.innerHTML = '<div class="picker-empty">' +
            (state.loadError ? '供给加载失败：' + U.esc(UI.errorText(state.loadError)) : '没有匹配的供给') + '</div>';
          return;
        }
        el.supplyList.innerHTML = list.map(function (s) {
          var sub = ['#' + s.id];
          if (s.location_city || s.location_country) sub.push([s.location_city, s.location_country].filter(Boolean).join(' · '));
          if (s.delivery_lead_time) sub.push('交付 ' + s.delivery_lead_time);
          sub.push('价格 ' + U.text(s.price_indication, '待确认'));
          if (s.verified) sub.push('已核验');
          return '<label class="picker-item"><input type="checkbox" name="m-supply" value="' + U.esc(String(s.id)) + '"' +
            (state.selected[String(s.id)] ? ' checked' : '') + '>' +
            '<span class="pi-main">' + U.esc(txt(s.gpu_model)) + ' × ' + U.esc(String(s.gpu_count === null || s.gpu_count === undefined ? '—' : s.gpu_count)) +
            ' <span class="badge badge--gray badge--sm">可售 ' + U.esc(String(s.sellable_gpu_count === null || s.sellable_gpu_count === undefined ? '—' : s.sellable_gpu_count)) + '</span>' +
            '<span class="pi-sub">' + U.esc(sub.join(' · ')) + '</span></span></label>';
        }).join('');
      }

      function currentDemand() {
        for (var i = 0; i < state.demands.length; i++) {
          if (String(state.demands[i].id) === String(state.demandId)) return state.demands[i];
        }
        return null;
      }

      function renderPreview() {
        var d = currentDemand();
        if (!d) {
          el.preview.innerHTML = '<span class="dash-text">尚未选择需求</span>';
          return;
        }
        var pairs = [
          ['线索等级', leadBadge(d.lead_grade)],
          ['负载类型', U.esc(workload(d.workload_type))],
          ['GPU 型号', U.esc(txt(d.gpu_models))],
          ['卡数范围', U.esc((d.min_gpu_count || '?') + '–' + (d.max_gpu_count || '?') + ' 卡')],
          ['时长', U.esc(d.duration_months === null || d.duration_months === undefined ? '待确认' : d.duration_months + ' 个月')],
          ['时间窗', U.esc(txt(d.timeline))],
          ['地点偏好', U.esc(txt(d.location_preference))],
          ['预算', U.esc(d.budget_range === 'UNKNOWN' || U.isEmpty(d.budget_range) ? '待确认' : d.budget_range)]
        ];
        el.preview.innerHTML = '<div class="dp-title">' + U.esc(txt(d.title)) + '</div>' +
          '<div class="dp-grid">' + pairs.map(function (p) {
            return '<span>' + p[0] + '</span><b>' + p[1] + '</b>';
          }).join('') + '</div>';
      }
      function leadBadge(v) {
        return UI.badge(v, S.leadGradeKind ? S.leadGradeKind(v) : S.statusKind(v), { sm: true });
      }

      function loadPools() {
        state.loadError = null;
        el.demandList.innerHTML = '<div class="picker-empty"><span class="spinner spinner--sm"></span> 加载需求…</div>';
        el.supplyList.innerHTML = '<div class="picker-empty"><span class="spinner spinner--sm"></span> 加载供给…</div>';
        var p1 = API.list('demands', { page_size: 200, sort: '-updated_at' }).then(function (res) {
          state.demands = (res && res.items) || [];
        }).catch(function (err) { state.demands = []; state.loadError = err; });
        var p2 = API.list('supplies', { page_size: 200, sort: '-updated_at' }).then(function (res) {
          state.supplies = (res && res.items) || [];
          supplyMap = {};
          state.supplies.forEach(function (s) { supplyMap[String(s.id)] = s; });
        }).catch(function (err) { state.supplies = []; state.loadError = state.loadError || err; });
        return Promise.all([p1, p2]).then(function () {
          renderDemands(); renderSupplies(); renderPreview();
          if (state.loadError) UI.toast('warn', UI.errorText(state.loadError), 5200);
        });
      }

      function selectedSupplyIds() {
        return Object.keys(state.selected).filter(function (k) { return state.selected[k]; });
      }

      function renderResults() {
        if (!state.results.length) return;
        el.results.innerHTML = state.results.map(function (r) { return resultCard(r, supplyMap); }).join('');
        el.resultSub.textContent = '需求 #' + state.demandId + ' · ' + state.results.length + ' 条结果 · 运行时间 ' + U.dateTime(U.nowIso());
        var savedAll = state.results.every(function (r) { return !!r.id; });
        el.resultActions.innerHTML = UI.button({
          label: savedAll ? '已保存' : '一键保存匹配记录',
          kind: 'primary', size: 'sm', icon: 'database', act: 'save',
          disabled: savedAll || state.running
        }) + ' ' + UI.button({ label: '清空结果', kind: 'ghost', size: 'sm', icon: 'x', act: 'clear-results' });
      }

      function runMatch() {
        if (state.running) return;
        if (!state.demandId) { UI.toast('warn', '请先选择一个需求'); return; }
        var ids = selectedSupplyIds();
        if (!ids.length) { UI.toast('warn', '请至少勾选一个供给'); return; }
        state.running = true;
        state.results = [];
        state.saved = false;
        el.results.innerHTML = '<div class="notice-state"><span class="spinner"></span>正在运行 8 维评分…</div>';
        el.resultSub.textContent = '匹配中…';
        el.resultActions.innerHTML = '';
        API.matchRun({ demand_id: state.demandId, supply_ids: ids, persist: false })
          .then(function (data) {
            state.results = (data && (data.results || data.items)) || [];
            state.running = false;
            if (!state.results.length) {
              el.results.innerHTML = UI.empty({ icon: 'flow', title: '没有匹配结果', text: '后端未返回结果，请检查供给与需求数据是否完整。' });
              el.resultSub.textContent = '0 条结果';
            } else {
              renderResults();
              UI.toast('success', '匹配完成：' + state.results.length + ' 条结果（尚未保存）');
            }
          })
          .catch(function (err) {
            state.running = false;
            el.results.innerHTML = UI.errorState(err, function () { runMatch(); });
            el.resultSub.textContent = '运行失败';
            UI.toast('error', UI.errorText(err), 5200);
          });
      }

      function saveResults() {
        if (!state.results.length || state.saved) return;
        var ids = state.results.map(function (r) { return r.supply_id; });
        el.resultActions.innerHTML = '<span class="small muted">保存中…</span>';
        API.matchRun({ demand_id: state.demandId, supply_ids: ids, persist: true })
          .then(function (data) {
            var fresh = (data && (data.results || data.items)) || [];
            if (fresh.length) state.results = fresh;
            state.saved = true;
            renderResults();
            UI.toast('success', '已保存 ' + state.results.length + ' 条匹配记录（状态 DRAFT）');
            refreshHistory();
          })
          .catch(function (err) {
            renderResults();
            UI.toast('error', UI.errorText(err), 5200);
          });
      }

      function refreshHistory() {
        if (!el.historySlot) return;
        if (historyCtx) { historyCtx.reload(); return; }
        historyCtx = UI.listPage(el.historySlot, {
          resource: 'matches',
          title: '历史匹配记录',
          subtitle: '最近保存的候选匹配（只读）；状态推进需经 CEO 审批',
          actions: false,
          defaultSort: '-created_at',
          pageSize: 10,
          columns: [
            { key: 'id', label: 'ID', sortable: true, className: 'cell--id' },
            { key: 'demand_id', label: '需求', sortable: true, className: 'cell--mono', render: function (r) { return '#' + U.esc(String(r.demand_id === null || r.demand_id === undefined ? '—' : r.demand_id)); } },
            { key: 'supply_id', label: '供给', sortable: true, className: 'cell--mono', render: function (r) { return '#' + U.esc(String(r.supply_id === null || r.supply_id === undefined ? '—' : r.supply_id)); } },
            { key: 'score', label: '总分', sortable: true, className: 'cell--num', render: function (r) { return U.esc(scoreText(r.score)); } },
            { key: 'recommendation', label: '建议', sortable: true, render: function (r) { return recBadge(r.recommendation); } },
            { key: 'confidence', label: '置信度', sortable: true, render: function (r) { return confBadge(r.confidence); } },
            { key: 'status', label: '状态', sortable: true, render: function (r) { return statusBadge(r.status); } },
            { key: 'created_at', label: '时间', sortable: true, className: 'cell--mono', render: function (r) { return U.esc(iso(r.created_at)); } }
          ],
          detail: {
            size: 'lg',
            title: function (r) { return '匹配记录 #' + r.id; },
            keys: [['需求', 'demand_id'], ['供给', 'supply_id'], ['状态', 'status']],
            body: function (r) {
              var dims = r.match_dimensions || r.dimensions;
              return '<div class="toolbar toolbar--plain" style="margin-bottom:10px">' +
                recBadge(r.recommendation) + ' ' + confBadge(r.confidence) +
                '<span class="toolbar-spacer"></span><span class="small muted">总分 ' + U.esc(scoreText(r.score)) + ' / 100</span></div>' +
                dimsHtml(dims) + whyHtml(r.why_match, r.why_not_match) +
                (r.risks ? '<div class="detail-block"><h4>风险</h4><div class="detail-text">' + U.esc(r.risks) + '</div></div>' : '') +
                '<p class="help" style="margin-top:10px">匹配记录为内部候选，未经 CEO 批准不得外发。</p>';
            }
          }
        });
      }

      /* ---------------- 事件 ---------------- */
      UI.on(root, 'input', '#m-demand-search', function () { renderDemands(); });
      UI.on(root, 'input', '#m-supply-search', function () { renderSupplies(); });
      UI.on(root, 'change', '#m-demand-list input[type="radio"]', function (ev) {
        state.demandId = ev.target.value;
        renderPreview();
      });
      UI.on(root, 'change', '#m-supply-list input[type="checkbox"]', function (ev) {
        state.selected[ev.target.value] = ev.target.checked;
        renderSupplies();
      });
      UI.on(root, 'click', '[data-act]', function (ev) {
        var btn = ev.target.closest('[data-act]');
        if (!btn || btn.disabled) return;
        var act = btn.getAttribute('data-act');
        if (act === 'run') runMatch();
        else if (act === 'retry') runMatch();
        else if (act === 'save') saveResults();
        else if (act === 'select-all') {
          state.supplies.filter(supplyMatches).forEach(function (s) { state.selected[String(s.id)] = true; });
          renderSupplies();
        } else if (act === 'clear-supplies') {
          state.selected = {}; renderSupplies();
        } else if (act === 'clear-results') {
          state.results = []; el.resultSub.textContent = '尚未运行'; el.resultActions.innerHTML = '';
          el.results.innerHTML = UI.empty({ icon: 'flow', title: '尚未运行匹配', text: '选择需求与供给后点击「运行匹配」。' });
        } else if (act === 'reload-pools') loadPools();
      });

      loadPools().then(function () { refreshHistory(); });
      return function () { /* 事件委托挂在 root 上，路由切换时随 DOM 移除 */ };
    }
  };

  /* ============================================================
   * 模块 10 · 采购分析报告
   * 基于匹配记录生成方案对比表；报告为内部草案，不报价、不签约、不外发。
   * ============================================================ */
  function parseOptions(v) {
    var p = parseJson(v);
    if (!p) return [];
    if (Array.isArray(p)) return p;
    if (Array.isArray(p.options)) return p.options;
    if (Array.isArray(p.items)) return p.items;
    return [];
  }

  CCGS.views.procurement = {
    title: '采购分析报告',
    subtitle: '基于匹配记录生成方案对比表（草案，未经 CEO 批准不得外发）',
    mount: function (root) {
      root.innerHTML = '<div class="view">' +
        UI.draftRibbon('本页报告为内部采购分析草案，未经 CEO 批准不得外发，不构成正式报价或合同') +
        '<div class="toolbar">' +
          UI.button({ label: '新建分析报告', kind: 'primary', icon: 'plus', act: 'new-report' }) +
          UI.button({ label: '刷新', kind: 'ghost', size: 'sm', icon: 'refresh', act: 'refresh-reports' }) +
          '<div class="toolbar-spacer"></div>' +
          '<span class="small muted">对比表仅基于本地匹配记录生成，不对外发送</span>' +
        '</div>' +
        '<div class="grid grid-2" style="grid-template-columns:minmax(0,0.8fr) minmax(0,1.2fr);align-items:start">' +
          '<section class="card"><div class="card-head"><div class="card-title">分析报告</div>' +
            '<span class="card-sub" id="rp-count">加载中…</span></div>' +
            '<div class="card-body" id="rp-list"></div></section>' +
          '<section class="card"><div class="card-head"><div class="card-title">报告详情</div>' +
            '<span class="card-sub">方案对比 · 只读</span></div>' +
            '<div class="card-body" id="rp-detail"></div></section>' +
        '</div>' +
        '</div>';

      var el = {
        list: U.byId('rp-list'),
        count: U.byId('rp-count'),
        detail: U.byId('rp-detail')
      };
      var state = {
        reports: [],
        currentId: null,
        current: null,
        matches: [],
        matchesError: null,
        loading: false,
        loaded: false,
        reportFields: S.formFields('procurement')
      };

      function patchDemandField() {
        var FU = CCGS.formUtil;
        if (!FU || !FU.loadDemands) return;
        try {
          var p = FU.loadDemands(state.reportFields, 'demand_id');
          if (p && typeof p.catch === 'function') p.catch(function () {});
        } catch (e) { /* 忽略：下拉退化为空，仍可输入 */ }
      }

      function renderList() {
        var rs = state.reports;
        el.count.textContent = rs.length + ' 份';
        if (state.loading && !state.loaded) {
          el.list.innerHTML = '<div class="table-loading"><span class="spinner spinner--sm"></span> 加载分析报告…</div>';
          return;
        }
        if (!rs.length) {
          el.list.innerHTML = UI.empty({
            icon: 'file',
            title: '暂无采购分析报告',
            text: '先运行并保存匹配记录，然后新建一份报告，详情页会自动生成方案对比表。',
            actions: UI.button({ label: '新建分析报告', kind: 'primary', size: 'sm', icon: 'plus', act: 'new-report' })
          });
          return;
        }
        var rows = rs.map(function (r) {
          var cur = String(state.currentId) === String(r.id);
          return '<tr class="clickable" data-report-id="' + U.esc(String(r.id)) + '"' +
            (cur ? ' style="background:rgba(76,154,255,0.08)"' : '') + '>' +
            '<td><span class="cell-link">' + U.esc(txt(r.title)) + '</span>' +
            '<span class="cell-sub">#' + U.esc(String(r.id)) + ' · ' + U.esc(iso(r.updated_at)) + '</span></td>' +
            '<td class="cell--mono">' + U.esc(r.demand_id === null || r.demand_id === undefined ? '—' : '#' + r.demand_id) + '</td>' +
            '<td>' + statusBadge(r.status) + '</td>' +
            '</tr>';
        }).join('');
        el.list.innerHTML = '<div class="table-wrap"><table class="data-table"><thead><tr>' +
          '<th>标题</th><th>需求</th><th>状态</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
      }

      function loadReports() {
        state.loading = true;
        if (!state.loaded) renderList();
        return API.list('procurement-analyses', { page_size: 100, sort: '-updated_at' })
          .then(function (res) {
            state.reports = (res && res.items) || [];
            state.loaded = true;
            state.loading = false;
            renderList();
          })
          .catch(function (err) {
            state.loading = false;
            state.loaded = true;
            el.count.textContent = '加载失败';
            el.list.innerHTML = UI.errorState(err, function () { loadReports(); }) +
              '<div style="margin-top:8px">' +
              UI.button({ label: '重试', size: 'sm', act: 'retry-reports', icon: 'refresh' }) + '</div>';
            UI.toast('error', UI.errorText(err), 5200);
          });
      }

      function fetchMatches(demandId) {
        if (demandId === null || demandId === undefined || demandId === '') {
          return Promise.resolve([]);
        }
        return API.list('matches', { demand_id: demandId, page_size: 200, sort: '-score' })
          .then(function (res) { return (res && res.items) || []; });
      }

      function blankDetail() {
        el.detail.innerHTML = UI.empty({
          icon: 'file',
          title: '选择一份报告',
          text: '在左侧选择报告查看方案对比；或点击「新建分析报告」创建。',
          actions: UI.button({ label: '新建分析报告', kind: 'primary', size: 'sm', icon: 'plus', act: 'new-report' })
        });
      }

      function selectReport(id) {
        state.currentId = id;
        renderList();
        el.detail.innerHTML = '<div class="table-loading"><span class="spinner spinner--sm"></span> 加载报告与匹配记录…</div>';
        var item;
        API.get('procurement-analyses', id)
          .then(function (data) {
            item = data;
            state.current = item;
            return fetchMatches(item.demand_id).then(function (ms) {
              state.matches = ms;
              state.matchesError = null;
            }).catch(function (err) {
              state.matches = [];
              state.matchesError = err;
            });
          })
          .then(function () { renderDetail(item, state.matches, state.matchesError); })
          .catch(function (err) {
            state.current = null;
            el.detail.innerHTML = UI.errorState(err, function () { selectReport(id); });
            UI.toast('error', UI.errorText(err), 5200);
          });
      }

      function comparisonRows(item) {
        var opts = parseOptions(item.options_json);
        var liveMap = {};
        (state.matches || []).forEach(function (m) { liveMap[String(m.supply_id)] = m; });
        var rows;
        if (opts.length) {
          rows = opts.map(function (o) {
            var live = liveMap[String(o.supply_id)] || {};
            return {
              supply_id: o.supply_id,
              score: o.score !== undefined ? o.score : live.score,
              recommendation: o.recommendation || live.recommendation,
              confidence: o.confidence || live.confidence,
              why_match: o.why_match || live.why_match,
              why_not_match: o.why_not_match || live.why_not_match,
              dimensions: o.dimensions || live.match_dimensions || live.dimensions,
              source: 'snapshot'
            };
          });
        } else {
          rows = (state.matches || []).map(function (m) {
            return {
              supply_id: m.supply_id,
              score: m.score,
              recommendation: m.recommendation,
              confidence: m.confidence,
              why_match: m.why_match,
              why_not_match: m.why_not_match,
              dimensions: m.match_dimensions || m.dimensions,
              source: 'live'
            };
          });
        }
        return { rows: rows, fromSnapshot: opts.length > 0 };
      }

      function renderComparison(item) {
        var cmp = comparisonRows(item);
        var rows = cmp.rows;
        if (state.matchesError) {
          return UI.errorState(state.matchesError, function () { selectReport(item.id); });
        }
        if (!rows.length) {
          return UI.empty({
            icon: 'flow',
            title: '暂无方案对比数据',
            text: '该需求还没有保存的匹配记录。请先到「供需智能匹配」运行匹配并保存，再回到本页刷新。',
            actions: '<a class="btn btn--primary btn--sm" href="#/matching">前往供需匹配</a>'
          });
        }
        var advance = rows.filter(function (r) { return r.recommendation === 'ADVANCE'; }).length;
        var needsInfo = rows.filter(function (r) { return r.recommendation === 'NEED_MORE_INFO'; }).length;
        var avg = 0;
        rows.forEach(function (r) { avg += scoreNum(r.score); });
        avg = rows.length ? (avg / rows.length) : 0;
        var body = rows.map(function (r) {
          return '<tr>' +
            '<td class="cell--mono">#' + U.esc(String(r.supply_id)) + '</td>' +
            '<td class="cell--num">' + U.esc(scoreText(r.score)) + '</td>' +
            '<td>' + recBadge(r.recommendation) + '</td>' +
            '<td>' + confBadge(r.confidence) + '</td>' +
            '<td>' + U.esc(U.text(r.why_match, '—')) + '</td>' +
            '<td>' + U.esc(U.text(r.why_not_match, '—')) + '</td>' +
            '</tr>';
        }).join('');
        return '<div class="report-result" style="margin-top:0">' +
          '<div class="rr-head">方案对比（' + rows.length + ' 个候选方案）</div>' +
          '<div class="rr-body">' +
          '<div class="result-nums">' +
          '<span class="result-num">方案数<b>' + rows.length + '</b></span>' +
          '<span class="result-num result-num--ok">建议推进<b>' + advance + '</b></span>' +
          '<span class="result-num result-num--warn">需补充信息<b>' + needsInfo + '</b></span>' +
          '<span class="result-num">平均分<b>' + scoreText(Math.round(avg * 10) / 10) + '</b></span>' +
          '</div>' +
          '<p class="help" style="margin:0 0 8px">数据来源：' +
          (cmp.fromSnapshot ? '报告保存的方案快照（options_json）' : '该需求的历史匹配记录（实时生成，只读）') +
          '。<strong class="' + (cmp.fromSnapshot ? '' : '') + '">匹配只是候选，不构成对外承诺。</strong></p>' +
          '<div class="table-wrap"><table class="data-table"><thead><tr>' +
          '<th>供给</th><th>总分</th><th>建议</th><th>置信度</th><th>匹配理由</th><th>缺口 / 风险</th>' +
          '</tr></thead><tbody>' + body + '</tbody></table></div>' +
          '</div></div>';
      }

      function renderDetail(item, matches, matchesError) {
        if (!item) { blankDetail(); return; }
        state.current = item;
        var meta = '<div class="toolbar toolbar--plain" style="margin-bottom:10px">' +
          '<div><strong style="color:#e9f1fd;font-size:13px">' + U.esc(txt(item.title)) + '</strong>' +
          '<span class="cell-sub">#' + U.esc(String(item.id)) + ' · 需求 #' +
          U.esc(item.demand_id === null || item.demand_id === undefined ? '—' : String(item.demand_id)) + '</span></div>' +
          '<div class="toolbar-spacer"></div>' + statusBadge(item.status) + '</div>' +
          '<div class="runner-actions" style="margin-bottom:10px">' +
          UI.button({ label: '编辑报告', size: 'sm', icon: 'edit', act: 'edit-report' }) +
          UI.button({ label: '删除', size: 'sm', kind: 'danger', icon: 'trash', act: 'del-report' }) +
          UI.button({ label: '刷新对比', size: 'sm', kind: 'ghost', icon: 'refresh', act: 'reload-report' }) +
          '<a class="btn btn--sm btn--ghost" href="#/matching">前往供需匹配</a>' +
          '</div>' +
          UI.draftRibbon('本报告为内部草案，未经 CEO 批准不得外发；不构成正式报价或合同') +
          renderComparison(item);
        var extra = '';
        if (item.recommendation) extra += UI.detailBlock('建议方案（摘要）', item.recommendation);
        if (item.risks) extra += UI.detailBlock('风险', item.risks);
        if (item.assumptions) extra += UI.detailBlock('假设与前提', item.assumptions);
        if (!extra) extra = '<p class="help">尚未填写建议、风险与假设。</p>';
        var scoring = '';
        if (item.scoring_json) {
          scoring = '<div class="detail-block"><h4>评分明细（原始 JSON）</h4>' + UI.prettyJson(item.scoring_json) + '</div>';
        }
        var foot = '<div class="kv" style="margin-top:12px">' +
          '<div class="kv-row"><span class="kv-key">分析师</span><span class="kv-val">' + U.esc(txt(item.analyst)) + '</span></div>' +
          '<div class="kv-row"><span class="kv-key">创建时间</span><span class="kv-val">' + U.esc(iso(item.created_at)) + '</span></div>' +
          '<div class="kv-row"><span class="kv-key">更新时间</span><span class="kv-val">' + U.esc(iso(item.updated_at)) + '</span></div>' +
          '</div>';
        el.detail.innerHTML = meta + extra + scoring + foot;
      }

      function newReport() {
        patchDemandField();
        UI.openForm({
          title: '新建采购分析报告',
          subtitle: '保存后详情页会基于该需求的历史匹配记录生成方案对比表（仅内部使用）',
          fields: state.reportFields,
          values: { status: 'DRAFT' },
          submitText: '创建报告',
          onSubmit: function (payload) {
            payload = nullifyEmpty(payload);
            return API.create('procurement-analyses', payload).then(function (item) {
              UI.toast('success', '分析报告已创建（状态 DRAFT）');
              return loadReports().then(function () {
                if (item && item.id) selectReport(item.id);
              });
            });
          }
        });
      }

      function editReport() {
        var item = state.current;
        if (!item) return;
        patchDemandField();
        var values = {};
        state.reportFields.forEach(function (f) {
          if (item[f.key] !== undefined && item[f.key] !== null) values[f.key] = item[f.key];
        });
        UI.openForm({
          title: '编辑采购分析报告 #' + item.id,
          fields: state.reportFields,
          values: values,
          original: item,
          submitText: '保存修改',
          onSubmit: function (payload) {
            payload = nullifyEmpty(payload);
            return API.update('procurement-analyses', item.id, payload).then(function () {
              UI.toast('success', '报告已更新');
              return loadReports().then(function () { selectReport(item.id); });
            });
          }
        });
      }

      function deleteReport() {
        var item = state.current;
        if (!item) return;
        UI.confirm({
          title: '删除采购分析报告',
          message: '确定删除《' + txt(item.title) + '》？删除后不可恢复，操作会写入审计日志。',
          danger: true,
          confirmText: '删除报告'
        }).then(function (res) {
          if (!res.ok) return;
          API.remove('procurement-analyses', item.id).then(function () {
            UI.toast('success', '报告已删除');
            state.current = null;
            state.currentId = null;
            state.matches = [];
            blankDetail();
            loadReports();
          }).catch(function (err) { UI.toast('error', UI.errorText(err), 5200); });
        });
      }

      /* ---------------- 事件 ---------------- */
      UI.on(root, 'click', '[data-report-id]', function (ev) {
        var tr = ev.target.closest('[data-report-id]');
        if (!tr) return;
        selectReport(tr.getAttribute('data-report-id'));
      });
      UI.on(root, 'click', '[data-act]', function (ev) {
        var btn = ev.target.closest('[data-act]');
        if (!btn || btn.disabled) return;
        var act = btn.getAttribute('data-act');
        if (act === 'new-report') newReport();
        else if (act === 'refresh-reports' || act === 'retry-reports') loadReports();
        else if (act === 'edit-report') editReport();
        else if (act === 'del-report') deleteReport();
        else if (act === 'reload-report') { if (state.current) selectReport(state.current.id); }
      });

      blankDetail();
      loadReports();
      return function () { /* 委托挂在 root 上 */ };
    }
  };
})();
