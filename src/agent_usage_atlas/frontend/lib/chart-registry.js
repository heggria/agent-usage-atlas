/**
 * ChartRegistry — declarative chart lifecycle manager.
 *
 * Coexists with the existing bare-function chart system (charts.js).
 * Future charts can use ChartRegistry.define() instead of writing
 * standalone render functions.
 *
 * Load order: chart-factories.js < chart-registry.js < charts.js
 * (alphabetical sort in builder.py).  registerLazy is defined in
 * charts.js but is only called at runtime (from initAll), not at
 * parse time, so the dependency is safe.
 */

/* ── Chart metadata for CommandPalette search and quick-nav ────────── */

const _CHART_META = {
  /* ── Cost & Tokens section ── */
  'token-burn-curve':     {label: 'Token Burn Curve',       labelZh: 'Token \u71c3\u70e7\u66f2\u7ebf',  icon: 'fa-fire',              section: 'sec-cost-tokens'},
  'daily-cost-chart':     {label: 'Daily Cost',             labelZh: '\u6bcf\u65e5\u82b1\u8d39',          icon: 'fa-chart-line',        section: 'sec-cost-tokens'},
  'cost-breakdown-chart': {label: 'Cost Breakdown',         labelZh: '\u82b1\u8d39\u7ec4\u6210',          icon: 'fa-chart-pie',         section: 'sec-cost-tokens'},
  'daily-token-chart':    {label: 'Daily Tokens',           labelZh: '\u6bcf\u65e5 Token',        icon: 'fa-chart-bar',         section: 'sec-cost-tokens'},
  'daily-cost-type-chart':{label: 'Daily Cost by Type',     labelZh: '\u6bcf\u65e5\u5206\u7c7b\u82b1\u8d39',      icon: 'fa-chart-area',        section: 'sec-cost-tokens'},
  'cost-calendar-chart':  {label: 'Cost Calendar',          labelZh: '\u82b1\u8d39\u65e5\u5386',          icon: 'fa-calendar-days',     section: 'sec-cost-tokens'},
  'token-calendar-chart': {label: 'Token Calendar',         labelZh: 'Token \u65e5\u5386',        icon: 'fa-calendar-days',     section: 'sec-cost-tokens'},
  'model-cost-chart':     {label: 'Model Cost',             labelZh: '\u6a21\u578b\u82b1\u8d39',          icon: 'fa-robot',             section: 'sec-cost-tokens'},
  'cost-sankey-chart':    {label: 'Cost Sankey',            labelZh: '\u82b1\u8d39\u6851\u57fa\u56fe',        icon: 'fa-diagram-project',   section: 'sec-cost-tokens'},
  'rose-chart':           {label: 'Source Rose',            labelZh: '\u6765\u6e90\u73ab\u7470\u56fe',        icon: 'fa-chart-pie',         section: 'sec-cost-tokens'},
  'cache-gauge':          {label: 'Efficiency Gauges',      labelZh: '\u6548\u7387\u4eea\u8868\u76d8',        icon: 'fa-gauge-high',        section: 'sec-cost-tokens'},
  'token-sankey-chart':   {label: 'Token Sankey',           labelZh: 'Token \u6851\u57fa\u56fe',      icon: 'fa-diagram-project',   section: 'sec-cost-tokens'},

  /* ── Activity & Sessions section ── */
  'heatmap-chart':        {label: 'Activity Heatmap',       labelZh: '\u6d3b\u8dc3\u70ed\u529b\u56fe',        icon: 'fa-braille',           section: 'sec-activity'},
  'source-radar-chart':   {label: 'Source Radar',           labelZh: '\u6765\u6e90\u96f7\u8fbe\u56fe',        icon: 'fa-satellite-dish',    section: 'sec-activity'},
  'timeline-chart':       {label: 'Session Timeline',       labelZh: '\u4f1a\u8bdd\u65f6\u95f4\u7ebf',        icon: 'fa-timeline',          section: 'sec-activity'},
  'bubble-chart':         {label: 'Session Bubble',         labelZh: '\u4f1a\u8bdd\u6c14\u6ce1\u56fe',        icon: 'fa-circle',            section: 'sec-activity'},
  'tempo-chart':          {label: 'Hourly Tempo',           labelZh: '\u5c0f\u65f6\u8282\u594f',          icon: 'fa-wave-square',       section: 'sec-activity'},
  'session-duration-chart':{label: 'Session Duration',      labelZh: '\u4f1a\u8bdd\u65f6\u957f',          icon: 'fa-hourglass-half',    section: 'sec-activity'},
  'model-radar-chart':    {label: 'Model Radar',            labelZh: '\u6a21\u578b\u96f7\u8fbe\u56fe',        icon: 'fa-satellite-dish',    section: 'sec-activity'},
  'turn-dur-chart':       {label: 'Turn Duration',          labelZh: '\u56de\u5408\u65f6\u957f',          icon: 'fa-stopwatch',         section: 'sec-activity'},
  'daily-turn-dur-chart': {label: 'Daily Turn Duration',    labelZh: '\u6bcf\u65e5\u56de\u5408\u65f6\u957f',      icon: 'fa-stopwatch',         section: 'sec-activity'},
  'task-rate-chart':      {label: 'Task Rate',              labelZh: '\u4efb\u52a1\u901f\u7387',          icon: 'fa-tasks',             section: 'sec-activity'},
  'codegen-model-chart':  {label: 'Codegen by Model',       labelZh: '\u6a21\u578b\u4ee3\u7801\u751f\u6210',      icon: 'fa-code',              section: 'sec-activity'},
  'codegen-daily-chart':  {label: 'Daily Codegen',          labelZh: '\u6bcf\u65e5\u4ee3\u7801\u751f\u6210',      icon: 'fa-code',              section: 'sec-activity'},
  'ai-contribution-chart':{label: 'AI Contribution',        labelZh: 'AI \u8d21\u732e\u5ea6',         icon: 'fa-wand-magic-sparkles', section: 'sec-activity'},

  /* ── Tooling & Projects section ── */
  'tool-ranking-chart':   {label: 'Tool Ranking',           labelZh: '\u5de5\u5177\u6392\u540d',          icon: 'fa-ranking-star',      section: 'sec-tooling'},
  'project-ranking-chart':{label: 'Project Ranking',        labelZh: '\u9879\u76ee\u6392\u540d',          icon: 'fa-folder-tree',       section: 'sec-tooling'},
  'tool-density-chart':   {label: 'Tool Density',           labelZh: '\u5de5\u5177\u5bc6\u5ea6',          icon: 'fa-chart-area',        section: 'sec-tooling'},
  'tool-bigram-chart':    {label: 'Tool Bigram',            labelZh: '\u5de5\u5177\u4e8c\u5143\u7ec4',        icon: 'fa-arrow-right-arrow-left', section: 'sec-tooling'},
  'top-commands-chart':   {label: 'Top Commands',           labelZh: '\u70ed\u95e8\u547d\u4ee4',          icon: 'fa-terminal',          section: 'sec-tooling'},
  'command-success-chart':{label: 'Command Success Rate',   labelZh: '\u547d\u4ee4\u6210\u529f\u7387',        icon: 'fa-circle-check',      section: 'sec-tooling'},
  'efficiency-chart':     {label: 'Efficiency',             labelZh: '\u6548\u7387\u5206\u6790',          icon: 'fa-bolt',              section: 'sec-tooling'},
  'file-types-chart':     {label: 'File Types',             labelZh: '\u6587\u4ef6\u7c7b\u578b',          icon: 'fa-file-code',         section: 'sec-tooling'},
  'branch-activity-chart':{label: 'Branch Activity',        labelZh: '\u5206\u652f\u6d3b\u8dc3',          icon: 'fa-code-branch',       section: 'sec-tooling'},
  'productivity-chart':   {label: 'Productivity',           labelZh: '\u751f\u4ea7\u529b',            icon: 'fa-chart-line',        section: 'sec-tooling'},
  'burn-rate-chart':      {label: 'Burn Rate',              labelZh: '\u71c3\u70e7\u901f\u7387',          icon: 'fa-fire-flame-curved', section: 'sec-tooling'},
  'cost-per-tool-chart':  {label: 'Cost per Tool',          labelZh: '\u5de5\u5177\u6210\u672c',          icon: 'fa-coins',             section: 'sec-tooling'},
};

/**
 * Look up metadata for a chart by its DOM element id.
 * Returns { label, labelZh, icon, section } or null if unknown.
 *
 * @param {string} id - chart container DOM id
 * @returns {object|null} chart metadata
 */
function getChartMeta(id) {
  return _CHART_META[id] || null;
}

/**
 * Return all chart metadata entries as an array of { id, label, labelZh, icon, section }.
 * Useful for populating search indexes (e.g. CommandPalette).
 *
 * @returns {Array<{id:string, label:string, labelZh:string, icon:string, section:string}>}
 */
function getAllChartMeta() {
  return Object.keys(_CHART_META).map(function(id) {
    return Object.assign({id: id}, _CHART_META[id]);
  });
}

const ChartRegistry = {
  _charts: new Map(),

  /**
   * Register a chart definition.
   * @param {string} id   - DOM element id for the chart container
   * @param {object} spec
   * @param {string[]}          [spec.deps]   - dot-path data keys that must be non-null
   * @param {(el, data) => any}  spec.init     - create and return the chart instance
   * @param {(chart, data) => void} [spec.update] - update an existing instance with new data
   * @param {boolean}            [spec.eager]  - if true, render immediately instead of lazily
   */
  define(id, spec) {
    this._charts.set(id, {...spec, instance: null, initialized: false});
  },

  /**
   * Initialise all registered charts.  Eager charts render immediately;
   * the rest are handed to the IntersectionObserver-based lazy system.
   */
  initAll(data) {
    this._charts.forEach((spec, id) => {
      if (spec.eager) {
        this._initOne(id, data);
      } else {
        registerLazy(id, () => this._initOne(id, data));
      }
    });
  },

  /** @private */
  _initOne(id, data) {
    const spec = this._charts.get(id);
    if (!spec) return;
    const el = document.getElementById(id);
    if (!el) return;
    // Check that every declared data dependency is present
    if (spec.deps && !spec.deps.every(dep => {
      let obj = data;
      for (const k of dep.split('.')) { obj = obj && obj[k]; }
      return obj != null;
    })) return;
    spec.instance = spec.init(el, data);
    spec.initialized = true;
  },

  /** Re-push data into every initialised chart that has an update fn. */
  updateAll(data) {
    this._charts.forEach((spec, _id) => {
      if (spec.initialized && spec.instance && spec.update) {
        spec.update(spec.instance, data);
      }
    });
  },

  /** Resize every live chart (call on window resize). */
  resizeAll() {
    this._charts.forEach(spec => {
      if (spec.instance && typeof spec.instance.resize === 'function') {
        spec.instance.resize();
      }
    });
  },

  /** Dispose every live chart and reset state. */
  disposeAll() {
    this._charts.forEach(spec => {
      if (spec.instance && typeof spec.instance.dispose === 'function') {
        spec.instance.dispose();
      }
      spec.instance = null;
      spec.initialized = false;
    });
  }
};
