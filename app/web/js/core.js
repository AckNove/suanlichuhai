/* CCGS 内部工作台 · core.js
 * 全局命名空间、事件总线、通用工具（无依赖、无网络资源）。
 * 加载顺序：core.js → api.js → ui.js → schema.js → views/*.js → app.js
 */
var CCGS = window.CCGS || (window.CCGS = {});

(function () {
  'use strict';

  var U = CCGS.util = CCGS.util || {};

  /* ---------- 转义与取值 ---------- */
  U.esc = function (value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  };

  U.isEmpty = function (value) {
    return value === null || value === undefined || value === '' ||
      (typeof value === 'string' && value.trim() === '') ||
      (Array.isArray(value) && value.length === 0);
  };

  /** 缺字段统一占位：— ，需求类待确认字段可用 U.pending */
  U.text = function (value, fallback) {
    if (U.isEmpty(value)) return fallback === undefined ? '—' : fallback;
    return String(value);
  };
  U.pending = '待确认';

  U.escText = function (value, fallback) {
    return U.esc(U.text(value, fallback));
  };

  U.num = function (value, digits) {
    if (value === null || value === undefined || value === '') return '—';
    var n = Number(value);
    if (!isFinite(n)) return U.esc(value);
    if (digits === undefined) return String(n);
    return n.toFixed(digits);
  };

  U.int = function (value) {
    var n = parseInt(value, 10);
    return isFinite(n) ? n : 0;
  };

  U.bool = function (value) {
    if (value === true || value === 1 || value === '1' || value === 'true' || value === 'TRUE') return true;
    return false;
  };

  /** data-table 排序取值：数字按数值、空值排后、其余按中文本地化比较 */
  U.cmp = function (a, b) {
    var ae = U.isEmpty(a), be = U.isEmpty(b);
    if (ae && be) return 0;
    if (ae) return 1;
    if (be) return -1;
    var an = Number(a), bn = Number(b);
    if (!isNaN(an) && !isNaN(bn) && String(a).trim() !== '' && String(b).trim() !== '') return an - bn;
    return String(a).localeCompare(String(b), 'zh-Hans-CN');
  };

  /* ---------- 时间 ---------- */
  U.dateOnly = function (value) {
    if (U.isEmpty(value)) return '—';
    var s = String(value);
    var m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
    return m ? m[1] + '-' + m[2] + '-' + m[3] : s;
  };

  U.dateTime = function (value) {
    if (U.isEmpty(value)) return '—';
    var s = String(value);
    var m = s.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
    if (m) return m[1] + '-' + m[2] + '-' + m[3] + ' ' + m[4] + ':' + m[5];
    return U.dateOnly(value);
  };

  U.relTime = function (value) {
    if (U.isEmpty(value)) return '—';
    var t = Date.parse(String(value).replace(' ', 'T'));
    if (!isFinite(t)) return U.dateTime(value);
    var diff = Date.now() - t;
    if (diff < 0) return U.dateTime(value);
    var mins = Math.floor(diff / 60000);
    if (mins < 1) return '刚刚';
    if (mins < 60) return mins + ' 分钟前';
    var hours = Math.floor(mins / 60);
    if (hours < 24) return hours + ' 小时前';
    var days = Math.floor(hours / 24);
    if (days < 30) return days + ' 天前';
    return U.dateOnly(value);
  };

  U.nowIso = function () {
    var d = new Date();
    var pad = function (n) { return String(n).padStart(2, '0'); };
    var off = -d.getTimezoneOffset();
    var sign = off >= 0 ? '+' : '-';
    var oh = pad(Math.floor(Math.abs(off) / 60));
    var om = pad(Math.abs(off) % 60);
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) +
      'T' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds()) + sign + oh + ':' + om;
  };

  U.bytes = function (value) {
    var n = Number(value);
    if (!isFinite(n) || n <= 0) return '—';
    if (n < 1024) return n + ' B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
    if (n < 1024 * 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + ' MB';
    return (n / 1024 / 1024 / 1024).toFixed(2) + ' GB';
  };

  /* ---------- 通用 ---------- */
  U.uid = function (prefix) {
    return (prefix || 'u') + '-' + Math.random().toString(36).slice(2, 9) + '-' + Date.now().toString(36);
  };

  U.debounce = function (fn, wait) {
    var timer = null;
    return function () {
      var self = this, args = arguments;
      clearTimeout(timer);
      timer = setTimeout(function () { fn.apply(self, args); }, wait || 300);
    };
  };

  U.byId = function (id) { return document.getElementById(id); };

  U.qs = function (params) {
    var parts = [];
    Object.keys(params || {}).forEach(function (k) {
      var v = params[k];
      if (v === undefined || v === null || v === '') return;
      parts.push(encodeURIComponent(k) + '=' + encodeURIComponent(String(v)));
    });
    return parts.length ? '?' + parts.join('&') : '';
  };

  U.parseHash = function () {
    var raw = String(window.location.hash || '').replace(/^#\/?/, '');
    var qi = raw.indexOf('?');
    var path = qi >= 0 ? raw.slice(0, qi) : raw;
    var query = {};
    if (qi >= 0) {
      raw.slice(qi + 1).split('&').forEach(function (pair) {
        if (!pair) return;
        var idx = pair.indexOf('=');
        var k = idx >= 0 ? pair.slice(0, idx) : pair;
        var v = idx >= 0 ? pair.slice(idx + 1) : '';
        try { query[decodeURIComponent(k)] = decodeURIComponent(v); } catch (e) { /* ignore */ }
      });
    }
    return { route: path || '', query: query };
  };

  U.hashFor = function (route, query) {
    return '#/' + String(route).replace(/^#?\/?/, '') + U.qs(query || {});
  };

  U.safeParse = function (value, fallback) {
    if (value === null || value === undefined || value === '') return fallback === undefined ? null : fallback;
    if (typeof value === 'object') return value;
    try { return JSON.parse(value); } catch (e) { return fallback === undefined ? null : fallback; }
  };

  U.jsonPretty = function (value) {
    if (U.isEmpty(value)) return '';
    var obj = typeof value === 'string' ? U.safeParse(value, value) : value;
    if (typeof obj === 'string') return obj;
    try { return JSON.stringify(obj, null, 2); } catch (e) { return String(value); }
  };

  U.storage = {
    get: function (key, fallback) {
      try {
        var v = window.localStorage.getItem(key);
        return v === null ? fallback : v;
      } catch (e) { return fallback; }
    },
    set: function (key, value) {
      try { window.localStorage.setItem(key, String(value)); } catch (e) { /* ignore */ }
    },
    del: function (key) {
      try { window.localStorage.removeItem(key); } catch (e) { /* ignore */ }
    }
  };

  U.summarize = function (text, len) {
    if (U.isEmpty(text)) return '—';
    var s = String(text).replace(/\s+/g, ' ').trim();
    var max = len || 80;
    return s.length > max ? s.slice(0, max) + '…' : s;
  };

  U.pick = function (obj, keys) {
    var out = {};
    (keys || []).forEach(function (k) {
      if (obj && Object.prototype.hasOwnProperty.call(obj, k)) out[k] = obj[k];
    });
    return out;
  };

  U.clamp = function (n, min, max) { return Math.min(max, Math.max(min, n)); };

  U.options = function (values, labelMap) {
    return (values || []).map(function (v) {
      return { value: v, label: (labelMap && labelMap[v]) || v };
    });
  };

  /* ---------- 事件总线 ---------- */
  var handlers = {};
  CCGS.bus = {
    on: function (name, fn) {
      (handlers[name] = handlers[name] || []).push(fn);
      return function () { CCGS.bus.off(name, fn); };
    },
    off: function (name, fn) {
      var list = handlers[name] || [];
      var i = list.indexOf(fn);
      if (i >= 0) list.splice(i, 1);
    },
    emit: function (name, payload) {
      (handlers[name] || []).slice().forEach(function (fn) {
        try { fn(payload); } catch (e) { if (window.console) console.error('[bus]', name, e); }
      });
    }
  };

  /* ---------- 内联图标（无外部图标库） ---------- */
  var ICONS = {
    search: '<circle cx="9" cy="9" r="5.5"></circle><path d="M13.5 13.5 17 17"></path>',
    plus: '<path d="M10 4v12M4 10h12"></path>',
    refresh: '<path d="M16 10a6 6 0 1 1-1.8-4.3"></path><path d="M16 3v4h-4"></path>',
    close: '<path d="M5 5l10 10M15 5 5 15"></path>',
    edit: '<path d="M12.5 4.5 15.5 7.5 8 15H5v-3z"></path><path d="M11 6l3 3"></path>',
    trash: '<path d="M4 6h12M8 6V4h4v2M6 6l1 10h6l1-10"></path>',
    eye: '<path d="M2 10s3-5 8-5 8 5 8 5-3 5-8 5-8-5-8-5z"></path><circle cx="10" cy="10" r="2.2"></circle>',
    play: '<path d="M7 4.5v11l8-5.5z"></path>',
    check: '<path d="M4 10.5l4 4 8-9"></path>',
    x: '<path d="M5 5l10 10M15 5 5 15"></path>',
    alert: '<path d="M10 3.5 17.5 16.5h-15z"></path><path d="M10 8v3.5M10 14.2v.3"></path>',
    info: '<circle cx="10" cy="10" r="7.5"></circle><path d="M10 9v5M10 6.5v.4"></path>',
    download: '<path d="M10 3v9M6.5 8.5 10 12l3.5-3.5"></path><path d="M4 14.5V17h12v-2.5"></path>',
    upload: '<path d="M10 12V3M6.5 6.5 10 3l3.5 3.5"></path><path d="M4 14.5V17h12v-2.5"></path>',
    database: '<ellipse cx="10" cy="5" rx="6.5" ry="2.6"></ellipse><path d="M3.5 5v10c0 1.4 2.9 2.6 6.5 2.6s6.5-1.2 6.5-2.6V5"></path><path d="M3.5 10c0 1.4 2.9 2.6 6.5 2.6s6.5-1.2 6.5-2.6"></path>',
    'chevron-right': '<path d="M7.5 4 13.5 10l-6 6"></path>',
    'arrow-right': '<path d="M3 10h13M11.5 5.5 16 10l-4.5 4.5"></path>',
    shield: '<path d="M10 2.5 16 5v5c0 4-2.6 6.6-6 7.5-3.4-.9-6-3.5-6-7.5V5z"></path><path d="M7 10l2 2 4-4.5"></path>',
    file: '<path d="M5 3h7l3 3v11H5z"></path><path d="M12 3v3h3"></path>',
    lock: '<rect x="4.5" y="8.5" width="11" height="8" rx="1.5"></rect><path d="M7 8.5V6a3 3 0 0 1 6 0v2.5"></path>',
    clock: '<circle cx="10" cy="10" r="7"></circle><path d="M10 6v4.5l3 1.5"></path>',
    external: '<path d="M11 4h5v5"></path><path d="M16 4l-7 7"></path><path d="M14 12v4H4V6h4"></path>',
    filter: '<path d="M3 5h14l-5.5 6v4.5l-3 1.5V11z"></path>',
    flow: '<circle cx="5" cy="5" r="2.2"></circle><circle cx="15" cy="10" r="2.2"></circle><circle cx="5" cy="15" r="2.2"></circle><path d="M7 6l6 3M7 14l6-3"></path>',
    grid: '<rect x="3" y="3" width="6" height="6" rx="1"></rect><rect x="11" y="3" width="6" height="6" rx="1"></rect><rect x="3" y="11" width="6" height="6" rx="1"></rect><rect x="11" y="11" width="6" height="6" rx="1"></rect>'
  };

  U.icon = function (name, size) {
    var body = ICONS[name] || ICONS.info;
    var s = size || 16;
    return '<svg viewBox="0 0 20 20" width="' + s + '" height="' + s + '" fill="none" stroke="currentColor" ' +
      'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + body + '</svg>';
  };

  /* ---------- 文本高亮（全局搜索用） ---------- */
  U.escapeRegExp = function (s) {
    return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  };

  /* ---------- 状态默认文案 ---------- */
  CCGS.HONESTY = {
    banner: '内部工作台 v1.0 · 本地单用户 · 不对外发送邮件/私信 · 不生成正式报价 · 真实数据仅存本地',
    draft: '草案，未经 CEO 批准不得外发',
    caps: [
      { name: 'Web 搜索', status: 'yes', detail: '可用（搜索公开信息，结果需人工核实）' },
      { name: '网页读取', status: 'yes', detail: '可用（读取公开网页正文）' },
      { name: '浏览器自动化', status: 'partial', detail: '部分可用（本机 Chrome + CDP 仅本地自测/截图；不做自动登录、发帖、外联）' },
      { name: 'PDF 解析', status: 'partial', detail: '部分可用（文本型 PDF 可提取，扫描件需人工）' },
      { name: 'MCP 连接器', status: 'no', detail: '0 个（未接入任何 MCP 连接器）' },
      { name: '邮件 / 私信发送', status: 'no', detail: '不可用，不对外发送任何消息' },
      { name: '正式报价 / 合同生成', status: 'no', detail: '不可用，页面出现的一切价格信息均为待确认线索' }
    ]
  };
})();
