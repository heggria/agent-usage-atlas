function _escHtml(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
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
  const a = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  if (a >= 1000) return sign + '$' + a.toLocaleString('en-US', {maximumFractionDigits: 0});
  if (a >= 100) return sign + '$' + a.toFixed(1);
  if (a >= 1) return sign + '$' + a.toFixed(2);
  if (a >= 0.01) return sign + '$' + a.toFixed(3);
  return sign + '$' + a.toFixed(4);
};
const _C_DARK = {Codex:'#ff8a50',Claude:'#ffd43b',Cursor:'#748ffc',Hermit:'#a78bfa',uncached:'#f4b183',cacheRead:'#51cf66',cacheWrite:'#b197fc',output:'#74c0fc',reason:'#e599f7',cost:'#ff6b6b'};
const _C_LIGHT = {Codex:'#e06830',Claude:'#d4960a',Cursor:'#5a73d9',Hermit:'#7c3aed',uncached:'#d4845a',cacheRead:'#2b8a3e',cacheWrite:'#8b6cc0',output:'#3a8fd4',reason:'#c06ad0',cost:'#dc3545'};
let _currentPalette = _C_DARK;
function refreshPalette() { _currentPalette = _isLight() ? _C_LIGHT : _C_DARK; }
refreshPalette();
const C = new Proxy({}, {get(_, key) { return _currentPalette[key]; }});
const _TX = () => _isLight() ? 'rgba(0,0,0,.55)' : 'rgba(255,255,255,.68)';
const _AX = () => _isLight() ? 'rgba(0,0,0,.09)' : 'rgba(255,255,255,.06)';
const _BG = () => _isLight() ? 'rgba(0,0,0,.03)' : 'rgba(255,255,255,.03)';
const _CARD_BG = () => _isLight() ? '#ffffff' : '#0d1016';
const _LINE_ACCENT = () => _isLight() ? 'rgba(0,0,0,.55)' : 'rgba(255,255,255,.75)';
const _LINE_DOT = () => _isLight() ? '#1a1a2e' : '#fff';
/* Backward-compatible: TX/AX/BG are now getters so existing chart code keeps working */
Object.defineProperty(window, 'TX', {get: _TX});
Object.defineProperty(window, 'AX', {get: _AX});
Object.defineProperty(window, 'BG', {get: _BG});
const getTokenSources = () => (data && data.source_cards ? data.source_cards.filter(card => card.token_capable) : []);

/* ── Number transition animation (batched RAF) ── */
let _numPrevValues = new WeakMap();
const _animBatch = []; /* {el, oldVal, newVal, locked, formatter, startTime, duration} */
let _animRafId = null;
const _MAX_CONCURRENT_ANIMS = 15;

/* Build a locked formatter that keeps the same decimal places / scale throughout animation */
function _lockFmt(formatter, targetVal) {
  if (formatter === fmtShort) {
    const a = Math.abs(targetVal);
    if (a >= 1e9) return v => (v / 1e9).toFixed(2) + 'B';
    if (a >= 1e6) return v => (v / 1e6).toFixed(2) + 'M';
    if (a >= 1e3) return v => (v / 1e3).toFixed(1) + 'K';
    return v => String(Math.round(v));
  }
  if (formatter === fmtUSD) {
    const av = Math.abs(targetVal);
    if (av >= 1000) return v => { const a = Math.abs(v), s = v < 0 ? '-' : ''; return s + '$' + a.toLocaleString('en-US', {maximumFractionDigits: 0}); };
    if (av >= 100) return v => { const a = Math.abs(v), s = v < 0 ? '-' : ''; return s + '$' + a.toFixed(1); };
    if (av >= 1) return v => { const a = Math.abs(v), s = v < 0 ? '-' : ''; return s + '$' + a.toFixed(2); };
    if (av >= 0.01) return v => { const a = Math.abs(v), s = v < 0 ? '-' : ''; return s + '$' + a.toFixed(3); };
    return v => { const a = Math.abs(v), s = v < 0 ? '-' : ''; return s + '$' + a.toFixed(4); };
  }
  if (formatter === fmtPct) {
    return v => ((Number(v || 0) * 100).toFixed(1)) + '%';
  }
  if (formatter === fmtInt) {
    return v => Math.round(v).toLocaleString('en-US');
  }
  return formatter;
}

function _animTick(now) {
  let i = _animBatch.length;
  while (i--) {
    const a = _animBatch[i];
    const t = Math.min((now - a.startTime) / a.duration, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    const cur = a.oldVal + (a.newVal - a.oldVal) * ease;
    a.el.textContent = a.locked(cur);
    if (t >= 1) {
      _numPrevValues.set(a.el, a.newVal);
      a.el.textContent = a.formatter(a.newVal);
      /* Swap with last element and pop for O(1) removal */
      _animBatch[i] = _animBatch[_animBatch.length - 1];
      _animBatch.pop();
    }
  }
  if (_animBatch.length > 0) {
    _animRafId = requestAnimationFrame(_animTick);
  } else {
    _animRafId = null;
  }
}

function animateNum(el, newRaw, formatter) {
  if (!el) return;
  const newVal = Number(newRaw) || 0;
  if (prefersReducedMotion()) { el.textContent = formatter(newVal); _numPrevValues.set(el, newVal); return; }
  /* Remove existing animation for this element if any */
  for (let i = _animBatch.length - 1; i >= 0; i--) {
    if (_animBatch[i].el === el) { _animBatch[i] = _animBatch[_animBatch.length - 1]; _animBatch.pop(); break; }
  }
  const oldVal = _numPrevValues.has(el) ? _numPrevValues.get(el) : newVal;
  _numPrevValues.set(el, newVal);
  if (isFirstRender || oldVal === newVal) {
    el.textContent = formatter(newVal);
    return;
  }
  /* Cap concurrent animations — set value directly if at limit */
  if (_animBatch.length >= _MAX_CONCURRENT_ANIMS) {
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
  _animBatch.push({el, oldVal, newVal, locked, formatter, startTime: performance.now(), duration: 600});
  if (!_animRafId) {
    _animRafId = requestAnimationFrame(_animTick);
  }
}

const _mqlReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const prefersReducedMotion = () => _mqlReducedMotion.matches;

function buildSparklineSvg(values, color, width, height) {
  if (!values || values.length < 2) return '';
  const max = Math.max(...values, 0.001);
  const step = width / (values.length - 1);
  const points = values.map((v, i) => `${i * step},${height - (v / max) * height * 0.8 - 1}`).join(' ');
  return `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" style="display:block;margin:4px auto"><polyline points="${points}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
}

function syncCSSTokens(d) {
  if (!d || !d.source_cards) return;
  document.documentElement.style.setProperty('--source-count', d.source_cards.length);
}
