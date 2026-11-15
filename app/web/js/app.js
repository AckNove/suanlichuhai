/* CCGS 前端 · 全局布局、hash 路由、健康检查、全局搜索、关于弹窗
 * 纯原生 JS（经典脚本，非 ES module），由 index.html 按序 defer 加载。 */
var CCGS = window.CCGS || (window.CCGS = {});
(function () {
  'use strict';

  var U = CCGS.util, UI = CCGS.ui, API = CCGS.api, H = CCGS.HONESTY || { caps: [] };

  /* ============================ 路由与导航 ============================ */

  var NAV_GROUPS = [
    { title: '概览', items: [
      { route: 'dashboard', view: 'dashboard', label: '经营总览', icon: 'grid' }
    ] },
    { title: '线索与供给', items: [
      { route: 'demands', view: 'demands', label: '需求管理', icon: 'file' },
      { route: 'suppliers', view: 'companies', label: '供应商 / 需求方', icon: 'shield' },
      { route: 'supplies', view: 'supplies', label: 'GPU 资源', icon: 'database' }
    ] },
    { title: '核验与匹配', items: [
      { route: 'evidence', view: 'evidence', label: '证据来源', icon: 'external' },
      { route: 'supplier-verifications', view: 'supplierVerifications', label: '供应商核验', icon: 'check' },
      { route: 'demand-qualifications', view: 'demandQualifications', label: '需求资格核验', icon: 'check' },
      { route: 'specs', view: 'specs', label: '算力规格', icon: 'filter' },
      { route: 'matching', view: 'matching', label: '供需匹配', icon: 'flow' },
      { route: 'procurement', view: 'procurement', label: '采购分析', icon: 'file' }
    ] },
    { title: '商业化', items: [
      { route: 'opportunities', view: 'opportunities', label: '商机管理', icon: 'arrow-right' },
      { route: 'activities', view: 'activities', label: '项目进度', icon: 'clock' }
    ] },
    { title: 'Agent 与治理', items: [
      { route: 'agents', view: 'agents', label: 'Agent 任务', icon: 'play' },
      { route: 'approvals', view: 'approvals', label: 'CEO 审批', icon: 'check' }
    ] },
    { title: '知识', items: [
      { route: 'knowledge', view: 'knowledge', label: '知识库', icon: 'file' }
    ] },
    { title: '数据与审计', items: [
      { route: 'data', view: 'data', label: 'CSV 导入导出', icon: 'download' },
      { route: 'backup', view: 'backup', label: '数据备份', icon: 'database' },
      { route: 'audit', view: 'audit', label: '审计日志', icon: 'lock' }
    ] }
  ];

  var ROUTES = {};
  NAV_GROUPS.forEach(function (g) {
    g.items.forEach(function (it) { ROUTES[it.route] = it; });
  });

  var ALIASES = {
    overview: 'dashboard', home: 'dashboard',
    companies: 'suppliers', company: 'suppliers', demander: 'suppliers', demanders: 'suppliers',
    supply: 'supplies',
    verifications: 'supplier-verifications', verify: 'supplier-verifications',
    qualification: 'demand-qualifications', qualifications: 'demand-qualifications',
    spec: 'specs', specs: 'specs',
    match: 'matching',
    report: 'procurement', reports: 'procurement',
    opportunity: 'opportunities',
    agent: 'agents',
    approval: 'approvals',
    import: 'data', export: 'data',
    backups: 'backup', logs: 'audit', 'audit-logs': 'audit'
  };

  var SEARCH_TYPES = {
    company: '公司', companies: '公司', demand: '需求', demands: '需求',
    supply: '供给', supplies: '供给', evidence: '证据', knowledge: '知识',
    match: '匹配', matches: '匹配', opportunity: '商机', opportunities: '商机'
  };
  var SEARCH_ROUTES = {
    company: 'suppliers', companies: 'suppliers', demand: 'demands', demands: 'demands',
    supply: 'supplies', supplies: 'supplies', evidence: 'evidence', knowledge: 'knowledge',
    match: 'matching', matches: 'matching', opportunity: 'opportunities', opportunities: 'opportunities'
  };

  var mountedCleanup = null;
  var currentRoute = null;
  var lastHealthOk = null;
  var pendingCount = 0;

  function byId(id) { return document.getElementById(id); }

  /* ============================ 导航构建 ============================ */

  function buildNav() {
    var nav = byId('nav');
    if (!nav) return;
    nav.innerHTML = NAV_GROUPS.map(function (g) {
      return '<div class="nav-group">' +
        '<div class="nav-group-title">' + U.esc(g.title) + '</div>' +
        g.items.map(function (it) {
          return '<a class="nav-item" href="#/' + U.esc(it.route) + '" data-route="' + U.esc(it.route) + '">' +
            '<span class="nav-icon">' + U.icon(it.icon, 16) + '</span>' +
            '<span class="nav-label">' + U.esc(it.label) + '</span>' +
            (it.route === 'approvals' ? '<span class="nav-badge" data-badge="approvals" hidden></span>' : '') +
            '</a>';
        }).join('') +
        '</div>';
    }).join('');
  }

  function setActiveNav(routeKey) {
    var nav = byId('nav');
    if (!nav) return;
    var items = nav.querySelectorAll('.nav-item');
    for (var i = 0; i < items.length; i++) {
      var r = items[i].getAttribute('data-route');
      items[i].classList.toggle('active', r === routeKey);
    }
  }

  function setHeader(routeKey) {
    var item = ROUTES[routeKey];
    var view = item ? (CCGS.views || {})[item.view] : null;
    var title = (view && view.title) || (item ? item.label : '经营总览');
    var sub = (view && view.subtitle) || '本地单用户工作台 · 数据仅存本机';
    var t = byId('page-title');
    var s = byId('page-sub');
    if (t) t.textContent = title;
    if (s) s.textContent = sub;
    document.title = title + ' · CCGS 内部工作台';
  }

  function updatePendingBadge() {
    var badges = document.querySelectorAll('[data-badge="approvals"]');
    for (var i = 0; i < badges.length; i++) {
      if (pendingCount > 0) {
        badges[i].hidden = false;
        badges[i].textContent = pendingCount > 99 ? '99+' : String(pendingCount);
        badges[i].title = pendingCount + ' 项待审批';
      } else {
        badges[i].hidden = true;
        badges[i].textContent = '';
      }
    }
  }

  function refreshPendingBadge() {
    API.pendingApprovals()
      .then(function (res) {
        var n = 0;
        if (res) {
          if (typeof res.total === 'number') n = res.total;
          else if (Array.isArray(res.items)) n = res.items.length;
          else if (Array.isArray(res)) n = res.length;
        }
        pendingCount = n;
        updatePendingBadge();
      })
      .catch(function () { /* 后端未连接时保持当前值，不打扰用户 */ });
  }

  /* ============================ 路由解析与挂载 ============================ */

  function resolveRoute() {
    var parsed = U.parseHash();
    var key = parsed.route || 'dashboard';
    if (!ROUTES[key]) key = ALIASES[key] || 'dashboard';
    return { key: key, query: parsed.query || {} };
  }

  function teardown() {
    if (typeof mountedCleanup === 'function') {
      try { mountedCleanup(); } catch (e) { if (window.console) console.error('[route] cleanup failed', e); }
    }
    mountedCleanup = null;
  }

  function renderMountError(host, err) {
    var text = err && err.message ? err.message : String(err || '未知错误');
    host.innerHTML = '<div class="error-state">' +
      '<div class="error-icon">' + U.icon('alert', 30) + '</div>' +
      '<div class="error-title">页面渲染失败</div>' +
      '<div class="error-text">' + U.esc(text) + '</div>' +
      '<div class="empty-actions">' +
        '<button class="btn btn--primary btn--sm" type="button" data-act="retry-mount">重试</button>' +
        '<a class="btn btn--ghost btn--sm" href="#/dashboard">回到总览</a>' +
      '</div></div>';
    host.addEventListener('click', function (ev) {
      var btn = ev.target.closest('[data-act="retry-mount"]');
      if (btn) mountRoute();
    });
  }

  function mountRoute() {
    var r = resolveRoute();
    currentRoute = r.key;
    var root = byId('view');
    if (!root) return;

    teardown();
    var rm = root.querySelector('[data-act="retry-mount"]');
    if (rm) { /* 旧错误容器随 innerHTML 清理 */ }
    var host = document.createElement('div');
    host.className = 'route-host';
    root.innerHTML = '';
    root.appendChild(host);

    setActiveNav(r.key);
    setHeader(r.key);
    refreshPendingBadge();

    var item = ROUTES[r.key];
    var views = CCGS.views || {};
    var view = item ? views[item.view] : null;
    if (!view || typeof view.mount !== 'function') {
      host.innerHTML = UI.empty({
        icon: 'alert',
        title: '模块未加载',
        text: '找不到该路由对应的前端视图（' + U.esc((item && item.view) || 'unknown') + '）。请确认 app/web/js/views/*.js 已正确加载。',
        actions: '<a class="btn btn--primary btn--sm" href="#/dashboard">回到总览</a>'
      });
      return;
    }

    try {
      mountedCleanup = view.mount(host) || null;
    } catch (err) {
      if (window.console) console.error('[route] mount failed:', r.key, err);
      mountedCleanup = null;
      renderMountError(host, err);
      UI.toast('error', '页面渲染失败：' + (err && err.message ? err.message : err), 8000);
    }
    root.scrollTop = 0;
    if (typeof window.scrollTo === 'function') {
      try { window.scrollTo(0, 0); } catch (e) { /* ignore */ }
    }
    if (window.innerWidth <= 1000) closeSidebar();
  }

  /* ============================ 侧栏 / 顶栏交互 ============================ */

  function openSidebar() {
    var sidebar = byId('sidebar');
    var btn = byId('btn-menu');
    if (sidebar) sidebar.classList.add('open');
    if (btn) btn.setAttribute('aria-expanded', 'true');
  }
  function closeSidebar() {
    var sidebar = byId('sidebar');
    var btn = byId('btn-menu');
    if (sidebar) sidebar.classList.remove('open');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  }
  function toggleSidebar() {
    var sidebar = byId('sidebar');
    if (!sidebar) return;
    if (sidebar.classList.contains('open')) closeSidebar(); else openSidebar();
  }

  function bindTopbar() {
    var menuBtn = byId('btn-menu');
    if (menuBtn) menuBtn.addEventListener('click', function (ev) { ev.stopPropagation(); toggleSidebar(); });

    var brand = byId('brand');
    if (brand) brand.addEventListener('click', function () {
      if (window.location.hash !== '#/dashboard') window.location.hash = '#/dashboard';
    });

    var aboutBtn = byId('btn-about');
    var aboutSide = byId('btn-about-side');
    if (aboutBtn) aboutBtn.addEventListener('click', showAbout);
    if (aboutSide) aboutSide.addEventListener('click', showAbout);

    var retry = byId('btn-retry-conn');
    if (retry) {
      retry.addEventListener('click', function () {
        retry.disabled = true;
        var old = retry.textContent;
        retry.textContent = '连接中…';
        checkHealth().then(function (ok) {
          retry.disabled = false;
          retry.textContent = old;
          if (ok) {
            UI.toast('success', '后端已连接');
            mountRoute();
          } else {
            UI.toast('error', '仍无法连接后端：请确认 Flask 已在 127.0.0.1:8770 启动。', 8000);
          }
        });
      });
    }

    var health = byId('health-indicator');
    if (health) {
      health.addEventListener('click', function () {
        checkHealth().then(function (ok) {
          if (ok) UI.toast('success', '后端在线 · 数据库可访问');
          else UI.toast('error', '后端未连接：请确认 Flask 已在 127.0.0.1:8770 启动。', 6000);
        });
      });
    }

    document.addEventListener('click', function (ev) {
      var sidebar = byId('sidebar');
      var menuBtn = byId('btn-menu');
      if (!sidebar || !sidebar.classList.contains('open')) return;
      if (sidebar.contains(ev.target)) return;
      if (menuBtn && menuBtn.contains(ev.target)) return;
      closeSidebar();
    });
  }

  /* ============================ 健康检查 ============================ */

  function applyHealth(ok, info) {
    var health = byId('health-indicator');
    var side = byId('side-health');
    var banner = byId('offline-banner');
    if (health) {
      health.classList.toggle('online', ok);
      health.classList.toggle('offline', !ok);
      var txt = health.querySelector('.health-text');
      if (txt) txt.textContent = ok ? '后端在线' : '后端未连接';
      health.title = ok
        ? ('后端在线' + (info && info.version ? ' · v' + info.version : '') + (info && info.db ? ' · ' + info.db : ''))
        : '点击重试连接 127.0.0.1:8770';
    }
    if (side) {
      side.classList.toggle('online', ok);
      side.classList.toggle('offline', !ok);
      side.textContent = ok ? ('后端在线 · ' + (info && info.version ? 'v' + info.version : 'v1.0')) : '后端未连接';
    }
    if (banner) banner.hidden = !!ok;
    if (lastHealthOk === true && !ok) UI.toast('warn', '后端连接已断开：页面保留当前内容，可点击「重试连接」。', 7000);
    lastHealthOk = ok;
  }

  function checkHealth() {
    return API.health()
      .then(function (info) { applyHealth(true, info); return true; })
      .catch(function () { applyHealth(false, null); return false; });
  }

  /* ============================ 全局搜索 ============================ */

  function initGlobalSearch() {
    var box = byId('global-search-box');
    var input = byId('global-search');
    var results = byId('search-results');
    if (!input || !results) return;
    var timer = null;
    var seq = 0;

    function hide() {
      results.hidden = true;
      results.innerHTML = '';
    }

    function renderResults(query, data) {
      var items = (data && data.results) || [];
      if (!items.length) {
        results.innerHTML = '<div class="search-empty">未找到与「' + U.esc(query) + '」匹配的结果。可尝试公司名 / GPU 型号 / 需求标题 / 证据主张。</div>';
        results.hidden = false;
        return;
      }
      results.innerHTML = items.map(function (r) {
        var type = String(r.type || '').toLowerCase();
        var hash = '#/' + (SEARCH_ROUTES[type] || 'dashboard');
        return '<button class="search-result" type="button" data-search-hash="' + U.esc(hash) + '">' +
          '<span class="sr-title">' + U.esc(r.title || '（无标题）') + '</span>' +
          '<span class="sr-type">' + U.esc(SEARCH_TYPES[type] || type || '结果') + '</span>' +
          (r.snippet ? '<span class="sr-snippet">' + U.esc(r.snippet) + '</span>' : '') +
          '</button>';
      }).join('');
      results.hidden = false;
    }

    function search(query) {
      var my = ++seq;
      API.search(query, 20)
        .then(function (data) {
          if (my !== seq) return;
          renderResults(query, data);
        })
        .catch(function (err) {
          if (my !== seq) return;
          results.innerHTML = '<div class="search-empty">' + U.esc(UI.errorText(err)) + '</div>';
          results.hidden = false;
        });
    }

    input.addEventListener('input', function () {
      var q = input.value.trim();
      if (timer) clearTimeout(timer);
      if (!q) { hide(); return; }
      timer = setTimeout(function () { search(q); }, 320);
    });
    input.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape') {
        input.value = '';
        hide();
        input.blur();
      } else if (ev.key === 'Enter') {
        var first = results.querySelector('[data-search-hash]');
        if (first) first.click();
      }
    });
    results.addEventListener('click', function (ev) {
      var btn = ev.target.closest('[data-search-hash]');
      if (!btn) return;
      window.location.hash = btn.getAttribute('data-search-hash');
      input.value = '';
      hide();
    });
    document.addEventListener('click', function (ev) {
      if (!box.contains(ev.target)) hide();
    });
  }

  /* ============================ 关于 / 能力清单 ============================ */

  function showAbout() {
    var caps = (H && H.caps) || [];
    var rows = caps.map(function (c) {
      var status = c.status || 'no';
      var cls = status === 'yes' ? 'cap-yes' : (status === 'partial' ? 'cap-partial' : 'cap-no');
      var badgeKind = status === 'yes' ? 'green' : (status === 'partial' ? 'amber' : 'red');
      var iconName = status === 'yes' ? 'check' : (status === 'partial' ? 'alert' : 'x');
      var label = status === 'yes' ? '可用' : (status === 'partial' ? '部分可用' : '不可用');
      return '<div class="about-row ' + cls + '">' +
        '<span class="cap-icon">' + U.icon(iconName, 15) + '</span>' +
        '<div><div class="cap-name">' + U.esc(c.name) + '</div>' +
        '<div class="cap-detail">' + U.esc(c.detail) + '</div></div>' +
        '<span class="toolbar-spacer"></span>' +
        '<span class="badge badge--' + badgeKind + ' badge--sm">' + label + '</span>' +
        '</div>';
    }).join('');

    var body =
      '<div class="tip-box">' + U.esc(H.banner || '内部工作台 v1.0 · 本地单用户 · 真实数据仅存本地') + '</div>' +
      '<p class="help" style="margin-top:10px">这是内部经营工作台：<strong>本地单用户</strong>，' +
      '所有真实数据只存本机 SQLite；不对外发送邮件 / 私信，不生成正式报价或合同；' +
      '任何审批都只能由人工点击完成，系统不会自动批准。</p>' +
      '<div class="section-title" style="margin:16px 0 8px">能力清单</div>' +
      '<div class="about-list">' + rows + '</div>' +
      '<div class="section-title" style="margin:16px 0 8px">诚实边界</div>' +
      '<ul class="warn-list" style="color:var(--muted)">' +
        '<li>当前为 v1.0 内部版本：0 成交、0 正式核验结论对外、0 正式报价。</li>' +
        '<li>所有对外材料、话术、商机与采购报告均为 DRAFT 草案，未经 CEO 批准不得外发。</li>' +
        '<li>页面上的价格、容量、交付时间若为空或标注「待确认」，表示尚未取得一手证据。</li>' +
        '<li>外部网页内容只作为线索，需人工核实并登记 evidence_registry 后才可用于结论。</li>' +
      '</ul>';

    UI.openModal({
      title: '关于 · 能力清单',
      subtitle: '内部工作台 v1.0 · 本地单用户',
      size: 'lg',
      body: body,
      actions: [
        { label: '我知道了', kind: 'primary', onClick: function (h) { h.close(); markAboutSeen(); } }
      ]
    });
  }

  function markAboutSeen() {
    try { window.localStorage.setItem('ccgs.about.seen.v1', '1'); } catch (e) { /* ignore */ }
  }
  function maybeShowAbout() {
    var seen = false;
    try { seen = window.localStorage.getItem('ccgs.about.seen.v1') === '1'; } catch (e) { seen = false; }
    if (!seen) {
      setTimeout(function () {
        showAbout();
        markAboutSeen();
      }, 700);
    }
  }

  /* ============================ 启动 ============================ */

  function boot() {
    buildNav();
    bindTopbar();
    initGlobalSearch();

    window.addEventListener('hashchange', function () {
      mountRoute();
    });

    if (!window.location.hash) {
      try { window.history.replaceState(null, '', '#/dashboard'); }
      catch (e) { window.location.hash = '#/dashboard'; }
    }

    mountRoute();
    checkHealth();
    refreshPendingBadge();

    window.setInterval(function () { checkHealth(); }, 30000);
    window.setInterval(function () { refreshPendingBadge(); }, 60000);

    maybeShowAbout();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
