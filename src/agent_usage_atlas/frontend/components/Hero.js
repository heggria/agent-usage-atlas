/* ── CSS source whitelist ── */
const _KNOWN_SOURCES = new Set(['codex', 'claude', 'cursor', 'hermit']);
function _safeCssSource(name) {
  const lower = (name || '').toLowerCase();
  return _KNOWN_SOURCES.has(lower) ? lower : 'text-muted';
}

/* ── Trend helpers ── */
function _calcTrend(days, accessor) {
  if (!days || days.length < 2) return {pct: 0, dir: 'flat'};
  const mid = Math.ceil(days.length / 2);
  const firstHalf = days.slice(0, mid);
  const secondHalf = days.slice(mid);
  const sumFirst = firstHalf.reduce((s, d) => s + (accessor(d) || 0), 0) / firstHalf.length;
  const sumSecond = secondHalf.reduce((s, d) => s + (accessor(d) || 0), 0) / secondHalf.length;
  if (sumFirst === 0 && sumSecond === 0) return {pct: 0, dir: 'flat'};
  if (sumFirst === 0) return {pct: 100, dir: 'up'};
  const pct = ((sumSecond - sumFirst) / Math.abs(sumFirst)) * 100;
  const dir = pct > 2 ? 'up' : pct < -2 ? 'down' : 'flat';
  return {pct: Math.abs(pct), dir};
}

function _trendHtml(trend, positiveIsGood) {
  const arrows = {up: '<i class="fa-solid fa-arrow-up" aria-hidden="true"></i>', down: '<i class="fa-solid fa-arrow-down" aria-hidden="true"></i>', flat: '\u2014'};
  const arrow = arrows[trend.dir];
  const isGood = trend.dir === 'flat' ||
    (positiveIsGood && trend.dir === 'up') ||
    (!positiveIsGood && trend.dir === 'down');
  const cls = trend.dir === 'flat' ? 'trend-neutral' : (isGood ? 'trend-good' : 'trend-bad');
  const pctStr = trend.pct > 0.1 ? trend.pct.toFixed(1) + '%' : '';
  /* Pulse animation on first render for trend indicators */
  const pulseStyle = 'animation:trendPulse 0.8s ease-out 1';
  return `<span class="trend-indicator ${_escHtml(cls)}" style="${pulseStyle}">${arrow}${pctStr ? ' ' + _escHtml(pctStr) : ''}</span>`;
}

function _fmtDateRange(startIso, endIso) {
  const opts = {month: 'short', day: 'numeric'};
  try {
    const s = new Date(startIso);
    const e = new Date(endIso);
    if (isNaN(s.getTime()) || isNaN(e.getTime())) return _escHtml(startIso) + ' \u2014 ' + _escHtml(endIso);
    const sf = s.toLocaleDateString('en-US', opts);
    const ef = e.toLocaleDateString('en-US', opts);
    /* Add year if they span different years */
    if (s.getFullYear() !== e.getFullYear()) {
      return _escHtml(sf + ', ' + s.getFullYear()) + ' \u2014 ' + _escHtml(ef + ', ' + e.getFullYear());
    }
    return _escHtml(sf) + ' \u2014 ' + _escHtml(ef);
  } catch (_) {
    return _escHtml(startIso) + ' \u2014 ' + _escHtml(endIso);
  }
}

function _tesGradeBadgeHtml(d) {
  if (!d || !d.token_economy || !d.token_economy.grade) return '';
  const gradeRaw = String(d.token_economy.grade);
  const score = d.token_economy.overall_tes != null ? d.token_economy.overall_tes : '';
  const gradeClass = 'tes-' + gradeRaw.toLowerCase();
  return `<span class="tes-badge ${_escHtml(gradeClass)}" title="Token Economy Score: ${_escHtml(String(score))}">${_escHtml(gradeRaw)}${score ? '<small>' + _escHtml(String(score)) + '</small>' : ''}</span>`;
}

/* ── Inject hero-specific keyframes once ── */
(function _injectHeroKeyframes() {
  if (document.getElementById('hero-ux-keyframes')) return;
  const style = document.createElement('style');
  style.id = 'hero-ux-keyframes';
  style.textContent = [
    '@keyframes chipFadeInUp{0%{opacity:0;transform:translateY(10px)}100%{opacity:1;transform:translateY(0)}}',
    '@keyframes trendPulse{0%{opacity:1}30%{opacity:0.4}60%{opacity:1}100%{opacity:1}}',
    '.hero-title-wrap{position:relative;display:inline-block}',
    '.hero-title-wrap.live-active::after{content:"";position:absolute;top:50%;right:-18px;transform:translateY(-50%);width:8px;height:8px;border-radius:50%;background:#51cf66;box-shadow:0 0 6px rgba(81,207,102,.6);animation:liveDotPulse 2s ease-in-out infinite}',
    '[data-theme="light"] .hero-title-wrap.live-active::after{box-shadow:0 0 6px rgba(81,207,102,.4)}',
    '@keyframes liveDotPulse{0%,100%{opacity:1;box-shadow:0 0 6px rgba(81,207,102,.6)}50%{opacity:0.45;box-shadow:0 0 12px rgba(81,207,102,.9)}}',
    '@media(prefers-reduced-motion:reduce){.hero-title-wrap.live-active::after{animation:none}}',
  ].join('\n');
  document.head.appendChild(style);
})();

function renderHero(){
  const titleEl = document.getElementById('hero-title');
  titleEl.textContent = t('heroTitle');

  /* ── Live mode pulse indicator ── */
  const titleWrap = titleEl.parentElement || titleEl;
  if (!titleWrap.classList.contains('hero-title-wrap')) {
    titleWrap.classList.add('hero-title-wrap');
  }
  if (typeof isLiveMode !== 'undefined' && isLiveMode) {
    titleWrap.classList.add('live-active');
  } else {
    titleWrap.classList.remove('live-active');
  }

  if (!data || !data.totals) {
    document.getElementById('hero-copy').textContent = t('heroWaiting');
    return;
  }
  const T = data.totals;

  /* ── Compute trends from data.days ── */
  const days = data.days || [];
  const tokenTrend = _calcTrend(days, d => d.total_tokens);
  const costTrend = _calcTrend(days, d => d.cost);
  const cacheTrend = _calcTrend(days, d => {
    const total = (d.cache_read || 0) + (d.uncached_input || 0);
    return total > 0 ? (d.cache_read || 0) / total : 0;
  });

  /* ── Date range display ── */
  const dateRangeStr = _fmtDateRange(data.range.start_local, data.range.end_local);

  /* ── Hero copy with formatted date range ── */
  const heroCopyEl = document.getElementById('hero-copy');
  heroCopyEl.innerHTML =
    '<span class="hero-date-range"><i class="fa-regular fa-calendar"></i> ' + dateRangeStr + '</span> ' +
    _escHtml(t('heroCopyTpl', {
      start: data.range.start_local, end: data.range.end_local,
      tokens: fmtShort(T.grand_total), cost: fmtUSD(T.grand_cost), cache: fmtPct(T.cache_ratio)
    }));

  /* ── TES grade badge (if available) ── */
  const tesBadge = _tesGradeBadgeHtml(data);

  const chipsEl = document.getElementById('hero-chips');
  const chipDefs = [
    {id: 'chip-tokens', icon: 'fa-fire', color: 'var(--codex)', value: T.grand_total, fmt: fmtShort, suffix: t('chipTokens'), trend: _trendHtml(tokenTrend, true), rawValue: T.grand_total},
    {id: 'chip-cost', icon: 'fa-dollar-sign', color: 'var(--cost)', value: T.grand_cost, fmt: fmtUSD, suffix: t('chipCost'), trend: _trendHtml(costTrend, false), rawValue: T.grand_cost},
    {id: 'chip-cache', icon: 'fa-database', color: 'var(--cache-read)', value: T.cache_ratio, fmt: fmtPct, suffix: t('chipCached'), trend: _trendHtml(cacheTrend, true), rawValue: T.cache_ratio},
    {id: 'chip-tools', icon: 'fa-wrench', color: 'var(--accent)', value: T.tool_call_total, fmt: fmtInt, suffix: t('chipTools'), trend: '', rawValue: T.tool_call_total}
  ];
  if (!document.getElementById('chip-tokens')) {
    const noMotion = typeof prefersReducedMotion === 'function' && prefersReducedMotion();
    chipsEl.innerHTML = (tesBadge ? tesBadge : '') + chipDefs.map((c, i) => {
      /* Staggered chip animation: each chip 80ms after the previous */
      const animStyle = noMotion
        ? ''
        : `animation:chipFadeInUp 0.4s ease forwards;animation-delay:${i * 80}ms;opacity:0`;
      return `<span class="chip" style="${animStyle}" title="${_escHtml(String(c.rawValue))}"><i class="fa-solid ${_escHtml(c.icon)}" style="color:${c.color}"></i><span id="${_escHtml(c.id)}"></span>${_escHtml(c.suffix)}${c.trend}</span>`;
    }).join('');
  }
  chipDefs.forEach(c => animateNum(document.getElementById(c.id), c.value, c.fmt));

  /* ── Summary side cards with enhanced hierarchy ── */
  const costPerDay = T.average_cost_per_day || (days.length > 0 ? T.grand_cost / days.length : 0);
  const cardDefs = [
    {id: 'sv-tokens', label: t('lblTotalTokens'), value: T.grand_total, fmt: fmtShort,
      hint: t('hintTotalTokens', {avg: fmtShort(T.average_per_day), peak: T.peak_day_label}),
      trend: _trendHtml(tokenTrend, true)},
    {id: 'sv-cost', label: t('lblEstCost'), value: T.grand_cost, fmt: fmtUSD,
      hint: t('hintEstCost', {avg: fmtUSD(T.average_cost_per_day), proj: fmtUSD(T.burn_rate_projection_30d)}),
      trend: _trendHtml(costTrend, false),
      secondary: '<span class="val-secondary"><i class="fa-solid fa-chart-line"></i> ' + _escHtml(fmtUSD(costPerDay)) + '/d</span>'},
    {id: 'sv-cache', label: t('lblCacheStack'), value: T.cache_read + T.cache_write, fmt: fmtShort,
      hint: t('hintCacheStack', {save: fmtUSD(T.cache_savings_usd), rate: fmtPct(T.cache_ratio)}),
      trend: _trendHtml(cacheTrend, true)},
    {id: 'sv-session', label: t('lblMedianSession'), value: T.median_session_tokens, fmt: fmtShort,
      hint: t('hintMedianSession', {min: T.median_session_minutes, cost: fmtUSD(T.median_session_cost)}),
      trend: ''}
  ];
  const sideEl = document.getElementById('summary-side');
  if (!document.getElementById('sv-tokens')) {
    sideEl.innerHTML = cardDefs.map(c => `
      <div class="sc">
        <div class="lbl">${_escHtml(c.label)} ${c.trend}</div>
        <div class="val val-hero" id="${_escHtml(c.id)}"></div>
        ${c.secondary || ''}
        <div class="hint" id="${_escHtml(c.id)}-hint">${_escHtml(c.hint)}</div>
      </div>`).join('');
  }
  cardDefs.forEach(c => {
    animateNum(document.getElementById(c.id), c.value, c.fmt);
    const hintEl = document.getElementById(c.id + '-hint');
    if (hintEl) hintEl.textContent = c.hint;
  });

  /* ── hero-stats mini grid with session context and hover tooltips ── */
  const projectCount = (data.projects && data.projects.count) ? data.projects.count : T.project_count;
  const heroStatsDefs = [
    {id: 'hs-sessions', label: t('lblHeroSessions'), value: T.tracked_session_count, fmt: fmtInt, context: projectCount > 0 ? _escHtml(t('lblHeroAcrossProjects', {n: fmtInt(projectCount)})) : '', rawValue: T.tracked_session_count},
    {id: 'hs-projects', label: t('lblHeroProjects'), value: projectCount, fmt: fmtInt, rawValue: projectCount},
    {id: 'hs-days', label: t('lblHeroDays'), value: data.range.day_count, fmt: fmtInt, rawValue: data.range.day_count},
    {id: 'hs-burn', label: t('lblHeroAvgBurn'), value: T.avg_daily_burn, fmt: fmtUSD, suffix: '/d', rawValue: T.avg_daily_burn}
  ];
  const hsEl = document.getElementById('hero-stats');
  if (!document.getElementById('hs-sessions')) {
    hsEl.innerHTML = heroStatsDefs.map(c =>
      `<div class="hero-stat" title="${_escHtml(String(c.rawValue))}"><div class="k">${_escHtml(c.label)}</div><div class="v" id="${_escHtml(c.id)}"></div>${c.context ? '<div class="hero-stat-ctx">' + c.context + '</div>' : ''}</div>`
    ).join('');
  }
  heroStatsDefs.forEach(c => {
    const el = document.getElementById(c.id);
    if (el) {
      /* Update tooltip with latest raw value */
      const statEl = el.closest('.hero-stat');
      if (statEl) statEl.title = String(c.rawValue);
      if (c.suffix) {
        animateNum(el, c.value, v => c.fmt(v) + c.suffix);
      } else {
        animateNum(el, c.value, c.fmt);
      }
    }
  });

  /* ── source proportion bar ── */
  const sbEl = document.getElementById('source-bar');
  if (data.source_cards && data.source_cards.length && T.grand_total > 0 && !sbEl.querySelector('.source-bar')) {
    const segs = data.source_cards.map(card => {
      const pct = (card.total / T.grand_total * 100);
      const name = card.source.toLowerCase();
      return {name, pct, label: card.source};
    }).filter(s => s.pct > 0);
    sbEl.innerHTML =
      `<div class="source-bar">${segs.map(s =>
        `<div class="seg" style="width:${s.pct.toFixed(2)}%;background:var(--${_safeCssSource(s.name)})"></div>`
      ).join('')}</div>` +
      `<div class="source-bar-legend">${segs.map(s =>
        `<span class="source-bar-label"><span class="sbl-dot" style="background:var(--${_safeCssSource(s.name)})"></span>${_escHtml(s.label)} ${s.pct.toFixed(1)}%</span>`
      ).join('')}</div>`;
  }
}
