function _costCardDailyValues(metric) {
  const days = data.days || [];
  const recent = days.slice(-7);
  if (metric === 'grand_cost') return recent.map(d => d.cost || 0);
  if (metric === 'average_cost_per_day') return recent.map(d => d.cost || 0);
  if (metric === 'cost_per_message') return recent.map(d => d.messages > 0 ? (d.cost / d.messages) : 0);
  if (metric === 'cache_savings_usd') return recent.map(d => d.cost_cache_read || 0);
  return [];
}

function _costCardComparison(metric) {
  const days = data.days || [];
  if (days.length < 2) return null;
  const recent7 = days.slice(-7);
  const prior7 = days.slice(-14, -7);
  if (prior7.length === 0) return null;

  const sumRecent = _costCardSliceSum(recent7, metric);
  const sumPrior = _costCardSliceSum(prior7, metric);
  if (sumPrior === 0) return null;
  const pctChange = (sumRecent - sumPrior) / sumPrior;
  return pctChange;
}

function _costCardSliceSum(slice, metric) {
  if (metric === 'grand_cost' || metric === 'average_cost_per_day') {
    return slice.reduce((s, d) => s + (d.cost || 0), 0);
  }
  if (metric === 'cost_per_message') {
    const totalCost = slice.reduce((s, d) => s + (d.cost || 0), 0);
    const totalMsgs = slice.reduce((s, d) => s + (d.messages || 0), 0);
    return totalMsgs > 0 ? totalCost / totalMsgs : 0;
  }
  if (metric === 'cache_savings_usd') {
    return slice.reduce((s, d) => s + (d.cost_cache_read || 0), 0);
  }
  return 0;
}

function _costBadgeHtml(pctChange) {
  if (pctChange === null) return '';
  const absPct = Math.abs(pctChange * 100);
  const display = absPct >= 100 ? Math.round(absPct) : absPct.toFixed(1);
  const isIncrease = pctChange > 0;
  /* For cost metrics, increase is bad (red), decrease is good (green) */
  const color = isIncrease ? 'var(--cost)' : 'var(--cache-read)';
  const bgColor = isIncrease ? 'rgba(255,107,107,.12)' : 'rgba(81,207,102,.12)';
  const arrow = isIncrease ? '\u2191' : '\u2193';
  const sign = isIncrease ? '+' : '-';
  return `<span class="cc-badge" style="display:inline-flex;align-items:center;gap:2px;padding:2px 8px;border-radius:999px;font-size:10px;font-weight:700;letter-spacing:.02em;background:${_escHtml(bgColor)};color:${_escHtml(color)};margin-left:8px;white-space:nowrap;vertical-align:middle;animation:ccBounceIn .3s ease both" title="vs prior 7 days">${_escHtml(sign)}${_escHtml(String(display))}% ${_escHtml(arrow)}</span>`;
}

function _cacheSavingsBarHtml(savingsUsd, totalCost) {
  const total = savingsUsd + totalCost;
  if (total <= 0) return '';
  const pct = Math.min(100, Math.max(0, (savingsUsd / total) * 100));
  const pctDisplay = pct.toFixed(1);
  return `<div class="cc-progress-wrap" style="margin-top:8px" title="Cache savings as % of potential cost: ${_escHtml(pctDisplay)}%">
    <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--text-muted);font-weight:700;letter-spacing:.06em;margin-bottom:3px">
      <span>SAVINGS RATIO</span><span>${_escHtml(pctDisplay)}%</span>
    </div>
    <div style="height:4px;border-radius:2px;background:var(--surface-strong);overflow:hidden">
      <div style="height:100%;width:${pct}%;border-radius:2px;background:linear-gradient(90deg,var(--cache-read),rgba(81,207,102,.5));transition:width .6s cubic-bezier(0.25,0.46,0.45,0.94)"></div>
    </div>
  </div>`;
}

/* Build sparkline SVG with <title> tooltips on each data point */
function _costCardSparklineSvg(values, color, width, height, fmt) {
  if (!values || values.length < 2) return '';
  const max = Math.max(...values, 0.001);
  const step = width / (values.length - 1);
  const r = 3; /* hover hit-area radius */
  const points = values.map((v, i) => `${i * step},${height - (v / max) * height * 0.8 - 1}`).join(' ');
  /* Invisible circles with <title> for native browser tooltip on hover */
  const circles = values.map((v, i) => {
    const cx = i * step;
    const cy = height - (v / max) * height * 0.8 - 1;
    const label = fmt ? fmt(v) : v.toFixed(2);
    const dayLabel = (typeof t === 'function' ? t('sparklineDay', {n: i + 1}) : 'Day ' + (i + 1)) + ': ' + label;
    return `<circle cx="${cx}" cy="${cy}" r="${r}" fill="transparent" stroke="transparent" style="cursor:crosshair"><title>${_escHtml(dayLabel)}</title></circle>`;
  }).join('');
  return `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" style="display:block;margin:4px auto"><polyline points="${points}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>${circles}</svg>`;
}

/* Inject keyframes for cost card animations (idempotent) */
function _ccEnsureKeyframes() {
  if (document.getElementById('cc-keyframes')) return;
  const style = document.createElement('style');
  style.id = 'cc-keyframes';
  style.textContent = [
    '@keyframes ccFadeInUp{0%{opacity:0;transform:translateY(14px)}100%{opacity:1;transform:translateY(0)}}',
    '@keyframes ccBounceIn{0%{opacity:0;transform:scale(.3)}50%{opacity:1;transform:scale(1.08)}70%{transform:scale(.95)}100%{opacity:1;transform:scale(1)}}',
    '.cc .big{transition:transform .25s ease,text-shadow .25s ease}',
    '.cc:hover .big{transform:scale(1.05)}',
    '.cc.cost:hover .big{text-shadow:0 0 18px rgba(255,107,107,.35)}',
    '.cc.save:hover .big{text-shadow:0 0 18px rgba(81,207,102,.35)}',
    '[data-theme="light"] .cc.cost:hover .big{text-shadow:0 0 14px rgba(255,107,107,.2)}',
    '[data-theme="light"] .cc.save:hover .big{text-shadow:0 0 14px rgba(81,207,102,.2)}',
    '.cc.cc-zero{opacity:.6}',
    '.cc.cc-zero:hover{opacity:.85}',
    '.cc-group-label{font-weight:600;transition:font-weight .2s ease,color .2s ease}',
    '.cc-group-label:hover{font-weight:800;color:var(--text)}',
    '@media(prefers-reduced-motion:reduce){.cc{animation:none !important;opacity:1 !important}}',
  ].join('\n');
  document.head.appendChild(style);
}

/* Determine whether a card value is effectively zero */
function _ccIsZeroValue(value) {
  return value === 0 || value === null || value === undefined || (typeof value === 'number' && Math.abs(value) < 0.005);
}

function renderCostCards(){
  _ccEnsureKeyframes();
  const T = data.totals;
  const sparkColor = {cost: C.cost, save: C.cacheRead};
  const metricKeys = {
    'cc-total': 'grand_cost',
    'cc-avg': 'average_cost_per_day',
    'cc-msg': 'cost_per_message',
    'cc-save': 'cache_savings_usd'
  };
  const defs = [
    {id: 'cc-total', label: t('lblTotalCost'), value: T.grand_cost, fmt: fmtUSD, hint: t('hintTotalCost', {days: data.range.day_count}), cls: 'cost', group: 'cost'},
    {id: 'cc-avg', label: t('lblDailyAvg'), value: T.average_cost_per_day, fmt: fmtUSD, hint: t('hintDailyAvg', {peak: T.cost_peak_day_label, cost: fmtUSD(T.cost_peak_day_total)}), cls: 'cost', group: 'cost'},
    {id: 'cc-msg', label: t('lblCostPerMsg'), value: T.cost_per_message, fmt: fmtUSD, hint: t('hintCostPerMsg', {cost: fmtUSD(T.median_session_cost)}), cls: 'cost', group: 'efficiency'},
    {id: 'cc-save', label: t('lblCacheSavings'), value: T.cache_savings_usd, fmt: fmtUSD, hint: t('hintCacheSavings', {pct: fmtPct(T.cache_savings_ratio)}), cls: 'save', group: 'efficiency'}
  ];
  const container = document.getElementById('cost-cards');
  const noMotion = typeof prefersReducedMotion === 'function' && prefersReducedMotion();
  if (!document.getElementById('cc-total')) {
    container.innerHTML = defs.map((c, idx) => {
      const metricKey = metricKeys[c.id];
      const sparkVals = _costCardDailyValues(metricKey);
      const sColor = c.cls === 'save' ? sparkColor.save : sparkColor.cost;
      const sparkline = _costCardSparklineSvg(sparkVals, sColor, 80, 22, c.fmt);
      const comparison = _costCardComparison(metricKey);
      const badge = _costBadgeHtml(comparison);
      const exactValue = c.fmt(c.value);
      const shortValue = c.value >= 1000 ? fmtShort(c.value) : null;
      /* Group divider: insert a subtle left border on the first efficiency card */
      const groupBorder = c.group === 'efficiency' && idx > 0 && defs[idx - 1].group !== 'efficiency'
        ? 'border-left:2px solid var(--border);'
        : '';
      /* Cache savings progress bar — only for the savings card */
      const progressBar = c.id === 'cc-save' ? _cacheSavingsBarHtml(T.cache_savings_usd, T.grand_cost) : '';
      /* Zero-value de-emphasis */
      const zeroCls = _ccIsZeroValue(c.value) ? ' cc-zero' : '';
      /* Staggered entrance animation */
      const animStyle = noMotion
        ? ''
        : `animation:ccFadeInUp .5s ease forwards;animation-delay:${idx * 80}ms;opacity:0;`;

      return `<article class="p cc ${_escHtml(c.cls)}${zeroCls}" style="${animStyle}${groupBorder}">
        <div class="metric-k">${_escHtml(c.label)}${badge}</div>
        <div class="big" id="${_escHtml(c.id)}"${shortValue ? ` title="${_escHtml(exactValue)}"` : ''}></div>
        <div class="cc-spark" id="${_escHtml(c.id)}-spark">${sparkline}</div>
        <div class="tiny" id="${_escHtml(c.id)}-hint">${c.hint}</div>
        ${progressBar}
      </article>`;
    }).join('');
  }
  defs.forEach(c => {
    const metricKey = metricKeys[c.id];

    /* Animate the main number */
    const bigEl = document.getElementById(c.id);
    if (bigEl) {
      const shortValue = c.value >= 1000 ? fmtShort(c.value) : null;
      if (shortValue) {
        bigEl.title = c.fmt(c.value);
      }
      animateNum(bigEl, c.value, c.fmt);
    }

    /* Update sparkline with tooltip-enabled version */
    const sparkEl = document.getElementById(c.id + '-spark');
    if (sparkEl) {
      const sparkVals = _costCardDailyValues(metricKey);
      const sColor = c.cls === 'save' ? sparkColor.save : sparkColor.cost;
      sparkEl.innerHTML = _costCardSparklineSvg(sparkVals, sColor, 80, 22, c.fmt);
    }

    /* Update hint */
    const hintEl = document.getElementById(c.id + '-hint');
    if (hintEl) hintEl.textContent = c.hint;

    /* Update zero-value de-emphasis on data refresh */
    const cardEl = bigEl ? bigEl.closest('.cc') : null;
    if (cardEl) {
      if (_ccIsZeroValue(c.value)) {
        cardEl.classList.add('cc-zero');
      } else {
        cardEl.classList.remove('cc-zero');
      }
    }
  });
}
