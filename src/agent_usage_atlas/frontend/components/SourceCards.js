function renderSourceCards(){
  const container = document.getElementById('source-cards');
  const prefix = 'src-';
  if (!document.getElementById(prefix + (data.source_cards[0] || {}).source)) {
    container.innerHTML = data.source_cards.map(card => {
      const cls = card.source.toLowerCase();
      const id = prefix + card.source;
      const icon = card.source === 'Codex' ? 'fa-terminal' : card.source === 'Claude' ? 'fa-feather-pointed' : 'fa-arrow-pointer';
      return `<article class="p src ${cls}" id="${id}">
        <div class="title"><span><i class="fa-solid ${icon}"></i> ${card.source}</span><span class="pill">${card.token_capable ? t('pillTokenTracked') : t('pillActivityOnly')}</span></div>
        <div class="big" id="${id}-big"></div>
        <div class="sub">${card.token_capable ? t('subTrackedTokens') : t('subMessagesOnly')}</div>
        <div class="mg">
          <div class="mi"><div class="k">${t('lblSessions')}</div><div class="v" id="${id}-sess"></div></div>
          <div class="mi"><div class="k">${t('lblCost')}</div><div class="v" id="${id}-cost" style="color:var(--cost)"></div></div>
          <div class="mi"><div class="k">${t('lblTopModel')}</div><div class="v" style="font-size:12px">${card.top_model}</div></div>
          <div class="mi"><div class="k">${t('lblCache')}</div><div class="v" id="${id}-cache"></div></div>
        </div>
      </article>`;
    }).join('');
  }
  data.source_cards.forEach(card => {
    const id = prefix + card.source;
    animateNum(document.getElementById(id + '-big'), card.token_capable ? card.total : card.messages, card.token_capable ? fmtShort : fmtInt);
    animateNum(document.getElementById(id + '-sess'), card.sessions, fmtInt);
    if (card.token_capable) {
      animateNum(document.getElementById(id + '-cost'), card.cost, fmtUSD);
      animateNum(document.getElementById(id + '-cache'), card.cache_read + card.cache_write, fmtShort);
    } else {
      const costEl = document.getElementById(id + '-cost');
      if (costEl) costEl.textContent = '-';
      const cacheEl = document.getElementById(id + '-cache');
      if (cacheEl) cacheEl.textContent = '-';
    }
  });
}
