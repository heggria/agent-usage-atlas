let toastTimer = null;
function showToast(message, type = 'info', duration = 3000){
  const el = document.getElementById('toast');
  if (!el) return;
  clearTimeout(toastTimer);
  el.className = 'toast ' + type;
  const icon = type === 'ok' ? '<i class="fa-solid fa-check"></i>'
    : type === 'err' ? '<i class="fa-solid fa-xmark"></i>'
    : '<span class="spinner"></span>';
  el.innerHTML = icon + ' ' + message;
  requestAnimationFrame(() => el.classList.add('show'));
  if (duration > 0) {
    toastTimer = setTimeout(() => el.classList.remove('show'), duration);
  }
}

function updateLiveBadge(state){
  const badge = document.getElementById('live-badge');
  if (!badge) return;
  badge.className = 'live-badge ' + state;
  badge.querySelector('.dot') || badge.insertAdjacentHTML('afterbegin','<span class="dot"></span>');
  const label = state === 'connected' ? t('badgeLive') : state === 'disconnected' ? t('badgeOffline') : t('badgeStatic');
  const spans = badge.childNodes;
  if (spans.length > 1) spans[spans.length - 1].textContent = label;
  else badge.appendChild(document.createTextNode(label));
}

function setStatus(message, isError = false){
  if (!message) return;
  if (data === null || isError) {
    const copy = document.getElementById('hero-copy');
    if (copy) {
      copy.textContent = message;
    }
  }
  if (isError) {
    showToast(message, 'err', 5000);
    console.error(`[dashboard] ${message}`);
  } else {
    console.debug(`[dashboard] ${message}`);
  }
}

function buildDashboardUrl(){
  return dashboardApiUrl;
}

function setStreamStatus(message, isError = false){
  if (isError) {
    isStreamConnected = false;
    updateLiveBadge('disconnected');
  } else {
    isStreamConnected = true;
    updateLiveBadge('connected');
  }
  setStatus(message, isError);
}

async function fetchDashboardOnce(){
  if (!isLiveMode) return;
  const url = buildDashboardUrl();
  try {
    const res = await fetch(url, {cache: 'no-store'});
    if (!res.ok) {
      setStreamStatus(t('toastRefreshFail', {err: res.status + ' ' + res.statusText}), true);
      return;
    }
    const nextData = await res.json();
    if (!nextData || typeof nextData !== 'object') {
      setStreamStatus(t('toastRefreshEmpty'), true);
      return;
    }
    if (setDashboard(nextData)) {
      renderDashboard();
    }
    setStreamStatus(t('toastPollOk'));
  } catch (err) {
    setStreamStatus(t('toastRefreshFail', {err: String(err && err.message ? err.message : err)}), true);
    return;
  }
}

function stopStream(){
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
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
  const intervalMs = Math.max(1000, Number(__POLL_MS__) || 5000);
  refreshTimer = setInterval(() => {
    void fetchDashboardOnce();
  }, intervalMs);
}

function startSseDashboard(){
  if (!isLiveMode || streamSource) return;
  if (typeof EventSource === 'undefined') {
    startPollingFallback();
    return;
  }

  try {
    streamSource = new EventSource(dashboardStreamUrl);
  } catch (err) {
    setStreamStatus(t('toastSseInitFail', {err: String(err && err.message ? err.message : err)}), true);
    startPollingFallback();
    return;
  }

  streamSource.onopen = () => {
    setStreamStatus(t('toastSseInit'));
  };

  streamSource.onerror = () => {
    setStreamStatus(t('toastSseReconnect'), true);
  };

  streamSource.onmessage = event => {
    try {
      const nextData = JSON.parse(event.data);
      if (setDashboard(nextData)) {
        renderDashboard();
      }
      setStreamStatus(t('toastSseOk'));
    } catch (err) {
      setStreamStatus(t('toastSseParseFail', {err: String(err && err.message ? err.message : err)}), true);
    }
  };
}
