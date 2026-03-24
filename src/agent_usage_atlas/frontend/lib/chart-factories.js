/**
 * Chart factory functions for reducing boilerplate across chart files.
 *
 * Existing factories:
 *   makeCalendarHeatmap — shared setup for CostCalendar / TokenCalendar
 *   makeHorizontalBar   — shared setup for horizontal bar charts
 *
 * Unified design factories (new):
 *   makeTooltip(opts)           — polished, theme-aware tooltip config (blurred backdrop, 12px body / 13px header)
 *   smartFormatter(value, type) — auto-format values by metric type
 *   makeLegend(opts)            — scrollable, styled legend config with emphasis feedback
 *   makeGrid(opts)              — responsive grid with smart margins
 *   emptyChartOption(msg)       — centered "no data" placeholder for empty charts
 */

/* ── Unified Tooltip Factory ─────────────────────────────────────────── */

/**
 * Build a consistently styled, theme-aware ECharts tooltip config.
 *
 * @param {object} [opts]
 * @param {'item'|'axis'|'none'} [opts.trigger='item'] - tooltip trigger type
 * @param {'shadow'|'cross'|'line'|'none'} [opts.axisPointerType] - axis pointer style (only for trigger:'axis')
 * @param {string} [opts.metricType] - auto-format values: 'cost','tokens','count','percent','duration'
 * @param {function} [opts.formatter] - custom formatter (overrides metricType)
 * @param {function} [opts.valueFormatter] - custom value formatter (overrides metricType)
 * @param {boolean} [opts.colorDot=true] - show color dot before series name
 * @param {object} [opts.extra] - additional ECharts tooltip properties to merge
 * @returns {object} ECharts tooltip configuration object
 */
function makeTooltip(opts) {
  const o = opts || {};
  const light = _isLight();

  const base = {
    backgroundColor: light ? 'rgba(255,255,255,0.96)' : 'rgba(20,20,30,0.9)',
    borderColor: light ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.1)',
    borderWidth: 1,
    borderRadius: 8,
    padding: [10, 14],
    textStyle: {
      color: light ? '#1a1a2e' : '#ece7df',
      fontSize: 12,
      fontFamily: 'Inter,-apple-system,PingFang SC,sans-serif'
    },
    extraCssText: light
      ? 'backdrop-filter:blur(8px);border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,0.12);max-width:320px;'
      : 'backdrop-filter:blur(8px);border-radius:8px;box-shadow:0 8px 32px rgba(0,0,0,0.3);max-width:320px;'
  };

  if (o.trigger) {
    base.trigger = o.trigger;
  }

  if (o.trigger === 'axis' && o.axisPointerType) {
    base.axisPointer = {type: o.axisPointerType};
  }

  /* Apply value formatting — explicit formatter wins, then metricType */
  if (o.formatter) {
    base.formatter = o.formatter;
  } else if (o.valueFormatter) {
    base.valueFormatter = o.valueFormatter;
  } else if (o.metricType) {
    base.valueFormatter = function(value) {
      return smartFormatter(value, o.metricType);
    };
  }

  /* Rich axis tooltip with color dots and right-aligned values */
  if (o.trigger === 'axis' && !o.formatter && o.colorDot !== false) {
    const valueFmt = o.valueFormatter || base.valueFormatter || null;
    base.formatter = function(params) {
      if (!Array.isArray(params)) params = [params];
      const header = _escHtml(String(params[0].axisValueLabel || params[0].name || ''));
      const secondaryColor = light ? 'rgba(0,0,0,0.45)' : 'rgba(255,255,255,0.5)';
      const borderColor = light ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)';
      const filtered = params.filter(function(p) { return p.value != null; });
      var total = 0;
      var showTotal = filtered.length > 1;
      const lines = filtered
        .map(function(p) {
          const rawVal = typeof p.value === 'object' ? p.value[1] : p.value;
          const numVal = Number(rawVal) || 0;
          total += numVal;
          const dot = '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:'
            + (p.color || '#999') + ';margin-right:6px;vertical-align:middle;flex-shrink:0;"></span>';
          const name = '<span style="font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
            + _escHtml(p.seriesName || '') + '</span>';
          const val = valueFmt ? valueFmt(rawVal) : String(rawVal);
          const valSpan = '<span style="margin-left:16px;font-weight:600;font-size:12px;font-family:\'SF Mono\',Menlo,Consolas,monospace;white-space:nowrap">'
            + _escHtml(val) + '</span>';
          return '<div style="display:flex;align-items:center;justify-content:space-between;margin:3px 0">'
            + '<span style="display:flex;align-items:center;overflow:hidden">' + dot + name + '</span>'
            + valSpan + '</div>';
        });
      var totalRow = '';
      if (showTotal) {
        const totalVal = valueFmt ? valueFmt(total) : String(total);
        totalRow = '<div style="display:flex;align-items:center;justify-content:space-between;margin-top:5px;'
          + 'padding-top:5px;border-top:1px solid ' + borderColor + ';font-size:12px">'
          + '<span style="opacity:.7">Total</span>'
          + '<span style="font-weight:700;font-family:\'SF Mono\',Menlo,Consolas,monospace">'
          + _escHtml(totalVal) + '</span></div>';
      }
      return '<div style="font-size:13px;font-weight:600;padding-bottom:5px;margin-bottom:4px;'
        + 'border-bottom:1px solid ' + borderColor + ';color:' + (light ? '#1a1a2e' : '#ece7df') + '">'
        + header + '</div>'
        + lines.join('')
        + totalRow;
    };
  }

  if (o.extra) {
    Object.assign(base, o.extra);
  }

  return base;
}

/* ── Smart Value Formatter ───────────────────────────────────────────── */

/**
 * Auto-format a value based on its metric type.
 *
 * @param {number} value - the numeric value
 * @param {string} metricType - one of 'cost','tokens','count','percent','duration'
 * @returns {string} formatted string
 */
function smartFormatter(value, metricType) {
  const v = Number(value || 0);
  switch (metricType) {
    case 'cost':
      return fmtUSD(v);
    case 'tokens':
      return fmtShort(v);
    case 'count':
      return fmtInt(v);
    case 'percent':
      return fmtPct(v);
    case 'duration': {
      const abs = Math.abs(v);
      const sign = v < 0 ? '-' : '';
      if (abs >= 3600) {
        const h = Math.floor(abs / 3600);
        const m = Math.round((abs % 3600) / 60);
        return sign + h + 'h ' + m + 'm';
      }
      if (abs >= 60) {
        const m = Math.floor(abs / 60);
        const s = Math.round(abs % 60);
        return sign + m + 'm ' + s + 's';
      }
      return sign + Math.round(abs) + 's';
    }
    default:
      return String(v);
  }
}

/* ── Unified Legend Factory ───────────────────────────────────────────── */

/**
 * Build a consistently styled ECharts legend config.
 *
 * @param {object} [opts]
 * @param {'scroll'|'plain'} [opts.type] - legend type; defaults to 'scroll' when itemCount > 5
 * @param {'horizontal'|'vertical'} [opts.orient='horizontal'] - layout
 * @param {string|number} [opts.top=6] - position top
 * @param {string|number} [opts.left='center'] - position left
 * @param {string|number} [opts.bottom] - position bottom (overrides top when set)
 * @param {string|number} [opts.right] - position right
 * @param {number} [opts.itemCount] - hint for auto-choosing scroll type
 * @param {'circle'|'roundRect'|'rect'|'triangle'|'diamond'|'pin'|'arrow'|'none'} [opts.icon] - icon shape
 * @param {'line'|'bar'|'scatter'|'pie'} [opts.chartType] - auto-pick icon: circle for line/scatter/pie, roundRect for bar
 * @param {number} [opts.itemWidth=12] - icon width
 * @param {number} [opts.itemHeight=12] - icon height
 * @param {number} [opts.itemGap=16] - gap between items
 * @param {object} [opts.extra] - additional ECharts legend properties to merge
 * @returns {object} ECharts legend configuration object
 */
function makeLegend(opts) {
  const o = opts || {};
  const light = _isLight();

  /* Auto-determine icon shape from chart type if not explicitly set */
  let icon = o.icon;
  if (!icon && o.chartType) {
    icon = (o.chartType === 'bar') ? 'roundRect' : 'circle';
  }

  /* Auto-scroll when many items */
  const count = o.itemCount || 0;
  const legendType = o.type || (count > 5 ? 'scroll' : 'plain');

  const base = {
    type: legendType,
    orient: o.orient || 'horizontal',
    itemWidth: o.itemWidth || 12,
    itemHeight: o.itemHeight || 12,
    itemGap: o.itemGap || 16,
    textStyle: {
      color: light ? 'rgba(0,0,0,0.6)' : TX,
      fontSize: 12,
      fontFamily: 'Inter,-apple-system,PingFang SC,sans-serif'
    },
    inactiveColor: light ? 'rgba(0,0,0,0.2)' : 'rgba(255,255,255,0.15)',
    selectedMode: true,
    emphasis: {
      selectorLabel: {fontSize: 13}
    }
  };

  if (icon) {
    base.icon = icon;
  }

  /* Position — bottom overrides top */
  if (o.bottom != null) {
    base.bottom = o.bottom;
  } else {
    base.top = o.top != null ? o.top : 6;
  }
  if (o.left != null) {
    base.left = o.left;
  }
  if (o.right != null) {
    base.right = o.right;
  }

  /* Scroll-mode page controls */
  if (legendType === 'scroll') {
    base.pageTextStyle = {color: light ? 'rgba(0,0,0,0.55)' : 'rgba(255,255,255,0.68)'};
    base.pageIconColor = light ? 'rgba(0,0,0,0.45)' : 'rgba(255,255,255,0.6)';
    base.pageIconInactiveColor = light ? 'rgba(0,0,0,0.15)' : 'rgba(255,255,255,0.15)';
  }

  if (o.extra) {
    Object.assign(base, o.extra);
  }

  return base;
}

/* ── Responsive Grid Helper ──────────────────────────────────────────── */

/**
 * Build a responsive ECharts grid config with smart margin detection.
 *
 * @param {object} [opts]
 * @param {number} [opts.top=36] - top margin
 * @param {number} [opts.right=24] - right margin
 * @param {number} [opts.bottom=44] - bottom margin
 * @param {number} [opts.left] - left margin (auto-detected if omitted)
 * @param {boolean} [opts.containLabel=false] - use ECharts containLabel mode
 * @param {boolean} [opts.compact=false] - mobile-optimized tight margins
 * @param {boolean} [opts.hasLegend=false] - add extra top space for legend
 * @param {'cost'|'tokens'|'count'|'percent'} [opts.yMetricType] - auto-detect left margin from expected label width
 * @param {number} [opts.maxYValue] - largest Y-axis value (used with yMetricType for margin calc)
 * @returns {object} ECharts grid configuration object
 */
function makeGrid(opts) {
  const o = opts || {};
  const compact = o.compact || false;

  /* Defaults vary by compact mode */
  const defaults = compact
    ? {top: 28, right: 12, bottom: 32, left: 44}
    : {top: 36, right: 24, bottom: 44, left: 60};

  /* Auto-detect left margin based on Y-axis value magnitudes */
  let autoLeft = defaults.left;
  if (o.yMetricType && o.maxYValue != null) {
    const sample = smartFormatter(o.maxYValue, o.yMetricType);
    const charWidth = compact ? 6.5 : 7.5;
    /* Approximate width: character count * avg char width + padding */
    autoLeft = Math.max(defaults.left, Math.ceil(sample.length * charWidth) + 16);
  }

  const grid = {
    top: o.top != null ? o.top : (o.hasLegend ? defaults.top + 24 : defaults.top),
    right: o.right != null ? o.right : defaults.right,
    bottom: o.bottom != null ? o.bottom : defaults.bottom,
    left: o.left != null ? o.left : autoLeft
  };

  if (o.containLabel) {
    grid.containLabel = true;
  }

  return grid;
}

/* ── Empty Chart Placeholder ───────────────────────────────────────── */

/**
 * Return an ECharts option that displays a centered "no data" message.
 * Use when a chart has no data to render, providing a clean empty state
 * instead of a blank container.
 *
 * @param {string} [msg='No data'] - message to display
 * @returns {object} ECharts option object
 */
function emptyChartOption(msg) {
  const light = _isLight();
  return {
    title: {
      text: msg || 'No data',
      left: 'center',
      top: 'center',
      textStyle: {
        color: light ? 'rgba(0,0,0,0.35)' : 'rgba(255,255,255,0.35)',
        fontSize: 14,
        fontWeight: 'normal',
        fontFamily: 'Inter,-apple-system,PingFang SC,sans-serif'
      }
    }
  };
}

/**
 * Create a calendar heatmap chart.
 * @param {string} containerId - DOM element id
 * @param {function} dataMapper - (day) => [dateStr, value]
 * @param {function} tooltipFmt - (params) => tooltip string
 * @param {string[]} colorRange - array of colors for visualMap inRange
 * @param {string[]} lightColorRange - array of colors for light theme
 * @returns {object|null} ECharts instance or null if data missing
 */
function makeCalendarHeatmap(containerId, dataMapper, tooltipFmt, colorRange, lightColorRange) {
  if (!data || !data.days || !data.days.length || !data.range) return null;
  const chart = initChart(containerId);
  const cells = data.days.map(dataMapper);
  const maxVal = Math.max(...cells.map(c => c[1]), 1);
  chart.setOption({
    ...chartTheme(),
    tooltip: {...chartTheme().tooltip, formatter: tooltipFmt},
    visualMap: {
      min: 0, max: maxVal, orient: 'horizontal', left: 'center', bottom: 8,
      textStyle: {color: TX},
      inRange: {color: _isLight() ? (lightColorRange || colorRange) : colorRange}
    },
    calendar: {
      orient: 'vertical', top: 28, left: 36, right: 16, bottom: 48,
      cellSize: ['auto', 'auto'],
      range: [data.range.start_local.slice(0, 10), data.range.end_local.slice(0, 10)],
      yearLabel: {show: false},
      monthLabel: {color: TX, ...(lang === 'zh' ? {nameMap: 'ZH'} : {}), margin: 8},
      dayLabel: {color: TX, firstDay: 1, ...(lang === 'zh' ? {nameMap: 'ZH'} : {})},
      splitLine: {lineStyle: {color: AX}},
      itemStyle: {borderWidth: 3, borderColor: _CARD_BG(), color: BG}
    },
    series: [{type: 'heatmap', coordinateSystem: 'calendar', data: cells}]
  });
  return chart;
}

/**
 * Create a horizontal bar chart.
 * @param {string} containerId - DOM element id
 * @param {object} opts
 * @param {Array} opts.rows - data rows
 * @param {function} opts.labelFn - (row) => label string
 * @param {function} opts.valueFn - (row) => numeric value
 * @param {function|string|string[]} opts.color - color string, array (indexed), or (row, index) => color
 * @param {number} [opts.leftMargin=120] - grid left margin
 * @param {function} [opts.tooltipFmt] - tooltip value formatter
 * @param {function} [opts.labelFmt] - bar label formatter
 * @param {function} [opts.xAxisFmt] - x-axis label formatter
 * @param {number} [opts.labelWidth] - y-axis label width (overflow: truncate)
 * @param {object} [opts.tooltipOpts] - extra tooltip config
 * @returns {object|null} ECharts instance or null if no data
 */
function makeHorizontalBar(containerId, opts) {
  if (!opts.rows || !opts.rows.length) return null;
  const chart = initChart(containerId);
  const rows = opts.rows;
  const labels = rows.map(opts.labelFn).reverse();
  const _getColor = (row, i) => {
    if (typeof opts.color === 'function') return opts.color(row, i);
    if (Array.isArray(opts.color)) return opts.color[i % opts.color.length];
    return opts.color || '#ffd43b';
  };
  const barData = rows.map((row, i) => ({
    value: opts.valueFn(row),
    itemStyle: {color: _getColor(row, i), borderRadius: [0, 6, 6, 0]}
  })).reverse();

  const seriesConfig = {
    type: 'bar',
    barMaxWidth: 22,
    data: barData,
    label: {show: true, position: 'right', color: TX, fontSize: 11}
  };
  if (opts.labelFmt) {
    seriesConfig.label.formatter = opts.labelFmt;
  }

  const yAxisConfig = {
    type: 'category', data: labels,
    axisLabel: {color: TX, fontSize: 11}
  };
  if (opts.labelWidth) {
    yAxisConfig.axisLabel.width = opts.labelWidth;
    yAxisConfig.axisLabel.overflow = 'truncate';
  }

  const chartOpts = {
    ...chartTheme(),
    grid: {top: 24, left: opts.leftMargin || 120, right: opts.rightMargin || 60, bottom: opts.bottomMargin || 24, ...(opts.containLabel ? {containLabel: true} : {})},
    xAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    yAxis: yAxisConfig,
    series: [seriesConfig]
  };
  if (opts.xAxisFmt) {
    chartOpts.xAxis.axisLabel.formatter = opts.xAxisFmt;
  }
  if (opts.tooltipFmt) {
    chartOpts.tooltip = {...chartTheme().tooltip, valueFormatter: opts.tooltipFmt};
  }
  if (opts.tooltipOpts) {
    chartOpts.tooltip = {...chartTheme().tooltip, ...opts.tooltipOpts};
  }

  chart.setOption(chartOpts);
  return chart;
}
