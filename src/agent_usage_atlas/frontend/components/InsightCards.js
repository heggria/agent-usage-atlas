/* ── Inject supplemental styles once (scoped to insight UX enhancements) ── */
(function _injectInsightStyles() {
  if (document.getElementById('insight-ux-styles')) return;
  const s = document.createElement('style');
  s.id = 'insight-ux-styles';
  s.textContent = [
    /* Smooth expand/collapse: add opacity transition alongside max-height */
    '.insight-detail{opacity:0;transition:max-height .35s cubic-bezier(.22,1,.36,1),opacity .25s ease}',
    '.insight-card.expanded .insight-detail{opacity:1}',

    /* Critical severity: subtle pulsing border glow */
    '@keyframes insight-critical-border-pulse{' +
      '0%,100%{border-left-color:#dc2626;box-shadow:inset 3px 0 8px -4px rgba(220,38,38,.0)}' +
      '50%{border-left-color:#ef4444;box-shadow:inset 3px 0 8px -4px rgba(220,38,38,.35)}' +
    '}',
    '.insight-critical-pulse{animation:insight-enter .45s cubic-bezier(.22,1,.36,1) both,' +
      'insight-critical-border-pulse 2.5s ease-in-out 1s infinite}',

    /* Override the card entry animation to use translateY for fadeInUp */
    '@keyframes insight-enter{' +
      '0%{opacity:0;transform:translateY(14px)}' +
      '100%{opacity:1;transform:translateY(0)}' +
    '}',

    /* Tip lightbulb icon for actionable suggestions */
    '.insight-tip-icon{color:#eab308;font-size:12px;margin-top:2px;flex-shrink:0;' +
      'filter:drop-shadow(0 0 3px rgba(234,179,8,.4))}',
    '[data-theme="light"] .insight-tip-icon{color:#ca8a04;filter:drop-shadow(0 0 2px rgba(202,138,4,.25))}',

    /* Respect reduced motion */
    '@media(prefers-reduced-motion:reduce){' +
      '.insight-critical-pulse{animation:none}' +
      '.insight-detail{transition:none}' +
      '.insight-gauge-fill{transition:none}' +
    '}',
  ].join('\n');
  document.head.appendChild(s);
})();

/* ── Insight category classification ── */
const _INSIGHT_CATEGORIES = {
  'fa-money-bill-wave': 'cost',
  'fa-fire': 'cost',
  'fa-scale-balanced': 'cost',
  'fa-chart-line': 'cost',
  'fa-database': 'efficiency',
  'fa-gears': 'efficiency',
  'fa-expand': 'efficiency',
  'fa-comment-slash': 'efficiency',
  'fa-hourglass-half': 'behavioral',
  'fa-moon': 'behavioral',
  'fa-bullseye': 'behavioral',
  'fa-triangle-exclamation': 'behavioral',
};

function _insightCategory(icon) {
  return _INSIGHT_CATEGORIES[icon] || 'behavioral';
}

/* ── Impact score color (green 0 -> yellow 40 -> orange 65 -> red 85+) ── */
function _scoreColor(score) {
  if (score >= 85) return '#dc2626';
  if (score >= 65) return '#f59e0b';
  if (score >= 40) return '#eab308';
  return '#22c55e';
}

/* ── Highlight dollar amounts in body text ── */
function _highlightDollars(html) {
  return html.replace(
    /(\$[\d,]+(?:\.\d+)?)/g,
    '<span class="insight-dollar">$1</span>'
  );
}

/* ── Group insights by similar type (same icon) ── */
function _groupInsights(insights) {
  const groups = {};
  const order = [];
  for (const ins of insights) {
    const key = ins.icon || 'fa-circle-info';
    if (!groups[key]) {
      groups[key] = [];
      order.push(key);
    }
    groups[key].push(ins);
  }
  /* Flatten back, but attach group count to the first of each group */
  const result = [];
  for (const key of order) {
    const group = groups[key];
    for (let i = 0; i < group.length; i++) {
      result.push({
        ...group[i],
        _groupCount: i === 0 ? group.length : 0,
      });
    }
  }
  return result;
}

/* ── Animate score number from 0 to target over ~800ms ── */
function _animateScoreNum(el, target) {
  if (!el) return;
  if (prefersReducedMotion() || target === 0) { el.textContent = target; return; }
  const start = performance.now();
  const duration = 800;
  const step = (now) => {
    const elapsed = Math.min(now - start, duration);
    const progress = elapsed / duration;
    /* Ease-out cubic for a satisfying deceleration */
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(eased * target);
    if (elapsed < duration) requestAnimationFrame(step);
  };
  el.textContent = '0';
  requestAnimationFrame(step);
}

/* ── Kick gauge arcs: start at 0, transition to real value ── */
function _animateGauges(container) {
  const fills = container.querySelectorAll('.insight-gauge-fill[data-target-dash]');
  if (prefersReducedMotion()) {
    /* Skip animation; set final value immediately */
    for (const circle of fills) {
      const target = circle.getAttribute('data-target-dash');
      if (target) circle.setAttribute('stroke-dasharray', target);
    }
    return;
  }
  /* Small delay lets the browser paint the initial 0-state first */
  setTimeout(() => {
    for (const circle of fills) {
      const target = circle.getAttribute('data-target-dash');
      if (target) circle.setAttribute('stroke-dasharray', target);
    }
  }, 100);
}

/* ── Animate score numbers after DOM insertion ── */
function _animateScoreNums(container) {
  const nums = container.querySelectorAll('.insight-score-num[data-target-score]');
  for (const el of nums) {
    const target = parseInt(el.getAttribute('data-target-score'), 10);
    _animateScoreNum(el, target);
  }
}

function renderInsights() {
  const insights = data.insights;
  const el = document.getElementById('insight-cards');
  if (!el) return;

  /* Empty state */
  if (!insights || !insights.length) {
    el.innerHTML = `
      <div class="insight-empty">
        <i class="fa-solid fa-circle-check"></i>
        <div class="insight-empty-title">${_escHtml(t('insightAllClear'))}</div>
        <div class="insight-empty-sub">${_escHtml(t('insightAllClearSub'))}</div>
      </div>
    `;
    return;
  }

  const severityLabel = {
    critical: t('lblInsightCritical'),
    high: t('lblInsightHigh'),
    medium: t('lblInsightMedium'),
    low: t('lblInsightLow'),
    info: t('lblInsightInfo'),
  };

  const grouped = _groupInsights(insights);

  /* Preserve expanded state across re-renders */
  const expandedIds = new Set(
    [...el.querySelectorAll('.insight-card.expanded')].map(c => c.id)
  );

  el.innerHTML = grouped.map((ins, idx) => {
    const title = lang === 'en' ? (ins.title_en || ins.title) : ins.title;
    const body = lang === 'en' ? (ins.body_en || ins.body) : ins.body;
    const action = lang === 'en' ? (ins.action_en || ins.action) : ins.action;
    const sev = ins.severity || 'info';
    const score = typeof ins.impact_score === 'number' ? ins.impact_score : 0;
    const icon = ins.icon || 'fa-circle-info';
    const cat = _insightCategory(icon);
    const scoreClr = _scoreColor(score);
    const bodyHighlighted = _highlightDollars(_escHtml(body));
    const cardId = 'insight-' + idx;
    const groupBadge = ins._groupCount > 1
      ? `<span class="insight-group-badge">${ins._groupCount}</span>`
      : '';

    /* Severity-specific card class for pulse animation on critical */
    const criticalPulseClass = sev === 'critical' ? ' insight-critical-pulse' : '';

    /* Tip icon for actionable suggestions */
    const actionIcon = action
      ? '<i class="fa-solid fa-lightbulb insight-tip-icon" aria-hidden="true"></i>'
      : '<i class="fa-solid fa-wand-magic-sparkles insight-action-icon"></i>';

    return `
      <div class="insight-card ${_escHtml(sev)} cat-${cat}${criticalPulseClass}"
           style="animation-delay:${idx * 80}ms"
           id="${cardId}"
           data-insight-id="${cardId}">
        <div class="insight-header">
          <i class="fa-solid ${_escHtml(icon)} insight-icon cat-${cat}"></i>
          <strong class="insight-title">${_escHtml(title)}</strong>
          ${groupBadge}
          <span class="insight-score" style="--score-color:${scoreClr}">
            <svg class="insight-gauge" viewBox="0 0 36 36" aria-hidden="true">
              <circle class="insight-gauge-bg" cx="18" cy="18" r="15.9"
                      fill="none" stroke-width="3"/>
              <circle class="insight-gauge-fill" cx="18" cy="18" r="15.9"
                      fill="none" stroke="${scoreClr}" stroke-width="3"
                      stroke-dasharray="0 100"
                      data-target-dash="${score} ${100 - score}"
                      stroke-dashoffset="25" stroke-linecap="round"
                      style="transition:stroke-dasharray 1s cubic-bezier(0.4,0,0.2,1)"/>
            </svg>
            <span class="insight-score-num" style="color:${scoreClr}"
                  data-target-score="${score}">0</span>
          </span>
          <span class="insight-badge ${_escHtml(sev)}">${_escHtml(severityLabel[sev] || sev)}</span>
          <i class="fa-solid fa-chevron-down insight-chevron" aria-hidden="true"></i>
        </div>
        <div class="insight-detail">
          <div class="insight-body">${bodyHighlighted}</div>
          <div class="insight-action">
            ${actionIcon}
            <span>${_escHtml(action)}</span>
          </div>
        </div>
      </div>
    `;
  }).join('');

  /* Trigger gauge arc and score count-up animations */
  _animateGauges(el);
  _animateScoreNums(el);

  /* Event delegation for expand/collapse */
  el.addEventListener('click', (e) => {
    const header = e.target.closest('.insight-header');
    if (!header) return;
    const card = header.closest('.insight-card');
    if (!card) return;
    const cardId = card.id;
    if (cardId) toggleInsightDetail(cardId);
  });

  /* Restore previously expanded cards */
  expandedIds.forEach(id => {
    const card = document.getElementById(id);
    if (card) {
      card.classList.add('expanded');
      const detail = card.querySelector('.insight-detail');
      if (detail) {
        detail.style.maxHeight = detail.scrollHeight + 'px';
        detail.style.opacity = '1';
      }
    }
  });
}

/* ── Expand / collapse individual insight detail ── */
function toggleInsightDetail(id) {
  const card = document.getElementById(id);
  if (!card) return;
  const detail = card.querySelector('.insight-detail');
  if (!detail) return;
  const isExpanded = card.classList.contains('expanded');
  if (isExpanded) {
    /* Collapse: lock current height, then animate to 0 */
    detail.style.opacity = '1';
    detail.style.maxHeight = detail.scrollHeight + 'px';
    requestAnimationFrame(() => {
      detail.style.opacity = '0';
      detail.style.maxHeight = '0';
    });
    card.classList.remove('expanded');
  } else {
    /* Expand: animate from 0 to scrollHeight, fade in */
    card.classList.add('expanded');
    detail.style.maxHeight = detail.scrollHeight + 'px';
    detail.style.opacity = '1';
    setTimeout(() => { detail.style.maxHeight = 'none'; }, 350);
  }
}
