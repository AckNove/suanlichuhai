/* CCGS 内部工作台 · views/overview.js
 * 模块 1：经营总览（统计卡 / 漏斗 / 告警 / 最近活动 / 待审批数）
 */
var CCGS = window.CCGS || (window.CCGS = {});

(function () {
  'use strict';

  var U = CCGS.util, UI = CCGS.ui, API = CCGS.api;
  var V = CCGS.views = CCGS.views || {};

  var SUPPLIER_ORDER = ['LEAD', 'RESEARCHED', 'NEEDS_VERIFICATION', 'VERIFIED', 'QUALIFIED', 'ACTIVE', 'PAUSED', 'CEO_PENDING', 'INSUFFICIENT_INFO', 'EXPIRED', 'REJECTED'];
  var DEMAND_ORDER = ['LEAD', 'RESEARCHED', 'NEEDS_VERIFICATION', 'VERIFIED', 'QUALIFIED', 'MATCHED', 'COMMERCIAL', 'WON', 'LOST', 'NOT_MATCHED', 'CEO_PENDING', 'PAUSED', 'REJECTED'];
  var OPP_ORDER = ['OPEN', 'DISCLOSED', 'INTRODUCED', 'TERM_SHEET', 'CA', 'CLOSED_WON', 'CLOSED_LOST'];
  var GRADE_ORDER = ['PUBLIC_LEAD', 'INFERRED', 'POTENTIAL', 'VERIFIED', 'QUALIFIED'];

  function esc(v) { return U.esc(v); }

  function stat(label, value, hint, kind) {
    return '<div class="stat' + (kind ? ' stat--' + kind : '') + '">' +
      '<div class="stat-label">' + esc(label) + '</div>' +
      '<div class="stat-value">' + (value === null || value === undefined ? '—' : esc(String(value))) + '</div>' +
      (hint ? '<div class="stat-hint">' + hint + '</div>' : '') +
      '</div>';
  }

  function card(title, sub, body, actions, flush) {
    return '<div class="card' + (flush ? ' card--flush' : '') + '">' +
      '<div class="card-head"><div><h2 class="card-title">' + esc(title) +
      (sub ? '<span class="small muted">' + esc(sub) + '</span>' : '') + '</h2></div>' +
      '<div class="card-actions">' + (actions || '') + '</div></div>' +
      '<div class="card-body">' + body + '</div>' +
      '</div>';
  }

  function funnel(title, data, order) {
    data = data || {};
    var known = {};
    order.forEach(function (k) { known[k] = true; });
    var extra = Object.keys(data).filter(function (k) { return !known[k]; });
    var keys = order.concat(extra).filter(function (k) { return (data[k] || 0) > 0 || order.indexOf(k) >= 0; });
    var total = keys.reduce(function (s, k) { return s + (Number(data[k]) || 0); }, 0);
    var rows = keys.map(function (k) {
      var n = Number(data[k]) || 0;
      var pct = total > 0 ? Math.round((n / total) * 100) : 0;
      return '<div class="funnel-row">' +
        '<span class="funnel-label">' + esc(CCGS.schema.label(k)) + '</span>' +
        '<span class="funnel-track"><span class="funnel-fill' + (/WON|APPROVED|ACTIVE|VERIFIED|QUALIFIED/.test(k) ? ' funnel-fill--green' : '') + '" style="width:' + Math.max(n > 0 ? 3 : 0, pct) + '%"></span></span>' +
        '<span class="funnel-val">' + n + '</span>' +
        '</div>';
    }).join('');
    return '<div style="margin-bottom:16px;"><h3 class="section-title">' + esc(title) +
      '<span class="small faint">共 ' + total + '</span></h3>' +
      (rows || '<div class="small faint">暂无数据</div>') + '</div>';
  }

  function gradeBars(grades) {
    grades = grades || {};
    var keys = GRADE_ORDER.concat(Object.keys(grades).filter(function (k) { return GRADE_ORDER.indexOf(k) < 0; }));
    var total = keys.reduce(function (s, k) { return s + (Number(grades[k]) || 0); }, 0);
    if (!total) return '<div class="small faint">暂无线索等级数据</div>';
    return '<div class="funnel">' + keys.map(function (k) {
      var n = Number(grades[k]) || 0;
      var pct = total ? Math.round((n / total) * 100) : 0;
      return '<div class="funnel-row">' +
        '<span class="funnel-label"><span class="badge badge--sm badge--' + CCGS.schema.leadGradeKind(k) + '">' + esc(CCGS.schema.leadGradeLabel(k)) + '</span></span>' +
        '<span class="funnel-track"><span class="funnel-fill" style="width:' + Math.max(n > 0 ? 3 : 0, pct) + '%"></span></span>' +
        '<span class="funnel-val">' + n + '</span></div>';
    }).join('') + '</div>';
  }

  function verificationBlock(v) {
    v = v || {};
    var rows = [
      ['已核验', v.verified || 0, 'good'],
      ['待核验', v.needs_verification || 0, 'warn'],
      ['已拒绝', v.rejected || 0, 'danger']
    ];
    return '<div class="stat-grid">' + rows.map(function (r) {
      return '<div class="stat stat--' + r[2] + '"><div class="stat-label">' + esc(r[0]) + '</div>' +
        '<div class="stat-value">' + esc(String(r[1])) + '</div></div>';
    }).join('') + '</div>';
  }

  function alertsBlock(alerts) {
    if (!alerts || !alerts.length) {
      return '<div class="notice-state"><div class="empty-title">暂无告警</div>' +
        '<div class="empty-text">当前没有需要处理的风险提示。核验缺口、证据不足等告警会在此出现。</div></div>';
    }
    return '<div class="alert-list">' + alerts.map(function (a) {
      var level = (a.level || 'INFO').toUpperCase();
      return '<div class="alert alert--' + esc(level) + '">' +
        '<span class="alert-level">' + esc(level === 'WARN' ? '警告' : level === 'ERROR' ? '错误' : '提示') + '</span>' +
        '<div class="alert-body">' +
        (a.code ? '<span class="alert-code">' + esc(a.code) + '</span>' : '') +
        '<span class="alert-msg">' + esc(a.message || '') + '</span></div></div>';
    }).join('') + '</div>';
  }

  function pendingBlock(pending) {
    var items = (pending && pending.items) || [];
    var count = (pending && typeof pending.total === 'number') ? pending.total : items.length;
    if (!items.length) {
      return '<div class="notice-state"><div class="empty-title">无待审批事项</div>' +
        '<div class="empty-text">CEO 审批只能由人工在审批中心逐条点击；系统不会自动批准。</div>' +
        '<div class="empty-actions"><a class="btn btn--sm" href="#/approvals">打开审批中心</a></div></div>';
    }
    return '<div class="small muted" style="margin-bottom:10px;">待审批 ' + esc(String(count)) + ' 项 · 仅人工决策，系统不自动批准</div>' +
      '<div class="timeline">' + items.slice(0, 5).map(function (a) {
        return '<div class="tl-item"><span class="tl-dot tl-dot--amber"></span>' +
          '<div class="tl-head"><div class="tl-summary">' + esc(a.subject || a.approval_type || '审批事项') + '</div>' +
          '<div class="tl-meta">' + esc(a.approval_type || '') +
          (a.requested_by ? ' · 申请人 ' + esc(a.requested_by) : '') + '</div>' +
          '<div class="tl-date">' + esc(U.dateTime(a.requested_at)) + '</div></div></div>';
      }).join('') + '</div>' +
      '<div class="empty-actions" style="margin-top:10px;"><a class="btn btn--sm btn--primary" href="#/approvals">前往审批中心</a></div>';
  }

  function activityTimeline(activities) {
    if (!activities || !activities.length) {
      return '<div class="table-empty"><div class="empty-title">暂无活动记录</div>' +
        '<div class="empty-text">新建、编辑、状态推进、导入导出等写操作会记录在此。</div></div>';
    }
    function dot(action) {
      var a = String(action || '').toUpperCase();
      if (/DELETE|REJECT|FAIL|CANCEL/.test(a)) return 'red';
      if (/CREATE|IMPORT|APPROVE|BUILD/.test(a)) return 'green';
      return 'amber';
    }
    return '<div class="timeline">' + activities.slice(0, 12).map(function (a) {
      return '<div class="tl-item">' +
        '<span class="tl-dot tl-dot--' + dot(a.action) + '"></span>' +
        '<div class="tl-head">' +
        '<div class="tl-summary">' + esc(a.summary || a.action || '活动') + '</div>' +
        '<div class="tl-meta">' + esc(a.actor || 'local') + ' · ' + esc(a.action || '') +
        (a.entity_type ? ' · ' + esc(a.entity_type) + '#' + esc(a.entity_id === null || a.entity_id === undefined ? '—' : a.entity_id) : '') +
        '</div><div class="tl-date">' + esc(U.dateTime(a.ts)) + '</div></div></div>';
    }).join('') + '</div>';
  }

  function healthLine(health) {
    if (!health) {
      return '<span class="small faint">后端健康信息不可用</span>';
    }
    return '<span class="small faint">API ' + esc(health.version || '—') +
      ' · 数据库 ' + esc(health.db || '—') +
      ' · 表 ' + esc(String(health.tables === undefined ? '—' : health.tables)) +
      ' · 检查时间 ' + esc(U.dateTime(health.time)) + '</span>';
  }

  function render(root, dash, pending, health) {
    var c = dash.counts || {};
    var counts = [
      ['供应商', c.suppliers],
      ['需求方', c.demanders],
      ['算力供给', c.supplies],
      ['需求', c.demands],
      ['证据', c.evidence],
      ['匹配记录', c.matches],
      ['商机', c.opportunities],
      ['Agent 任务', c.agent_tasks],
      ['待审批', c.pending_approvals, 'warn'],
      ['知识库', c.knowledge]
    ];
    var stats = counts.map(function (r) {
      return stat(r[0], r[1], null, r[2]);
    }).join('');

    var html = '<div class="view">' +
      '<div class="toolbar toolbar--plain">' +
      '<span class="page-lead" style="margin:0;">内部数据快照 · 仅统计本地 SQLite 记录</span>' +
      '<span class="toolbar-spacer"></span>' +
      UI.button({ label: '刷新', act: 'refresh', size: 'sm', icon: 'refresh' }) +
      '<a class="btn btn--sm" href="#/approvals">审批中心</a>' +
      '<a class="btn btn--sm" href="#/data">数据管理</a>' +
      '</div>' +
      '<div class="tip-box"><strong>诚实提示：</strong>工作台不发送邮件/私信、不生成正式报价或合同；所有对外材料/话术均为「草案」，未经 CEO 批准不得外发。成交、签约与收款在系统外由人工完成，本页不承诺任何对外数字。</div>' +
      '<div class="stat-grid">' + stats + '</div>' +
      '<div class="grid grid-2">' +
      card('业务漏斗', '按状态计数', funnel('供应商', (dash.pipeline || {}).supplier, SUPPLIER_ORDER) +
        funnel('需求', (dash.pipeline || {}).demand, DEMAND_ORDER) +
        funnel('商机', (dash.pipeline || {}).opportunity, OPP_ORDER)) +
      card('线索等级与核验状态', '线索等级只看证据，不对外承诺',
        '<h3 class="section-title">线索等级分布</h3>' + gradeBars(dash.grades) +
        '<h3 class="section-title" style="margin-top:18px;">供应商核验状态</h3>' + verificationBlock(dash.verification)) +
      '</div>' +
      '<div class="grid grid-3">' +
      card('告警', '需要人工关注的风险', alertsBlock(dash.alerts)) +
      card('待审批', 'CEO 人工决策', pendingBlock(pending)) +
      card('对外纪律', '本工作台的能力边界',
        '<div class="about-list">' +
        '<div class="about-row cap-no"><span class="cap-icon">✕</span><span class="cap-name">外发邮件 / 私信</span><span class="cap-detail">不可用 · 0 个外发通道</span></div>' +
        '<div class="about-row cap-no"><span class="cap-icon">✕</span><span class="cap-name">正式报价 / 合同</span><span class="cap-detail">不生成 · 仅内部草案</span></div>' +
        '<div class="about-row cap-partial"><span class="cap-icon">△</span><span class="cap-name">网页读取 / Web 搜索</span><span class="cap-detail">可用 · 需人工判断来源</span></div>' +
        '<div class="about-row cap-partial"><span class="cap-icon">△</span><span class="cap-name">浏览器自动化</span><span class="cap-detail">部分可用 · 仅本机 Chrome 自测</span></div>' +
        '<div class="about-row cap-partial"><span class="cap-icon">△</span><span class="cap-name">PDF 解析</span><span class="cap-detail">部分可用</span></div>' +
        '<div class="about-row cap-no"><span class="cap-icon">✕</span><span class="cap-name">MCP 连接</span><span class="cap-detail">0 个</span></div>' +
        '</div>') +
      '</div>' +
      card('最近活动', '写操作留痕', activityTimeline(dash.recent_activities), '', true) +
      '<div class="small faint" style="margin-top:14px;">' + healthLine(health) + '</div>' +
      '</div>';

    root.innerHTML = html;
  }

  function renderError(root, err) {
    root.innerHTML = '<div class="view">' +
      '<div class="toolbar toolbar--plain"><span class="page-lead" style="margin:0;">经营总览</span>' +
      '<span class="toolbar-spacer"></span>' + UI.button({ label: '重试', act: 'retry', size: 'sm', icon: 'refresh' }) + '</div>' +
      UI.errorState(err, true) +
      '<div class="tip-box" style="margin-top:16px;"><strong>提示：</strong>若后端尚未启动，请确认 Flask 已在 <code>127.0.0.1:8770</code> 运行；本页面不会白屏，可随时点击「重试」。</div>' +
      '</div>';
  }

  V.dashboard = {
    title: '经营总览',
    subtitle: '经营数据 · 漏斗 · 告警 · 待审批',
    mount: function (root) {
      var alive = true;

      function load() {
        root.innerHTML = '<div class="boot-loading"><span class="spinner"></span> 正在加载经营总览…</div>';
        Promise.all([
          API.dashboard().catch(function (e) { return { __error: e }; }),
          API.pendingApprovals().catch(function () { return { items: [] }; }),
          API.health().catch(function () { return null; })
        ]).then(function (res) {
          if (!alive) return;
          var dash = res[0];
          if (dash && dash.__error) { renderError(root, dash.__error); return; }
          render(root, dash, res[1], res[2]);
        }).catch(function (e) {
          if (alive) renderError(root, e);
        });
      }

      root.addEventListener('click', function (e) {
        var b = e.target.closest ? e.target.closest('[data-act="refresh"],[data-act="retry"]') : null;
        if (b) load();
      });

      load();
      return function () { alive = false; };
    }
  };
})();
