/* CCGS 前端 · 模块 16 CSV 导入导出 / 17 数据备份 / 18 审计日志 */
var CCGS = window.CCGS || (window.CCGS = {});
(function () {
  'use strict';

  var U = CCGS.util, UI = CCGS.ui, API = CCGS.api, S = CCGS.schema;

  function esc(v) { return U.esc(v); }
  function iso(v) { return U.isEmpty(v) ? '—' : U.dateTime(v); }
  function txt(v) { return U.text(v, '—'); }
  function todayName() {
    var d = new Date();
    var m = ('0' + (d.getMonth() + 1)).slice(-2);
    var day = ('0' + d.getDate()).slice(-2);
    return String(d.getFullYear()) + m + day;
  }

  /* 可导出实体（SPEC_API §export 短名清单） */
  var EXPORT_ENTITIES = [
    { res: 'companies', label: '公司（供应商 / 需求方）' },
    { res: 'demands', label: '需求' },
    { res: 'supplies', label: 'GPU 供给资源' },
    { res: 'specs', label: '算力规格' },
    { res: 'evidence', label: '证据来源' },
    { res: 'supplier-verifications', label: '供应商核验' },
    { res: 'demand-qualifications', label: '需求资格核验' },
    { res: 'matches', label: '匹配记录' },
    { res: 'procurement-analyses', label: '采购分析' },
    { res: 'commercial-opportunities', label: '商机' },
    { res: 'quotes', label: '报价（DRAFT）' },
    { res: 'contracts', label: '合同元数据' },
    { res: 'agent-tasks', label: 'Agent 任务' },
    { res: 'knowledge', label: '知识库' },
    { res: 'approvals', label: '审批' }
  ];

  function entityLabel(res) {
    for (var i = 0; i < EXPORT_ENTITIES.length; i++) {
      if (EXPORT_ENTITIES[i].res === res) return EXPORT_ENTITIES[i].label;
    }
    return res;
  }

  /* ============================================================
   * 模块 16 · CSV 导入导出
   * ============================================================ */
  CCGS.views.data = {
    title: 'CSV 导入导出',
    subtitle: '按实体导出 UTF-8 BOM CSV；导入结果为本地操作，错误逐行报告',
    mount: function (root) {
      var opts = EXPORT_ENTITIES.map(function (e) {
        return '<option value="' + esc(e.res) + '">' + esc(e.label) + '（' + esc(e.res) + '）</option>';
      }).join('');

      root.innerHTML = '<div class="view">' +
        UI.tip('CSV 导出带 UTF-8 BOM，Excel 可直接打开；导入只写本地数据库并记录审计日志。' +
          '不得把手机号 / 邮箱 / 微信等敏感信息写入公开备注字段。') +
        '<div class="grid grid-2">' +
          '<section class="card"><div class="card-head"><div class="card-title">导出 CSV</div>' +
            '<div class="card-sub">文件名 &lt;entity&gt;-YYYYmmdd.csv</div></div>' +
            '<div class="card-body">' +
              '<div class="form-field"><label>选择实体</label>' +
                '<select class="select" id="ex-entity">' + opts + '</select>' +
                '<p class="help">导出只读快照，不修改数据；对外使用前需确认是否含内部信息。</p></div>' +
              '<div class="runner-actions">' +
                UI.button({ label: '导出 CSV', kind: 'primary', icon: 'download', id: 'btn-export' }) +
              '</div>' +
              '<p class="help" id="ex-hint" style="margin-top:8px"></p>' +
            '</div></section>' +
          '<section class="card"><div class="card-head"><div class="card-title">导入 CSV</div>' +
            '<div class="card-sub">upsert 依主键 id；缺 id 自动生成</div></div>' +
            '<div class="card-body">' +
              '<div class="form-field"><label>目标实体</label>' +
                '<select class="select" id="im-entity">' + opts + '</select></div>' +
              '<div class="form-field"><label>导入模式</label>' +
                '<div class="radio-row">' +
                  '<label class="radio-item checked"><input type="radio" name="im-mode" value="upsert" checked> <span>upsert（按 id 更新或插入）</span></label>' +
                  '<label class="radio-item"><input type="radio" name="im-mode" value="insert"> <span>insert（只插入，冲突跳过）</span></label>' +
                '</div>' +
                '<p class="help">未知字段会被忽略并报告；导入错误不会中断其余行。</p></div>' +
              '<div class="form-field"><label>CSV 文件</label>' +
                '<input type="file" class="file-input" id="im-file" accept=".csv,text/csv">' +
                '<p class="help">最大建议 5MB；表单字段名：file。</p></div>' +
              '<div class="runner-actions">' +
                UI.button({ label: '开始导入', kind: 'primary', icon: 'upload', id: 'btn-import' }) +
              '</div>' +
              '<div id="im-result"></div>' +
            '</div></section>' +
        '</div>' +
        '</div>';

      var el = {
        exEntity: U.byId('ex-entity'), exHint: U.byId('ex-hint'), btnExport: U.byId('btn-export'),
        imEntity: U.byId('im-entity'), imFile: U.byId('im-file'), btnImport: U.byId('btn-import'), result: U.byId('im-result')
      };

      el.exHint.textContent = '将导出 ' + entityLabel(el.exEntity.value) + '（' + el.exEntity.value + '）';

      UI.on(root, 'change', '#ex-entity', function () {
        el.exHint.textContent = '将导出 ' + entityLabel(el.exEntity.value) + '（' + el.exEntity.value + '）';
      });
      UI.on(root, 'change', 'input[name="im-mode"]', function (ev) {
        var items = root.querySelectorAll('.radio-item');
        for (var i = 0; i < items.length; i++) {
          var input = items[i].querySelector('input');
          items[i].classList.toggle('checked', !!(input && input.checked));
        }
      });

      UI.on(root, 'click', '#btn-export', function () {
        var entity = el.exEntity.value;
        var btn = el.btnExport;
        btn.disabled = true;
        el.exHint.textContent = '正在导出 ' + entityLabel(entity) + '…';
        API.exportCsv(entity, entity + '-' + todayName() + '.csv')
          .then(function () {
            el.exHint.textContent = '已触发下载：' + entity + '-' + todayName() + '.csv（UTF-8 BOM）';
            UI.toast('success', '导出已开始：' + entityLabel(entity));
          })
          .catch(function (err) {
            el.exHint.textContent = '导出失败：' + UI.errorText(err);
            UI.toast('error', UI.errorText(err), 8000);
          })
          .then(function () { btn.disabled = false; });
      });

      UI.on(root, 'click', '#btn-import', function () {
        var entity = el.imEntity.value;
        var modeBtn = root.querySelector('input[name="im-mode"]:checked');
        var mode = modeBtn ? modeBtn.value : 'upsert';
        var file = el.imFile.files && el.imFile.files[0];
        if (!file) {
          UI.toast('warn', '请先选择要导入的 CSV 文件。');
          return;
        }
        el.btnImport.disabled = true;
        el.result.innerHTML = '<div class="table-loading" style="margin-top:12px"><span class="spinner spinner--sm"></span> 正在导入 ' + esc(file.name) + '…</div>';
        API.importCsv(entity, mode, file)
          .then(function (res) {
            renderImportResult(res, entity, mode, file.name);
            UI.toast('success', '导入完成：新增 ' + (res.inserted || 0) + ' · 更新 ' + (res.updated || 0) + ' · 跳过 ' + (res.skipped || 0));
          })
          .catch(function (err) {
            el.result.innerHTML = '<div class="report-result"><div class="rr-head">导入失败</div>' +
              '<div class="rr-body">' + UI.errorText(err) + '</div></div>';
            UI.toast('error', UI.errorText(err), 8000);
          })
          .then(function () { el.btnImport.disabled = false; });
      });

      function renderImportResult(res, entity, mode, fileName) {
        res = res || {};
        var errors = Array.isArray(res.errors) ? res.errors : [];
        var warnings = Array.isArray(res.warnings) ? res.warnings : [];
        var nums = '<div class="result-nums">' +
          '<span class="result-num result-num--ok">新增<b>' + (res.inserted || 0) + '</b></span>' +
          '<span class="result-num">更新<b>' + (res.updated || 0) + '</b></span>' +
          '<span class="result-num result-num--warn">跳过<b>' + (res.skipped || 0) + '</b></span>' +
          '<span class="result-num' + (errors.length ? ' result-num--err' : '') + '">错误<b>' + errors.length + '</b></span>' +
          '</div>';
        var errTable = '';
        if (errors.length) {
          errTable = '<table class="error-table"><thead><tr><th style="width:80px">行号</th><th>错误</th></tr></thead><tbody>' +
            errors.map(function (e) {
              var row = e && (e.row !== undefined ? e.row : e.line);
              var msg = e && (e.error || e.message || (typeof e === 'string' ? e : JSON.stringify(e)));
              return '<tr><td>' + esc(row === undefined || row === null ? '—' : row) + '</td><td>' + esc(msg) + '</td></tr>';
            }).join('') + '</tbody></table>';
        } else {
          errTable = '<p class="help" style="color:var(--green)">无错误行。</p>';
        }
        var warnList = warnings.length
          ? '<ul class="warn-list">' + warnings.map(function (w) {
              return '<li>' + esc(typeof w === 'string' ? w : (w && (w.message || w.warning)) || JSON.stringify(w)) + '</li>';
            }).join('') + '</ul>'
          : '';
        el.result.innerHTML = '<div class="report-result"><div class="rr-head">导入结果 · ' +
          esc(entityLabel(entity)) + ' · ' + esc(mode) + ' · ' + esc(fileName) + '</div>' +
          '<div class="rr-body">' + nums + errTable + warnList +
          '<p class="help" style="margin-top:8px">导入已写入本地数据库与审计日志；请刷新对应模块核对数据。</p>' +
          '</div></div>';
      }

      return function () {};
    }
  };

  /* ============================================================
   * 模块 17 · 数据备份
   * ============================================================ */
  CCGS.views.backup = {
    title: '数据备份',
    subtitle: 'SQLite 备份 / 恢复；恢复必须输入 RESTORE，属高风险操作',
    mount: function (root) {
      root.innerHTML = '<div class="view">' +
        '<div class="backup-warn"><span>' + U.icon('alert', 18) + '</span>' +
          '<div><strong>恢复会覆盖当前数据库。</strong>恢复前系统会自动创建一份安全备份；' +
          '请务必在恢复前确认当前数据已备份。只有输入 RESTORE 才能执行恢复。</div></div>' +
        '<section class="card" style="margin-bottom:16px"><div class="card-head">' +
          '<div class="card-title">创建备份</div><div class="card-sub">写入 backups/ 目录并计算 SHA-256</div></div>' +
          '<div class="card-body"><div class="form-grid">' +
            '<div class="form-field form-field--span"><label>备份备注（可选）</label>' +
              '<input class="input" id="bk-note" type="text" placeholder="例如：导入数据前快照" maxlength="200"></div>' +
          '</div>' +
          '<div class="runner-actions">' +
            UI.button({ label: '创建备份', kind: 'primary', icon: 'database', id: 'btn-backup' }) +
            UI.button({ label: '刷新列表', size: 'sm', kind: 'ghost', icon: 'refresh', id: 'btn-backup-refresh' }) +
          '</div></div></section>' +
        '<section class="card" style="margin-bottom:16px"><div class="card-head">' +
          '<div class="card-title">备份列表</div><div class="card-sub">按时间倒序 · 本地文件</div></div>' +
          '<div class="card-body" id="bk-list"></div></section>' +
        '<section class="card"><div class="card-head"><div class="card-title">数据库健康</div>' +
          '<div class="card-sub">GET /api/health/db</div></div>' +
          '<div class="card-body" id="bk-health"></div></section>' +
        '</div>';

      var el = { note: U.byId('bk-note'), list: U.byId('bk-list'), health: U.byId('bk-health'), btn: U.byId('btn-backup') };
      var state = { items: [], loading: true, error: null };

      function renderList() {
        if (state.loading) { el.list.innerHTML = '<div class="table-loading"><span class="spinner spinner--sm"></span> 加载备份列表…</div>'; return; }
        if (state.error) {
          el.list.innerHTML = UI.errorState(state.error, true) +
            '<div style="margin-top:8px">' + UI.button({ label: '重试', size: 'sm', act: 'retry-backup', icon: 'refresh' }) + '</div>';
          return;
        }
        var items = state.items || [];
        if (!items.length) {
          el.list.innerHTML = UI.empty({ icon: 'database', title: '暂无备份', text: '点击「创建备份」生成第一份 SQLite 快照。' });
          return;
        }
        el.list.innerHTML = '<div class="table-wrap"><table class="data-table"><thead><tr>' +
          '<th>备份 ID</th><th>创建时间</th><th>大小</th><th>文件路径</th><th>SHA-256</th><th>备注</th><th class="cell--actions">操作</th>' +
          '</tr></thead><tbody>' + items.map(function (b) {
            var sha = txt(b.sha256);
            return '<tr>' +
              '<td class="cell--mono">' + esc(txt(b.id)) + '</td>' +
              '<td class="cell--mono">' + esc(iso(b.created_at)) + '</td>' +
              '<td class="cell--num">' + esc(b.size_bytes === undefined || b.size_bytes === null ? '—' : U.bytes(b.size_bytes)) + '</td>' +
              '<td class="cell--mono">' + esc(txt(b.file_path)) + '</td>' +
              '<td class="cell--mono" title="' + esc(sha) + '">' + esc(sha === '—' ? sha : sha.slice(0, 16) + '…') + '</td>' +
              '<td>' + esc(txt(b.note)) + '</td>' +
              '<td class="cell--actions"><div class="row-actions">' +
                UI.button({ label: '恢复', size: 'sm', kind: 'danger', act: 'restore-backup', data: { id: b.id } }) +
              '</div></td>' +
            '</tr>';
          }).join('') + '</tbody></table></div>' +
          '<p class="help" style="margin-top:8px">共 ' + items.length + ' 份备份；恢复操作会先自动创建安全备份。</p>';
      }

      function load() {
        state.loading = true; state.error = null; renderList();
        API.backups()
          .then(function (res) {
            state.items = (res && (res.items || res)) || [];
            if (!Array.isArray(state.items)) state.items = [];
            state.loading = false; renderList();
          })
          .catch(function (err) {
            state.loading = false; state.error = err; renderList();
            if (err && err.status !== 0) UI.toast('warn', UI.errorText(err), 5200);
          });
      }

      function loadHealth() {
        el.health.innerHTML = '<div class="table-loading"><span class="spinner spinner--sm"></span> 检查数据库…</div>';
        API.healthDb()
          .then(function (doc) {
            doc = doc || {};
            var tags = [];
            if (doc.tables && typeof doc.tables === 'object' && !Array.isArray(doc.tables)) {
              Object.keys(doc.tables).forEach(function (t) {
                tags.push('<span class="tag">' + esc(t) + ' · ' + esc(String(doc.tables[t])) + '</span>');
              });
            } else if (typeof doc.tables === 'number') {
              tags.push('<span class="tag">表数量 · ' + esc(String(doc.tables)) + '</span>');
            }
            ['db', 'integrity', 'status', 'size_bytes', 'journal_mode'].forEach(function (k) {
              if (doc[k] !== undefined && doc[k] !== null && typeof doc[k] !== 'object') {
                tags.push('<span class="tag">' + esc(k) + ' · ' + esc(String(doc[k])) + '</span>');
              }
            });
            el.health.innerHTML = (tags.length ? '<div class="healthdb">' + tags.join('') + '</div>' : '') +
              '<details style="margin-top:6px"><summary class="small muted" style="cursor:pointer">原始响应</summary>' +
              UI.prettyJson(doc) + '</details>';
          })
          .catch(function (err) {
            el.health.innerHTML = UI.errorState(err, true) +
              '<div style="margin-top:8px">' + UI.button({ label: '重试', size: 'sm', act: 'retry-health', icon: 'refresh' }) + '</div>';
          });
      }

      function afterCreate(res) {
        res = res || {};
        var body = UI.kv([
          ['备份 ID', esc(txt(res.id))],
          ['文件路径', esc(txt(res.file_path))],
          ['大小', esc(res.size_bytes === undefined ? '—' : U.bytes(res.size_bytes))],
          ['SHA-256', '<span class="cell--mono">' + esc(txt(res.sha256)) + '</span>']
        ]) + '<p class="help" style="margin-top:10px">备份文件只保存在本地磁盘，不会上传或外发。</p>';
        UI.openModal({
          title: '备份已创建',
          size: 'sm',
          body: body,
          actions: [{ label: '关闭', onClick: function (h) { h.close(); } }]
        });
        load();
      }

      UI.on(root, 'click', '#btn-backup', function () {
        var btn = el.btn;
        btn.disabled = true;
        API.backupCreate(el.note.value.trim())
          .then(function (res) { afterCreate(res); el.note.value = ''; })
          .catch(function (err) { UI.toast('error', UI.errorText(err), 8000); })
          .then(function () { btn.disabled = false; });
      });
      UI.on(root, 'click', '#btn-backup-refresh', function () { load(); });
      UI.on(root, 'click', '[data-act="retry-health"]', function () { loadHealth(); });

      UI.on(root, 'click', '[data-act="restore-backup"]', function (ev) {
        var btn = ev.target.closest('[data-act="restore-backup"]');
        if (!btn || btn.disabled) return;
        var id = btn.getAttribute('data-id');
        var item = null;
        state.items.forEach(function (b) { if (String(b.id) === String(id)) item = b; });
        UI.confirm({
          title: '恢复数据库（高风险）',
          message: '将用备份「' + txt(id) + '」（' + (item ? iso(item.created_at) : '—') + '）覆盖当前数据库。',
          warn: '恢复会覆盖现有全部数据；系统会先自动创建一份安全备份。该操作不可撤销，请确认后再继续。',
          danger: true,
          requireText: 'RESTORE',
          note: true,
          noteLabel: '恢复原因（建议填写）',
          notePlaceholder: '例如：导入失败后回滚',
          confirmText: '执行恢复',
          cancelText: '取消'
        }).then(function (r) {
          if (!r.ok) return;
          btn.disabled = true;
          API.backupRestore(id)
            .then(function (res) {
              res = res || {};
              var body = UI.kv([
                ['恢复结果', res.restored ? '<span class="badge badge--green badge--sm">已恢复</span>' : esc(txt(res.restored))],
                ['安全备份', esc(txt(res.safety_backup))]
              ]) + '<p class="help" style="margin-top:10px">恢复完成；建议刷新页面并核对待审批、匹配与审计记录。</p>';
              UI.openModal({
                title: '数据库已恢复',
                size: 'sm',
                body: body,
                actions: [{
                  label: '刷新页面', kind: 'primary', onClick: function (h) { h.close(); location.reload(); }
                }, { label: '关闭', onClick: function (h) { h.close(); } }]
              });
              load();
            })
            .catch(function (err) { UI.toast('error', UI.errorText(err), 9000); })
            .then(function () { btn.disabled = false; });
        });
      });
      UI.on(root, 'click', '[data-act="retry-backup"]', function () { load(); });

      load();
      loadHealth();
      return function () {};
    }
  };

  /* ============================================================
   * 模块 18 · 审计日志（只读）
   * ============================================================ */
  CCGS.views.audit = {
    title: '审计日志',
    subtitle: '只读 · 按时间倒序 · 可按实体 / 动作筛选',
    mount: function (root) {
      root.innerHTML = '<div class="view">' +
        UI.tip('审计日志为 append-only 只读记录，任何页面都不提供修改或删除入口。' +
          '当前加载最近 200 条，筛选与搜索在本地进行。') +
        '<section class="card"><div class="card-head"><div class="card-title">审计日志</div>' +
          '<div class="card-sub" id="au-sub">加载中…</div>' +
          '<div class="card-actions">' + UI.button({ label: '刷新', size: 'sm', kind: 'ghost', icon: 'refresh', act: 'refresh-audit' }) + '</div></div>' +
          '<div class="toolbar">' +
            '<label class="search-field">' + U.icon('search', 15) +
              '<input type="search" id="au-q" placeholder="搜索操作者 / 备注 / 实体 ID…" autocomplete="off"></label>' +
            '<label class="filter-label">实体</label>' +
            '<select class="select select--filter" id="au-entity"><option value="">全部实体</option></select>' +
            '<label class="filter-label">动作</label>' +
            '<select class="select select--filter" id="au-action"><option value="">全部动作</option></select>' +
            '<span class="toolbar-spacer"></span>' +
            '<span class="small muted" id="au-count"></span>' +
          '</div>' +
          '<div class="card-body" id="au-table"></div></section>' +
        '</div>';

      var el = {
        sub: U.byId('au-sub'), q: U.byId('au-q'), entity: U.byId('au-entity'),
        action: U.byId('au-action'), table: U.byId('au-table'), count: U.byId('au-count')
      };
      var state = { items: [], loading: true, error: null };

      function actionKind(a) {
        var s = String(a || '').toUpperCase();
        if (/DELETE|REJECT|FAIL|CANCEL|LOST|RESTORE/.test(s)) return 'red';
        if (/CREATE|APPROVE|IMPORT|BUILD|DONE|SUCCESS/.test(s)) return 'green';
        return 'blue';
      }

      function renderOptions() {
        var ents = {}, acts = {};
        state.items.forEach(function (r) {
          if (r.entity) ents[r.entity] = true;
          if (r.action) acts[r.action] = true;
        });
        var curE = el.entity.value, curA = el.action.value;
        el.entity.innerHTML = '<option value="">全部实体</option>' + Object.keys(ents).sort().map(function (e) {
          return '<option value="' + esc(e) + '"' + (curE === e ? ' selected' : '') + '>' + esc(e) + '</option>';
        }).join('');
        el.action.innerHTML = '<option value="">全部动作</option>' + Object.keys(acts).sort().map(function (a) {
          return '<option value="' + esc(a) + '"' + (curA === a ? ' selected' : '') + '>' + esc(a) + '</option>';
        }).join('');
      }

      function filtered() {
        var q = (el.q.value || '').trim().toLowerCase();
        var ent = el.entity.value, act = el.action.value;
        return state.items.filter(function (r) {
          if (ent && r.entity !== ent) return false;
          if (act && r.action !== act) return false;
          if (!q) return true;
          return [r.actor, r.action, r.entity, r.entity_id, r.note, r.before_json, r.after_json]
            .map(function (x) { return String(x === null || x === undefined ? '' : x).toLowerCase(); })
            .join(' ').indexOf(q) >= 0;
        });
      }

      function renderTable() {
        if (state.loading) { el.table.innerHTML = '<div class="table-loading"><span class="spinner spinner--sm"></span> 加载审计日志…</div>'; return; }
        if (state.error) {
          el.table.innerHTML = UI.errorState(state.error, true) +
            '<div style="margin-top:8px">' + UI.button({ label: '重试', size: 'sm', act: 'retry-audit', icon: 'refresh' }) + '</div>';
          return;
        }
        var list = filtered();
        el.count.textContent = '显示 ' + list.length + ' / 共 ' + state.items.length + ' 条';
        if (!list.length) {
          el.table.innerHTML = UI.empty({
            icon: 'file',
            title: '没有匹配的审计记录',
            text: '调整筛选条件或搜索关键词；若列表为空，说明还没有写操作产生日志。'
          });
          return;
        }
        el.table.innerHTML = '<div class="table-wrap"><table class="data-table"><thead><tr>' +
          '<th>时间</th><th>操作者</th><th>动作</th><th>实体</th><th>实体 ID</th><th>备注</th><th class="cell--actions">操作</th>' +
          '</tr></thead><tbody>' + list.map(function (r) {
            return '<tr>' +
              '<td class="cell--mono">' + esc(iso(r.ts)) + '</td>' +
              '<td>' + esc(txt(r.actor)) + '</td>' +
              '<td>' + UI.badge(r.action, actionKind(r.action), { sm: true }) + '</td>' +
              '<td class="cell--mono">' + esc(txt(r.entity)) + '</td>' +
              '<td class="cell--id">' + esc(txt(r.entity_id)) + '</td>' +
              '<td>' + esc(txt(r.note)) + '</td>' +
              '<td class="cell--actions"><div class="row-actions">' +
                UI.button({ label: '详情', size: 'sm', act: 'audit-detail', data: { idx: state.items.indexOf(r) } }) +
              '</div></td>' +
            '</tr>';
          }).join('') + '</tbody></table></div>';
      }

      function openDetail(r) {
        var body = UI.kv([
          ['时间', esc(iso(r.ts))],
          ['操作者', esc(txt(r.actor))],
          ['动作', UI.badge(r.action, actionKind(r.action), { sm: true })],
          ['实体', esc(txt(r.entity))],
          ['实体 ID', esc(txt(r.entity_id))],
          ['IP', esc(txt(r.ip))],
          ['备注', esc(txt(r.note))]
        ]) +
          UI.detailBlock('变更前 before_json', r.before_json) +
          UI.detailBlock('变更后 after_json', r.after_json);
        UI.openModal({
          title: '审计日志详情',
          size: 'lg',
          body: body,
          actions: [{ label: '关闭', onClick: function (h) { h.close(); } }]
        });
      }

      function load() {
        state.loading = true; state.error = null; renderTable();
        API.list('audit-logs', { page_size: 200, sort: '-ts' })
          .then(function (res) {
            state.items = (res && res.items) || [];
            state.loading = false;
            el.sub.textContent = '最近 ' + state.items.length + ' 条 · append-only 只读';
            renderOptions(); renderTable();
          })
          .catch(function (err) {
            state.loading = false; state.error = err; renderTable();
            if (err && err.status !== 0) UI.toast('warn', UI.errorText(err), 5200);
          });
      }

      UI.on(root, 'input', '#au-q', function () { renderTable(); });
      UI.on(root, 'change', '#au-entity', function () { renderTable(); });
      UI.on(root, 'change', '#au-action', function () { renderTable(); });
      UI.on(root, 'click', '[data-act="refresh-audit"], [data-act="retry-audit"]', function () { load(); });
      UI.on(root, 'click', '[data-act="audit-detail"]', function (ev) {
        var btn = ev.target.closest('[data-act="audit-detail"]');
        if (!btn) return;
        var idx = Number(btn.getAttribute('data-idx'));
        if (!isNaN(idx) && state.items[idx]) openDetail(state.items[idx]);
      });

      load();
      return function () {};
    }
  };
})();
