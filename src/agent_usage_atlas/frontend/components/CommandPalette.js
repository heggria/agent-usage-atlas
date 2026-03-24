/* ── Command Palette (Cmd+K / Ctrl+K) ── */

/* ── Command registry with categories ── */
const _CP_CAT_SECTIONS = 'sections';
const _CP_CAT_ACTIONS  = 'actions';
const _CP_CAT_CHARTS   = 'charts';

const _CP_CAT_LABELS = {
  [_CP_CAT_SECTIONS]: {en: 'Sections', zh: '区块导航'},
  [_CP_CAT_ACTIONS]:  {en: 'Actions',  zh: '操作'},
  [_CP_CAT_CHARTS]:   {en: 'Charts',   zh: '图表'},
};

const _CP_COMMANDS = [
  /* ── Section navigation ── */
  {cat: _CP_CAT_SECTIONS, label: 'Jump to Sources',            labelZh: '跳转到 Sources',           icon: 'fa-layer-group',       sub: 'Section 1', subZh: '区块 1', action: () => _cpGoSection('sec-sources')},
  {cat: _CP_CAT_SECTIONS, label: 'Jump to Cost & Tokens',      labelZh: '跳转到花费与 Token',        icon: 'fa-dollar-sign',       sub: 'Section 2', subZh: '区块 2', action: () => _cpGoSection('sec-cost-tokens')},
  {cat: _CP_CAT_SECTIONS, label: 'Jump to Activity & Sessions', labelZh: '跳转到活跃与会话',         icon: 'fa-clock',             sub: 'Section 3', subZh: '区块 3', action: () => _cpGoSection('sec-activity')},
  {cat: _CP_CAT_SECTIONS, label: 'Jump to Tooling & Projects', labelZh: '跳转到工具与项目',        icon: 'fa-wrench',            sub: 'Section 4', subZh: '区块 4', action: () => _cpGoSection('sec-tooling')},
  {cat: _CP_CAT_SECTIONS, label: 'Jump to Insights & Prompts', labelZh: '跳转到 Insights',          icon: 'fa-lightbulb',         sub: 'Section 5', subZh: '区块 5', action: () => _cpGoSection('sec-insights')},
  {cat: _CP_CAT_SECTIONS, label: 'Jump to Session Leaderboard', labelZh: '跳转到排行榜',             icon: 'fa-list-ol',           sub: 'Section 6', subZh: '区块 6', action: () => _cpGoSection('sec-leaderboard')},
  {cat: _CP_CAT_SECTIONS, label: 'Back to Top',                labelZh: '返回顶部',                icon: 'fa-arrow-up',          action: () => window.scrollTo({top: 0, behavior: 'smooth'})},

  /* ── Theme, language & range ── */
  {cat: _CP_CAT_ACTIONS, label: 'Toggle Theme',             labelZh: '切换主题',                icon: 'fa-circle-half-stroke', sub: 'Dark / Light', subZh: '深色 / 浅色', action: () => { toggleTheme(); }},
  {cat: _CP_CAT_ACTIONS, label: 'Toggle Language',           labelZh: '切换语言',                icon: 'fa-globe',             sub: 'ZH / EN', subZh: '中 / 英', action: () => { toggleLang(); }},
  {cat: _CP_CAT_ACTIONS, label: 'Show Keyboard Shortcuts',   labelZh: '显示快捷键',              icon: 'fa-keyboard',          sub: 'Press ?', subZh: '按 ?', action: () => { if (typeof _kbdToggleHelp === 'function') _kbdToggleHelp(); }},
  {cat: _CP_CAT_ACTIONS, label: 'Export Data',               labelZh: '导出数据',                icon: 'fa-download',          sub: 'JSON / CSV', subZh: 'JSON / CSV', action: () => { /* placeholder — triggers download if available */ const a = document.querySelector('[data-export]'); if (a) a.click(); }},

  /* ── Range switching ── */
  {cat: _CP_CAT_ACTIONS, label: 'Switch to Today',          labelZh: '切换到今日',              icon: 'fa-calendar-day',      action: () => { if (typeof switchRange === 'function') switchRange('today'); }},
  {cat: _CP_CAT_ACTIONS, label: 'Switch to Last 3 Days',    labelZh: '切换到近 3 天',           icon: 'fa-calendar-week',     action: () => { if (typeof switchRange === 'function') switchRange('3day'); }},
  {cat: _CP_CAT_ACTIONS, label: 'Switch to Last 7 Days',    labelZh: '切换到近 7 天',           icon: 'fa-calendar-week',     action: () => { if (typeof switchRange === 'function') switchRange('week'); }},
  {cat: _CP_CAT_ACTIONS, label: 'Switch to All Time',       labelZh: '切换到全部',              icon: 'fa-calendar',          action: () => { if (typeof switchRange === 'function') switchRange('all'); }},

  /* ── Chart shortcuts ── */
  {cat: _CP_CAT_CHARTS, label: 'Daily Cost Trend',           labelZh: '每日花费趋势',             icon: 'fa-chart-line',        sub: 'Cost & Tokens', subZh: '花费与 Token', action: () => _cpGoChart('daily-cost-chart')},
  {cat: _CP_CAT_CHARTS, label: 'Cost Breakdown',             labelZh: '花费结构拆解',             icon: 'fa-chart-pie',         sub: 'Cost & Tokens', subZh: '花费与 Token', action: () => _cpGoChart('cost-breakdown-chart')},
  {cat: _CP_CAT_CHARTS, label: 'Model Cost Ranking',         labelZh: '模型花费排行',             icon: 'fa-ranking-star',      sub: 'Cost & Tokens', subZh: '花费与 Token', action: () => _cpGoChart('model-cost-chart')},
  {cat: _CP_CAT_CHARTS, label: 'Activity Heatmap',           labelZh: '活跃热力图',               icon: 'fa-fire',              sub: 'Activity', subZh: '活跃', action: () => _cpGoChart('heatmap-chart')},
  {cat: _CP_CAT_CHARTS, label: 'Session Bubble Chart',       labelZh: '会话气泡图',               icon: 'fa-circle-nodes',      sub: 'Activity', subZh: '活跃', action: () => _cpGoChart('bubble-chart')},
  {cat: _CP_CAT_CHARTS, label: 'Tool Ranking',               labelZh: '工具排行',                 icon: 'fa-screwdriver-wrench',sub: 'Tooling', subZh: '工具', action: () => _cpGoChart('tool-ranking-chart')},
  {cat: _CP_CAT_CHARTS, label: 'Tool Bigram Chord',          labelZh: '工具跳转弦图',             icon: 'fa-diagram-project',   sub: 'Tooling', subZh: '工具', action: () => _cpGoChart('tool-bigram-chart')},
  {cat: _CP_CAT_CHARTS, label: 'Project Ranking',            labelZh: '项目排行',                 icon: 'fa-folder-open',       sub: 'Tooling', subZh: '工具', action: () => _cpGoChart('project-ranking-chart')},
  {cat: _CP_CAT_CHARTS, label: 'Efficiency Gauges',          labelZh: '效率仪表盘',               icon: 'fa-gauge-high',        sub: 'Cost & Tokens', subZh: '花费与 Token', action: () => _cpGoChart('cache-gauge')},
  {cat: _CP_CAT_CHARTS, label: 'Token Burn Curve',           labelZh: 'Token 燃烧曲线',           icon: 'fa-fire-flame-curved', sub: 'Cost & Tokens', subZh: '花费与 Token', action: () => _cpGoChart('token-burn-chart')},
  {cat: _CP_CAT_CHARTS, label: 'Productivity Score',         labelZh: '生产力评分',               icon: 'fa-trophy',            sub: 'Tooling', subZh: '工具', action: () => _cpGoChart('productivity-chart')},
  {cat: _CP_CAT_CHARTS, label: 'Burn Rate Projection',       labelZh: '消耗速率投影',             icon: 'fa-chart-area',        sub: 'Tooling', subZh: '工具', action: () => _cpGoChart('burn-rate-chart')},
];

let _cpVisible = false;
let _cpSelectedIdx = 0;
let _cpFiltered = [];
let _cpQuery = '';
let _cpDebounceTimer = null;
let _cpPanel = null;
let _cpOverlay = null;
let _cpPrevFocus = null;

function _cpGoSection(sectionId) {
  const divEl = document.getElementById(sectionId);
  if (!divEl) return;
  const wrap = document.querySelector('.section-wrap[data-section="' + sectionId + '"]');
  if (wrap && wrap.classList.contains('collapsed')) {
    expandSection(divEl, wrap);
    if (typeof _collapseState !== 'undefined') {
      _collapseState[sectionId] = false;
      _saveCollapsed(_collapseState);
    }
  }
  divEl.scrollIntoView({behavior: 'smooth'});
}

function _cpGoChart(chartId) {
  const el = document.getElementById(chartId);
  if (!el) return;
  /* Expand parent section if collapsed */
  const sectionWrap = el.closest('.section-wrap');
  if (sectionWrap && sectionWrap.classList.contains('collapsed')) {
    const sectionId = sectionWrap.dataset.section;
    const divEl = document.getElementById(sectionId);
    if (divEl) {
      expandSection(divEl, sectionWrap);
      if (typeof _collapseState !== 'undefined') {
        _collapseState[sectionId] = false;
        _saveCollapsed(_collapseState);
      }
    }
  }
  /* Expand parent show-more if collapsed */
  const moreEl = el.closest('.section-more');
  if (moreEl && !moreEl.classList.contains('expanded')) {
    const btn = document.querySelector('.show-more-btn[data-more="' + moreEl.id + '"]');
    if (btn) btn.click();
  }
  setTimeout(() => el.scrollIntoView({behavior: 'smooth', block: 'center'}), 120);
}

function _cpGetLabel(cmd) {
  return (typeof lang !== 'undefined' && lang === 'zh') ? cmd.labelZh : cmd.label;
}

function _cpGetSub(cmd) {
  if (!cmd.sub) return '';
  return (typeof lang !== 'undefined' && lang === 'zh') ? (cmd.subZh || cmd.sub) : cmd.sub;
}

function _cpGetCatLabel(cat) {
  const entry = _CP_CAT_LABELS[cat];
  if (!entry) return cat;
  return (typeof lang !== 'undefined' && lang === 'zh') ? entry.zh : entry.en;
}

function _cpScore(text, query) {
  const lower = text.toLowerCase();
  const q = query.toLowerCase();
  const idx = lower.indexOf(q);
  if (idx === -1) return -1;
  /* Earlier match = higher score; exact start = best */
  return 1000 - idx;
}

function _cpFilter(query) {
  _cpQuery = query;
  if (!query) {
    _cpFiltered = _CP_COMMANDS.slice();
    return;
  }
  const scored = [];
  for (let i = 0; i < _CP_COMMANDS.length; i++) {
    const cmd = _CP_COMMANDS[i];
    const sEn = _cpScore(cmd.label, query);
    const sZh = _cpScore(cmd.labelZh, query);
    const sSub = cmd.sub ? _cpScore(cmd.sub, query) : -1;
    const sSubZh = cmd.subZh ? _cpScore(cmd.subZh, query) : -1;
    const best = Math.max(sEn, sZh, sSub, sSubZh);
    if (best > 0) scored.push({cmd, score: best});
  }
  scored.sort((a, b) => b.score - a.score);
  _cpFiltered = scored.map(s => s.cmd);
}

function _cpHighlight(text, query) {
  if (!query) return _escHtml(text);
  const lower = text.toLowerCase();
  const q = query.toLowerCase();
  const idx = lower.indexOf(q);
  if (idx === -1) return _escHtml(text);
  const before = text.slice(0, idx);
  const match = text.slice(idx, idx + q.length);
  const after = text.slice(idx + q.length);
  return _escHtml(before) + '<strong style="color:rgba(255,255,255,.95);font-weight:600;">' + _escHtml(match) + '</strong>' + _escHtml(after);
}

function _cpRenderList() {
  const list = document.getElementById('cp-list');
  if (!list) return;

  if (_cpFiltered.length === 0) {
    const noResultsQuery = _escHtml(_cpQuery || '');
    const isZh = typeof lang !== 'undefined' && lang === 'zh';
    const msg = noResultsQuery
      ? (isZh ? '未找到 "' + noResultsQuery + '" 相关结果' : 'No results for "' + noResultsQuery + '"')
      : (isZh ? '无结果' : 'No results');
    list.innerHTML = '<div class="cp-empty">'
      + '<i class="fa-solid fa-magnifying-glass cp-empty-icon"></i>'
      + '<span>' + msg + '</span>'
      + '</div>';
    return;
  }

  if (_cpSelectedIdx >= _cpFiltered.length) _cpSelectedIdx = _cpFiltered.length - 1;
  if (_cpSelectedIdx < 0) _cpSelectedIdx = 0;

  /* Group by category */
  let lastCat = null;
  const parts = [];
  for (let i = 0; i < _cpFiltered.length; i++) {
    const cmd = _cpFiltered[i];
    const cat = cmd.cat || '';
    if (cat !== lastCat) {
      parts.push('<div class="cp-cat-header">' + _escHtml(_cpGetCatLabel(cat)) + '</div>');
      lastCat = cat;
    }
    const active = i === _cpSelectedIdx;
    const lbl = _cpHighlight(_cpGetLabel(cmd), _cpQuery);
    const sub = _cpGetSub(cmd);
    parts.push(
      '<div class="cp-item' + (active ? ' cp-active' : '') + '" data-idx="' + i + '">'
      + '<i class="fa-solid ' + _escHtml(cmd.icon) + ' cp-item-icon"></i>'
      + '<div class="cp-item-text">'
      + '<span class="cp-item-label">' + lbl + '</span>'
      + (sub ? '<span class="cp-item-sub">' + _escHtml(sub) + '</span>' : '')
      + '</div>'
      + (active ? '<kbd class="cp-item-hint">Enter</kbd>' : '')
      + '</div>'
    );
  }
  list.innerHTML = parts.join('');
}

function _cpExecute(idx) {
  if (idx < 0 || idx >= _cpFiltered.length) return;
  const cmd = _cpFiltered[idx];
  closePalette();
  cmd.action();
}

function openPalette() {
  if (!_cpOverlay) return;
  _cpPrevFocus = document.activeElement;
  _cpVisible = true;
  _cpSelectedIdx = 0;
  _cpQuery = '';
  _cpFilter('');
  _cpRenderList();
  _cpOverlay.style.display = 'flex';
  /* Trigger open animation in the next frame */
  requestAnimationFrame(() => {
    _cpOverlay.classList.add('cp-open');
    const input = document.getElementById('cp-input');
    if (input) { input.value = ''; input.focus(); }
  });
}

function closePalette() {
  if (!_cpOverlay) return;
  _cpVisible = false;
  _cpOverlay.classList.remove('cp-open');
  _cpOverlay.classList.add('cp-closing');
  const prevFocus = _cpPrevFocus;
  _cpPrevFocus = null;
  setTimeout(() => {
    if (_cpOverlay) {
      _cpOverlay.classList.remove('cp-closing');
      _cpOverlay.style.display = 'none';
    }
    if (prevFocus && typeof prevFocus.focus === 'function') {
      prevFocus.focus();
    }
  }, 120);
}

function initCommandPalette() {
  /* ── Inject styles ── */
  const style = document.createElement('style');
  style.textContent = [
    /* Overlay */
    '#cp-overlay{position:fixed;inset:0;z-index:9999;display:none;',
    'align-items:flex-start;justify-content:center;padding-top:min(20vh,160px);',
    'background:rgba(0,0,0,0);backdrop-filter:blur(0px);-webkit-backdrop-filter:blur(0px);',
    'transition:background .15s ease,backdrop-filter .15s ease,-webkit-backdrop-filter .15s ease;}',

    '#cp-overlay.cp-open{background:rgba(0,0,0,.5);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);}',
    '#cp-overlay.cp-closing{background:rgba(0,0,0,0);backdrop-filter:blur(0px);-webkit-backdrop-filter:blur(0px);}',

    /* Panel */
    '.cp-panel{width:min(560px,calc(100vw - 32px));max-height:460px;display:flex;flex-direction:column;',
    'border-radius:16px;overflow:hidden;',
    'background:rgba(22,24,35,.88);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);',
    'border:1px solid rgba(255,255,255,.1);box-shadow:0 24px 80px rgba(0,0,0,.55),0 0 0 1px rgba(255,255,255,.05);',
    'transform:scale(.95);opacity:0;transition:transform .15s cubic-bezier(.2,.9,.3,1),opacity .15s ease;}',

    '#cp-overlay.cp-open .cp-panel{transform:scale(1);opacity:1;}',
    '#cp-overlay.cp-closing .cp-panel{transform:scale(.97);opacity:0;transition:transform .1s ease,opacity .1s ease;}',

    /* Input area */
    '.cp-input-wrap{display:flex;align-items:center;gap:12px;padding:16px 18px;',
    'border-bottom:1px solid rgba(255,255,255,.08);}',

    '.cp-search-icon{color:rgba(255,255,255,.35);font-size:16px;flex-shrink:0;}',

    '#cp-input{flex:1;background:none;border:none;outline:none;color:#fff;font-size:16px;',
    'font-family:inherit;caret-color:rgba(99,102,241,.9);letter-spacing:-.2px;}',
    '#cp-input::placeholder{color:rgba(255,255,255,.3);font-weight:400;}',

    '.cp-esc-kbd{font-size:11px;padding:3px 7px;border-radius:5px;flex-shrink:0;',
    'background:rgba(255,255,255,.08);color:rgba(255,255,255,.35);border:1px solid rgba(255,255,255,.1);',
    'font-family:inherit;line-height:1;}',

    /* Result list */
    '#cp-list{overflow-y:auto;padding:4px 0;flex:1;scroll-behavior:smooth;}',
    '#cp-list::-webkit-scrollbar{width:5px;}',
    '#cp-list::-webkit-scrollbar-thumb{background:rgba(255,255,255,.1);border-radius:3px;}',

    /* Category headers */
    '.cp-cat-header{padding:8px 20px 4px;font-size:11px;font-weight:600;text-transform:uppercase;',
    'letter-spacing:.6px;color:rgba(255,255,255,.3);user-select:none;}',

    /* Result items */
    '.cp-item{display:flex;align-items:center;gap:12px;padding:9px 18px;cursor:pointer;min-height:44px;',
    'border-radius:8px;margin:1px 8px;transition:background .08s ease;}',
    '.cp-item:hover{background:rgba(255,255,255,.06);}',
    '.cp-item.cp-active{background:rgba(99,102,241,.25);}',
    '.cp-item.cp-active:hover{background:rgba(99,102,241,.3);}',

    '.cp-item-icon{width:20px;text-align:center;opacity:.55;font-size:13px;flex-shrink:0;color:rgba(255,255,255,.7);}',
    '.cp-active .cp-item-icon{opacity:.85;color:rgba(165,180,252,.9);}',

    '.cp-item-text{flex:1;min-width:0;display:flex;align-items:baseline;gap:8px;}',
    '.cp-item-label{font-size:14px;color:rgba(255,255,255,.82);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}',
    '.cp-active .cp-item-label{color:rgba(255,255,255,.95);}',
    '.cp-item-sub{font-size:12px;color:rgba(255,255,255,.28);white-space:nowrap;flex-shrink:0;}',
    '.cp-active .cp-item-sub{color:rgba(165,180,252,.5);}',

    '.cp-item-hint{font-size:10px;padding:2px 6px;border-radius:4px;flex-shrink:0;',
    'background:rgba(99,102,241,.2);color:rgba(165,180,252,.7);border:1px solid rgba(99,102,241,.25);',
    'font-family:inherit;line-height:1;}',

    /* Empty state */
    '.cp-empty{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;',
    'padding:32px 16px;color:rgba(255,255,255,.3);font-size:13px;}',
    '.cp-empty-icon{font-size:24px;opacity:.4;margin-bottom:4px;}',

    /* Light theme overrides */
    '[data-theme="light"] .cp-panel{background:rgba(255,255,255,.92);border-color:rgba(0,0,0,.1);',
    'box-shadow:0 24px 80px rgba(0,0,0,.18),0 0 0 1px rgba(0,0,0,.06);}',
    '[data-theme="light"] #cp-overlay.cp-open{background:rgba(0,0,0,.25);}',
    '[data-theme="light"] .cp-input-wrap{border-bottom-color:rgba(0,0,0,.08);}',
    '[data-theme="light"] .cp-search-icon{color:rgba(0,0,0,.3);}',
    '[data-theme="light"] #cp-input{color:rgba(0,0,0,.85);}',
    '[data-theme="light"] #cp-input::placeholder{color:rgba(0,0,0,.3);}',
    '[data-theme="light"] .cp-esc-kbd{background:rgba(0,0,0,.06);color:rgba(0,0,0,.35);border-color:rgba(0,0,0,.1);}',
    '[data-theme="light"] .cp-cat-header{color:rgba(0,0,0,.35);}',
    '[data-theme="light"] .cp-item:hover{background:rgba(0,0,0,.04);}',
    '[data-theme="light"] .cp-item.cp-active{background:rgba(99,102,241,.12);}',
    '[data-theme="light"] .cp-item.cp-active:hover{background:rgba(99,102,241,.16);}',
    '[data-theme="light"] .cp-item-icon{color:rgba(0,0,0,.45);}',
    '[data-theme="light"] .cp-active .cp-item-icon{color:rgba(79,70,229,.8);}',
    '[data-theme="light"] .cp-item-label{color:rgba(0,0,0,.7);}',
    '[data-theme="light"] .cp-active .cp-item-label{color:rgba(0,0,0,.9);}',
    '[data-theme="light"] .cp-item-label strong{color:rgba(0,0,0,.95) !important;}',
    '[data-theme="light"] .cp-item-sub{color:rgba(0,0,0,.3);}',
    '[data-theme="light"] .cp-active .cp-item-sub{color:rgba(79,70,229,.5);}',
    '[data-theme="light"] .cp-item-hint{background:rgba(99,102,241,.1);color:rgba(79,70,229,.65);border-color:rgba(99,102,241,.15);}',
    '[data-theme="light"] .cp-empty{color:rgba(0,0,0,.3);}',
    '[data-theme="light"] #cp-list::-webkit-scrollbar-thumb{background:rgba(0,0,0,.1);}',
  ].join('\n');
  document.head.appendChild(style);

  /* ── Build DOM ── */
  const overlay = document.createElement('div');
  overlay.id = 'cp-overlay';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-label', 'Command palette');
  _cpOverlay = overlay;

  const panel = document.createElement('div');
  panel.className = 'cp-panel';
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-modal', 'true');
  _cpPanel = panel;

  const inputWrap = document.createElement('div');
  inputWrap.className = 'cp-input-wrap';

  const searchIcon = document.createElement('i');
  searchIcon.className = 'fa-solid fa-magnifying-glass cp-search-icon';

  const input = document.createElement('input');
  input.id = 'cp-input';
  input.type = 'text';
  input.placeholder = (typeof lang !== 'undefined' && lang === 'zh')
    ? '搜索区块、图表、操作…'
    : 'Search sections, charts, actions...';
  input.setAttribute('autocomplete', 'off');
  input.setAttribute('spellcheck', 'false');
  input.setAttribute('aria-label', 'Search commands');

  const kbd = document.createElement('kbd');
  kbd.textContent = 'ESC';
  kbd.className = 'cp-esc-kbd';

  inputWrap.appendChild(searchIcon);
  inputWrap.appendChild(input);
  inputWrap.appendChild(kbd);

  const list = document.createElement('div');
  list.id = 'cp-list';
  list.setAttribute('aria-live', 'polite');

  panel.appendChild(inputWrap);
  panel.appendChild(list);
  overlay.appendChild(panel);
  document.body.appendChild(overlay);

  /* ── Event: click overlay backdrop to close ── */
  overlay.addEventListener('mousedown', (e) => {
    if (e.target === overlay) closePalette();
  });

  /* ── Event: input filtering with debounce ── */
  input.addEventListener('input', () => {
    clearTimeout(_cpDebounceTimer);
    _cpDebounceTimer = setTimeout(() => {
      _cpSelectedIdx = 0;
      _cpFilter(input.value.trim());
      _cpRenderList();
    }, 60);
  });

  /* ── Event: keyboard navigation inside input ── */
  input.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      _cpSelectedIdx = Math.min(_cpSelectedIdx + 1, _cpFiltered.length - 1);
      _cpRenderList();
      _cpScrollActive();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      _cpSelectedIdx = Math.max(_cpSelectedIdx - 1, 0);
      _cpRenderList();
      _cpScrollActive();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      _cpExecute(_cpSelectedIdx);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      closePalette();
    }
  });

  /* ── Event: click on result items ── */
  list.addEventListener('mousedown', (e) => {
    const item = e.target.closest('.cp-item');
    if (item) {
      e.preventDefault();
      const idx = parseInt(item.dataset.idx, 10);
      _cpExecute(idx);
    }
  });

  /* ── Event: hover highlight ── */
  list.addEventListener('mousemove', (e) => {
    const item = e.target.closest('.cp-item');
    if (item) {
      const idx = parseInt(item.dataset.idx, 10);
      if (idx !== _cpSelectedIdx) {
        _cpSelectedIdx = idx;
        _cpRenderList();
      }
    }
  });

  /* ── Global hotkey: Cmd+K / Ctrl+K ── */
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      if (_cpVisible) closePalette();
      else openPalette();
    }
  });
}

function _cpScrollActive() {
  const list = document.getElementById('cp-list');
  if (!list) return;
  const active = list.querySelector('.cp-active');
  if (active) active.scrollIntoView({block: 'nearest', behavior: 'smooth'});
}

initCommandPalette();
