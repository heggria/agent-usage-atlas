let isFirstRender = true;
let _isLiveUpdate = false;
let _cachedTheme = null;
let _cachedThemeKey = null;
const setLiveUpdate = (flag) => { _isLiveUpdate = !!flag; };
const _isLight = () => document.documentElement.getAttribute('data-theme') === 'light';
const THEME_BASE = () => {
  const light = _isLight();
  return {
    textStyle: {color: light ? 'rgba(0,0,0,.6)' : TX, fontFamily: 'Inter,-apple-system,PingFang SC,sans-serif'},
    tooltip: {
      backgroundColor: light ? 'rgba(255,255,255,.96)' : 'rgba(15,18,28,.92)',
      borderColor: light ? 'rgba(0,0,0,.1)' : 'rgba(255,255,255,.08)',
      borderWidth: 1,
      textStyle: {color: light ? '#1a1a2e' : '#ece7df', fontSize: 12}
    }
  };
};
const chartTheme = () => {
  const light = _isLight();
  const reduced = prefersReducedMotion();
  const key = `${isFirstRender}|${light}|${reduced}|${_isLiveUpdate}`;
  if (_cachedThemeKey === key && _cachedTheme) return _cachedTheme;
  const animationDuration = _isLiveUpdate ? 0 : (isFirstRender && !reduced) ? 700 : (!reduced ? 300 : 0);
  _cachedTheme = {...THEME_BASE(), animationDuration, animation: !_isLiveUpdate};
  _cachedThemeKey = key;
  return _cachedTheme;
};

/* ── Chart skeleton placeholder ── */
function _showChartSkeleton(el) {
  if (el.querySelector('.chart-skeleton')) return;
  const skeleton = document.createElement('div');
  skeleton.className = 'chart-skeleton';
  skeleton.style.cssText = 'width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:12px';
  skeleton.innerHTML = '<div style="text-align:center"><div style="width:40px;height:40px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 8px"></div></div>';
  el.appendChild(skeleton);
}

/* ── ResizeObserver for individual chart containers ── */
let _resizeObserver = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(entries => {
  for (const entry of entries) {
    if (entry.contentRect.width > 0 && entry.contentRect.height > 0) {
      const chart = echarts.getInstanceByDom(entry.target);
      if (chart) chart.resize();
    }
  }
}) : null;

function _recreateResizeObserver() {
  if (typeof ResizeObserver === 'undefined') return;
  if (_resizeObserver) {
    _resizeObserver.disconnect();
  }
  _resizeObserver = new ResizeObserver(entries => {
    for (const entry of entries) {
      if (entry.contentRect.width > 0 && entry.contentRect.height > 0) {
        const chart = echarts.getInstanceByDom(entry.target);
        if (chart) chart.resize();
      }
    }
  });
}

const initChart = id => {
  if (chartCache[id]) {
    if (!chartCache[id].isDisposed()) return chartCache[id];
    /* Disposed instance found — clean up stale reference before re-init */
    const idx = charts.indexOf(chartCache[id]);
    if (idx !== -1) charts.splice(idx, 1);
    delete chartCache[id];
  }
  const el = document.getElementById(id);
  /* Dispose any orphaned echarts instance on this DOM element */
  const existing = echarts.getInstanceByDom(el);
  if (existing) existing.dispose();
  /* Remove skeleton if present */
  const skeleton = el.querySelector('.chart-skeleton');
  if (skeleton) skeleton.remove();
  const chart = echarts.init(el, null, {renderer: 'canvas'});
  chartCache[id] = chart;
  charts.push(chart);
  /* Observe container for resize */
  if (_resizeObserver) _resizeObserver.observe(el);
  /* Fade-in transition */
  el.style.opacity = '0';
  el.style.transition = 'opacity 0.3s ease';
  requestAnimationFrame(() => { el.style.opacity = '1'; });
  return chart;
};

function clearCharts(){
  charts.forEach(chart => { if (!chart.isDisposed()) chart.dispose(); });
  charts.length = 0;
  Object.keys(chartCache).forEach(key => delete chartCache[key]);
  /* Fully disconnect and recreate ResizeObserver to release all tracked elements */
  if (_resizeObserver) {
    _resizeObserver.disconnect();
    _recreateResizeObserver();
  }
  /* Reset lazy state so charts re-render from scratch */
  lazyRendered.clear();
}

/** Remove disposed/orphaned entries from charts[] and chartCache without touching live instances */
function pruneCharts(){
  for (let i = charts.length - 1; i >= 0; i--) {
    if (charts[i].isDisposed()) charts.splice(i, 1);
  }
  Object.keys(chartCache).forEach(key => {
    if (chartCache[key].isDisposed()) delete chartCache[key];
  });
}

function refreshChartThemes(){
  _cachedTheme = null;
  _cachedThemeKey = null;
  requestAnimationFrame(() => {
    const theme = chartTheme();
    Object.keys(chartCache).forEach(key => {
      const chart = chartCache[key];
      if (chart && !chart.isDisposed()) {
        chart.setOption(theme, {replaceMerge: [], lazyUpdate: true});
      }
    });
  });
}

/* ── Lazy chart rendering via IntersectionObserver ── */
const lazyQueue = [];
let lazyObserver = null;
const lazyRendered = new Set();
const lazyRenderFns = {};

function registerLazy(chartId, renderFn) {
  lazyRenderFns[chartId] = renderFn;
  lazyQueue.push({chartId, renderFn});
}

/** Wrap a render function with error boundary */
function _safeRender(id, fn) {
  try {
    fn();
  } catch (err) {
    console.error(`Chart ${id} failed:`, err);
    const el = document.getElementById(id);
    if (el) {
      /* Remove skeleton if still present */
      const skeleton = el.querySelector('.chart-skeleton');
      if (skeleton) skeleton.remove();
      el.innerHTML = '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:12px"><div style="text-align:center"><i class="fa-solid fa-triangle-exclamation" style="font-size:18px;opacity:.5;margin-bottom:6px;display:block"></i>Chart unavailable</div></div>';
    }
  }
}

function flushLazy() {
  /* Re-render charts already visible (live-mode update) */
  if (lazyRendered.size > 0) {
    _isLiveUpdate = true;
    _cachedTheme = null;
    _cachedThemeKey = null;
    lazyRendered.forEach(id => {
      const fn = lazyRenderFns[id];
      if (fn) requestAnimationFrame(() => _safeRender(id, fn));
    });
    _isLiveUpdate = false;
    _cachedTheme = null;
    _cachedThemeKey = null;
    /* Observe any newly registered charts not yet seen */
    if (lazyObserver) {
      lazyQueue.forEach(item => {
        if (lazyRendered.has(item.chartId)) return;
        const el = document.getElementById(item.chartId);
        if (el) lazyObserver.observe(el);
      });
    }
    return;
  }

  /* First render: set up observer from scratch */
  if (typeof IntersectionObserver === 'undefined') {
    lazyQueue.forEach(item => _safeRender(item.chartId, item.renderFn));
    lazyQueue.length = 0;
    return;
  }

  if (lazyObserver) {
    lazyObserver.disconnect();
  }
  /* Clear stale queue entries before creating new observer */
  lazyQueue.length = 0;
  Object.keys(lazyRenderFns).forEach(id => {
    lazyQueue.push({chartId: id, renderFn: lazyRenderFns[id]});
  });

  lazyObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const id = entry.target.id;
      if (lazyRendered.has(id)) return;
      /* Show skeleton while chart initialises */
      _showChartSkeleton(entry.target);
      lazyRendered.add(id);
      lazyObserver.unobserve(entry.target);
      const fn = lazyRenderFns[id];
      if (fn) {
        requestAnimationFrame(() => _safeRender(id, fn));
      }
    });
  }, {rootMargin: '50px 0px'});

  lazyQueue.forEach(item => {
    const el = document.getElementById(item.chartId);
    if (el) lazyObserver.observe(el);
  });
}
