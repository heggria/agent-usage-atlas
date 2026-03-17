function renderEfficiencyChart(){
  const rows = data.efficiency_metrics.daily;
  const chart = initChart('efficiency-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {top: 4, textStyle: {color: TX}},
    grid: {top: 52, left: 56, right: 56, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis'},
    xAxis: {type: 'category', data: rows.map(row => row.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: [
      {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtPct(value)}},
      {type: 'value', splitLine: {show: false}, axisLabel: {color: TX, formatter: value => fmtShort(value)}}
    ],
    series: [
      {name: t('seriesReasonRatio'), type: 'line', smooth: true, itemStyle: {color: C.reason}, lineStyle: {width: 3, color: C.reason}, data: rows.map(row => row.reasoning_ratio)},
      {name: t('seriesCacheHitRate'), type: 'line', smooth: true, itemStyle: {color: C.cacheRead}, lineStyle: {width: 3, color: C.cacheRead}, data: rows.map(row => row.cache_hit_rate)},
      {name: t('seriesTokensPerMsg'), type: 'line', yAxisIndex: 1, smooth: true, itemStyle: {color: C.output}, lineStyle: {width: 3, color: C.output}, data: rows.map(row => row.tokens_per_message)}
    ]
  });
}
