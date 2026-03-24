/* ── Icon-to-category mapping for grouping story blocks ── */
const _STORY_ICON_CATEGORIES = {
  'fa-bolt': 'overview',
  'fa-fire': 'peaks',
  'fa-database': 'cache',
  'fa-wrench': 'tooling',
  'fa-comment-dots': 'humor',
};

/* ── Dot color by category ── */
const _STORY_DOT_COLORS = {
  overview: 'var(--accent)',
  peaks: 'var(--cost)',
  cache: 'var(--cache-read)',
  tooling: 'var(--cursor)',
  humor: 'var(--hermit)',
};

const _STORY_COLLAPSE_THRESHOLD = 5;
const _STORY_VISIBLE_COUNT = 3;

/**
 * Highlight numbers in story text: dollar amounts, percentages,
 * comma-separated integers, and plain integers >= 2 digits.
 * Operates on already-escaped HTML.
 */
function _highlightMetrics(escapedText) {
  return escapedText
    /* $1,234.56 or $0.02 style dollar amounts */
    .replace(/(\$[\d,]+(?:\.\d+)?)/g, '<strong class="story-metric story-metric--cost">$1</strong>')
    /* 85.3% style percentages */
    .replace(/([\d,.]+%)/g, '<strong class="story-metric story-metric--pct">$1</strong>')
    /* large comma-separated numbers like 1,234,567 (not already inside a tag) */
    .replace(/(?<![>\d])(\d{1,3}(?:,\d{3})+)(?![<\d%$])/g, '<strong class="story-metric story-metric--num">$1</strong>')
    /* standalone integers of 2+ digits not already wrapped */
    .replace(/(?<![>\d,])(\d{2,})(?![<\d,%$])/g, '<strong class="story-metric story-metric--num">$1</strong>');
}

/**
 * Set up an IntersectionObserver for scroll-reveal animation on story blocks.
 * Each block starts invisible and slides in from the left when it enters the viewport.
 */
function _initStoryScrollReveal(container) {
  const blocks = container.querySelectorAll('.story-block:not(.story-block--hidden)');
  if (!blocks.length) return;

  /* Apply initial hidden state for reveal */
  blocks.forEach(function(block) {
    block.style.opacity = '0';
    block.style.transform = 'translateX(-20px)';
    block.style.transition = 'opacity 0.5s ease, transform 0.5s ease, background 0.25s ease, border-color 0.25s ease, max-height 0.35s ease, border-left-width 0.25s ease, padding-left 0.25s ease';
  });

  if (!('IntersectionObserver' in window)) {
    /* Fallback: just show everything immediately */
    blocks.forEach(function(block) {
      block.style.opacity = '1';
      block.style.transform = 'translateX(0)';
    });
    return;
  }

  var revealDelay = 0;
  var observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        var el = entry.target;
        var delay = parseInt(el.getAttribute('data-reveal-delay') || '0', 10);
        setTimeout(function() {
          el.style.opacity = '1';
          el.style.transform = 'translateX(0)';
        }, delay);
        observer.unobserve(el);
      }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -30px 0px' });

  blocks.forEach(function(block, idx) {
    block.setAttribute('data-reveal-delay', String(idx * 80));
    observer.observe(block);
  });
}

function renderStory() {
  const container = document.getElementById('story-list');
  if (!container) return;

  const storyKey = lang === 'en' ? 'narrative_en' : 'narrative';
  const jokesKey = lang === 'en' ? 'jokes_en' : 'jokes';
  const narrative = (data.story && data.story[storyKey]) || (data.story && data.story.narrative) || [];
  const jokes = (data.story && data.story[jokesKey]) || (data.story && data.story.jokes) || [];

  const blocks = [
    ...narrative,
    ...jokes.map(txt => ({icon: 'fa-comment-dots', text: txt}))
  ];

  /* ── Empty state ── */
  if (blocks.length === 0) {
    container.innerHTML = `
      <div class="story-empty">
        <i class="fa-solid fa-book-open story-empty-icon"></i>
        <p class="story-empty-text">${_escHtml(t('storyEmpty'))}</p>
      </div>`;
    return;
  }

  /* ── Group blocks by category ── */
  const grouped = [];
  let currentCat = null;
  for (const block of blocks) {
    const cat = _STORY_ICON_CATEGORIES[block.icon] || 'overview';
    if (cat !== currentCat) {
      grouped.push({category: cat, items: []});
      currentCat = cat;
    }
    grouped[grouped.length - 1].items.push(block);
  }

  /* ── Determine if collapsible ── */
  const totalBlocks = blocks.length;
  const needsCollapse = totalBlocks > _STORY_COLLAPSE_THRESHOLD;

  /* ── Inject pulse keyframes once ── */
  if (!document.getElementById('story-pulse-style')) {
    const styleEl = document.createElement('style');
    styleEl.id = 'story-pulse-style';
    styleEl.textContent =
      '@keyframes storyDotPulse{' +
        '0%{box-shadow:0 0 8px var(--_dot-color,var(--accent)),0 0 0 0 var(--_dot-color,var(--accent))}' +
        '50%{box-shadow:0 0 8px var(--_dot-color,var(--accent)),0 0 0 6px transparent}' +
        '100%{box-shadow:0 0 8px var(--_dot-color,var(--accent)),0 0 0 0 transparent}' +
      '}' +
      '@media(prefers-reduced-motion:reduce){.story-dot{animation:none !important}.story-block{transition:none !important}}';
    document.head.appendChild(styleEl);
  }

  let blockIndex = 0;
  let html = '<div class="story-timeline">';
  html += '<div class="story-timeline-line"></div>';

  for (let gi = 0; gi < grouped.length; gi++) {
    const group = grouped[gi];
    const dotColor = _STORY_DOT_COLORS[group.category] || 'var(--accent)';

    /* Section divider between groups (skip first) */
    if (gi > 0) {
      html += '<div class="story-group-divider"></div>';
    }

    for (const block of group.items) {
      const isHidden = needsCollapse && blockIndex >= _STORY_VISIBLE_COUNT;
      const escapedText = _escHtml(block.text);
      const highlightedText = _highlightMetrics(escapedText);
      const isFirst = blockIndex === 0;

      /* Pulse animation on the first (most recent) block's dot */
      const pulseStyle = isFirst
        ? 'animation:storyDotPulse 2s ease-in-out infinite;--_dot-color:' + dotColor
        : '';

      html += '<div class="story-block' + (isHidden ? ' story-block--hidden' : '') + '" data-story-idx="' + blockIndex + '">';
      html += '<div class="story-dot" style="background:' + dotColor + ';box-shadow:0 0 8px ' + dotColor + ';' + pulseStyle + '"></div>';
      html += '<div class="story-content">';
      html += '<i class="fa-solid ' + _escHtml(block.icon) + ' story-icon" style="color:' + dotColor + '"></i>';
      html += '<p class="story-text">' + highlightedText + '</p>';
      html += '</div>';
      html += '</div>';
      blockIndex++;
    }
  }

  html += '</div>';

  /* ── Collapsible toggle ── */
  if (needsCollapse) {
    const hiddenCount = totalBlocks - _STORY_VISIBLE_COUNT;
    html += `<button class="story-toggle" type="button" aria-expanded="false" aria-controls="story-list">`;
    html += `<span class="story-toggle-text">${_escHtml(t('storyShowMore', {count: hiddenCount}))}</span>`;
    html += '<i class="fa-solid fa-chevron-down story-toggle-chevron"></i>';
    html += '</button>';
  }

  container.innerHTML = html;

  /* ── Block hover depth: pull-out effect via border-left expansion ── */
  const allBlocks = container.querySelectorAll('.story-block');
  allBlocks.forEach(function(block) {
    block.addEventListener('mouseenter', function() {
      block.style.borderLeftWidth = '4px';
      block.style.paddingLeft = '18px';
    });
    block.addEventListener('mouseleave', function() {
      block.style.borderLeftWidth = '';
      block.style.paddingLeft = '';
    });
  });

  /* ── Scroll-reveal animation ── */
  _initStoryScrollReveal(container);

  /* ── Bind toggle ── */
  if (needsCollapse) {
    const toggleBtn = container.querySelector('.story-toggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => {
        const isExpanded = toggleBtn.getAttribute('aria-expanded') === 'true';
        const textEl = toggleBtn.querySelector('.story-toggle-text');
        /* Select blocks beyond the visible threshold by data attribute */
        const overflowBlocks = container.querySelectorAll(
          Array.from({length: totalBlocks - _STORY_VISIBLE_COUNT}, (_, i) =>
            `.story-block[data-story-idx="${_STORY_VISIBLE_COUNT + i}"]`
          ).join(',')
        );
        if (isExpanded) {
          /* Collapse: animate out then add hidden class */
          overflowBlocks.forEach(el => { el.style.maxHeight = '0'; el.style.opacity = '0'; el.style.transform = 'translateX(-20px)'; });
          setTimeout(() => overflowBlocks.forEach(el => el.classList.add('story-block--hidden')), 350);
          toggleBtn.setAttribute('aria-expanded', 'false');
          toggleBtn.classList.remove('story-toggle--expanded');
          if (textEl) {
            const hiddenCount = totalBlocks - _STORY_VISIBLE_COUNT;
            textEl.textContent = t('storyShowMore', {count: hiddenCount});
          }
        } else {
          /* Expand: remove hidden class then animate in with staggered reveal */
          overflowBlocks.forEach((el, idx) => {
            el.classList.remove('story-block--hidden');
            el.style.opacity = '0';
            el.style.transform = 'translateX(-20px)';
            el.style.transition = 'opacity 0.5s ease, transform 0.5s ease, background 0.25s ease, border-color 0.25s ease, max-height 0.35s ease, border-left-width 0.25s ease, padding-left 0.25s ease';
            requestAnimationFrame(() => {
              setTimeout(function() {
                el.style.maxHeight = '120px';
                el.style.opacity = '1';
                el.style.transform = 'translateX(0)';
              }, idx * 60);
            });
          });
          toggleBtn.setAttribute('aria-expanded', 'true');
          toggleBtn.classList.add('story-toggle--expanded');
          if (textEl) textEl.textContent = t('storyShowLess');
        }
      });
    }
  }
}
