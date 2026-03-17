const fmtInt = n => Number(n || 0).toLocaleString('en-US');
const fmtShort = n => {
  const v = Number(n || 0);
  const a = Math.abs(v);
  if (a >= 1e9) return (v / 1e9).toFixed(2) + 'B';
  if (a >= 1e6) return (v / 1e6).toFixed(2) + 'M';
  if (a >= 1e3) return (v / 1e3).toFixed(1) + 'K';
  return String(Math.round(v));
};
const fmtPct = v => ((Number(v || 0) * 100).toFixed(1)) + '%';
const fmtUSD = v => {
  const value = Number(v || 0);
  if (value >= 1000) return '$' + value.toLocaleString('en-US', {maximumFractionDigits: 0});
  if (value >= 100) return '$' + value.toFixed(1);
  if (value >= 1) return '$' + value.toFixed(2);
  if (value >= 0.01) return '$' + value.toFixed(3);
  return '$' + value.toFixed(4);
};
const C = {
  Codex: '#ff8a50',
  Claude: '#ffd43b',
  Cursor: '#748ffc',
  uncached: '#f4b183',
  cacheRead: '#51cf66',
  cacheWrite: '#b197fc',
  output: '#74c0fc',
  reason: '#e599f7',
  cost: '#ff6b6b'
};
const TX = 'rgba(255,255,255,.68)';
const AX = 'rgba(255,255,255,.06)';
const BG = 'rgba(255,255,255,.03)';
const getTokenSources = () => (data && data.source_cards ? data.source_cards.filter(card => card.token_capable) : []);

/* ── Number transition animation ── */
let _numPrevValues = new WeakMap();
/* Build a locked formatter that keeps the same decimal places / scale throughout animation */
function _lockFmt(formatter, targetVal) {
  const targetStr = formatter(targetVal);
  if (formatter === fmtShort) {
    const a = Math.abs(targetVal);
    if (a >= 1e9) return v => (v / 1e9).toFixed(2) + 'B';
    if (a >= 1e6) return v => (v / 1e6).toFixed(2) + 'M';
    if (a >= 1e3) return v => (v / 1e3).toFixed(1) + 'K';
    return v => String(Math.round(v));
  }
  if (formatter === fmtUSD) {
    const av = Math.abs(targetVal);
    if (av >= 1000) return v => '$' + v.toLocaleString('en-US', {maximumFractionDigits: 0});
    if (av >= 100) return v => '$' + v.toFixed(1);
    if (av >= 1) return v => '$' + v.toFixed(2);
    if (av >= 0.01) return v => '$' + v.toFixed(3);
    return v => '$' + v.toFixed(4);
  }
  if (formatter === fmtPct) {
    return v => ((Number(v || 0) * 100).toFixed(1)) + '%';
  }
  if (formatter === fmtInt) {
    return v => Math.round(v).toLocaleString('en-US');
  }
  return formatter;
}
function animateNum(el, newRaw, formatter) {
  if (!el) return;
  const newVal = Number(newRaw) || 0;
  const oldVal = _numPrevValues.has(el) ? _numPrevValues.get(el) : newVal;
  _numPrevValues.set(el, newVal);
  if (isFirstRender || oldVal === newVal) {
    el.textContent = formatter(newVal);
    return;
  }
  /* Stock-style color flash */
  const dir = newVal > oldVal ? 'num-up' : 'num-down';
  el.classList.remove('num-up', 'num-down');
  /* Force reflow so re-adding the same class restarts the animation */
  void el.offsetWidth;
  el.classList.add(dir);
  const locked = _lockFmt(formatter, newVal);
  const duration = 600;
  const startTime = performance.now();
  const step = (now) => {
    const t = Math.min((now - startTime) / duration, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    const cur = oldVal + (newVal - oldVal) * ease;
    el.textContent = locked(cur);
    if (t < 1) requestAnimationFrame(step);
    else { _numPrevValues.set(el, newVal); el.textContent = formatter(newVal); }
  };
  requestAnimationFrame(step);
}
