let isFirstRender = true;
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
const chartTheme = () => ({...THEME_BASE(), animationDuration: isFirstRender ? 700 : 0});
const initChart = id => {
  if (chartCache[id]) {
    return chartCache[id];
  }
  const chart = echarts.init(document.getElementById(id), null, {renderer: 'canvas'});
  chartCache[id] = chart;
  charts.push(chart);
  return chart;
};

function clearCharts(){
  charts.forEach(chart => chart.dispose());
  charts.length = 0;
  Object.keys(chartCache).forEach(key => delete chartCache[key]);
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

function flushLazy() {
  /* Re-render charts already visible (live-mode update) */
  if (lazyRendered.size > 0) {
    lazyRendered.forEach(id => {
      const fn = lazyRenderFns[id];
      if (fn) requestAnimationFrame(() => fn());
    });
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
    lazyQueue.forEach(item => item.renderFn());
    lazyQueue.length = 0;
    return;
  }

  if (lazyObserver) {
    lazyObserver.disconnect();
  }

  lazyObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const id = entry.target.id;
      if (lazyRendered.has(id)) return;
      lazyRendered.add(id);
      lazyObserver.unobserve(entry.target);
      const fn = lazyRenderFns[id];
      if (fn) {
        requestAnimationFrame(() => fn());
      }
    });
  }, {rootMargin: '200px 0px'});

  lazyQueue.forEach(item => {
    const el = document.getElementById(item.chartId);
    if (el) lazyObserver.observe(el);
  });
}
