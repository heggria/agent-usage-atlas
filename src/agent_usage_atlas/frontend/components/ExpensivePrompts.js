function renderExpensivePrompts(){
  const p = data.prompts;
  if (!p) return;
  const el = document.getElementById('expensive-table');
  if (!el) return;
  const rows = (p.expensive_prompts || []).slice(0, 30);
  if (!rows.length) {
    el.innerHTML = '<tbody><tr><td class="tiny" style="padding:12px">' + _escHtml(t('emptyPromptCost')) + '</td></tr></tbody>';
    return;
  }

  const totalPromptCost = p.total_prompt_cost || 0;
  const maxCost = Math.max(...rows.map(r => r.cost), 0.0001);

  /* Model color mapping: pick color from source palette or hash-based */
  const _modelColor = (model) => {
    const ml = (model || '').toLowerCase();
    if (ml.includes('opus')) return '#e599f7';
    if (ml.includes('sonnet')) return '#74c0fc';
    if (ml.includes('haiku')) return '#51cf66';
    if (ml.includes('gpt-5') || ml.includes('codex')) return '#ff8a50';
    if (ml.includes('minimax')) return '#ffd43b';
    if (ml.includes('gemini')) return '#748ffc';
    if (ml.includes('deepseek')) return '#20c997';
    if (ml.includes('llama')) return '#da77f2';
    if (ml.includes('mistral')) return '#ff6b6b';
    if (ml.includes('grok')) return '#ffa94d';
    return '#888';
  };

  /* ── Inject expensive-prompts styles once ── */
  if (!document.getElementById('expensive-prompts-style')) {
    var styleEl = document.createElement('style');
    styleEl.id = 'expensive-prompts-style';
    styleEl.textContent =
      '.exp-row{transition:background 0.2s ease}' +
      '.exp-row:hover{background:rgba(255,255,255,.04)}' +
      '[data-theme="light"] .exp-row:hover{background:rgba(0,0,0,.03)}' +
      '.exp-row:hover .exp-cost-val{transform:scale(1.08);display:inline-block}' +
      '.exp-cost-val{transition:transform 0.2s ease;display:inline-block}' +
      '.exp-model-badge{' +
        'display:inline-block;padding:2px 10px;border-radius:999px;' +
        'font-size:10px;font-weight:700;white-space:nowrap;' +
        'transition:transform 0.15s ease,box-shadow 0.15s ease' +
      '}' +
      '.exp-model-badge:hover{transform:scale(1.05);box-shadow:0 2px 8px rgba(0,0,0,.15)}' +
      '[data-theme="light"] .exp-model-badge:hover{box-shadow:0 1px 4px rgba(0,0,0,.08)}' +
      '.exp-text-cell{max-width:320px;font-size:12px;position:relative;cursor:pointer}' +
      '.exp-text-truncated{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
      '.exp-text-expanded{white-space:pre-wrap;word-break:break-word}' +
      '.exp-cost-bar{' +
        'position:absolute;left:0;top:0;bottom:0;width:0;' +
        'background:rgba(255,107,107,.05);pointer-events:none;z-index:0;' +
        'transition:width 0.6s cubic-bezier(0.25,0.46,0.45,0.94)' +
      '}' +
      '[data-theme="light"] .exp-cost-bar{background:rgba(255,107,107,.08)}' +
      '@media(prefers-reduced-motion:reduce){.exp-cost-bar{transition:none !important}}';
    document.head.appendChild(styleEl);
  }

  el.innerHTML = '<thead>'
    + '<tr>'
    + '<th>' + _escHtml(t('tblRank')) + '</th>'
    + '<th>' + _escHtml(t('tblPrompt')) + '</th>'
    + '<th>' + _escHtml(t('tblPromptTokens')) + '</th>'
    + '<th>' + _escHtml(t('tblPromptCost')) + '</th>'
    + '<th>' + _escHtml(t('tblPromptCostPct')) + '</th>'
    + '<th>' + _escHtml(t('tblPromptModel')) + '</th>'
    + '<th>' + _escHtml(t('tblPromptSource')) + '</th>'
    + '</tr>'
    + '</thead>'
    + '<tbody>'
    + rows.map((row, i) => {
      const costBarWidth = Math.max(2, (row.cost / maxCost) * 100);
      const costPct = totalPromptCost > 0 ? (row.cost / totalPromptCost * 100) : 0;
      const mColor = _modelColor(row.model);
      const truncLen = 80;
      const isTruncated = row.text.length > truncLen;
      const truncatedText = isTruncated ? row.text.slice(0, truncLen) + '...' : row.text;

      /* Token breakdown tooltip */
      const inputTk = row.input_tokens != null ? row.input_tokens : 0;
      const outputTk = row.output_tokens != null ? row.output_tokens : 0;
      const reasonTk = row.reasoning_tokens != null ? row.reasoning_tokens : 0;
      const tooltipText = 'Input: ' + _escHtml(fmtShort(inputTk)) + ' | Output: ' + _escHtml(fmtShort(outputTk)) + ' | Reasoning: ' + _escHtml(fmtShort(reasonTk));

      return '<tr class="exp-row" style="position:relative">'
        + '<td style="position:relative">'
        + '<div class="exp-cost-bar" data-target-width="' + costBarWidth + '"></div>'
        + '<span style="position:relative;color:var(--text-muted);font-weight:700">' + _escHtml(String(i + 1)) + '</span>'
        + '</td>'
        + '<td class="exp-text-cell" title="' + _escHtml(row.text) + '" data-full-text="' + _escHtml(row.text) + '" data-short-text="' + _escHtml(truncatedText) + '" data-expandable="' + (isTruncated ? '1' : '0') + '">'
        + '<span class="exp-text-truncated">' + _escHtml(truncatedText) + '</span>'
        + '</td>'
        + '<td title="' + _escHtml(tooltipText) + '" style="cursor:help">' + _escHtml(fmtShort(row.tokens)) + '</td>'
        + '<td style="color:var(--cost);font-weight:700"><span class="exp-cost-val">' + _escHtml(fmtUSD(row.cost)) + '</span></td>'
        + '<td style="font-size:12px;color:var(--text-muted)">' + _escHtml(costPct.toFixed(1) + '%') + '</td>'
        + '<td><span class="exp-model-badge" style="background:' + mColor + '20;color:' + mColor + ';border:1px solid ' + mColor + '30">' + _escHtml(row.model) + '</span></td>'
        + '<td>' + _escHtml(row.source) + '</td>'
        + '</tr>';
    }).join('')
    + '</tbody>';

  /* ── Animate cost bars from 0 to target width ── */
  requestAnimationFrame(function() {
    var bars = el.querySelectorAll('.exp-cost-bar');
    bars.forEach(function(bar) {
      var target = bar.getAttribute('data-target-width');
      requestAnimationFrame(function() {
        bar.style.width = target + '%';
      });
    });
  });

  /* ── Truncated text expand/collapse on click ── */
  var textCells = el.querySelectorAll('.exp-text-cell[data-expandable="1"]');
  textCells.forEach(function(cell) {
    cell.addEventListener('click', function() {
      var span = cell.querySelector('span');
      if (!span) return;
      var isExpanded = span.classList.contains('exp-text-expanded');
      if (isExpanded) {
        span.textContent = cell.getAttribute('data-short-text');
        span.classList.remove('exp-text-expanded');
        span.classList.add('exp-text-truncated');
      } else {
        span.textContent = cell.getAttribute('data-full-text');
        span.classList.remove('exp-text-truncated');
        span.classList.add('exp-text-expanded');
      }
    });
  });
}
