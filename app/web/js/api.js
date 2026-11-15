/* CCGS 内部工作台 · api.js
 * 唯一网络出口：所有请求均走同源相对路径 /api/...
 * 统一错误对象、连接状态事件（CCGS.bus: 'conn'）、分页/单条响应归一化。
 * 加载顺序：core.js → api.js → ui.js → ...
 */
var CCGS = window.CCGS || (window.CCGS = {});

(function () {
  'use strict';

  var U = CCGS.util;

  /* ---------- 错误对象 ---------- */
  function ApiError(status, code, message, body) {
    this.name = 'ApiError';
    this.status = status;
    this.code = code || 'INTERNAL';
    this.message = message || '请求失败';
    this.body = body || null;
  }
  ApiError.prototype = Object.create(Error.prototype);
  ApiError.prototype.constructor = ApiError;

  /* ---------- 连接状态 ---------- */
  var connected = null;
  function markOffline() {
    if (connected !== false) {
      connected = false;
      CCGS.bus.emit('conn', false);
    }
  }
  function markOnline() {
    if (connected !== true) {
      connected = true;
      CCGS.bus.emit('conn', true);
    }
  }

  var ACTOR = 'local';
  var OFFLINE_MSG = '无法连接后端服务（127.0.0.1:8770）。请确认后端已启动，或稍后重试。';

  /* ---------- 归一化：不同实现可能返回数组/包裹对象 ---------- */
  function normalizeList(payload, fallbackPage, fallbackSize) {
    if (Array.isArray(payload)) {
      return { items: payload, total: payload.length, page: 1, page_size: payload.length || fallbackSize || 0 };
    }
    payload = payload || {};
    var items = payload.items || payload.data || payload.results || payload.records || [];
    if (!Array.isArray(items)) items = [];
    var total = payload.total;
    if (total === undefined || total === null) total = items.length;
    return {
      items: items,
      total: Number(total) || 0,
      page: Number(payload.page) || fallbackPage || 1,
      page_size: Number(payload.page_size) || fallbackSize || items.length || 0
    };
  }

  function normalizeItem(payload) {
    if (!payload || typeof payload !== 'object') return null;
    if (payload.item && typeof payload.item === 'object') return payload.item;
    if (payload.data && typeof payload.data === 'object' && !Array.isArray(payload.data)) return payload.data;
    return payload;
  }

  /* ---------- 核心请求 ---------- */
  async function request(method, path, opts) {
    opts = opts || {};
    var init = {
      method: method,
      headers: { 'Accept': 'application/json', 'X-Actor': ACTOR },
      cache: 'no-store'
    };
    var body = opts.body;
    if (body !== undefined && body !== null) {
      if (typeof FormData !== 'undefined' && body instanceof FormData) {
        init.body = body;
      } else {
        init.headers['Content-Type'] = 'application/json';
        init.body = JSON.stringify(body);
      }
    }
    if (opts.headers) {
      Object.keys(opts.headers).forEach(function (k) { init.headers[k] = opts.headers[k]; });
    }

    var res;
    try {
      res = await fetch(path, init);
    } catch (e) {
      markOffline();
      throw new ApiError(0, 'OFFLINE', OFFLINE_MSG, null);
    }
    markOnline();

    var text = '';
    try { text = await res.text(); } catch (e) { text = ''; }
    var payload = null;
    if (text) {
      try { payload = JSON.parse(text); } catch (e) { payload = { raw: text }; }
    }

    if (!res.ok) {
      var errObj = payload && payload.error ? payload.error : null;
      var code = (errObj && errObj.code) || ('HTTP_' + res.status);
      var message = (errObj && errObj.message) || '';
      if (!message) {
        if (res.status === 404) message = '记录或接口不存在（404）';
        else if (res.status === 409) message = '操作与当前数据状态冲突（409）';
        else if (res.status === 403) message = '没有权限执行该操作（403）';
        else if (res.status === 400) message = '请求参数不合法（400）';
        else message = '请求失败（HTTP ' + res.status + '）';
      }
      throw new ApiError(res.status, code, message, payload);
    }
    return payload;
  }

  function resPath(resource) {
    return '/api/' + String(resource).replace(/^\/+/, '');
  }

  function itemPath(resource, id) {
    return resPath(resource) + '/' + encodeURIComponent(String(id));
  }

  /* ---------- 下载（CSV 导出 / 备份文件等） ---------- */
  function filenameFromDisposition(value) {
    if (!value) return '';
    var m = String(value).match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
    if (!m) return '';
    try { return decodeURIComponent(m[1]); } catch (e) { return m[1]; }
  }

  async function download(path, fallbackName) {
    var res;
    try {
      res = await fetch(path, { headers: { 'X-Actor': ACTOR }, cache: 'no-store' });
    } catch (e) {
      markOffline();
      throw new ApiError(0, 'OFFLINE', OFFLINE_MSG, null);
    }
    markOnline();
    if (!res.ok) {
      var text = '';
      try { text = await res.text(); } catch (e) { text = ''; }
      var payload = U.safeParse(text, null);
      var errObj = payload && payload.error ? payload.error : null;
      throw new ApiError(
        res.status,
        (errObj && errObj.code) || ('HTTP_' + res.status),
        (errObj && errObj.message) || ('下载失败（HTTP ' + res.status + '）'),
        payload
      );
    }
    var blob = await res.blob();
    var name = filenameFromDisposition(res.headers.get('Content-Disposition')) || fallbackName || 'download.dat';
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
    return name;
  }

  var api = {
    ApiError: ApiError,
    actor: ACTOR,
    request: request,
    normalizeList: normalizeList,
    normalizeItem: normalizeItem,
    download: download,

    /* 通用 CRUD */
    list: async function (resource, params) {
      var payload = await request('GET', resPath(resource) + U.qs(params || {}));
      return normalizeList(payload, params && params.page, params && params.page_size);
    },
    get: async function (resource, id) {
      return normalizeItem(await request('GET', itemPath(resource, id)));
    },
    create: async function (resource, body) {
      return normalizeItem(await request('POST', resPath(resource), { body: body || {} }));
    },
    update: async function (resource, id, body) {
      return normalizeItem(await request('PATCH', itemPath(resource, id), { body: body || {} }));
    },
    replace: async function (resource, id, body) {
      return normalizeItem(await request('PUT', itemPath(resource, id), { body: body || {} }));
    },
    remove: async function (resource, id) {
      await request('DELETE', itemPath(resource, id));
      return true;
    },

    /* 健康检查 / 总览 */
    health: function () { return request('GET', '/api/health'); },
    healthDb: function () { return request('GET', '/api/health/db'); },
    dashboard: function () { return request('GET', '/api/dashboard'); },
    search: function (q, limit) {
      return request('GET', '/api/search' + U.qs({ q: q, limit: limit || 20 }));
    },

    /* 匹配 */
    matchRun: function (payload) {
      return request('POST', '/api/match/run', { body: payload });
    },
    matchScore: function (payload) {
      return request('POST', '/api/match/score', { body: payload });
    },

    /* 报告 / 状态机 */
    reportPipeline: function () { return request('GET', '/api/reports/pipeline'); },
    reportFeeScenarios: function () { return request('GET', '/api/reports/fee-scenarios'); },
    transitions: function () { return request('GET', '/api/state/transitions'); },

    /* 导入导出 */
    exportPath: function (entity, format) {
      return '/api/export' + U.qs({ entity: entity, format: format || 'csv' });
    },
    exportCsv: async function (entity, fallbackName) {
      var fmt = 'csv';
      var name = fallbackName || (entity + '-' + U.dateOnly(U.nowIso()).replace(/-/g, '') + '.' + fmt);
      return download(api.exportPath(entity, fmt), name);
    },
    importCsv: async function (entity, mode, file) {
      var fd = new FormData();
      fd.append('file', file);
      var path = '/api/import' + U.qs({ entity: entity, mode: mode || 'upsert' });
      return request('POST', path, { body: fd });
    },

    /* 备份 */
    backupCreate: function (note) {
      return request('POST', '/api/backup', { body: { note: note || '' } });
    },
    backups: async function () {
      var payload = await request('GET', '/api/backups');
      return normalizeList(payload);
    },
    backupRestore: function (id) {
      return request('POST', '/api/backup/restore', { body: { id: id, confirm: 'RESTORE' } });
    },

    /* Agent */
    agents: async function () {
      var payload = await request('GET', '/api/agents');
      if (Array.isArray(payload)) return payload;
      var list = payload && (payload.items || payload.agents || payload.data || payload.results);
      return Array.isArray(list) ? list : [];
    },
    skills: async function () {
      var payload = await request('GET', '/api/skills');
      if (Array.isArray(payload)) return payload;
      var list = payload && (payload.items || payload.skills || payload.data || payload.results);
      return Array.isArray(list) ? list : [];
    },
    runAgentTask: function (id) {
      return request('POST', '/api/agent-tasks/' + encodeURIComponent(String(id)) + '/run');
    },

    /* 审批（只能由人工点击触发） */
    pendingApprovals: async function () {
      var payload = await request('GET', '/api/approvals/pending');
      return normalizeList(payload);
    },
    decideApproval: function (id, decision, note) {
      return request('POST', '/api/approvals/' + encodeURIComponent(String(id)) + '/decide', {
        body: { decision: decision, decided_by: 'CEO', note: note || '' }
      });
    }
  };

  CCGS.api = api;
})();
