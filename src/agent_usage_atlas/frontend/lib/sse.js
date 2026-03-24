/* ── Toast notification system (stacking, progress, slide transitions) ── */
const _TOAST_MAX = 3;
const _toastQueue = []; /* active toast entries: { el, timer, id } */
let _toastIdCounter = 0;

const _TOAST_STYLES = {
  ok: {
    border: '1px solid rgba(81,207,102,.35)',
    borderLeft: '4px solid #51cf66',
    background: 'rgba(13,16,22,.88)',
    color: '#a3e635',
    icon: 'fa-solid fa-circle-check',
    tint: 'rgba(81,207,102,.08)',
  },
  err: {
    border: '1px solid rgba(255,107,107,.35)',
    borderLeft: '4px solid #ff6b6b',
    background: 'rgba(13,16,22,.88)',
    color: '#ff6b6b',
    icon: 'fa-solid fa-circle-exclamation',
    tint: 'rgba(255,107,107,.08)',
  },
  info: {
    border: '1px solid rgba(116,192,252,.3)',
    borderLeft: '4px solid #74c0fc',
    background: 'rgba(13,16,22,.88)',
    color: '#74c0fc',
    icon: 'fa-solid fa-circle-info',
    tint: 'rgba(116,192,252,.08)',
  },
};

const _TOAST_STYLES_LIGHT = {
  ok: {
    border: '1px solid rgba(81,207,102,.3)',
    borderLeft: '4px solid #2b8a3e',
    background: 'rgba(255,255,255,.92)',
    color: '#2b8a3e',
    tint: 'rgba(81,207,102,.06)',
  },
  err: {
    border: '1px solid rgba(255,107,107,.3)',
    borderLeft: '4px solid #c92a2a',
    background: 'rgba(255,255,255,.92)',
    color: '#c92a2a',
    tint: 'rgba(255,107,107,.06)',
  },
  info: {
    border: '1px solid rgba(116,192,252,.25)',
    borderLeft: '4px solid #1971c2',
    background: 'rgba(255,255,255,.92)',
    color: '#1971c2',
    tint: 'rgba(116,192,252,.06)',
  },
};

function _isLightTheme() {
  return document.documentElement.getAttribute('data-theme') === 'light';
}

function _getToastStyle(type) {
  const base = _TOAST_STYLES[type] || _TOAST_STYLES.info;
  if (!_isLightTheme()) return base;
  const light = _TOAST_STYLES_LIGHT[type] || _TOAST_STYLES_LIGHT.info;
  return Object.assign({}, base, light);
}

function _dismissToast(entry) {
  if (!entry || !entry.el) return;
  clearTimeout(entry.timer);
  entry.el.style.transform = 'translateX(120%)';
  entry.el.style.opacity = '0';
  const idx = _toastQueue.indexOf(entry);
  if (idx !== -1) _toastQueue.splice(idx, 1);
  setTimeout(() => {
    if (entry.el.parentNode) entry.el.parentNode.removeChild(entry.el);
  }, 400);
}

function showToast(message, type, duration) {
  if (type === undefined) type = 'info';
  if (duration === undefined) duration = 3000;
  const container = document.getElementById('toast-container');
  if (!container) return;

  /* Evict oldest if at capacity */
  while (_toastQueue.length >= _TOAST_MAX) {
    _dismissToast(_toastQueue[0]);
  }

  const id = ++_toastIdCounter;
  const style = _getToastStyle(type);

  const el = document.createElement('div');
  el.setAttribute('role', 'status');
  el.setAttribute('aria-live', 'polite');
  Object.assign(el.style, {
    position: 'relative',
    padding: '10px 14px 10px 16px',
    borderRadius: '10px',
    fontSize: '12px',
    fontWeight: '600',
    letterSpacing: '.02em',
    pointerEvents: 'auto',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    backdropFilter: 'blur(16px)',
    WebkitBackdropFilter: 'blur(16px)',
    boxShadow: '0 8px 32px rgba(0,0,0,.45)',
    overflow: 'hidden',
    /* Slide in from right */
    transform: 'translateX(120%)',
    opacity: '0',
    transition: 'transform .4s cubic-bezier(.16,1,.3,1), opacity .4s ease',
    /* Type-specific */
    border: style.border,
    borderLeft: style.borderLeft,
    background: 'linear-gradient(135deg, ' + style.tint + ', ' + style.background + ')',
    color: style.color,
  });

  const iconHtml = '<i class="' + _escHtml(style.icon) + '" style="font-size:14px;flex-shrink:0;"></i>';
  const msgSpan = '<span style="flex:1;line-height:1.4;">' + _escHtml(message) + '</span>';
  const closeBtn = '<span style="font-size:10px;opacity:.5;flex-shrink:0;margin-left:4px;padding:2px;" aria-label="Dismiss">'
    + '<i class="fa-solid fa-xmark"></i></span>';

  el.innerHTML = iconHtml + msgSpan + closeBtn;

  /* Progress bar for timed toasts */
  if (duration > 0) {
    const bar = document.createElement('div');
    Object.assign(bar.style, {
      position: 'absolute',
      bottom: '0',
      left: '0',
      height: '2px',
      width: '100%',
      background: style.color,
      opacity: '.5',
      borderRadius: '0 0 0 10px',
      transformOrigin: 'left',
      transition: 'transform ' + duration + 'ms linear',
    });
    el.appendChild(bar);
    /* Trigger the shrink after layout paint */
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        bar.style.transform = 'scaleX(0)';
      });
    });
  }

  container.appendChild(el);

  const entry = { el: el, timer: null, id: id };

  /* Click to dismiss */
  el.addEventListener('click', () => _dismissToast(entry));

  /* Slide in */
  requestAnimationFrame(() => {
    el.style.transform = 'translateX(0)';
    el.style.opacity = '1';
  });

  /* Auto-dismiss after duration */
  if (duration > 0) {
    entry.timer = setTimeout(() => _dismissToast(entry), duration);
  }

  _toastQueue.push(entry);
}

/* ── Connection status badge (4 states) ── */
function updateLiveBadge(state) {
  const badge = document.getElementById('live-badge');
  if (!badge) return;

  /* State config: color, dotColor, dotShadow, pulsing, label key */
  const states = {
    connected:    { bg: 'rgba(81,207,102,.15)',  color: '#51cf66', dotBg: '#51cf66', dotShadow: '0 0 6px #51cf66', pulse: true,  labelKey: 'badgeLive' },
    reconnecting: { bg: 'rgba(255,212,59,.15)',  color: '#ffd43b', dotBg: '#ffd43b', dotShadow: '0 0 6px #ffd43b', pulse: true,  labelKey: 'badgeReconnecting' },
    disconnected: { bg: 'rgba(255,107,107,.15)',  color: '#ff6b6b', dotBg: '#ff6b6b', dotShadow: 'none',           pulse: false, labelKey: 'badgeOffline' },
    connecting:   { bg: 'rgba(255,255,255,.06)',  color: 'rgba(255,255,255,.55)', dotBg: 'rgba(255,255,255,.42)', dotShadow: 'none', pulse: true, labelKey: 'badgeConnecting' },
    off:          { bg: 'rgba(255,255,255,.06)',  color: 'var(--text-muted)', dotBg: 'var(--text-muted)', dotShadow: 'none', pulse: false, labelKey: 'badgeStatic' },
  };
  const cfg = states[state] || states.off;

  /* Reset class to base only — inline styles handle the rest */
  badge.className = 'live-badge';
  badge.style.background = cfg.bg;
  badge.style.color = cfg.color;

  let dot = badge.querySelector('.dot');
  if (!dot) {
    dot = document.createElement('span');
    dot.className = 'dot';
    badge.insertBefore(dot, badge.firstChild);
  }
  dot.style.background = cfg.dotBg;
  dot.style.boxShadow = cfg.dotShadow;
  dot.style.animation = cfg.pulse ? 'pulse-dot 2s ease-in-out infinite' : 'none';

  /* Set label text */
  const label = t(cfg.labelKey);
  /* Remove old text nodes and re-add */
  const children = Array.from(badge.childNodes);
  children.forEach(n => {
    if (n.nodeType === 3) badge.removeChild(n);
  });
  badge.appendChild(document.createTextNode(label));
}

function setStatus(message, isError){
  if (isError === undefined) isError = false;
  if (!message) return;
  if (data === null || isError) {
    const copy = document.getElementById('hero-copy');
    if (copy) {
      copy.textContent = message;
    }
  }
  if (isError) {
    showToast(message, 'err', 5000);
    console.error('[dashboard] ' + message);
  } else {
    console.debug('[dashboard] ' + message);
  }
}

function buildDashboardUrl(){
  return dashboardApiUrl;
}

function setStreamStatus(message, isError){
  if (isError === undefined) isError = false;
  if (isError) {
    isStreamConnected = false;
    updateLiveBadge('disconnected');
  } else {
    isStreamConnected = true;
    updateLiveBadge('connected');
  }
  setStatus(message, isError);
}

let _pollEtag = '';

async function fetchDashboardOnce(){
  if (!isLiveMode) return;
  if (getDashboardState() === 'ready') setDashboardState('refreshing');
  const url = buildDashboardUrl();
  try {
    const headers = {};
    if (_pollEtag) headers['If-None-Match'] = _pollEtag;
    const res = await fetch(url, {cache: 'no-cache', headers: headers});
    if (res.status === 304) {
      lastDataUpdate = Date.now();
      setStreamStatus(t('toastPollOk'));
      return;
    }
    if (!res.ok) {
      setDashboardError(res.status + ' ' + res.statusText);
      setStreamStatus(t('toastRefreshFail', {err: res.status + ' ' + res.statusText}), true);
      return;
    }
    const etag = res.headers.get('ETag');
    if (etag) _pollEtag = etag;
    const nextData = await res.json();
    if (!nextData || typeof nextData !== 'object') {
      setDashboardError(t('toastRefreshEmpty'));
      setStreamStatus(t('toastRefreshEmpty'), true);
      return;
    }
    if (setDashboard(nextData)) {
      renderDashboard();
    }
    setStreamStatus(t('toastPollOk'));
  } catch (err) {
    const msg = String(err && err.message ? err.message : err);
    setDashboardError(msg);
    setStreamStatus(t('toastRefreshFail', {err: msg}), true);
    return;
  }
}

function stopStream(){
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
  if (_sseBackoffTimer) {
    clearTimeout(_sseBackoffTimer);
    _sseBackoffTimer = null;
  }
  if (streamSource && streamSource.readyState !== EventSource.CLOSED) {
    streamSource.close();
  }
  streamSource = null;
}

function startPollingFallback(){
  if (!isLiveMode || refreshTimer !== null) return;
  setStreamStatus(t('toastPollFallback'));
  fetchDashboardOnce();
  // fallback 5000 is dead code: builder.py guarantees __POLL_MS__ >= 1000
  const intervalMs = Math.max(1000, Number(__POLL_MS__) || 5000);
  refreshTimer = setInterval(() => {
    void fetchDashboardOnce();
  }, intervalMs);
}

let _sseBackoffTimer = null;

function startSseDashboard(){
  if (!isLiveMode || streamSource) return;
  if (typeof EventSource === 'undefined') {
    startPollingFallback();
    return;
  }

  let _sseRetries = 0;
  const _SSE_MAX_RETRIES = 5;
  const _SSE_BASE_DELAY = 500;
  const _SSE_MAX_DELAY = 30000;

  function _connect() {
    updateLiveBadge('connecting');
    try {
      streamSource = new EventSource(dashboardStreamUrl);
    } catch (err) {
      setStreamStatus(t('toastSseInitFail', {err: String(err && err.message ? err.message : err)}), true);
      startPollingFallback();
      return;
    }

    streamSource.onopen = () => {
      _sseRetries = 0;
      setStreamStatus(t('toastSseInit'));
    };

    streamSource.onerror = () => {
      _sseRetries++;
      if (_sseRetries >= _SSE_MAX_RETRIES) {
        if (streamSource) { streamSource.close(); streamSource = null; }
        setStreamStatus(t('toastSseReconnect'), true);
        showToast(t('toastSseReconnect'), 'err', 0);
        startPollingFallback();
        return;
      }
      const delay = Math.min(_SSE_BASE_DELAY * Math.pow(2, _sseRetries - 1), _SSE_MAX_DELAY) + Math.random() * 500;
      updateLiveBadge('reconnecting');
      setStatus(t('toastSseReconnect'), true);
      if (streamSource) { streamSource.close(); streamSource = null; }
      clearTimeout(_sseBackoffTimer);
      _sseBackoffTimer = setTimeout(_connect, delay);
    };

    streamSource.onmessage = event => {
      _sseRetries = 0;
      try {
        const nextData = JSON.parse(event.data);
        if (getDashboardState() === 'ready') setDashboardState('refreshing');
        if (setDashboard(nextData)) {
          renderDashboard();
        }
        setStreamStatus(t('toastSseOk'));
      } catch (err) {
        const msg = String(err && err.message ? err.message : err);
        setDashboardError(msg);
        setStreamStatus(t('toastSseParseFail', {err: msg}), true);
      }
    };
  }

  _connect();
}

/* ── Cleanup on page unload ── */
window.addEventListener('unload', stopStream);
window.addEventListener('pagehide', stopStream);
