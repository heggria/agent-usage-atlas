/* ── Render progress bar ── */
let _progressBar = null;
let _progressTotal = 0;
let _progressDone = 0;

function _ensureProgressBar() {
  if (_progressBar) return _progressBar;
  _progressBar = document.createElement('div');
  _progressBar.className = 'render-progress';
  _progressBar.innerHTML = '<div class="render-progress-fill"></div>';
  document.body.appendChild(_progressBar);
  return _progressBar;
}

function _updateProgress(done, total) {
  const bar = _ensureProgressBar();
  const fill = bar.querySelector('.render-progress-fill');
  const pct = total > 0 ? Math.min((done / total) * 100, 100) : 0;
  fill.style.width = pct + '%';
  if (pct >= 100) {
    setTimeout(() => { bar.classList.remove('active'); }, 300);
  } else {
    bar.classList.add('active');
  }
}

/* ── Error boundary for eager render calls ── */
function _safeEager(id, fn) {
  try { fn(); } catch (err) {
    console.error('[dashboard] ' + id + ' render failed:', err);
    var el = document.getElementById(id);
    if (el) el.innerHTML = '<div style="padding:16px;color:var(--text-muted);font-size:12px">\u26A0 ' + id + ' unavailable</div>';
  }
}

function renderDashboard(){
  if (!data || !data.totals) {
    return;
  }
  try {
  /* Prune disposed chart references to prevent stale accumulation */
  pruneCharts();
  /* Remove skeleton placeholders once data arrives */
  _removeSkeletons();

  syncCSSTokens(data);
  /* Apply i18n to data-i18n elements */
  applyI18n();
  /* Token legend */
  const legendEl = document.getElementById('token-legend');
  if (legendEl) legendEl.innerHTML = [
    `<span><i class="dot" style="background:var(--uncached)"></i>${t('legendUncached')}</span>`,
    `<span><i class="dot" style="background:var(--cache-read)"></i>${t('legendCacheRead')}</span>`,
    `<span><i class="dot" style="background:var(--cache-write)"></i>${t('legendCacheWrite')}</span>`,
    `<span><i class="dot" style="background:var(--output)"></i>${t('legendOutputReason')}</span>`
  ].join('');
  /* Footer */
  const footerEl = document.getElementById('footer-text');
  if (footerEl) footerEl.innerHTML = t('footerText');

  /* Calculate total render steps for progress bar */
  const eagerCount = 7; /* eager charts */
  const lazyCount = 28; /* lazy charts */
  _progressTotal = eagerCount + lazyCount + 8; /* 8 = DOM-only sections */
  _progressDone = 0;
  _updateProgress(0, _progressTotal);

  /* DOM-only sections render immediately */
  _safeEager('hero-title', renderHero); _progressDone++; _updateProgress(_progressDone, _progressTotal);
  _safeEager('source-cards', renderSourceCards); _progressDone++; _updateProgress(_progressDone, _progressTotal);
  _safeEager('cost-cards', renderCostCards); _progressDone++; _updateProgress(_progressDone, _progressTotal);
  _safeEager('story-list', renderStory); _progressDone++; _updateProgress(_progressDone, _progressTotal);
  _safeEager('session-table', renderSessionTable); _progressDone++; _updateProgress(_progressDone, _progressTotal);
  _safeEager('vague-stats', renderVaguePrompts); _progressDone++; _updateProgress(_progressDone, _progressTotal);
  _safeEager('expensive-table', renderExpensivePrompts); _progressDone++; _updateProgress(_progressDone, _progressTotal);
  _safeEager('insight-cards', renderInsights); _progressDone++; _updateProgress(_progressDone, _progressTotal);

  /* Primary trend charts render eagerly (above the fold) */
  _safeEager('daily-cost-chart', renderDailyCostChart); _progressDone++; _updateProgress(_progressDone, _progressTotal);
  _safeEager('cost-breakdown-chart', renderCostBreakdownChart); _progressDone++; _updateProgress(_progressDone, _progressTotal);
  _safeEager('daily-token-chart', renderDailyTokenChart); _progressDone++; _updateProgress(_progressDone, _progressTotal);
  _safeEager('daily-cost-type-chart', renderDailyCostTypeChart); _progressDone++; _updateProgress(_progressDone, _progressTotal);
  _safeEager('token-burn-curve', renderTokenBurnCurve); _progressDone++; _updateProgress(_progressDone, _progressTotal);
  _safeEager('cost-calendar-chart', renderCostCalendar); _progressDone++; _updateProgress(_progressDone, _progressTotal);
  _safeEager('token-calendar-chart', renderTokenCalendar); _progressDone++; _updateProgress(_progressDone, _progressTotal);

  /* All remaining charts are lazy — only init when scrolled into view */
  lazyQueue.length = 0;
  registerLazy('model-cost-chart', renderModelCostChart);
  registerLazy('cost-sankey-chart', renderCostSankey);
  registerLazy('rose-chart', renderRoseChart);
  registerLazy('cache-gauge', renderEfficiencyGauges);
  registerLazy('token-sankey-chart', renderTokenSankey);
  registerLazy('heatmap-chart', renderHeatmap);
  registerLazy('source-radar-chart', renderSourceRadar);
  registerLazy('timeline-chart', renderTimeline);
  registerLazy('bubble-chart', renderBubble);
  registerLazy('tempo-chart', renderTempo);
  registerLazy('tool-ranking-chart', renderToolRanking);
  registerLazy('tool-density-chart', renderToolDensity);
  registerLazy('tool-bigram-chart', renderToolBigramChart);
  registerLazy('top-commands-chart', renderTopCommands);
  registerLazy('command-success-chart', renderCommandSuccessChart);
  registerLazy('efficiency-chart', renderEfficiencyChart);
  registerLazy('project-ranking-chart', renderProjectRanking);
  registerLazy('file-types-chart', renderFileTypesChart);
  registerLazy('branch-activity-chart', renderBranchActivityChart);
  registerLazy('productivity-chart', renderProductivityChart);
  registerLazy('burn-rate-chart', renderBurnRateChart);
  registerLazy('cost-per-tool-chart', renderCostPerToolChart);
  registerLazy('session-duration-chart', renderSessionDurationChart);
  registerLazy('model-radar-chart', renderModelRadarChart);
  registerLazy('turn-dur-chart', renderTurnDurChart);
  registerLazy('daily-turn-dur-chart', renderDailyTurnDurChart);
  registerLazy('task-rate-chart', renderTaskRateChart);
  registerLazy('codegen-model-chart', renderCodegenModelChart);
  registerLazy('codegen-daily-chart', renderCodegenDailyChart);
  registerLazy('ai-contribution-chart', renderAiContributionChart);
  flushLazy();

  /* Mark remaining lazy items as done for the progress bar */
  _progressDone = _progressTotal;
  _updateProgress(_progressDone, _progressTotal);

  requestAnimationFrame(() => {
    charts.forEach(chart => chart.resize());
    isFirstRender = false;
    if (typeof refreshSectionHeights === 'function') refreshSectionHeights();
  });
  } catch (err) {
    console.error('[dashboard] renderDashboard failed:', err);
  }
}

function renderRangeTabs(){
  const el = document.getElementById('range-tabs');
  if (!el) return;
  /* In static mode (no server), range switching is not possible — hide tabs */
  if (!isLiveMode) {
    const label = defaultSince ? t('rangeFrom', {since: defaultSince}) : t('rangeDays', {days: defaultDays});
    el.innerHTML = `<span class="range-tab active" style="cursor:default">${label}</span>`;
    return;
  }
  const allLabel = defaultSince ? t('rangeFrom', {since: defaultSince}) : t('rangeDays', {days: defaultDays});
  const tabs = [
    {key: 'all', label: allLabel},
    {key: 'week', label: t('rangeWeek')},
    {key: '3day', label: t('range3Day')},
    {key: 'today', label: t('rangeToday')}
  ];
  el.innerHTML = tabs.map(t =>
    `<button class="range-tab${t.key === activeRangeKey ? ' active' : ''}" data-range="${t.key}">${t.label}</button>`
  ).join('');
  el.querySelectorAll('.range-tab').forEach(btn => {
    btn.addEventListener('click', () => switchRange(btn.dataset.range));
  });
}

async function switchRange(key){
  if (key === activeRangeKey) return;
  setSelectedDate(null);
  setActiveRange(key);
  lastDashboardHash = '';
  /* Clear prev values so numbers animate on tab switch */
  _numPrevValues = new WeakMap();
  isFirstRender = false;
  /* Dispose all chart instances — range switch replaces the entire dataset */
  clearCharts();
  setDashboardState('loading');
  renderRangeTabs();
  if (isLiveMode) {
    stopStream();
    /* Fetch once immediately, then reconnect SSE */
    await fetchDashboardOnce();
    startSseDashboard();
  } else {
    /* Static mode: fetch from API if available, otherwise we can't switch */
    try {
      const res = await fetch(dashboardApiUrl, {cache: 'no-store'});
      if (res.ok) {
        const nextData = await res.json();
        if (setDashboard(nextData)) {
          renderDashboard();
        }
      }
    } catch (e) {
      setDashboardError(e.message || String(e));
      showToast(t('toastSwitchFail', {err: e.message || e}), 'err', 3000);
    }
  }
}

/* ── Skeleton loading placeholders ── */
function _showSkeletons() {
  const hero = document.getElementById('hero-title');
  if (hero && !hero.textContent.trim()) {
    hero.innerHTML = '<span class="skeleton-block" style="width:200px;height:28px"></span>';
  }
  const heroCopy = document.getElementById('hero-copy');
  if (heroCopy && !heroCopy.textContent.trim()) {
    heroCopy.innerHTML = '<span class="skeleton-block" style="width:320px;height:14px"></span>' +
      '<span class="skeleton-block" style="width:240px;height:14px;margin-top:6px"></span>';
  }
  const heroChips = document.getElementById('hero-chips');
  if (heroChips && !heroChips.children.length) {
    heroChips.innerHTML = Array.from({length: 4}, () =>
      '<span class="skeleton-block" style="width:100px;height:32px;border-radius:999px"></span>'
    ).join('');
  }
  const heroStats = document.getElementById('hero-stats');
  if (heroStats && !heroStats.children.length) {
    heroStats.innerHTML = Array.from({length: 4}, () =>
      '<div class="skeleton-block" style="height:52px;border-radius:10px"></div>'
    ).join('');
  }
  const sourceCards = document.getElementById('source-cards');
  if (sourceCards && !sourceCards.children.length) {
    sourceCards.innerHTML = Array.from({length: 3}, () =>
      '<div class="skeleton-block skeleton-card"></div>'
    ).join('');
  }
}

function _removeSkeletons() {
  document.querySelectorAll('.skeleton-block').forEach(el => {
    el.style.animation = 'none';
    el.style.opacity = '0';
    el.style.transition = 'opacity .3s ease';
    setTimeout(() => el.remove(), 300);
  });
}

function bootDashboard(){
  document.getElementById('lang-btn').textContent = '\u{1F310} ' + lang.toUpperCase();
  applyI18n();
  document.getElementById('hero-title').textContent = t('heroTitle');
  renderRangeTabs();
  if (data && data.totals) {
    if (!isLiveMode) updateLiveBadge('off');
    setDashboardState('ready');
    renderDashboard();
    return;
  }
  if (!isLiveMode) {
    updateLiveBadge('off');
    document.getElementById('hero-copy').textContent = t('heroNoData');
    return;
  }
  /* Live mode without data yet — show skeleton placeholders */
  setDashboardState('loading');
  _showSkeletons();
  startSseDashboard();
}

/* ── Debounced resize ── */
let _resizeTimer;
function _onResize() {
  clearTimeout(_resizeTimer);
  _resizeTimer = setTimeout(() => {
    charts.forEach(chart => {
      if (!chart.isDisposed()) chart.resize();
    });
  }, 250);
}
window.addEventListener('resize', _onResize);
window.addEventListener('beforeunload', stopStream);

/* ── Section collapse / expand ── */
const COLLAPSE_KEY = 'atlas-collapsed';
const DEFAULT_COLLAPSED = ['sec-insights', 'sec-leaderboard'];
const SECTION_EXPAND_MS = 420;
function _loadCollapsed(){try{return JSON.parse(localStorage.getItem(COLLAPSE_KEY))||{}}catch(e){return{}}}
function _saveCollapsed(state){try{localStorage.setItem(COLLAPSE_KEY,JSON.stringify(state))}catch(e){}}
let _collapseState = _loadCollapsed();

function expandSection(divEl, wrapEl){
  divEl.classList.remove('collapsed');
  divEl.setAttribute('aria-expanded', 'true');
  wrapEl.classList.remove('collapsed');
  /* Measure actual content height: read in first rAF, write in second rAF */
  wrapEl.style.willChange = 'max-height';
  requestAnimationFrame(() => {
    const height = wrapEl.scrollHeight; /* READ */
    requestAnimationFrame(() => {
      wrapEl.style.maxHeight = height + 'px'; /* WRITE */
    });
  });
  setTimeout(() => {
    wrapEl.style.maxHeight = 'none';
    wrapEl.style.willChange = '';
    const chartEls = wrapEl.querySelectorAll('.chart');
    chartEls.forEach(el => {
      const c = chartCache[el.id];
      if (c) c.resize();
    });
    if (lazyObserver) {
      chartEls.forEach(el => {
        if (!lazyRendered.has(el.id)) lazyObserver.observe(el);
      });
    }
  }, SECTION_EXPAND_MS);
}

function initCollapse(){
  const hasStoredState = Object.keys(_collapseState).length > 0;
  document.querySelectorAll('.divider[id]').forEach(div => {
    const id = div.id;
    const wrap = document.querySelector(`.section-wrap[data-section="${id}"]`);
    if (!wrap) return;
    /* Determine initial collapsed state: stored > default */
    const shouldCollapse = hasStoredState ? !!_collapseState[id] : DEFAULT_COLLAPSED.includes(id);
    if (shouldCollapse) {
      div.classList.add('collapsed');
      div.setAttribute('aria-expanded', 'false');
      wrap.classList.add('collapsed');
      wrap.style.maxHeight = '0';
    } else {
      div.setAttribute('aria-expanded', 'true');
      requestAnimationFrame(() => {
        const height = wrap.scrollHeight; /* READ */
        requestAnimationFrame(() => {
          wrap.style.maxHeight = height + 'px'; /* WRITE */
        });
      });
    }
    div.addEventListener('click', (e) => {
      /* Don't trigger on anchor link clicks inside nav */
      if (e.target.closest('a')) return;
      const isCollapsed = wrap.classList.toggle('collapsed');
      div.classList.toggle('collapsed', isCollapsed);
      div.setAttribute('aria-expanded', String(!isCollapsed));
      if (isCollapsed) {
        wrap.style.willChange = 'max-height';
        requestAnimationFrame(() => {
          const height = wrap.scrollHeight; /* READ */
          requestAnimationFrame(() => {
            wrap.style.maxHeight = height + 'px'; /* WRITE - set to current height first */
            requestAnimationFrame(() => {
              wrap.style.maxHeight = '0'; /* Then animate to 0 */
              setTimeout(() => { wrap.style.willChange = ''; }, SECTION_EXPAND_MS);
            });
          });
        });
        _collapseState[id] = true;
      } else {
        expandSection(div, wrap);
        _collapseState[id] = false;
      }
      _saveCollapsed(_collapseState);
    });
  });
}

/* ── "Show more" progressive disclosure within sections ── */
const SHOWMORE_KEY = 'atlas-showmore';
function _loadShowMore(){try{return JSON.parse(localStorage.getItem(SHOWMORE_KEY))||{}}catch(e){return{}}}
function _saveShowMore(state){localStorage.setItem(SHOWMORE_KEY,JSON.stringify(state))}

function initShowMore(){
  const state = _loadShowMore();
  document.querySelectorAll('.show-more-btn').forEach(btn => {
    const moreId = btn.dataset.more;
    const moreEl = document.getElementById(moreId);
    if (!moreEl) return;
    /* Restore saved state */
    if (state[moreId]) {
      _expandMore(btn, moreEl);
    }
    btn.addEventListener('click', () => {
      const isExpanded = moreEl.classList.contains('expanded');
      const sm = _loadShowMore();
      if (isExpanded) {
        _collapseMore(btn, moreEl);
        sm[moreId] = false;
      } else {
        _expandMore(btn, moreEl);
        sm[moreId] = true;
      }
      _saveShowMore(sm);
      /* Update parent section-wrap maxHeight */
      const parentWrap = btn.closest('.section-wrap');
      if (parentWrap && !parentWrap.classList.contains('collapsed')) {
        parentWrap.style.maxHeight = 'none';
      }
    });
  });
}

function _expandMore(btn, moreEl) {
  moreEl.classList.add('expanded');
  moreEl.style.willChange = 'max-height';
  requestAnimationFrame(() => {
    const height = moreEl.scrollHeight; /* READ */
    requestAnimationFrame(() => {
      moreEl.style.maxHeight = height + 'px'; /* WRITE */
    });
  });
  btn.classList.add('expanded');
  btn.setAttribute('aria-expanded', 'true');
  /* Update button text */
  const textEl = btn.querySelector('[data-i18n]');
  if (textEl) { textEl.setAttribute('data-i18n', 'showLess'); textEl.textContent = t('showLess'); }
  /* Trigger lazy observer for newly visible charts */
  setTimeout(() => {
    moreEl.style.maxHeight = 'none';
    moreEl.style.willChange = '';
    const chartEls = moreEl.querySelectorAll('.chart');
    chartEls.forEach(el => {
      const c = chartCache[el.id];
      if (c) c.resize();
      else if (lazyObserver && !lazyRendered.has(el.id)) lazyObserver.observe(el);
    });
  }, SECTION_EXPAND_MS);
}

function _collapseMore(btn, moreEl) {
  moreEl.style.willChange = 'max-height';
  requestAnimationFrame(() => {
    const height = moreEl.scrollHeight; /* READ */
    requestAnimationFrame(() => {
      moreEl.style.maxHeight = height + 'px'; /* WRITE - set current height first */
      requestAnimationFrame(() => {
        moreEl.style.maxHeight = '0'; /* Then animate to 0 */
        moreEl.classList.remove('expanded');
        setTimeout(() => { moreEl.style.willChange = ''; }, SECTION_EXPAND_MS);
      });
    });
  });
  btn.classList.remove('expanded');
  btn.setAttribute('aria-expanded', 'false');
  const textEl = btn.querySelector('[data-i18n]');
  if (textEl) { textEl.setAttribute('data-i18n', 'showMore'); textEl.textContent = t('showMore'); }
}

/* ── Quick nav scroll highlight + back-to-top ── */
let _scrollHandler = null;
let _navSectionObserver = null;
let _heroObserver = null;
function initQuickNav(){
  const backTop = document.getElementById('back-top');
  const navLinks = document.querySelectorAll('.quick-nav a');
  const sectionIds = Array.from(navLinks).map(a => a.getAttribute('href').slice(1));

  /* Create sliding indicator for active nav link */
  const navEl = document.getElementById('quick-nav');
  let navIndicator = null;
  if (navEl) {
    navIndicator = document.createElement('div');
    navIndicator.className = 'quick-nav-indicator';
    navEl.appendChild(navIndicator);
  }

  function _updateNavIndicator(activeLink) {
    if (!navIndicator || !activeLink || !navEl) return;
    const navRect = navEl.getBoundingClientRect();
    const linkRect = activeLink.getBoundingClientRect();
    navIndicator.style.top = (linkRect.top - navRect.top) + 'px';
    navIndicator.style.height = linkRect.height + 'px';
    navIndicator.classList.add('visible');
  }

  let _lastActiveId = null;

  /* ── IntersectionObserver for active section highlight ── */
  /* Track which sections are currently visible; the topmost one wins */
  const _visibleSections = new Map(); /* id → top offset at intersection time */

  if (typeof IntersectionObserver !== 'undefined') {
    _navSectionObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        const id = entry.target.id;
        if (entry.isIntersecting) {
          _visibleSections.set(id, entry.boundingClientRect.top);
        } else {
          _visibleSections.delete(id);
        }
      });
      /* Determine active section: among visible sections, pick the one
         that appears first in DOM order (sectionIds defines the order) */
      let currentId = null;
      for (const id of sectionIds) {
        if (_visibleSections.has(id)) { currentId = id; break; }
      }
      /* If no section intersects the top region, keep the last active */
      if (!currentId) return;

      navLinks.forEach(a => {
        const isActive = a.getAttribute('href') === '#' + currentId;
        a.classList.toggle('active', isActive);
        if (isActive && currentId !== _lastActiveId) {
          _updateNavIndicator(a);
          _lastActiveId = currentId;
        }
      });
    }, {
      /* Trigger when section header crosses the top 80px of the viewport */
      rootMargin: '-0px 0px -80% 0px',
      threshold: 0
    });

    sectionIds.forEach(id => {
      const el = document.getElementById(id);
      if (el) _navSectionObserver.observe(el);
    });

    /* ── IntersectionObserver for back-to-top button ── */
    const heroWrap = document.querySelector('.hero-wrap');
    if (backTop && heroWrap) {
      _heroObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          /* Show back-to-top when hero is NOT intersecting (scrolled past) */
          backTop.classList.toggle('show', !entry.isIntersecting);
        });
      }, {threshold: 0});
      _heroObserver.observe(heroWrap);
    }
  } else {
    /* Fallback for environments without IntersectionObserver */
    _scrollHandler = () => {
      if (backTop) {
        const heroWrap = document.querySelector('.hero-wrap');
        const heroBottom = heroWrap ? heroWrap.getBoundingClientRect().bottom + window.scrollY : 400;
        backTop.classList.toggle('show', window.scrollY > heroBottom);
      }
      let currentId = sectionIds[0];
      for (const id of sectionIds) {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top <= 80) currentId = id;
      }
      navLinks.forEach(a => {
        const isActive = a.getAttribute('href') === '#' + currentId;
        a.classList.toggle('active', isActive);
        if (isActive && currentId !== _lastActiveId) {
          _updateNavIndicator(a);
          _lastActiveId = currentId;
        }
      });
    };
    window.addEventListener('scroll', _scrollHandler, {passive: true});
  }

  /* Smooth scroll for nav links */
  navLinks.forEach(a => {
    a.addEventListener('click', (e) => {
      e.preventDefault();
      const id = a.getAttribute('href').slice(1);
      const el = document.getElementById(id);
      if (el) {
        /* Expand section if collapsed */
        const wrap = document.querySelector(`.section-wrap[data-section="${id}"]`);
        if (wrap && wrap.classList.contains('collapsed')) {
          expandSection(el, wrap);
          _collapseState[id] = false;
          _saveCollapsed(_collapseState);
        }
        el.scrollIntoView({behavior: 'smooth'});
      }
    });
  });
}

/* Update max-height after data re-render (for non-collapsed sections) */
function refreshSectionHeights(){
  document.querySelectorAll('.section-wrap').forEach(wrap => {
    if (!wrap.classList.contains('collapsed')) {
      wrap.style.maxHeight = 'none';
    }
  });
}

bootDashboard();
initCollapse();
initShowMore();
initQuickNav();
/* Dismiss loading screen after boot */
const _ls = document.getElementById('loading-screen');
if (_ls) _ls.style.display = 'none';

/* ── Cleanup on page unload ── */
window.addEventListener('pagehide', () => {
  window.removeEventListener('resize', _onResize);
  window.removeEventListener('beforeunload', stopStream);
  if (_scrollHandler) window.removeEventListener('scroll', _scrollHandler);
  if (_navSectionObserver) _navSectionObserver.disconnect();
  if (_heroObserver) _heroObserver.disconnect();
  clearTimeout(_resizeTimer);
  if (typeof _removeKeyboard === 'function') _removeKeyboard();
  stopStream();
});
