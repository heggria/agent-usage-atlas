/* ── Loading / Empty / Error state components ── */

function renderEmptyState(container, opts = {}) {
  const icon = opts.icon || 'fa-inbox';
  const title = opts.title || t('emptyNoData') || 'No data available';
  const subtitle = opts.subtitle || '';
  container.innerHTML = `
    <div style="text-align:center;padding:32px 16px;color:var(--text-muted)">
      <i class="fa-solid ${icon}" style="font-size:36px;margin-bottom:12px;opacity:0.4"></i>
      <div style="font-size:15px;font-weight:500;margin-bottom:4px">${_escHtml(title)}</div>
      ${subtitle ? `<div style="font-size:12px;opacity:0.6">${_escHtml(subtitle)}</div>` : ''}
    </div>
  `;
}

function renderErrorState(container, error, onRetry) {
  container.innerHTML = `
    <div style="text-align:center;padding:32px 16px;color:var(--cost)">
      <i class="fa-solid fa-triangle-exclamation" style="font-size:32px;margin-bottom:12px;opacity:0.6"></i>
      <div style="font-size:14px;margin-bottom:8px">${typeof t === 'function' ? _escHtml(t('errorSomethingWrong')) : 'Something went wrong'}</div>
      <div style="font-size:11px;color:var(--text-muted);margin-bottom:12px">${_escHtml(String(error))}</div>
      ${onRetry ? '<button style="padding:6px 16px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text);cursor:pointer;font-size:12px" class="retry-btn">' + (typeof t === 'function' ? _escHtml(t('errorRetry')) : 'Retry') + '</button>' : ''}
    </div>
  `;
  if (onRetry) {
    const btn = container.querySelector('.retry-btn');
    if (btn) btn.addEventListener('click', onRetry);
  }
}

function renderSkeletonCards(container, count = 3) {
  container.innerHTML = Array.from({length: count}, () => `
    <article class="p" style="min-height:120px">
      <div style="height:14px;width:60%;background:var(--surface);border-radius:6px;margin-bottom:12px;animation:pulse 1.5s infinite"></div>
      <div style="height:28px;width:40%;background:var(--surface);border-radius:6px;margin-bottom:8px;animation:pulse 1.5s infinite"></div>
      <div style="height:12px;width:80%;background:var(--surface);border-radius:6px;animation:pulse 1.5s infinite"></div>
    </article>
  `).join('');
}

function renderNoActivity(container) {
  renderEmptyState(container, {
    icon: 'fa-moon',
    title: lang === 'zh' ? '\u6682\u65e0\u6d3b\u52a8' : 'No recent activity',
    subtitle: lang === 'zh' ? '\u5f00\u59cb\u4f7f\u7528 AI \u7f16\u7a0b\u52a9\u624b\u540e\u6570\u636e\u5c06\u5728\u6b64\u663e\u793a' : 'Data will appear here once you start using AI coding agents'
  });
}
