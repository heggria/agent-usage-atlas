function renderVaguePrompts(){
  const p = data.prompts;
  if (!p) return;
  const el = document.getElementById('vague-stats');
  if (!el) return;
  el.innerHTML = [
    {lbl: t('lblVagueCount'), val: fmtInt(p.vague_count), hint: t('hintVagueCount', {total: fmtInt(p.total_user_messages)}), cls: 'cost'},
    {lbl: t('lblVagueRatio'), val: fmtPct(p.vague_ratio), hint: t('hintVagueRatio', {count: fmtInt(p.vague_count), total: fmtInt(p.total_user_messages)}), cls: 'cost'},
    {lbl: t('lblWastedTokens'), val: fmtShort(p.estimated_wasted_tokens), hint: t('hintWastedTokens'), cls: 'cost'},
    {lbl: t('lblWastedCost'), val: fmtUSD(p.estimated_wasted_cost), hint: t('hintWastedCost'), cls: 'cost'},
  ].map(c => `
    <article class="cc ${c.cls}">
      <div class="metric-k">${c.lbl}</div>
      <div class="big">${c.val}</div>
      <div class="tiny">${c.hint}</div>
    </article>
  `).join('');

  const listEl = document.getElementById('vague-list');
  if (!listEl) return;
  const items = (p.top_vague_prompts || []);
  if (!items.length) {
    listEl.innerHTML = '<div style="padding:32px 16px;text-align:center">'
      + '<div style="font-size:22px;margin-bottom:8px"><i class="fa-solid fa-wand-magic-sparkles" aria-hidden="true"></i></div>'
      + '<div style="color:var(--cache-read);font-weight:700;font-size:13px">' + _escHtml(t('vagueEmptyTitle')) + '</div>'
      + '<div class="tiny" style="margin-top:4px">' + _escHtml(t('vagueEmptyHint')) + '</div>'
      + '</div>';
    return;
  }

  /* Suggestion hints for common vague patterns */
  const _vagueHints = {
    'yes': 'Try: "Yes, apply the refactor to auth.js"',
    'y': 'Try: "Yes, apply the refactor to auth.js"',
    'yep': 'Try: "Yes, apply the refactor to auth.js"',
    'yea': 'Try: "Yes, go ahead with approach B"',
    'yeah': 'Try: "Yes, go ahead with approach B"',
    'sure': 'Try: "Sure, use the Redis cache strategy"',
    'ok': 'Try: "OK, proceed with the migration"',
    'k': 'Try: "OK, run the tests and fix failures"',
    'no': 'Try: "No, keep the original error handling"',
    'n': 'Try: "No, use a different approach for X"',
    'nope': 'Try: "No, revert that change"',
    'nah': 'Try: "No, skip that optimization"',
    'fix it': 'Try: "Fix the null check on line 42 in utils.ts"',
    'do it': 'Try: "Apply the changes to the login flow"',
    'go': 'Try: "Go ahead and deploy to staging"',
    'go ahead': 'Try: "Go ahead with the database schema migration"',
    'continue': 'Try: "Continue implementing the pagination logic"',
    'try again': 'Try: "Retry with a smaller batch size of 50"',
    'run it': 'Try: "Run the test suite for the auth module"',
    'proceed': 'Try: "Proceed with creating the API endpoint"',
    'retry': 'Try: "Retry the build with verbose logging"',
    'again': 'Try: "Run the linter again on src/"',
    'looks good': 'Try: "Looks good, commit with message \'fix: ...\'"',
    'lgtm': 'Try: "LGTM, merge and deploy to staging"',
    'please': 'Try: Be specific about what you need',
    'thanks': 'Consider: Add a follow-up task or close the session',
    'fine': 'Try: "Fine, use approach A for the cache layer"',
    'done': 'Try: "Done. Now run the integration tests"',
    'next': 'Try: "Next, implement the user settings page"',
    'correct': 'Try: "Correct. Now apply it to the remaining files"',
    'right': 'Try: "Right, update the config to match"',
    'good': 'Try: "Good. Now add error handling for edge cases"',
    'great': 'Try: "Great, commit and open a PR"',
    'nice': 'Try: "Nice. Now add unit tests for it"',
    'sounds good': 'Try: "Sounds good, proceed with the refactor"',
    'that works': 'Try: "That works. Deploy it to the test environment"',
    'perfect': 'Try: "Perfect, commit these changes"',
    'exactly': 'Try: "Exactly. Apply the same pattern to module B"',
  };

  /* ── Inject waste-cost pulse keyframes once ── */
  if (!document.getElementById('vague-pulse-style')) {
    var styleEl = document.createElement('style');
    styleEl.id = 'vague-pulse-style';
    styleEl.textContent =
      '@keyframes vagueWastePulse{' +
        '0%{box-shadow:0 0 4px rgba(255,107,107,.3)}' +
        '50%{box-shadow:0 0 10px rgba(255,107,107,.5),0 0 20px rgba(255,160,80,.2)}' +
        '100%{box-shadow:0 0 4px rgba(255,107,107,.3)}' +
      '}' +
      '[data-theme="light"] .vague-bar-bg{background:rgba(255,107,107,.10)}' +
      '@media(prefers-reduced-motion:reduce){.vague-row [style*="transition"]{transition:none !important}}';
    document.head.appendChild(styleEl);
  }

  const maxCount = Math.max(...items.map(item => item.count), 1);

  listEl.innerHTML = items.map((item) => {
    const barWidth = Math.max(4, (item.count / maxCount) * 100);
    const wasteCost = item.waste_cost || 0;
    const hint = _vagueHints[item.text] || '';

    /* Waste cost badge: prominent pulsing glow when cost > 0 */
    const wasteBadgeStyle = wasteCost > 0
      ? 'display:inline-block;padding:2px 7px;border-radius:999px;'
        + 'background:rgba(255,107,107,.15);color:var(--cost);font-size:10px;font-weight:700;'
        + 'animation:vagueWastePulse 2s ease-in-out infinite'
      : '';

    /* Hint: hidden by default, revealed on hover via opacity transition */
    const hintStyle = 'width:100%;font-size:11px;color:var(--text-muted);padding:2px 0 0 2px;'
      + 'position:relative;font-style:italic;'
      + 'opacity:0;max-height:0;overflow:hidden;'
      + 'transition:opacity 0.3s ease,max-height 0.3s ease';

    return '<div class="vague-row" style="position:relative;flex-wrap:wrap">'
      + '<div class="vague-bar-bg" style="position:absolute;left:0;top:0;bottom:0;width:0;background:rgba(255,107,107,.06);border-radius:4px;pointer-events:none;'
      + 'transition:width 0.6s cubic-bezier(0.25,0.46,0.45,0.94)" data-target-width="' + barWidth + '"></div>'
      + '<span class="vague-text" style="position:relative">' + _escHtml('"' + item.text + '"') + '</span>'
      + '<span style="display:flex;align-items:center;gap:8px;position:relative">'
      + (wasteCost > 0 ? '<span style="' + wasteBadgeStyle + '">' + _escHtml(fmtUSD(wasteCost)) + '</span>' : '')
      + '<span class="vague-count">' + _escHtml(String(item.count)) + 'x</span>'
      + '</span>'
      + (hint ? '<div class="vague-hint" style="' + hintStyle + '">' + _escHtml(hint) + '</div>' : '')
      + '</div>';
  }).join('');

  /* ── Animate bar widths from 0 to target after render ── */
  requestAnimationFrame(function() {
    var bars = listEl.querySelectorAll('.vague-bar-bg');
    bars.forEach(function(bar) {
      var target = bar.getAttribute('data-target-width');
      requestAnimationFrame(function() {
        bar.style.width = target + '%';
      });
    });
  });

  /* ── Hint reveal on hover ── */
  var rows = listEl.querySelectorAll('.vague-row');
  rows.forEach(function(row) {
    var hintEl = row.querySelector('.vague-hint');
    if (!hintEl) return;
    row.addEventListener('mouseenter', function() {
      hintEl.style.opacity = '1';
      hintEl.style.maxHeight = '60px';
    });
    row.addEventListener('mouseleave', function() {
      hintEl.style.opacity = '0';
      hintEl.style.maxHeight = '0';
    });
  });
}
/* _escHtml is defined in lib/utils.js */
