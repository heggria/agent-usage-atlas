function renderCostCards(){
  const T = data.totals;
  const defs = [
    {id: 'cc-total', label: t('lblTotalCost'), value: T.grand_cost, fmt: fmtUSD, hint: t('hintTotalCost', {days: data.range.day_count}), cls: 'cost'},
    {id: 'cc-avg', label: t('lblDailyAvg'), value: T.average_cost_per_day, fmt: fmtUSD, hint: t('hintDailyAvg', {peak: T.cost_peak_day_label, cost: fmtUSD(T.cost_peak_day_total)}), cls: 'cost'},
    {id: 'cc-msg', label: t('lblCostPerMsg'), value: T.cost_per_message, fmt: fmtUSD, hint: t('hintCostPerMsg', {cost: fmtUSD(T.median_session_cost)}), cls: 'cost'},
    {id: 'cc-save', label: t('lblCacheSavings'), value: T.cache_savings_usd, fmt: fmtUSD, hint: t('hintCacheSavings', {pct: fmtPct(T.cache_savings_ratio)}), cls: 'save'}
  ];
  const container = document.getElementById('cost-cards');
  if (!document.getElementById('cc-total')) {
    container.innerHTML = defs.map(c => `
      <article class="p cc ${c.cls}">
        <div class="metric-k">${c.label}</div>
        <div class="big" id="${c.id}"></div>
        <div class="tiny" id="${c.id}-hint">${c.hint}</div>
      </article>`).join('');
  }
  defs.forEach(c => {
    animateNum(document.getElementById(c.id), c.value, c.fmt);
    const hintEl = document.getElementById(c.id + '-hint');
    if (hintEl) hintEl.textContent = c.hint;
  });
}
