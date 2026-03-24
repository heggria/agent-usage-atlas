let data = __DATA__;

/* ── Dashboard lifecycle state ── */
let dashboardState = 'init'; // 'init' | 'loading' | 'ready' | 'refreshing' | 'error'
const _stateListeners = [];

function setDashboardState(state) {
  dashboardState = state;
  document.documentElement.dataset.dashboardState = state;
  _notifyStateListeners(state);
}

function getDashboardState() { return dashboardState; }

function onDashboardStateChange(fn) { _stateListeners.push(fn); }

function _notifyStateListeners(state) {
  _stateListeners.forEach(fn => fn(state));
}

/* ── Error tracking ── */
let lastError = null;

function setDashboardError(err) {
  lastError = err;
  setDashboardState('error');
}

function getLastError() { return lastError; }

/* ── Data freshness ── */
let lastDataUpdate = 0;
const intervalMs = Math.max(1000, Number(__POLL_MS__) || 5000);

function getDataAge() { return Date.now() - lastDataUpdate; }

function isDataStale() {
  if (!isLiveMode || lastDataUpdate === 0) return false;
  return getDataAge() > intervalMs * 2;
}


const pageParams = new URLSearchParams(window.location.search);
const baseRangeParams = new URLSearchParams();
if (pageParams.get('days')) baseRangeParams.set('days', pageParams.get('days'));
if (pageParams.get('since')) baseRangeParams.set('since', pageParams.get('since'));
const baseInterval = pageParams.get('interval');
const defaultDays = Number(baseRangeParams.get('days')) || 30;
const defaultSince = baseRangeParams.get('since') || null;

/* Active range tab state — persist across reloads */
const _RANGE_STORAGE_KEY = 'aua-range';
let activeRangeKey = localStorage.getItem(_RANGE_STORAGE_KEY) || 'all';
function _dateFmt(d) {
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}
function _buildParams(rangeKey) {
  const p = new URLSearchParams();
  if (rangeKey === 'today') {
    p.set('since', _dateFmt(new Date()));
  } else if (rangeKey === '3day') {
    p.set('days', '3');
  } else if (rangeKey === 'week') {
    p.set('days', '7');
  } else {
    if (defaultSince) p.set('since', defaultSince);
    else p.set('days', String(defaultDays));
  }
  if (baseInterval) p.set('interval', baseInterval);
  return p;
}
function _apiUrl(rangeKey) {
  const p = _buildParams(rangeKey);
  p.delete('interval');
  return '/api/dashboard' + (p.toString() ? `?${p}` : '');
}
function _streamUrl(rangeKey) {
  const p = _buildParams(rangeKey);
  return '/api/dashboard/stream' + (p.toString() ? `?${p}` : '');
}
let dashboardApiUrl = _apiUrl(activeRangeKey);
let dashboardStreamUrl = _streamUrl(activeRangeKey);
function setActiveRange(key) {
  activeRangeKey = key;
  dashboardApiUrl = _apiUrl(key);
  dashboardStreamUrl = _streamUrl(key);
  try { localStorage.setItem(_RANGE_STORAGE_KEY, key); } catch (_) {}
}
const isLiveMode = __LIVE_MODE__;
let lastDashboardHash = '';
let refreshTimer = null;
let streamSource = null;
let isStreamConnected = false;
const charts = [];
const chartCache = {};

/* ── Date drill-down filter (cost family) ── */
let selectedDate = null;
const _dateFilterListeners = {};
function onDateFilter(key, fn) { _dateFilterListeners[key] = fn; }
function setSelectedDate(date) {
  selectedDate = (date === selectedDate) ? null : date;
  requestAnimationFrame(() => {
    Object.values(_dateFilterListeners).forEach(fn => fn(selectedDate));
  });
}

function setDashboard(nextData){
  if (!nextData || typeof nextData !== 'object') {
    if (!data) setDashboardState('loading');
    return false;
  }
  const meta = nextData._meta;
  const hash = meta ? meta.generated_at : '';
  if (!data) {
    data = nextData;
    lastDashboardHash = hash;
    lastDataUpdate = Date.now();
    lastError = null;
    setDashboardState('ready');
    return true;
  }
  if (hash && hash === lastDashboardHash) {
    return false;
  }
  data = nextData;
  lastDashboardHash = hash;
  lastDataUpdate = Date.now();
  lastError = null;
  setDashboardState('ready');
  return true;
}
