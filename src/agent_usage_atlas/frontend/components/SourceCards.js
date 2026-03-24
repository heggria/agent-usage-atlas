const _SOURCE_ICONS = {Codex:'fa-terminal', Claude:'fa-feather-pointed', Hermit:'fa-wand-sparkles', Cursor:'fa-arrow-pointer'};

/* ── Inject source-card-specific keyframes once ── */
(function _injectSourceCardKeyframes() {
  if (document.getElementById('srccard-ux-keyframes')) return;
  const style = document.createElement('style');
  style.id = 'srccard-ux-keyframes';
  style.textContent = [
    '@keyframes srcCardFadeInUp{0%{opacity:0;transform:translateY(14px)}100%{opacity:1;transform:translateY(0)}}',
    '.src .sparkline-wrap{transition:transform 0.2s ease,opacity 0.2s ease;opacity:0.85}',
    '.src:hover .sparkline-wrap{transform:scale(1.05);opacity:1}',
    '.src.src-selected{border-color:var(--accent) !important;box-shadow:0 0 0 2px rgba(240,184,102,.25),0 12px 40px rgba(0,0,0,.2) !important}',
    '[data-theme="light"] .src.src-selected{box-shadow:0 0 0 2px rgba(200,127,32,.2),0 12px 40px rgba(0,0,0,.08) !important}',
    '[data-theme="light"] .src-pct-bar{background:rgba(0,0,0,.08)}',
    '@media(prefers-reduced-motion:reduce){[style*="srcCardFadeInUp"]{animation:none !important;opacity:1 !important}}',
  ].join('\n');
  document.head.appendChild(style);
})();

function renderSourceCards(){
  const container = document.getElementById('source-cards');
  const prefix = 'src-';
  /* Detect if the set of sources changed — rebuild HTML when it does */
  const newKeys = data.source_cards.map(c => c.source).join(',');
  const needsRebuild = container.dataset.srcKeys !== newKeys;
  if (needsRebuild) {
    container.dataset.srcKeys = newKeys;
    const noMotion = typeof prefersReducedMotion === 'function' && prefersReducedMotion();
    container.innerHTML = data.source_cards.map((card, idx) => {
      const cls = card.source.replace(/[^a-z0-9]/gi, '-').toLowerCase();
      const id = prefix + card.source.replace(/[^a-z0-9]/gi, '-');
      const icon = _SOURCE_ICONS[card.source] || 'fa-arrow-pointer';
      const recentCosts = (data.days || []).slice(-7).map(d => d.cost_sources && d.cost_sources[card.source] || 0);
      const sparklineRaw = card.token_capable ? buildSparklineSvg(recentCosts, C[card.source] || '#999', 80, 24) : '';
      /* Wrap sparkline SVG in a container for hover scaling */
      const sparkline = sparklineRaw ? `<div class="sparkline-wrap">${sparklineRaw}</div>` : '';
      /* Staggered card entrance animation: each card 80ms delayed */
      const animStyle = noMotion
        ? ''
        : ` style="animation:srcCardFadeInUp 0.45s ease forwards;animation-delay:${idx * 80}ms;opacity:0"`;
      /* Raw big number for tooltip */
      const rawBig = card.token_capable ? card.total : card.messages;
      return `<article class="p src ${cls}" id="${id}" aria-label="${_escHtml(card.source)} source"${animStyle}>
        <div class="title"><span><i class="fa-solid ${icon}"></i> ${_escHtml(card.source)}</span><span class="pill">${card.token_capable ? t('pillTokenTracked') : t('pillActivityOnly')}</span></div>
        <div class="big" id="${id}-big" title="${_escHtml(String(rawBig))}">${''}</div>
        ${sparkline}
        <div class="sub">${card.token_capable ? t('subTrackedTokens') : t('subMessagesOnly')}</div>
        <div class="mg">
          <div class="mi"><div class="k">${t('lblSessions')}</div><div class="v" id="${id}-sess"></div></div>
          <div class="mi"><div class="k">${t('lblCost')}</div><div class="v" id="${id}-cost" style="color:var(--cost)"></div></div>
          <div class="mi"><div class="k">${t('lblTopModel')}</div><div class="v" id="${id}-model" style="font-size:12px"></div></div>
          <div class="mi"><div class="k">${t('lblCache')}</div><div class="v" id="${id}-cache"></div></div>
        </div>
        <div class="src-pct-bar" style="margin-top:10px;height:4px;border-radius:2px;background:rgba(255,255,255,.06);overflow:hidden">
          <div class="src-pct-fill" id="${id}-pct" style="height:100%;width:0;border-radius:2px;background:var(--${_safeCssSource(cls)});transition:width 0.6s cubic-bezier(0.25,0.46,0.45,0.94)"></div>
        </div>
      </article>`;
    }).join('');

    /* ── Active source highlight: toggle selected on click ── */
    data.source_cards.forEach(card => {
      const id = prefix + card.source.replace(/[^a-z0-9]/gi, '-');
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('click', function() {
          el.classList.toggle('src-selected');
        });
      }
    });

    /* ── Animate progress bars from 0 to final width after DOM paint ── */
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        const grandTotal = (data.totals && data.totals.grand_total) || 1;
        data.source_cards.forEach(card => {
          if (!card.token_capable) return;
          const id = prefix + card.source.replace(/[^a-z0-9]/gi, '-');
          const pctEl = document.getElementById(id + '-pct');
          if (pctEl) {
            const pct = Math.min((card.total / grandTotal) * 100, 100);
            pctEl.style.width = pct.toFixed(2) + '%';
          }
        });
      });
    });
  }
  data.source_cards.forEach(card => {
    const id = prefix + card.source.replace(/[^a-z0-9]/gi, '-');
    const bigEl = document.getElementById(id + '-big');
    const rawBig = card.token_capable ? card.total : card.messages;
    animateNum(bigEl, rawBig, card.token_capable ? fmtShort : fmtInt);
    /* Update tooltip with latest raw value */
    if (bigEl) bigEl.title = String(rawBig);
    animateNum(document.getElementById(id + '-sess'), card.sessions, fmtInt);
    const modelEl = document.getElementById(id + '-model');
    if (modelEl) modelEl.textContent = card.top_model;
    if (card.token_capable) {
      animateNum(document.getElementById(id + '-cost'), card.cost, fmtUSD);
      animateNum(document.getElementById(id + '-cache'), card.cache_read + card.cache_write, fmtShort);
    } else {
      const costEl = document.getElementById(id + '-cost');
      if (costEl) costEl.textContent = '-';
      const cacheEl = document.getElementById(id + '-cache');
      if (cacheEl) cacheEl.textContent = '-';
    }

    /* ── Update progress bar width on data refresh ── */
    const grandTotal = (data.totals && data.totals.grand_total) || 1;
    if (card.token_capable) {
      const pctEl = document.getElementById(id + '-pct');
      if (pctEl) {
        const pct = Math.min((card.total / grandTotal) * 100, 100);
        pctEl.style.width = pct.toFixed(2) + '%';
      }
    }
  });
}
