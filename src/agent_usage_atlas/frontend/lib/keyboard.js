/* ── Keyboard Navigation ── */

const _SECTION_IDS = [
  'sec-sources',
  'sec-cost-tokens',
  'sec-activity',
  'sec-tooling',
  'sec-insights',
  'sec-leaderboard'
];

let _currentSectionIdx = -1;
let _kbdHelpVisible = false;
let _kbdHelpOverlay = null;

/* ── Guard: skip shortcuts when focus is inside form elements, palette, or dialogs ── */
function _kbdShouldIgnore() {
  const tag = (document.activeElement && document.activeElement.tagName) || '';
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  if (typeof _cpVisible !== 'undefined' && _cpVisible) return true;
  const openDialog = document.querySelector('dialog[open]');
  if (openDialog) return true;
  return false;
}

/* ── Visual focus ring management ── */
function _kbdClearFocus() {
  document.querySelectorAll('.kbd-focus').forEach(function(el) {
    el.classList.remove('kbd-focus');
  });
}

function _kbdApplyFocus(sectionId) {
  _kbdClearFocus();
  const divEl = document.getElementById(sectionId);
  if (!divEl) return;
  divEl.classList.add('kbd-focus');
  divEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/* ── Section navigation (J/K) ── */
function _kbdNextSection() {
  if (_SECTION_IDS.length === 0) return;
  _currentSectionIdx = (_currentSectionIdx + 1) % _SECTION_IDS.length;
  _kbdApplyFocus(_SECTION_IDS[_currentSectionIdx]);
}

function _kbdPrevSection() {
  if (_SECTION_IDS.length === 0) return;
  _currentSectionIdx = (_currentSectionIdx - 1 + _SECTION_IDS.length) % _SECTION_IDS.length;
  _kbdApplyFocus(_SECTION_IDS[_currentSectionIdx]);
}

/* ── Jump to section by number key ── */
function _kbdJumpSection(num) {
  var idx = num - 1;
  if (idx < 0 || idx >= _SECTION_IDS.length) return;
  _currentSectionIdx = idx;
  var sectionId = _SECTION_IDS[idx];
  var divEl = document.getElementById(sectionId);
  if (!divEl) return;
  /* Expand if collapsed */
  var wrap = document.querySelector('.section-wrap[data-section="' + sectionId + '"]');
  if (wrap && wrap.classList.contains('collapsed')) {
    expandSection(divEl, wrap);
    if (typeof _collapseState !== 'undefined') {
      _collapseState[sectionId] = false;
      _saveCollapsed(_collapseState);
    }
  }
  _kbdApplyFocus(sectionId);
}

/* ── Toggle section expand/collapse on Enter ── */
function _kbdToggleCurrentSection() {
  if (_currentSectionIdx < 0 || _currentSectionIdx >= _SECTION_IDS.length) return;
  var sectionId = _SECTION_IDS[_currentSectionIdx];
  var divEl = document.getElementById(sectionId);
  if (!divEl) return;
  /* Simulate a click on the divider to toggle */
  divEl.click();
}

/* ── Shortcut definitions (shared between help overlay and command palette) ── */
const _KBD_SHORTCUTS = [
  {key: 'J', keyZh: 'J', desc: 'Next section', descZh: '下一区块'},
  {key: 'K', keyZh: 'K', desc: 'Previous section', descZh: '上一区块'},
  {key: 'Enter', keyZh: 'Enter', desc: 'Toggle section expand/collapse', descZh: '展开/折叠区块'},
  {key: '1 - 6', keyZh: '1 - 6', desc: 'Jump to section (Sources, Cost, Activity, Tooling, Insights, Board)', descZh: '跳转到区块（来源、花费、活跃、工具、洞察、排行）'},
  {key: 'T', keyZh: 'T', desc: 'Toggle theme (dark/light)', descZh: '切换主题（深色/浅色）'},
  {key: 'L', keyZh: 'L', desc: 'Toggle language (ZH/EN)', descZh: '切换语言（中/英）'},
  {key: '/', keyZh: '/', desc: 'Focus range tabs', descZh: '聚焦时间范围选项'},
  {key: '?', keyZh: '?', desc: 'Show/hide keyboard shortcuts', descZh: '显示/隐藏快捷键'},
  {key: 'Escape', keyZh: 'Escape', desc: 'Close overlay / clear date filter', descZh: '关闭弹窗 / 清除日期筛选'},
  {key: navigator.platform.indexOf('Mac') > -1 ? 'Cmd+K' : 'Ctrl+K', keyZh: navigator.platform.indexOf('Mac') > -1 ? 'Cmd+K' : 'Ctrl+K', desc: 'Open command palette', descZh: '打开命令面板'},
];

/**
 * Returns the list of keyboard shortcuts for use by the command palette
 * or any other component that needs to display shortcut hints.
 * Each entry has: {key, desc} (localized based on current lang).
 */
function getKeyboardShortcuts() {
  const isZh = typeof lang !== 'undefined' && lang === 'zh';
  return _KBD_SHORTCUTS.map(function(s) {
    return {
      key: isZh ? s.keyZh : s.key,
      desc: isZh ? s.descZh : s.desc,
    };
  });
}

/* ── Help overlay ── */
function _kbdBuildHelpOverlay() {
  if (_kbdHelpOverlay) return _kbdHelpOverlay;

  /* Inject help overlay styles */
  var helpStyle = document.createElement('style');
  helpStyle.textContent = [
    '#kbd-help-overlay{position:fixed;inset:0;z-index:9998;display:none;',
    'align-items:flex-start;justify-content:center;padding-top:min(18vh,140px);',
    'background:rgba(0,0,0,0);backdrop-filter:blur(0px);-webkit-backdrop-filter:blur(0px);',
    'transition:background .18s ease,backdrop-filter .18s ease,-webkit-backdrop-filter .18s ease;}',

    '#kbd-help-overlay.kbd-open{background:rgba(0,0,0,.5);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);}',
    '#kbd-help-overlay.kbd-closing{background:rgba(0,0,0,0);backdrop-filter:blur(0px);-webkit-backdrop-filter:blur(0px);}',

    '.kbd-panel{width:min(480px,90vw);max-height:72vh;overflow-y:auto;',
    'border-radius:16px;padding:24px 28px;',
    'background:rgba(22,24,35,.88);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);',
    'border:1px solid rgba(255,255,255,.1);box-shadow:0 24px 80px rgba(0,0,0,.55),0 0 0 1px rgba(255,255,255,.05);',
    'color:rgba(255,255,255,.88);font-family:inherit;',
    'transform:scale(.95);opacity:0;transition:transform .15s cubic-bezier(.2,.9,.3,1),opacity .15s ease;}',

    '#kbd-help-overlay.kbd-open .kbd-panel{transform:scale(1);opacity:1;}',
    '#kbd-help-overlay.kbd-closing .kbd-panel{transform:scale(.97);opacity:0;transition:transform .1s ease,opacity .1s ease;}',

    /* Light theme */
    '[data-theme="light"] .kbd-panel{background:rgba(255,255,255,.92);border-color:rgba(0,0,0,.1);',
    'box-shadow:0 24px 80px rgba(0,0,0,.18);color:rgba(0,0,0,.75);}',
    '[data-theme="light"] #kbd-help-overlay.kbd-open{background:rgba(0,0,0,.25);}',
    '[data-theme="light"] .kbd-panel h2{color:rgba(0,0,0,.85) !important;}',
    '[data-theme="light"] .kbd-panel td:last-child{color:rgba(0,0,0,.55) !important;}',
    '[data-theme="light"] .kbd-panel tr{border-bottom-color:rgba(0,0,0,.06) !important;}',
    '[data-theme="light"] .kbd-panel kbd{background:rgba(0,0,0,.06) !important;color:rgba(0,0,0,.6) !important;border-color:rgba(0,0,0,.1) !important;}',
  ].join('\n');
  document.head.appendChild(helpStyle);

  var overlay = document.createElement('div');
  overlay.id = 'kbd-help-overlay';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-label', 'Keyboard shortcuts');

  var panel = document.createElement('div');
  panel.className = 'kbd-panel';

  var isZh = typeof lang !== 'undefined' && lang === 'zh';

  var title = document.createElement('h2');
  title.textContent = isZh ? '快捷键' : 'Keyboard Shortcuts';
  title.style.cssText = 'margin:0 0 16px 0;font-size:18px;font-weight:600;'
    + 'color:rgba(255,255,255,.95);letter-spacing:-.3px;';

  var table = document.createElement('table');
  table.style.cssText = 'width:100%;border-collapse:collapse;font-size:14px;';

  var shortcuts = getKeyboardShortcuts();

  for (var i = 0; i < shortcuts.length; i++) {
    var row = document.createElement('tr');
    row.style.cssText = 'border-bottom:1px solid rgba(255,255,255,.06);';

    var kbdCell = document.createElement('td');
    kbdCell.style.cssText = 'padding:8px 12px 8px 0;white-space:nowrap;width:100px;';

    var kbdEl = document.createElement('kbd');
    kbdEl.textContent = shortcuts[i].key;
    kbdEl.style.cssText = 'display:inline-block;min-width:24px;text-align:center;'
      + 'font-size:12px;padding:3px 8px;border-radius:5px;'
      + 'background:rgba(255,255,255,.1);color:rgba(255,255,255,.8);'
      + 'border:1px solid rgba(255,255,255,.15);font-family:inherit;';
    kbdCell.appendChild(kbdEl);

    var descCell = document.createElement('td');
    descCell.textContent = shortcuts[i].desc;
    descCell.style.cssText = 'padding:8px 0;color:rgba(255,255,255,.65);';

    row.appendChild(kbdCell);
    row.appendChild(descCell);
    table.appendChild(row);
  }

  panel.appendChild(title);
  panel.appendChild(table);
  overlay.appendChild(panel);
  document.body.appendChild(overlay);

  /* Click backdrop to close */
  overlay.addEventListener('mousedown', function(e) {
    if (e.target === overlay) _kbdCloseHelp();
  });

  _kbdHelpOverlay = overlay;
  return overlay;
}

function _kbdOpenHelp() {
  var overlay = _kbdBuildHelpOverlay();
  _kbdHelpVisible = true;
  overlay.style.display = 'flex';
  requestAnimationFrame(function() {
    overlay.classList.add('kbd-open');
  });
}

function _kbdCloseHelp() {
  if (!_kbdHelpOverlay) return;
  _kbdHelpVisible = false;
  _kbdHelpOverlay.classList.remove('kbd-open');
  _kbdHelpOverlay.classList.add('kbd-closing');
  setTimeout(function() {
    if (_kbdHelpOverlay) {
      _kbdHelpOverlay.classList.remove('kbd-closing');
      _kbdHelpOverlay.style.display = 'none';
    }
  }, 180);
}

function _kbdToggleHelp() {
  if (_kbdHelpVisible) _kbdCloseHelp();
  else _kbdOpenHelp();
}

/* ── Focus range tabs ── */
function _kbdFocusRangeTabs() {
  var el = document.getElementById('range-tabs');
  if (!el) return;
  var firstBtn = el.querySelector('button');
  if (firstBtn) {
    firstBtn.focus();
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

/* ── Main keydown handler ── */
function _kbdHandleKeydown(e) {
  /* Escape always works (closes overlays, clears filter) */
  if (e.key === 'Escape') {
    if (_kbdHelpVisible) {
      e.preventDefault();
      _kbdCloseHelp();
      return;
    }
    if (typeof _cpVisible !== 'undefined' && _cpVisible) {
      /* Let the command palette handle its own Escape */
      return;
    }
    /* Clear date filter if active */
    if (typeof selectedDate !== 'undefined' && selectedDate !== null) {
      e.preventDefault();
      setSelectedDate(null);
      return;
    }
    return;
  }

  /* All other shortcuts are guarded */
  if (_kbdShouldIgnore()) return;
  /* Also skip if help overlay is open (only Escape closes it) */
  if (_kbdHelpVisible) {
    if (e.key === '?') {
      e.preventDefault();
      _kbdCloseHelp();
    }
    return;
  }
  /* Skip if any modifier key is held (except Shift for ?) */
  if (e.ctrlKey || e.metaKey || e.altKey) return;

  switch (e.key) {
    case 'j':
    case 'J':
      e.preventDefault();
      _kbdNextSection();
      break;
    case 'k':
    case 'K':
      e.preventDefault();
      _kbdPrevSection();
      break;
    case 'Enter':
      if (_currentSectionIdx >= 0) {
        e.preventDefault();
        _kbdToggleCurrentSection();
      }
      break;
    case '1': case '2': case '3': case '4': case '5': case '6':
      e.preventDefault();
      _kbdJumpSection(parseInt(e.key, 10));
      break;
    case 't':
    case 'T':
      e.preventDefault();
      if (typeof toggleTheme === 'function') toggleTheme();
      break;
    case 'l':
    case 'L':
      e.preventDefault();
      if (typeof toggleLang === 'function') toggleLang();
      break;
    case '/':
      e.preventDefault();
      _kbdFocusRangeTabs();
      break;
    case '?':
      e.preventDefault();
      _kbdToggleHelp();
      break;
    default:
      break;
  }
}

/* ── Mouse click clears keyboard focus (switch back to pointer mode) ── */
function _kbdHandleMouseDown() {
  _kbdClearFocus();
}

/* ── Cleanup ── */
function _removeKeyboard() {
  document.removeEventListener('keydown', _kbdHandleKeydown);
  document.removeEventListener('mousedown', _kbdHandleMouseDown);
}

/* ── Init ── */
function _initKeyboard() {
  /* Inject kbd-focus style (avoids modifying main.css) */
  var style = document.createElement('style');
  style.textContent = '.kbd-focus{'
    + 'outline:2px solid rgba(99,102,241,.7);'
    + 'outline-offset:2px;'
    + 'box-shadow:0 0 0 4px rgba(99,102,241,.18);'
    + 'transition:outline .15s ease,box-shadow .15s ease;'
    + '}';
  document.head.appendChild(style);

  document.addEventListener('keydown', _kbdHandleKeydown);
  document.addEventListener('mousedown', _kbdHandleMouseDown);
}

_initKeyboard();
