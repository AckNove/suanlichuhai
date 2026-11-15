/* CCGS 内部工作台 · ui.js
 * 通用 UI 组件：toast、弹窗、确认框、抽屉表单、详情、空/错状态、Markdown、
 * 以及数据密集型「列表页」工厂（搜索/筛选/排序/分页/新建/编辑/删除/详情/状态推进）。
 * 加载顺序：core.js → api.js → ui.js → schema.js → views/*.js → app.js
 */
var CCGS = window.CCGS || (window.CCGS = {});

(function () {
  'use strict';

  var U = CCGS.util;
  var UI = CCGS.ui = {};

  function overlayRoot() { return U.byId('overlay-root') || document.body; }

  /* ============================================================
   * 事件委托
   * ============================================================ */
  UI.on = function (root, type, selector, handler) {
    if (!root) return;
    root.addEventListener(type, function (e) {
      var target = e.target;
      var match = target && target.closest ? target.closest(selector) : null;
      if (match && root.contains(match)) handler.call(match, e, match);
    });
  };

  /* ============================================================
   * 按钮 / 徽标 / 标签 / 图标块
   * ============================================================ */
  UI.button = function (opts) {
    opts = opts || {};
    var cls = 'btn';
    if (opts.kind) cls += ' btn--' + opts.kind;
    if (opts.size === 'sm') cls += ' btn--sm';
    if (opts.block) cls += ' btn--block';
    var attrs = ['type="button"'];
    if (opts.act) attrs.push('data-act="' + U.esc(opts.act) + '"');
    if (opts.id) attrs.push('id="' + U.esc(opts.id) + '"');
    if (opts.title) attrs.push('title="' + U.esc(opts.title) + '"');
    if (opts.disabled) attrs.push('disabled');
    Object.keys(opts.data || {}).forEach(function (k) {
      attrs.push('data-' + k + '="' + U.esc(opts.data[k]) + '"');
    });
    var inner = '';
    if (opts.icon) inner += U.icon(opts.icon, opts.size === 'sm' ? 13 : 15);
    if (opts.label) inner += '<span>' + U.esc(opts.label) + '</span>';
    return '<button class="' + cls + '" ' + attrs.join(' ') + '>' + inner + '</button>';
  };

  UI.badge = function (value, kind, opts) {
    if (U.isEmpty(value)) return '<span class="dash-text">—</span>';
    var k = kind || (CCGS.schema && CCGS.schema.statusKind ? CCGS.schema.statusKind(value) : 'gray');
    var label = (CCGS.schema && CCGS.schema.label ? CCGS.schema.label(value) : String(value));
    var extra = (opts && opts.sm) ? ' badge--sm' : '';
    return '<span class="badge badge--' + k + extra + '">' + U.esc(label) + '</span>';
  };

  UI.tags = function (value) {
    if (U.isEmpty(value)) return '<span class="dash-text">—</span>';
    var list = Array.isArray(value) ? value : String(value).split(/[,，;；\s]+/).filter(Boolean);
    if (!list.length) return '<span class="dash-text">—</span>';
    return '<span class="tags">' + list.map(function (t) {
      return '<span class="tag">' + U.esc(t) + '</span>';
    }).join('') + '</span>';
  };

  UI.link = function (url, text) {
    if (U.isEmpty(url)) return '<span class="dash-text">—</span>';
    var label = text || url;
    var safe = String(url).trim();
    if (!/^https?:\/\//i.test(safe)) return U.esc(label);
    return '<a href="' + U.esc(safe) + '" target="_blank" rel="noopener noreferrer">' + U.esc(label) + '</a>';
  };

  UI.boolBadge = function (value, yes, no) {
    var on = value === true || value === 1 || value === '1' || value === 'true';
    return on
      ? '<span class="badge badge--green badge--sm">' + U.esc(yes || '是') + '</span>'
      : '<span class="badge badge--gray badge--sm">' + U.esc(no || '否') + '</span>';
  };

  /* ============================================================
   * Toast
   * ============================================================ */
  UI.toast = function (type, message, ms) {
    var stack = U.byId('toasts');
    if (!stack) return function () {};
    type = type || 'info';
    var iconName = type === 'success' ? 'check' : (type === 'error' || type === 'warn') ? 'alert' : 'info';
    var el = document.createElement('div');
    el.className = 'toast toast--' + type;
    el.setAttribute('role', type === 'error' ? 'alert' : 'status');
    el.innerHTML = '<span class="toast-icon">' + U.icon(iconName, 14) + '</span>' +
      '<div class="toast-body">' + U.esc(message) + '</div>' +
      '<button class="toast-close" type="button" aria-label="关闭">' + U.icon('close', 13) + '</button>';
    stack.appendChild(el);
    var closed = false;
    function close() {
      if (closed) return;
      closed = true;
      if (el.parentNode) el.parentNode.removeChild(el);
    }
    el.querySelector('.toast-close').addEventListener('click', close);
    if (ms !== 0) setTimeout(close, ms || (type === 'error' ? 7000 : type === 'warn' ? 5200 : 3800));
    return close;
  };

  /* ============================================================
   * 弹窗基础设施
   * ============================================================ */
  var overlayStack = [];
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && overlayStack.length) {
      var top = overlayStack[overlayStack.length - 1];
      if (top && top.close) top.close();
    }
  });

  UI.openModal = function (opts) {
    opts = opts || {};
    var backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    var size = opts.size ? ' modal--' + opts.size : '';
    var closable = opts.closable !== false;
    var footButtons = '';
    (opts.actions || []).forEach(function (a, idx) {
      footButtons += '<button class="btn' + (a.kind ? ' btn--' + a.kind : '') + '" type="button" data-action-idx="' + idx + '">' +
        (a.icon ? U.icon(a.icon, 14) : '') + '<span>' + U.esc(a.label) + '</span></button>';
    });
    var footer = opts.footer || (footButtons ? footButtons : '');
    backdrop.innerHTML =
      '<div class="modal' + size + '" role="dialog" aria-modal="true">' +
        '<div class="modal-head">' +
          '<div class="modal-head-text">' +
            '<h3>' + U.esc(opts.title || '对话框') + '</h3>' +
            (opts.subtitle ? '<p>' + U.esc(opts.subtitle) + '</p>' : '') +
          '</div>' +
          (closable ? '<button class="modal-close" type="button" data-role="modal-close" aria-label="关闭">' + U.icon('close', 15) + '</button>' : '') +
        '</div>' +
        '<div class="modal-body">' + (opts.body || '') + '</div>' +
        (footer ? '<div class="modal-foot">' + footer + '</div>' : '') +
      '</div>';
    overlayRoot().appendChild(backdrop);
    var bodyEl = backdrop.querySelector('.modal-body');
    var handle = {
      el: backdrop,
      bodyEl: bodyEl,
      footEl: backdrop.querySelector('.modal-foot'),
      close: function () {
        var i = overlayStack.indexOf(handle);
        if (i >= 0) overlayStack.splice(i, 1);
        if (backdrop.parentNode) backdrop.parentNode.removeChild(backdrop);
        if (opts.onClose) opts.onClose();
      }
    };
    var closeBtn = backdrop.querySelector('[data-role="modal-close"]');
    if (closeBtn) closeBtn.addEventListener('click', handle.close);
    if (opts.backdropClose !== false) {
      backdrop.addEventListener('mousedown', function (e) {
        if (e.target === backdrop) handle.close();
      });
    }
    (opts.actions || []).forEach(function (a, idx) {
      var btn = backdrop.querySelector('[data-action-idx="' + idx + '"]');
      if (!btn) return;
      btn.addEventListener('click', function () {
        if (a.onClick) a.onClick(handle, btn);
        else handle.close();
      });
    });
    overlayStack.push(handle);
    if (opts.onMount) opts.onMount(handle);
    return handle;
  };

  /* ============================================================
   * 确认框（危险操作/CEO 审批等）；返回 Promise<{ok, note}>
   * ============================================================ */
  UI.confirm = function (opts) {
    opts = opts || {};
    return new Promise(function (resolve) {
      var decided = false;
      function done(ok, note) {
        if (decided) return;
        decided = true;
        resolve({ ok: ok, note: note || '' });
      }
      var body = '<div class="confirm-body">';
      if (opts.message) body += '<p>' + (opts.html ? opts.message : U.esc(opts.message)) + '</p>';
      if (opts.warn) body += '<div class="warn-box">' + (opts.warnHtml ? opts.warn : U.esc(opts.warn)) + '</div>';
      if (opts.dangerText) body += '<div class="danger-box">' + (opts.dangerHtml ? opts.dangerText : U.esc(opts.dangerText)) + '</div>';
      if (opts.requireText) {
        body += '<div class="confirm-note">' +
          '<label class="small muted">请输入 <strong>' + U.esc(opts.requireText) + '</strong> 以确认此操作</label>' +
          '<input class="input" type="text" data-role="confirm-text" autocomplete="off" placeholder="' + U.esc(opts.requireText) + '">' +
          '<div class="form-error" data-role="confirm-error"></div>' +
        '</div>';
      }
      if (opts.note) {
        body += '<div class="confirm-note">' +
          '<label class="small muted">' + U.esc(opts.noteLabel || '备注（可选）') + '</label>' +
          '<textarea rows="3" data-role="confirm-note" placeholder="' + U.esc(opts.notePlaceholder || '') + '"></textarea>' +
        '</div>';
      }
      body += '</div>';
      var handle = UI.openModal({
        title: opts.title || '请确认',
        subtitle: opts.subtitle || '',
        size: opts.requireText ? '' : 'sm',
        body: body,
        onClose: function () { done(false, ''); },
        actions: [
          { label: opts.cancelText || '取消', onClick: function (h) { h.close(); } },
          {
            label: opts.confirmText || '确认',
            kind: opts.danger === false ? 'primary' : 'danger',
            onClick: function (h) {
              var noteEl = h.el.querySelector('[data-role="confirm-note"]');
              var note = noteEl ? noteEl.value.trim() : '';
              if (opts.requireText) {
                var input = h.el.querySelector('[data-role="confirm-text"]');
                var val = input ? input.value.trim() : '';
                if (val !== opts.requireText) {
                  var errEl = h.el.querySelector('[data-role="confirm-error"]');
                  if (errEl) {
                    errEl.textContent = '输入不匹配，请输入 ' + opts.requireText + ' 确认。';
                    errEl.classList.add('visible');
                  }
                  return;
                }
              }
              if (opts.noteRequired && !note) {
                var noteErr = h.el.querySelector('[data-role="confirm-error"]');
                if (noteErr) {
                  noteErr.textContent = '请填写备注后再提交。';
                  noteErr.classList.add('visible');
                }
                return;
              }
              if (opts.requireText) {
                var input2 = h.el.querySelector('[data-role="confirm-text"]');
                if (input2) input2.value = '';
              }
              done(true, note);
              h.close();
            }
          }
        ]
      });
      var firstInput = handle.el.querySelector('[data-role="confirm-text"], [data-role="confirm-note"]');
      if (firstInput) setTimeout(function () { firstInput.focus(); }, 30);
    });
  };

  /* ============================================================
   * 抽屉
   * ============================================================ */
  UI.openDrawer = function (opts) {
    opts = opts || {};
    var backdrop = document.createElement('div');
    backdrop.className = 'drawer-backdrop';
    backdrop.innerHTML =
      '<div class="drawer' + (opts.wide ? ' drawer--wide' : '') + '" role="dialog" aria-modal="true">' +
        '<div class="drawer-head">' +
          '<div class="drawer-head-text">' +
            '<h3>' + U.esc(opts.title || '') + '</h3>' +
            (opts.subtitle ? '<p>' + U.esc(opts.subtitle) + '</p>' : '') +
          '</div>' +
          '<button class="drawer-close" type="button" data-role="drawer-close" aria-label="关闭">' + U.icon('close', 16) + '</button>' +
        '</div>' +
        '<div class="drawer-body">' + (opts.body || '') + '</div>' +
        (opts.footer ? '<div class="drawer-foot">' + opts.footer + '</div>' : '') +
      '</div>';
    overlayRoot().appendChild(backdrop);
    var handle = {
      el: backdrop,
      bodyEl: backdrop.querySelector('.drawer-body'),
      footEl: backdrop.querySelector('.drawer-foot'),
      close: function () {
        var i = overlayStack.indexOf(handle);
        if (i >= 0) overlayStack.splice(i, 1);
        if (backdrop.parentNode) backdrop.parentNode.removeChild(backdrop);
        if (opts.onClose) opts.onClose();
      }
    };
    backdrop.querySelector('[data-role="drawer-close"]').addEventListener('click', handle.close);
    if (opts.backdropClose !== false) {
      backdrop.addEventListener('mousedown', function (e) {
        if (e.target === backdrop) handle.close();
      });
    }
    overlayStack.push(handle);
    return handle;
  };

  /* ============================================================
   * 表单字段渲染 / 取值 / 校验
   * ============================================================ */
  function escAttr(v) { return U.esc(v === null || v === undefined ? '' : v); }

  function normalizeOptions(options) {
    return (options || []).map(function (o) {
      if (o && typeof o === 'object') return { value: o.value, label: o.label === undefined ? o.value : o.label };
      return { value: o, label: o };
    });
  }

  UI.formFields = function (fields, values) {
    values = values || {};
    var html = '';
    (fields || []).forEach(function (f) {
      if (!f || !f.key && f.type !== 'section') return;
      if (f.type === 'section') {
        html += '<div class="form-section-title form-field--span">' + U.esc(f.label || '') + '</div>';
        return;
      }
      var val = values[f.key];
      var span = f.span || f.type === 'textarea' || f.type === 'checks' ? ' form-field--span' : '';
      var req = f.required ? ' <span class="req">*</span>' : '';
      var help = f.help ? '<p class="help">' + U.esc(f.help) + '</p>' : '';

      if (f.type === 'hidden') {
        html += '<input type="hidden" name="' + U.esc(f.key) + '" value="' + escAttr(val) + '">';
        return;
      }
      if (f.type === 'static') {
        html += '<div class="form-field form-field--span"><label>' + U.esc(f.label || '') + '</label>' +
          '<div class="detail-text small">' + U.escText(val) + '</div>' + help + '</div>';
        return;
      }
      if (f.type === 'checkbox') {
        var checked = val === 1 || val === '1' || val === true || val === 'true';
        html += '<div class="form-field form-field--check' + span + '"><label>' +
          '<input type="checkbox" name="' + U.esc(f.key) + '" value="1"' + (checked ? ' checked' : '') + '> ' +
          U.esc(f.label || '') + '</label>' + help + '</div>';
        return;
      }
      if (f.type === 'checks') {
        html += '<div class="form-field form-field--span"><label>' + U.esc(f.label || '') + '</label>' +
          '<div class="check-grid">' +
          (f.items || []).map(function (it) {
            var itemChecked = values[it.key] === 1 || values[it.key] === '1' || values[it.key] === true || values[it.key] === 'true';
            return '<label class="form-field form-field--check check-item">' +
              '<input type="checkbox" name="' + U.esc(it.key) + '" value="1"' + (itemChecked ? ' checked' : '') + '> ' +
              U.esc(it.label || it.key) + '</label>';
          }).join('') + '</div>' + help + '</div>';
        return;
      }
      if (f.type === 'radio') {
        var options = normalizeOptions(f.options || [{ value: '1', label: '是' }, { value: '0', label: '否' }]);
        var current = val === null || val === undefined ? (f.default !== undefined ? f.default : '') : String(val);
        html += '<div class="form-field' + span + '"><label>' + U.esc(f.label || '') + req + '</label>' +
          '<div class="radio-row">' +
          options.map(function (o) {
            var selected = String(o.value) === String(current);
            return '<label class="radio-item' + (selected ? ' checked' : '') + '">' +
              '<input type="radio" name="' + U.esc(f.key) + '" value="' + escAttr(o.value) + '"' +
              (selected ? ' checked' : '') + '> ' + U.esc(o.label) + '</label>';
          }).join('') +
          '</div>' + help + '</div>';
        return;
      }
      if (f.type === 'select') {
        var opts2 = normalizeOptions(f.options);
        var cur = val === null || val === undefined ? '' : String(val);
        html += '<div class="form-field' + span + '"><label>' + U.esc(f.label || '') + req + '</label>' +
          '<select name="' + U.esc(f.key) + '">' +
          (f.allowEmpty === false ? '' : '<option value="">— 请选择 —</option>') +
          opts2.map(function (o) {
            return '<option value="' + escAttr(o.value) + '"' + (String(o.value) === cur ? ' selected' : '') + '>' +
              U.esc(o.label) + '</option>';
          }).join('') + '</select>' + help + '</div>';
        return;
      }
      if (f.type === 'textarea') {
        html += '<div class="form-field' + span + '"><label>' + U.esc(f.label || '') + req + '</label>' +
          '<textarea name="' + U.esc(f.key) + '" rows="' + (f.rows || 4) + '"' +
          (f.code ? ' class="code"' : '') +
          (f.placeholder ? ' placeholder="' + escAttr(f.placeholder) + '"' : '') + '>' +
          escAttr(val) + '</textarea>' + help + '</div>';
        return;
      }
      var inputType = f.type || 'text';
      if (inputType === 'date' && val) val = String(val).slice(0, 10);
      var extra = '';
      if (f.min !== undefined) extra += ' min="' + escAttr(f.min) + '"';
      if (f.max !== undefined) extra += ' max="' + escAttr(f.max) + '"';
      if (f.step !== undefined) extra += ' step="' + escAttr(f.step) + '"';
      if (f.readOnly || f.type === 'static') extra += ' readonly';
      html += '<div class="form-field' + span + '"><label>' + U.esc(f.label || '') + req + '</label>' +
        '<input type="' + inputType + '" name="' + U.esc(f.key) + '" value="' + escAttr(val) + '"' +
        (f.placeholder ? ' placeholder="' + escAttr(f.placeholder) + '"' : '') +
        (f.autocomplete === false ? ' autocomplete="off"' : '') + extra + '>' + help + '</div>';
    });
    return html;
  };

  UI.collectForm = function (formEl, fields) {
    var values = {};
    (fields || []).forEach(function (f) {
      if (!f || f.type === 'section' || f.type === 'static') return;
      if (f.type === 'checks') {
        (f.items || []).forEach(function (it) {
          var el = formEl.querySelector('[name="' + it.key + '"]');
          values[it.key] = el && el.checked ? 1 : 0;
        });
        return;
      }
      if (f.type === 'checkbox') {
        var cb = formEl.querySelector('[name="' + f.key + '"]');
        values[f.key] = cb && cb.checked ? 1 : 0;
        return;
      }
      if (f.type === 'radio') {
        var r = formEl.querySelector('[name="' + f.key + '"]:checked');
        values[f.key] = r ? r.value : (f.default !== undefined ? String(f.default) : '');
        return;
      }
      var el2 = formEl.querySelector('[name="' + f.key + '"]');
      var raw = el2 ? el2.value.trim() : '';
      if (f.type === 'number') values[f.key] = raw === '' ? null : Number(raw);
      else values[f.key] = raw;
    });
    return values;
  };

  UI.showFormError = function (formEl, message) {
    var el = formEl.querySelector('[data-role="form-error"]');
    if (!el) return;
    el.textContent = message;
    el.classList.toggle('visible', !!message);
  };

  UI.openForm = function (cfg) {
    cfg = cfg || {};
    var fields = cfg.fields || [];
    var body = '<form id="ccgs-entity-form" autocomplete="off" novalidate>' +
      '<div class="form-error" data-role="form-error"></div>' +
      '<div class="form-grid">' + UI.formFields(fields, cfg.values || {}) + '</div>' +
      '</form>';
    var drawer = UI.openDrawer({
      title: cfg.title || '编辑',
      subtitle: cfg.subtitle || '',
      wide: cfg.wide !== false,
      body: body,
      footer: '<button class="btn" type="button" data-role="form-cancel">取消</button>' +
        '<button class="btn btn--primary" type="button" data-role="form-submit">' +
        U.esc(cfg.submitText || '保存') + '</button>'
    });
    var formEl = drawer.el.querySelector('#ccgs-entity-form');
    formEl.addEventListener('change', function (e) {
      var t = e.target;
      if (t && t.type === 'radio') {
        var row = t.closest('.radio-row');
        if (row) {
          Array.prototype.forEach.call(row.querySelectorAll('.radio-item'), function (item) {
            item.classList.toggle('checked', !!item.querySelector('input:checked'));
          });
        }
      }
    });
    formEl.addEventListener('submit', function (e) { e.preventDefault(); submit(); });
    drawer.el.querySelector('[data-role="form-cancel"]').addEventListener('click', drawer.close);
    drawer.el.querySelector('[data-role="form-submit"]').addEventListener('click', submit);
    var first = formEl.querySelector('input:not([type="hidden"]), select, textarea');
    if (first) setTimeout(function () { first.focus(); }, 40);

    function submit() {
      UI.showFormError(formEl, '');
      var values = UI.collectForm(formEl, fields);
      var missing = [];
      fields.forEach(function (f) {
        if (!f || !f.required) return;
        var v = values[f.key];
        if (v === undefined || v === null || v === '' || (f.type === 'radio' && v === '')) missing.push(f.label || f.key);
      });
      if (missing.length) {
        UI.showFormError(formEl, '请填写必填项：' + missing.join('、'));
        var firstMissing = formEl.querySelector('[name="' + (fields.filter(function (f) { return f.required && (values[f.key] === '' || values[f.key] === null || values[f.key] === undefined || (f.type === 'radio' && values[f.key] === '')); })[0] || {}).key + '"]');
        if (firstMissing) firstMissing.focus();
        return;
      }
      var payload = cfg.buildPayload ? cfg.buildPayload(values, cfg.original || null) : values;
      if (payload && typeof payload.then === 'function') { /* 不支持的异步 buildPayload */ }
      var btn = drawer.el.querySelector('[data-role="form-submit"]');
      btn.disabled = true;
      var original = btn.innerHTML;
      btn.innerHTML = '保存中…';
      Promise.resolve()
        .then(function () { return cfg.onSubmit(payload, values); })
        .then(function () {
          btn.disabled = false;
          btn.innerHTML = original;
          drawer.close();
        })
        .catch(function (err) {
          btn.disabled = false;
          btn.innerHTML = original;
          UI.showFormError(formEl, UI.errorText(err));
          if (err && err.status !== 0) UI.toast('error', UI.errorText(err));
        });
    }
    return drawer;
  };

  /* ============================================================
   * 错误文案 / 状态迁移允许目标
   * ============================================================ */
  UI.allowedTargets = function (err) {
    var body = (err && err.body) || {};
    var errObj = body.error || body;
    var cand = errObj && (errObj.allowed || errObj.allowed_statuses || errObj.allowed_transitions ||
      errObj.allowed_targets || errObj.allows);
    if (Array.isArray(cand)) return cand.map(String);
    if (typeof cand === 'string' && cand) return [cand];
    var msg = String((errObj && errObj.message) || (err && err.message) || '');
    var m = msg.match(/(?:允许|allowed)[^:：]*[:：]\s*([A-Z_]+(?:\s*[,，、/]\s*[A-Z_]+)*)/i);
    if (m) return m[1].split(/[,，、/\s]+/).filter(Boolean);
    return [];
  };

  UI.errorText = function (err) {
    if (!err) return '未知错误';
    if (err.status === 0 || err.code === 'OFFLINE') {
      return '后端未连接：无法访问本地 API（/api/…）。请确认 Flask 已在 127.0.0.1:8770 启动，然后点击重试。';
    }
    if (err.status === 409) {
      var allowed = UI.allowedTargets(err);
      if (allowed.length) {
        return '状态迁移不允许：' + (err.message || '当前状态不支持该操作') +
          '（允许的目标状态：' + allowed.join('、') + '）';
      }
      return '操作被拒绝（409）：' + (err.message || '与现有数据冲突，请先处理关联数据。');
    }
    if (err.status === 404) return '记录不存在或已被删除（404）。';
    if (err.status === 403) return '没有权限执行该操作（403）。本工作台为本地单用户，请检查 X-Actor 头。';
    if (err.status === 400) return '提交内容不符合要求：' + (err.message || '参数校验失败');
    if (err.status >= 500) return '服务端错误：' + (err.message || '请查看后端日志');
    return err.message || '请求失败';
  };

  /* ============================================================
   * 空状态 / 错误状态 / 横幅 / 提示
   * ============================================================ */
  UI.empty = function (opts) {
    opts = opts || {};
    return '<div class="empty-state">' +
      '<span class="empty-icon">' + U.icon(opts.icon || 'database', 22) + '</span>' +
      '<div class="empty-title">' + U.esc(opts.title || '暂无数据') + '</div>' +
      '<div class="empty-text">' + U.esc(opts.text || '当前筛选条件下没有记录。可调整筛选或新建一条记录。') + '</div>' +
      (opts.actions ? '<div class="empty-actions">' + opts.actions + '</div>' : '') +
      '</div>';
  };

  UI.errorState = function (err, retry) {
    return '<div class="error-state">' +
      '<span class="error-icon">' + U.icon('alert', 22) + '</span>' +
      '<div class="empty-title">加载失败</div>' +
      '<div class="empty-text">' + U.esc(UI.errorText(err)) + '</div>' +
      (retry ? '<div class="empty-actions">' + UI.button({ label: '重试', act: 'retry', icon: 'refresh', size: 'sm' }) + '</div>' : '') +
      '</div>';
  };

  UI.draftRibbon = function (text) {
    return '<div class="ribbon-draft">' +
      '<span class="ribbon-icon">' + U.icon('file', 14) + '</span>' +
      '<strong>对外材料草案</strong><span>·</span>' +
      '<span>' + U.esc(text || CCGS.HONESTY.draft) + '</span>' +
      '<span class="muted">（本页不生成正式报价 / 合同，不自动外发）</span>' +
      '</div>';
  };

  UI.tip = function (html) {
    return '<div class="tip-box">' + U.icon('info', 15) + '<div>' + html + '</div></div>';
  };

  UI.sectionTitle = function (title, rightHtml) {
    return '<div class="section-title">' + U.esc(title) + (rightHtml || '') + '</div>';
  };

  /* ============================================================
   * 值格式化 / KV 详情
   * ============================================================ */
  UI.formatValue = function (value) {
    if (value === null || value === undefined || value === '') return '<span class="empty-val">—</span>';
    if (typeof value === 'boolean') return value ? '是' : '否';
    if (typeof value === 'object') {
      return '<pre>' + U.esc(U.jsonPretty(value)) + '</pre>';
    }
    var s = String(value);
    if (/^https?:\/\//i.test(s)) return UI.link(s, s);
    if (s.length > 160 || s.indexOf('\n') >= 0) return '<div class="detail-text">' + U.esc(s) + '</div>';
    return U.esc(s);
  };

  UI.kv = function (rows) {
    if (!rows || !rows.length) return '<div class="table-empty">' + U.empty({ title: '无字段', text: '该记录没有可展示的字段。' }) + '</div>';
    return '<div class="kv">' + rows.map(function (row) {
      var label = Array.isArray(row) ? row[0] : row.label;
      var value = Array.isArray(row) ? row[1] : row.value;
      return '<div class="kv-row"><div class="kv-key">' + U.esc(label) + '</div>' +
        '<div class="kv-val">' + (value === undefined || value === null ? '<span class="empty-val">—</span>' : value) + '</div></div>';
    }).join('') + '</div>';
  };

  UI.detailBlock = function (title, text) {
    if (U.isEmpty(text)) return '';
    return '<div class="detail-block"><h4>' + U.esc(title) + '</h4><div class="detail-text">' + U.esc(text) + '</div></div>';
  };

  UI.prettyJson = function (value) {
    if (U.isEmpty(value)) return '<span class="empty-val">—</span>';
    return '<pre>' + U.esc(U.jsonPretty(value)) + '</pre>';
  };

  /* ============================================================
   * 极简 Markdown 渲染器（先转义，再处理块级/行内语法）
   * ============================================================ */
  UI.markdown = function (md) {
    if (U.isEmpty(md)) return '<div class="markdown"><p class="muted">（内容为空）</p></div>';
    var src = String(md).replace(/\r\n?/g, '\n');
    var codeBlocks = [];
    src = src.replace(/```([a-zA-Z0-9_+-]*)[^\n]*\n([\s\S]*?)```/g, function (m, lang, code) {
      codeBlocks.push('<pre><code>' + U.esc(code.replace(/\n$/, '')) + '</code></pre>');
      return '\u0000B' + (codeBlocks.length - 1) + '\u0000';
    });
    var inlineCodes = [];
    src = U.esc(src);
    src = src.replace(/`([^`\n]+)`/g, function (m, code) {
      inlineCodes.push('<code>' + code + '</code>');
      return '\u0000I' + (inlineCodes.length - 1) + '\u0000';
    });
    src = src.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s)]+)\)/g, function (m, alt, url) {
      return '<a href="' + url + '" target="_blank" rel="noopener noreferrer">[图片] ' + (alt || url) + '</a>';
    });
    src = src.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, function (m, text, url) {
      return '<a href="' + url + '" target="_blank" rel="noopener noreferrer">' + text + '</a>';
    });

    function inline(s) {
      return s
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
        .replace(/~~([^~]+)~~/g, '<del>$1</del>');
    }

    var lines = src.split('\n');
    var out = [];
    var i = 0;

    function isBlockStart(line) {
      var t = line.trim();
      return !t || /^(#{1,6}\s|>\s?|```|\u0000B\d+\u0000$|[-*+]\s+|\d+[.)]\s+)/.test(t) ||
        /^([-*_]\s*){3,}$/.test(t) || (t.indexOf('|') === 0 && t.lastIndexOf('|') > 0);
    }

    while (i < lines.length) {
      var line = lines[i];
      var trimmed = line.trim();
      if (!trimmed) { i++; continue; }
      var blockCode = trimmed.match(/^\u0000B(\d+)\u0000$/);
      if (blockCode) { out.push(codeBlocks[Number(blockCode[1])] || ''); i++; continue; }
      var h = line.match(/^(#{1,6})\s+(.*)$/);
      if (h) {
        var level = h[1].length;
        out.push('<h' + level + '>' + inline(h[2].trim()) + '</h' + level + '>');
        i++; continue;
      }
      if (/^\s*([-*_]\s*){3,}$/.test(line)) { out.push('<hr>'); i++; continue; }
      if (/^>\s?/.test(line)) {
        var quotes = [];
        while (i < lines.length && /^>\s?/.test(lines[i])) {
          quotes.push(inline(lines[i].replace(/^>\s?/, '')));
          i++;
        }
        out.push('<blockquote>' + quotes.join('<br>') + '</blockquote>');
        continue;
      }
      var ulm = line.match(/^\s*[-*+]\s+(.*)$/);
      var olm = line.match(/^\s*\d+[.)]\s+(.*)$/);
      if (ulm || olm) {
        var tag = ulm ? 'ul' : 'ol';
        var items = [];
        var re = ulm ? /^\s*[-*+]\s+(.*)$/ : /^\s*\d+[.)]\s+(.*)$/;
        while (i < lines.length) {
          var lm = lines[i].match(re);
          if (!lm) break;
          items.push('<li>' + inline(lm[1]) + '</li>');
          i++;
        }
        out.push('<' + tag + '>' + items.join('') + '</' + tag + '>');
        continue;
      }
      // 简单表格
      if (trimmed.indexOf('|') >= 0 && i + 1 < lines.length && /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(lines[i + 1])) {
        var cells = function (row) {
          return row.replace(/^\s*\|/, '').replace(/\|\s*$/, '').split('|').map(function (c) { return c.trim(); });
        };
        var headCells = cells(lines[i]);
        i += 2;
        var bodyRows = [];
        while (i < lines.length && lines[i].indexOf('|') >= 0 && lines[i].trim()) {
          bodyRows.push('<tr>' + cells(lines[i]).map(function (c) { return '<td>' + inline(c) + '</td>'; }).join('') + '</tr>');
          i++;
        }
        out.push('<table><thead><tr>' + headCells.map(function (c) { return '<th>' + inline(c) + '</th>'; }).join('') +
          '</tr></thead><tbody>' + bodyRows.join('') + '</tbody></table>');
        continue;
      }
      // 段落（合并连续普通行）
      var paraLines = [line];
      i++;
      while (i < lines.length && lines[i].trim() && !isBlockStart(lines[i])) {
        paraLines.push(lines[i]);
        i++;
      }
      out.push('<p>' + paraLines.map(function (p) { return inline(p.trim()); }).join('<br>') + '</p>');
    }
    var html = out.join('');
    html = html.replace(/\u0000I(\d+)\u0000/g, function (m, idx) { return inlineCodes[Number(idx)] || ''; });
    html = html.replace(/\u0000B(\d+)\u0000/g, function (m, idx) { return codeBlocks[Number(idx)] || ''; });
    return '<div class="markdown">' + html + '</div>';
  };

  /* ============================================================
   * 列表页工厂
   * cfg 关键字段：
   *   resource, title, subtitle, draft, columns, filters, tabs, search,
   *   create: {label,title,subtitle,defaults}, form: {fields,wide,buildPayload},
   *   detail: {keys,title,body,size}, advance: {entity,field,dangerTargets},
   *   rowActions(row), canEdit(row), canDelete(row), onAction(act, el, ctx),
   *   fetchParams(state), afterLoad(state), empty, pageSize, defaultSort, pageLead
   * ============================================================ */
  UI.listPage = function (root, cfg) {
    cfg = cfg || {};
    var idKey = cfg.idKey || 'id';
    var state = {
      page: 1,
      pageSize: cfg.pageSize || 25,
      q: '',
      sort: cfg.defaultSort || '',
      filters: {},
      tab: '',
      loading: true,
      error: null,
      items: [],
      total: 0
    };
    (cfg.filters || []).forEach(function (f) {
      if (f.value !== undefined) state.filters[f.param] = f.value;
    });
    if (cfg.tabs && cfg.tabs.items && cfg.tabs.items.length) {
      state.tab = cfg.tabs.items[0].value === undefined ? '' : cfg.tabs.items[0].value;
    }

    var cols = (cfg.columns || []).slice();
    var showActions = cfg.actions !== false;
    var colspan = cols.length + (showActions ? 1 : 0);

    /* ---- 外层壳 ---- */
    var tabsHtml = '';
    if (cfg.tabs && cfg.tabs.items) {
      tabsHtml = '<div class="tabs" data-role="tabs">' + cfg.tabs.items.map(function (t) {
        var v = t.value === undefined ? '' : t.value;
        return '<button class="tab' + (String(v) === String(state.tab) ? ' active' : '') + '" type="button" ' +
          'data-act="tab" data-tab="' + U.esc(v) + '">' + U.esc(t.label) +
          (t.count !== undefined ? '<span class="tab-count">' + U.esc(t.count) + '</span>' : '') + '</button>';
      }).join('') + '</div>';
    }

    var searchHtml = cfg.search === false ? '' :
      '<label class="search-field">' + U.icon('search', 15) +
      '<input type="search" data-role="q" placeholder="' + U.esc(cfg.searchPlaceholder || '搜索…') + '" aria-label="搜索">' +
      '</label>';

    var filtersHtml = (cfg.filters || []).map(function (f) {
      var opts = (f.options || []).map(function (o) {
        var value = o && typeof o === 'object' ? o.value : o;
        var label = o && typeof o === 'object' ? o.label : o;
        return '<option value="' + U.esc(value) + '">' + U.esc(label) + '</option>';
      }).join('');
      var cur = state.filters[f.param] !== undefined ? state.filters[f.param] : '';
      return '<label class="filter-label">' + U.esc(f.label || '') + '</label>' +
        '<select class="select select--filter" data-filter="' + U.esc(f.param) + '" aria-label="' + U.esc(f.label || f.param) + '">' +
        '<option value="">' + U.esc(f.allLabel || '全部') + '</option>' + opts + '</select>';
    }).join('');

    var createBtn = cfg.create ? UI.button({
      label: cfg.create.label || ('新建' + (cfg.singular || '')),
      act: 'new', kind: 'primary', icon: 'plus'
    }) : '';

    var headActions = (cfg.headActions || '') + createBtn;

    root.innerHTML = '<div class="view">' +
      (cfg.draft ? UI.draftRibbon() : '') +
      tabsHtml +
      '<div class="card card--flush">' +
        '<div class="card-head">' +
          '<div><h2 class="card-title">' + U.esc(cfg.title || '') +
            (cfg.subtitle ? '<span class="small muted">' + U.esc(cfg.subtitle) + '</span>' : '') + '</h2></div>' +
          '<div class="card-actions">' + headActions + '</div>' +
        '</div>' +
        '<div class="toolbar">' + searchHtml + filtersHtml +
          '<span class="toolbar-spacer"></span>' +
          (cfg.toolbarNote ? '<span class="small faint">' + U.esc(cfg.toolbarNote) + '</span>' : '') +
          UI.button({ label: '刷新', act: 'refresh', size: 'sm', icon: 'refresh' }) +
        '</div>' +
        '<div class="table-wrap"><table class="data-table">' +
          '<thead><tr>' + cols.map(function (col) {
            var sortable = col.sortable !== false && !!col.key;
            var cls = sortable ? 'sortable' : '';
            if (sortable && state.sort === col.key) cls += ' sorted';
            if (sortable && state.sort === '-' + col.key) cls += ' sorted';
            var arrow = '';
            if (sortable) {
              arrow = '<span class="th-sort">' + (state.sort === col.key ? '▲' : state.sort === '-' + col.key ? '▼' : '↕') + '</span>';
            }
            return '<th class="' + cls + '"' + (sortable ? ' data-sort="' + U.esc(col.key) + '"' : '') + '>' +
              U.esc(col.label || '') + arrow + '</th>';
          }).join('') + (showActions ? '<th class="cell--actions">操作</th>' : '') +
          '</tr></thead><tbody data-role="tbody"></tbody></table></div>' +
        '<div class="pager" data-role="pager"></div>' +
      '</div>' +
    '</div>';

    var viewEl = root.firstElementChild;
    var tbody = viewEl.querySelector('[data-role="tbody"]');
    var pagerEl = viewEl.querySelector('[data-role="pager"]');
    var qInput = viewEl.querySelector('[data-role="q"]');

    /* ---- 工具函数 ---- */
    function findItem(id) {
      for (var i = 0; i < state.items.length; i++) {
        if (String(state.items[i][idKey]) === String(id)) return state.items[i];
      }
      return null;
    }

    function rowTitle(row) {
      if (!row) return '';
      if (cfg.titleField) return U.text(row[cfg.titleField]);
      var t = row.name || row.title || row.claim || row.subject || row.summary;
      return t ? String(t) : ('ID ' + row[idKey]);
    }

    function renderLoading() {
      tbody.innerHTML = '<tr><td colspan="' + colspan + '"><div class="table-loading">' +
        '<span class="spinner spinner--sm"></span> 加载中…</div></td></tr>';
    }

    function renderRows() {
      if (state.loading) { renderLoading(); return; }
      if (state.error) {
        tbody.innerHTML = '<tr><td colspan="' + colspan + '">' + UI.errorState(state.error, true) + '</td></tr>';
        return;
      }
      if (!state.items.length) {
        tbody.innerHTML = '<tr><td colspan="' + colspan + '"><div class="table-empty">' +
          UI.empty(Object.assign({
            title: cfg.emptyTitle || '暂无记录',
            text: cfg.emptyText || '当前筛选条件下没有数据。' + (cfg.create ? '可点击右上角「' + (cfg.create.label || '新建') + '」创建。' : ''),
            actions: cfg.create ? UI.button({ label: cfg.create.label || '新建', act: 'new', kind: 'primary', size: 'sm', icon: 'plus' }) : ''
          }, {})) + '</div></td></tr>';
        return;
      }
      tbody.innerHTML = state.items.map(function (row) {
        var tds = cols.map(function (col) {
          var content;
          try {
            content = col.render ? col.render(row) : U.escText(row[col.key]);
          } catch (e) {
            content = '<span class="badge badge--red badge--sm">渲染错误</span>';
          }
          return '<td' + (col.className ? ' class="' + col.className + '"' : '') + '>' + content + '</td>';
        }).join('');
        var actionsCell = '';
        if (showActions) {
          var actions;
          if (cfg.rowActions) actions = cfg.rowActions(row, ctx);
          else {
            actions = '<div class="row-actions">' +
              UI.button({ label: '详情', act: 'detail', size: 'sm', data: { id: row[idKey] } });
            if (cfg.form && (!cfg.canEdit || cfg.canEdit(row))) {
              actions += UI.button({ label: '编辑', act: 'edit', size: 'sm', data: { id: row[idKey] } });
            }
            if (!cfg.canDelete || cfg.canDelete(row)) {
              actions += UI.button({ label: '删除', act: 'del', size: 'sm', kind: 'danger', data: { id: row[idKey] } });
            }
            actions += '</div>';
          }
          actionsCell = '<td class="cell--actions">' + actions + '</td>';
        }
        return '<tr class="' + (cfg.detail === false ? '' : 'clickable') + '" data-row-id="' + U.esc(row[idKey]) + '">' +
          tds + actionsCell + '</tr>';
      }).join('');
    }

    function renderPager() {
      var totalPages = Math.max(1, Math.ceil(state.total / state.pageSize) || 1);
      var pages = [];
      for (var p = 1; p <= totalPages; p++) {
        if (p === 1 || p === totalPages || Math.abs(p - state.page) <= 2) pages.push(p);
        else if (pages[pages.length - 1] !== '…') pages.push('…');
      }
      var btns = '';
      btns += '<button class="pager-btn" type="button" data-act="page" data-page="' + (state.page - 1) + '"' +
        (state.page <= 1 ? ' disabled' : '') + ' aria-label="上一页">‹</button>';
      pages.forEach(function (p) {
        if (p === '…') { btns += '<span class="pager-btn" aria-hidden="true" style="border:0;background:none;">…</span>'; return; }
        btns += '<button class="pager-btn' + (p === state.page ? ' active' : '') + '" type="button" ' +
          'data-act="page" data-page="' + p + '">' + p + '</button>';
      });
      btns += '<button class="pager-btn" type="button" data-act="page" data-page="' + (state.page + 1) + '"' +
        (state.page >= totalPages ? ' disabled' : '') + ' aria-label="下一页">›</button>';
      var sizes = [25, 50, 100, 200].map(function (s) {
        return '<option value="' + s + '"' + (s === state.pageSize ? ' selected' : '') + '>' + s + ' 条/页</option>';
      }).join('');
      pagerEl.innerHTML = '<span class="pager-info">共 ' + state.total + ' 条 · 第 ' + state.page + '/' + totalPages + ' 页</span>' +
        '<span class="pager-spacer"></span>' +
        '<span class="pager-btns">' + btns + '</span>' +
        '<select class="select pager-size" data-role="pagesize" aria-label="每页条数">' + sizes + '</select>';
    }

    async function load() {
      state.loading = true;
      state.error = null;
      renderRows();
      try {
        var params = {
          page: state.page,
          page_size: state.pageSize,
          q: state.q || undefined,
          sort: state.sort || undefined
        };
        Object.keys(state.filters).forEach(function (k) {
          if (state.filters[k] !== '' && state.filters[k] !== undefined && state.filters[k] !== null) params[k] = state.filters[k];
        });
        if (cfg.tabs && state.tab !== '' && state.tab !== undefined) params[cfg.tabs.param] = state.tab;
        if (cfg.fetchParams) {
          var extra = cfg.fetchParams(state);
          if (extra) Object.keys(extra).forEach(function (k) { if (extra[k] !== undefined) params[k] = extra[k]; });
        }
        var res = await CCGS.api.list(cfg.resource, params);
        state.items = res.items;
        state.total = res.total;
        state.pageSize = res.page_size || state.pageSize;
        if (res.page) state.page = res.page;
        state.loading = false;
        renderRows();
        renderPager();
        if (cfg.afterLoad) cfg.afterLoad(state, viewEl);
      } catch (err) {
        state.loading = false;
        state.error = err;
        renderRows();
        renderPager();
        if (err && err.status !== 0) UI.toast('error', '加载失败：' + UI.errorText(err));
      }
    }

    /* ---- 详情 ---- */
    function defaultDetailBody(row) {
      var keys = (cfg.detail && cfg.detail.keys) || null;
      var rows = [];
      if (keys) {
        keys.forEach(function (k) {
          var label = k;
          if (Array.isArray(k)) { label = k[0]; k = k[1]; }
          if (CCGS.schema && CCGS.schema.fieldLabel) label = CCGS.schema.fieldLabel(label);
          rows.push([label, UI.formatValue(row[k])]);
        });
      } else {
        Object.keys(row).forEach(function (k) {
          if (k.indexOf('_') === 0) return;
          rows.push([CCGS.schema && CCGS.schema.fieldLabel ? CCGS.schema.fieldLabel(k) : k, UI.formatValue(row[k])]);
        });
      }
      var html = UI.kv(rows);
      var blocks = (cfg.detail && cfg.detail.blocks) || [];
      blocks.forEach(function (b) {
        html += UI.detailBlock(b.label, row[b.key]);
      });
      return html;
    }

    function advanceTargets(row) {
      if (!cfg.advance || !CCGS.schema || !CCGS.schema.transitions) return [];
      var entityTrans = CCGS.schema.transitions[cfg.advance.entity || cfg.resource];
      if (!entityTrans) return [];
      var field = cfg.advance.field || 'status';
      var current = row[field];
      return entityTrans[current] || [];
    }

    function openDetailById(id) {
      var row = findItem(id);
      if (!row) { load(); return; }
      var dcfg = cfg.detail || {};
      var body = dcfg.body ? dcfg.body(row, ctx) : defaultDetailBody(row);
      var actions = [];
      if (cfg.advance) {
        advanceTargets(row).forEach(function (target) {
          actions.push({
            label: '推进为 ' + ((CCGS.schema && CCGS.schema.label) ? CCGS.schema.label(target) : target),
            kind: /REJECT|LOST|FAIL|CANCEL|TERMINAT|EXPIRED/.test(target) ? 'danger' : 'primary',
            onClick: function (h) { h.close(); advanceTo(row, target); }
          });
        });
      }
      if (cfg.form && (!cfg.canEdit || cfg.canEdit(row))) {
        actions.push({ label: '编辑', icon: 'edit', onClick: function (h) { h.close(); openEdit(row[idKey]); } });
      }
      if (dcfg.actions) {
        dcfg.actions(row, ctx).forEach(function (a) { actions.push(a); });
      }
      actions.push({ label: '关闭', onClick: function (h) { h.close(); } });
      var title = dcfg.title ? dcfg.title(row) : (cfg.singular || '记录') + '详情';
      UI.openModal({
        title: title,
        subtitle: 'ID ' + row[idKey] + (row.created_at ? ' · 创建于 ' + U.dateTime(row.created_at) : ''),
        size: dcfg.size || 'lg',
        body: body,
        actions: actions
      });
    }

    function advanceTo(row, target) {
      var field = (cfg.advance && cfg.advance.field) || 'status';
      var payload = {};
      payload[field] = target;
      CCGS.api.update(cfg.resource, row[idKey], payload).then(function () {
        UI.toast('success', '状态已推进为 ' + ((CCGS.schema && CCGS.schema.label) ? CCGS.schema.label(target) : target));
        load();
      }).catch(function (err) {
        UI.toast('error', UI.errorText(err), 8000);
      });
    }

    /* ---- 新建 / 编辑 / 删除 ---- */
    function openCreate() {
      if (!cfg.form) return;
      var values = {};
      (cfg.form.fields || []).forEach(function (f) {
        if (f.default !== undefined) values[f.key] = f.default;
        if (f.type === 'checks' && f.items) {
          f.items.forEach(function (it) { values[it.key] = it.default !== undefined ? it.default : 0; });
        }
      });
      if (cfg.create && cfg.create.defaults) Object.assign(values, cfg.create.defaults);
      UI.openForm({
        title: (cfg.create && cfg.create.title) || ('新建' + (cfg.singular || '')),
        subtitle: cfg.create && cfg.create.subtitle || '',
        fields: cfg.form.fields,
        values: values,
        wide: cfg.form.wide !== false,
        submitText: '创建',
        onSubmit: function (payloadValues) {
          var payload = cfg.form.buildPayload ? cfg.form.buildPayload(payloadValues, null) : payloadValues;
          return CCGS.api.create(cfg.resource, payload).then(function (item) {
            UI.toast('success', '已创建：' + rowTitle(item));
            state.page = 1;
            load();
          });
        }
      });
    }

    function openEdit(id) {
      var row = findItem(id);
      if (!row) { load(); return; }
      var values = {};
      (cfg.form.fields || []).forEach(function (f) {
        if (f.type === 'checks' && f.items) {
          f.items.forEach(function (it) { values[it.key] = row[it.key]; });
        } else if (f.type !== 'section') {
          values[f.key] = row[f.key];
        }
      });
      UI.openForm({
        title: (cfg.form.editTitle || ('编辑' + (cfg.singular || ''))),
        subtitle: rowTitle(row) + ' · ID ' + row[idKey],
        fields: cfg.form.fields,
        values: values,
        original: row,
        wide: cfg.form.wide !== false,
        submitText: '保存修改',
        onSubmit: function (payloadValues) {
          var payload = cfg.form.buildPayload ? cfg.form.buildPayload(payloadValues, row) : payloadValues;
          return CCGS.api.update(cfg.resource, id, payload).then(function () {
            UI.toast('success', '已保存修改');
            load();
          });
        }
      });
    }

    function confirmDelete(id) {
      var row = findItem(id);
      var title = rowTitle(row);
      UI.confirm({
        title: '删除确认',
        message: '确定删除「' + title + '」吗？该操作不可撤销。',
        warn: '删除会写入审计日志。若该记录被其他数据引用，后端会拒绝删除。',
        confirmText: '删除',
        danger: true
      }).then(function (r) {
        if (!r.ok) return;
        CCGS.api.remove(cfg.resource, id).then(function () {
          UI.toast('success', '已删除：' + title);
          load();
        }).catch(function (err) {
          UI.toast('error', UI.errorText(err), 8000);
        });
      });
    }

    function switchTab(tabValue) {
      state.tab = tabValue;
      state.page = 1;
      Array.prototype.forEach.call(viewEl.querySelectorAll('[data-act="tab"]'), function (b) {
        b.classList.toggle('active', String(b.getAttribute('data-tab')) === String(tabValue));
      });
      load();
    }

    var ctx = {
      reload: load,
      state: state,
      openDetail: openDetailById,
      openCreate: openCreate,
      openEdit: openEdit,
      viewEl: viewEl
    };

    /* ---- 事件绑定 ---- */
    viewEl.addEventListener('click', function (e) {
      var th = e.target.closest ? e.target.closest('th[data-sort]') : null;
      if (th) {
        var key = th.getAttribute('data-sort');
        if (!key) return;
        if (state.sort === key) state.sort = '-' + key;
        else if (state.sort === '-' + key) state.sort = key;
        else state.sort = key;
        state.page = 1;
        // 更新表头箭头
        Array.prototype.forEach.call(viewEl.querySelectorAll('th[data-sort]'), function (h) {
          var k = h.getAttribute('data-sort');
          h.classList.toggle('sorted', state.sort === k || state.sort === '-' + k);
          var arrow = h.querySelector('.th-sort');
          if (arrow) arrow.textContent = state.sort === k ? '▲' : state.sort === '-' + k ? '▼' : '↕';
        });
        load();
        return;
      }
      var actEl = e.target.closest ? e.target.closest('[data-act]') : null;
      if (actEl) {
        var act = actEl.getAttribute('data-act');
        if (cfg.onAction && cfg.onAction(act, actEl, ctx) === true) return;
        if (act === 'new') { openCreate(); return; }
        if (act === 'refresh' || act === 'retry') { load(); return; }
        if (act === 'page') {
          var p = Number(actEl.getAttribute('data-page'));
          if (p >= 1 && p !== state.page) { state.page = p; load(); }
          return;
        }
        if (act === 'tab') { switchTab(actEl.getAttribute('data-tab')); return; }
        var id = actEl.getAttribute('data-id');
        if (act === 'detail') { openDetailById(id); return; }
        if (act === 'edit') { openEdit(id); return; }
        if (act === 'del') { confirmDelete(id); return; }
        return;
      }
      if (e.target.closest && e.target.closest('a[href]')) return;
      var tr = e.target.closest ? e.target.closest('tr[data-row-id]') : null;
      if (tr && cfg.detail !== false) openDetailById(tr.getAttribute('data-row-id'));
    });

    viewEl.addEventListener('change', function (e) {
      var t = e.target;
      if (t.matches('[data-filter]')) {
        state.filters[t.getAttribute('data-filter')] = t.value;
        state.page = 1;
        load();
      } else if (t.matches('[data-role="pagesize"]')) {
        state.pageSize = Number(t.value) || 25;
        state.page = 1;
        load();
      }
    });

    if (qInput) {
      var doSearch = U.debounce(function () {
        state.q = qInput.value.trim();
        state.page = 1;
        load();
      }, 320);
      qInput.addEventListener('input', doSearch);
      qInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') { e.preventDefault(); state.q = qInput.value.trim(); state.page = 1; load(); }
      });
    }

    load();
    return ctx;
  };
})();
