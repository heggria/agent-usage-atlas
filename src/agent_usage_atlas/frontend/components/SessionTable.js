/* ── Session Leaderboard Table ── */
let _sessionSortCol = 'total';
let _sessionSortAsc = false;
const _PAGE_SIZE = 50;
let _currentPage = 0;
let _stDelegationBound = false;
let _stSearchTerm = '';
let _stSearchTimer = null;
let _stExpandedRows = new Set(); /* track expanded row indices (by sort-stable key) */

function _fmtDuration(minutes) {
  const m = Number(minutes || 0);
  if (m <= 0) return '-';
  if (m < 60) return Math.round(m) + 'm';
  const h = Math.floor(m / 60);
  const rm = Math.round(m % 60);
  return rm > 0 ? h + 'h ' + rm + 'm' : h + 'h';
}

function _sessionSortKey(row, col) {
  switch (col) {
    case 'source': return (row.source || '').toLowerCase();
    case 'session_id': return (row.session_id || '').toLowerCase();
    case 'total': return Number(row.total || 0);
    case 'cost': return Number(row.cost || 0);
    case 'tool_calls': return Number(row.tool_calls || 0);
    case 'top_model': return (row.top_model || '').toLowerCase();
    case 'duration': {
      return Number(row.minutes || 0);
    }
    case 'window': return row.first_local || '';
    default: return 0;
  }
}

function _sortedSessions() {
  const rows = data.top_sessions ? data.top_sessions.slice() : [];
  rows.sort((a, b) => {
    const av = _sessionSortKey(a, _sessionSortCol);
    const bv = _sessionSortKey(b, _sessionSortCol);
    if (av < bv) return _sessionSortAsc ? -1 : 1;
    if (av > bv) return _sessionSortAsc ? 1 : -1;
    return 0;
  });
  return rows;
}

function _filteredSessions(sorted) {
  if (!_stSearchTerm) return sorted;
  const q = _stSearchTerm.toLowerCase();
  return sorted.filter(row => {
    const sid = (row.session_id || '').toLowerCase();
    const model = (row.top_model || '').toLowerCase();
    const source = (row.source || '').toLowerCase();
    const project = (row.project || row.branch || '').toLowerCase();
    return sid.indexOf(q) !== -1
      || model.indexOf(q) !== -1
      || source.indexOf(q) !== -1
      || project.indexOf(q) !== -1;
  });
}

function _sortArrow(col) {
  if (col !== _sessionSortCol) {
    return ' <span class="st-sort-icon st-sort-icon--inactive">\u25B2</span>';
  }
  return ' <span class="st-sort-icon st-sort-icon--active">'
    + (_sessionSortAsc ? '\u25B2' : '\u25BC')
    + '</span>';
}

function _sourceColor(source) {
  const s = (source || '').toLowerCase();
  const map = {codex: 'var(--codex)', claude: 'var(--claude)', cursor: 'var(--cursor)', hermit: 'var(--hermit)'};
  return map[s] || 'var(--text-muted)';
}

function _sourceRawColor(source) {
  const s = (source || '').toLowerCase();
  const map = {codex: '#ff8a50', claude: '#ffd43b', cursor: '#748ffc', hermit: '#a78bfa'};
  return map[s] || 'transparent';
}

function _cacheHitRate(row) {
  const cr = Number(row.cache_read || 0);
  const total = Number(row.total || 0);
  if (total <= 0) return 0;
  return cr / total;
}

function _rowStableKey(row) {
  return (row.source || '') + ':' + (row.session_id || '');
}

function _buildHoverDetail(row) {
  const tokens = [
    {label: 'Uncached', value: fmtShort(row.uncached_input || 0)},
    {label: 'Cache Read', value: fmtShort(row.cache_read || 0)},
    {label: 'Cache Write', value: fmtShort(row.cache_write || 0)},
    {label: 'Output', value: fmtShort(row.output || 0)},
    {label: 'Reasoning', value: fmtShort(row.reasoning || 0)},
  ];
  const cacheRate = _cacheHitRate(row);
  const details = tokens
    .filter(tok => tok.value !== '0')
    .map(tok => '<span class="st-detail-chip">' + _escHtml(tok.label) + ': <strong>' + _escHtml(tok.value) + '</strong></span>')
    .join('');
  return '<div class="st-detail-row">'
    + details
    + '<span class="st-detail-chip">' + _escHtml(t('tblTools')) + ': <strong>' + _escHtml(fmtInt(row.tool_calls)) + '</strong></span>'
    + '<span class="st-detail-chip">Cache: <strong>' + _escHtml(fmtPct(cacheRate)) + '</strong></span>'
    + '</div>';
}

/* ── Inject SessionTable-specific styles once ── */
let _stStylesInjected = false;
function _injectStStyles() {
  if (_stStylesInjected) return;
  _stStylesInjected = true;
  const css = `
/* ── Sort column visual feedback ── */
.st-sortable.st-sorted{color:var(--accent)}
.st-sort-icon{
  display:inline-block;font-size:8px;
  transition:opacity .25s ease, transform .25s ease;
  vertical-align:middle;margin-left:2px;
}
.st-sort-icon--inactive{opacity:.2}
.st-sort-icon--active{opacity:.85}

/* ── Row hover micro-interactions ── */
.st-row{
  cursor:pointer;
  transition:transform .2s cubic-bezier(.22,1,.36,1), background .2s ease, box-shadow .2s ease;
  border-left:3px solid transparent;
}
.st-row:hover{
  transform:translateY(-1px);
  box-shadow:0 2px 8px rgba(0,0,0,.12);
  border-left-color:var(--st-accent, transparent);
}
[data-theme="light"] .st-row:hover{box-shadow:0 2px 8px rgba(0,0,0,.06)}
.st-row td:first-child{
  transition:border-left-color .2s ease;
}

/* ── Chevron expand indicator ── */
.st-chevron{
  display:inline-block;font-size:9px;color:var(--text-muted);
  margin-right:6px;
  transition:transform .3s cubic-bezier(.22,1,.36,1), color .2s;
}
.st-row:hover .st-chevron{color:var(--text-secondary)}
.st-chevron--open{transform:rotate(90deg);color:var(--accent) !important}

/* ── Smooth expand/collapse detail ── */
.st-detail-tr{
  visibility:visible !important;
}
.st-detail-tr td{
  padding:0 8px !important;
  border-bottom:1px solid var(--border);
}
.st-detail-wrap{
  max-height:0;
  overflow:hidden;
  transition:max-height .35s cubic-bezier(.22,1,.36,1), opacity .25s cubic-bezier(.22,1,.36,1);
  opacity:0;
}
.st-detail-wrap--open{
  max-height:120px;
  opacity:1;
}

/* ── Row expand removes default hover-reveal ── */
.st-row:hover+.st-detail-tr{visibility:visible}

/* ── Search input ── */
.st-search-wrap{
  display:flex;align-items:center;gap:8px;
  margin-bottom:12px;
}
.st-search-box{
  position:relative;flex:1;max-width:360px;
}
.st-search-input{
  width:100%;padding:8px 32px 8px 12px;
  border:1px solid var(--border);border-radius:var(--radius-sm);
  background:var(--surface);color:var(--text);
  font-size:13px;font-family:inherit;
  outline:none;
  transition:border-color .25s ease, box-shadow .25s ease;
}
.st-search-input::placeholder{color:var(--text-muted);opacity:.7}
.st-search-input:focus{
  border-color:var(--accent);
  box-shadow:0 0 0 3px rgba(240,184,102,.12);
}
[data-theme="light"] .st-search-input:focus{
  box-shadow:0 0 0 3px rgba(200,127,32,.1);
}
.st-search-clear{
  position:absolute;right:8px;top:50%;transform:translateY(-50%);
  border:none;background:none;color:var(--text-muted);
  font-size:14px;cursor:pointer;padding:2px 4px;line-height:1;
  opacity:0;pointer-events:none;
  transition:opacity .2s, color .2s;
}
.st-search-clear--visible{opacity:1;pointer-events:auto}
.st-search-clear:hover{color:var(--text)}
.st-search-count{
  font-size:12px;color:var(--text-muted);white-space:nowrap;
}

/* ── Show More pill ── */
.st-show-more-btn{
  cursor:pointer;
  display:inline-flex;align-items:center;gap:8px;
  padding:8px 24px;border-radius:999px;
  border:1px solid var(--border);
  background:var(--surface);color:var(--text-secondary);
  font-size:12px;font-weight:600;letter-spacing:.02em;
  transition:all .25s ease;
}
.st-show-more-btn:hover{
  background:rgba(240,184,102,.08);
  border-color:var(--accent);
  color:var(--text);
}
.st-show-more-remaining{
  display:inline-flex;align-items:center;justify-content:center;
  min-width:22px;height:22px;padding:0 7px;border-radius:999px;
  background:rgba(255,255,255,.08);
  font-size:10px;font-weight:800;color:var(--text-muted);
}
[data-theme="light"] .st-show-more-remaining{background:rgba(0,0,0,.06)}

/* ── Fade-in for new rows ── */
@keyframes st-row-fadein{
  from{opacity:0;transform:translateY(6px)}
  to{opacity:1;transform:translateY(0)}
}
.st-row--new{animation:st-row-fadein .35s cubic-bezier(.22,1,.36,1) both}
.st-row--new+.st-detail-tr{animation:st-row-fadein .35s cubic-bezier(.22,1,.36,1) both}

/* ── Empty state ── */
.st-empty-state{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:48px 16px;gap:14px;
}
.st-empty-state-icon{font-size:36px;color:var(--text-muted);opacity:.45}
.st-empty-state-text{font-size:14px;color:var(--text-muted);font-weight:500}
.st-empty-state-hint{font-size:12px;color:var(--text-muted);opacity:.7}

@media(max-width:500px){.st-search-box{max-width:100%}}
`;
  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);
}

function _getTableWrap() {
  const tbl = document.getElementById('session-table');
  return tbl ? tbl.closest('.table-wrap') || tbl.parentElement : null;
}

function _setupSessionTableDelegation() {
  if (_stDelegationBound) return;
  const wrap = _getTableWrap();
  if (!wrap) return;
  _stDelegationBound = true;

  /* Sort header delegation */
  wrap.addEventListener('click', (e) => {
    const th = e.target.closest('.st-sortable');
    if (th) {
      const col = th.getAttribute('data-sort-col');
      if (_sessionSortCol === col) {
        _sessionSortAsc = !_sessionSortAsc;
      } else {
        _sessionSortCol = col;
        _sessionSortAsc = col === 'source' || col === 'session_id' || col === 'top_model' || col === 'window';
      }
      _currentPage = 0;
      renderSessionTable();
      return;
    }

    /* "Show More" button delegation */
    const showMoreBtn = e.target.closest('.st-show-more-btn');
    if (showMoreBtn) {
      const prevCount = (_currentPage + 1) * _PAGE_SIZE;
      _currentPage++;
      renderSessionTable(prevCount);
      return;
    }

    /* Search clear button */
    const clearBtn = e.target.closest('.st-search-clear');
    if (clearBtn) {
      _stSearchTerm = '';
      _currentPage = 0;
      const input = wrap.querySelector('.st-search-input');
      if (input) input.value = '';
      renderSessionTable();
      return;
    }

    /* Row click → toggle expand/collapse */
    const row = e.target.closest('.st-row');
    if (row) {
      const stableKey = row.dataset.stableKey;
      const detailTr = row.nextElementSibling;
      if (!detailTr || !detailTr.classList.contains('st-detail-tr')) return;

      const detailWrap = detailTr.querySelector('.st-detail-wrap');
      if (!detailWrap) return;

      const isOpen = _stExpandedRows.has(stableKey);
      if (isOpen) {
        /* Collapse */
        _stExpandedRows.delete(stableKey);
        detailWrap.classList.remove('st-detail-wrap--open');
        row.querySelector('.st-chevron').classList.remove('st-chevron--open');
      } else {
        /* Expand: lazy-load detail content */
        _stExpandedRows.add(stableKey);
        const td = detailTr.querySelector('td');
        if (td && !detailWrap.dataset.loaded) {
          const idx = Number(row.dataset.rowIdx);
          const sorted = _sortedSessions();
          const filtered = _filteredSessions(sorted);
          if (filtered[idx]) {
            detailWrap.innerHTML = _buildHoverDetail(filtered[idx]);
            detailWrap.dataset.loaded = '1';
          }
        }
        detailWrap.classList.add('st-detail-wrap--open');
        row.querySelector('.st-chevron').classList.add('st-chevron--open');
      }
      return;
    }
  });

  /* Search input delegation */
  wrap.addEventListener('input', (e) => {
    if (!e.target.classList.contains('st-search-input')) return;
    const val = e.target.value;
    if (_stSearchTimer) clearTimeout(_stSearchTimer);
    _stSearchTimer = setTimeout(() => {
      _stSearchTerm = val.trim();
      _currentPage = 0;
      _stExpandedRows.clear();
      renderSessionTable();
    }, 300);
  });
}

function renderSessionTable(prevVisibleCount) {
  const sessions = data.top_sessions || [];
  const wrap = _getTableWrap();
  if (!wrap) return;

  _injectStStyles();
  _setupSessionTableDelegation();

  /* ── Empty state ── */
  if (!sessions || sessions.length === 0) {
    wrap.innerHTML =
      '<div class="st-empty-state">'
      + '<div class="st-empty-state-icon"><i class="fa-solid fa-calendar-xmark"></i></div>'
      + '<div class="st-empty-state-text">'
      + (lang === 'zh' ? '\u8FD9\u4E2A\u65F6\u6BB5\u6CA1\u6709\u4F1A\u8BDD\u8BB0\u5F55' : 'No sessions in this period')
      + '</div>'
      + '<div class="st-empty-state-hint">'
      + (lang === 'zh' ? '\u8C03\u6574\u65E5\u671F\u8303\u56F4\u6216\u7B49\u5F85\u65B0\u6570\u636E' : 'Try adjusting the date range or wait for new data')
      + '</div>'
      + '</div>';
    return;
  }

  const sorted = _sortedSessions();
  const filtered = _filteredSessions(sorted);
  const totalCount = sorted.length;
  const matchCount = filtered.length;
  const maxCost = Math.max(...sessions.map(r => Number(r.cost || 0)), 0.001);
  const visibleCount = Math.min(filtered.length, (_currentPage + 1) * _PAGE_SIZE);
  const visible = filtered.slice(0, visibleCount);
  const fadeStart = typeof prevVisibleCount === 'number' ? prevVisibleCount : -1;

  /* ── Search bar ── */
  const searchHtml =
    '<div class="st-search-wrap">'
    + '<div class="st-search-box">'
    +   '<input class="st-search-input" type="text" aria-label="Search sessions" placeholder="'
    +   (lang === 'zh' ? '\u641C\u7D22\u4F1A\u8BDD\u3001\u6A21\u578B\u3001\u6765\u6E90\u2026' : 'Search sessions, models, sources\u2026')
    +   '" value="' + _escHtml(_stSearchTerm) + '">'
    +   '<button class="st-search-clear' + (_stSearchTerm ? ' st-search-clear--visible' : '') + '" title="Clear">\u00D7</button>'
    + '</div>'
    + (_stSearchTerm
      ? '<span class="st-search-count">'
        + (lang === 'zh'
          ? '\u663E\u793A ' + matchCount + ' / ' + totalCount + ' \u4E2A\u4F1A\u8BDD'
          : 'Showing ' + matchCount + ' of ' + totalCount + ' sessions')
        + '</span>'
      : '')
    + '</div>';

  const cols = [
    {key: 'source', label: t('tblSource')},
    {key: 'session_id', label: t('tblSession')},
    {key: 'total', label: t('tblTokens')},
    {key: 'cost', label: t('tblCost')},
    {key: 'duration', label: t('tblDuration')},
    {key: 'tool_calls', label: t('tblTools')},
    {key: 'top_model', label: t('tblModel')},
    {key: 'window', label: t('tblWindow')},
  ];

  const theadCells = cols.map(c => {
    const isSorted = c.key === _sessionSortCol;
    const ariaSort = isSorted ? (_sessionSortAsc ? 'ascending' : 'descending') : 'none';
    return '<th scope="col" class="st-sortable' + (isSorted ? ' st-sorted' : '') + '" data-sort-col="' + c.key + '"'
      + ' role="button" tabindex="0" aria-sort="' + ariaSort + '">'
      + _escHtml(c.label) + _sortArrow(c.key)
      + '</th>';
  }).join('');

  const tbodyRows = visible.map((row, idx) => {
    const costPct = Math.min(100, (Number(row.cost || 0) / maxCost) * 100);
    const srcColor = _sourceColor(row.source);
    const rawColor = _sourceRawColor(row.source);
    const sid = String(row.session_id || '');
    const shortId = sid.length > 8 ? _escHtml(sid.slice(0, 8)) + '\u2026' : _escHtml(sid);
    const fullId = _escHtml(sid);
    const stableKey = _rowStableKey(row);
    const isExpanded = _stExpandedRows.has(stableKey);
    const isNewRow = fadeStart >= 0 && idx >= fadeStart;
    const rowCls = 'st-row' + (isNewRow ? ' st-row--new' : '');
    const animDelay = isNewRow ? ' style="animation-delay:' + ((idx - fadeStart) * 30) + 'ms;--st-accent:' + rawColor + '"' : ' style="--st-accent:' + rawColor + '"';

    return '<tr class="' + rowCls + '" data-row-idx="' + idx + '" data-stable-key="' + _escHtml(stableKey) + '"' + animDelay + '>'
      + '<td>'
      +   '<span class="st-chevron' + (isExpanded ? ' st-chevron--open' : '') + '">\u25B6</span>'
      +   '<span class="st-source-badge" style="--src-color:' + srcColor + '">' + _escHtml(row.source) + '</span>'
      +   '<div class="tiny" style="margin-left:15px">' + _escHtml(t('tblEvents', {n: fmtInt(row.messages)})) + '</div>'
      + '</td>'
      + '<td>'
      +   '<span class="st-sid" title="' + fullId + '">' + shortId + '</span>'
      + '</td>'
      + '<td>' + _escHtml(fmtShort(row.total)) + '</td>'
      + '<td class="st-cost-cell">'
      +   '<div class="st-cost-bar" style="width:' + costPct.toFixed(1) + '%;background:' + srcColor + '"></div>'
      +   '<span class="st-cost-value">' + _escHtml(fmtUSD(row.cost)) + '</span>'
      + '</td>'
      + '<td>' + _escHtml(_fmtDuration(row.minutes)) + '</td>'
      + '<td>' + _escHtml(fmtInt(row.tool_calls)) + '</td>'
      + '<td style="font-size:11px">' + _escHtml(row.top_model) + '</td>'
      + '<td><div style="font-size:11px">' + _escHtml(row.first_local) + '</div><div class="tiny">\u2192 ' + _escHtml(row.last_local) + '</div></td>'
      + '</tr>'
      + '<tr class="st-detail-tr"><td colspan="8">'
      + '<div class="st-detail-wrap' + (isExpanded ? ' st-detail-wrap--open' : '') + '"'
      + (isExpanded ? ' data-loaded="1"' : '') + '>'
      + (isExpanded ? _buildHoverDetail(row) : '')
      + '</div>'
      + '</td></tr>';
  }).join('');

  /* ── Show More button ── */
  const remaining = filtered.length - visibleCount;
  const nextBatch = Math.min(_PAGE_SIZE, remaining);
  const showMoreHtml = remaining > 0
    ? '<tr><td colspan="8" style="text-align:center;padding:16px">'
      + '<button class="st-show-more-btn">'
      + (lang === 'zh' ? '\u518D\u52A0\u8F7D ' + nextBatch + ' \u4E2A' : 'Show ' + nextBatch + ' more')
      + ' <span class="st-show-more-remaining">' + remaining + '</span>'
      + '</button></td></tr>'
    : '';

  wrap.innerHTML =
    searchHtml
    + '<table><thead><tr>' + theadCells + '</tr></thead>'
    + '<tbody>' + tbodyRows + showMoreHtml + '</tbody></table>';

  /* Restore focus to search input if it was active */
  if (_stSearchTerm) {
    const input = wrap.querySelector('.st-search-input');
    if (input) {
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);
    }
  }
}
