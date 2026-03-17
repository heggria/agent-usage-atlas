function renderDailyCostChart(){
  const chart = initChart('daily-cost-chart');
  const sources = getTokenSources().map(card => card.source);
  chart.setOption({
    ...chartTheme(),
    legend: {top: 6, textStyle: {color: TX}},
    grid: {top: 58, left: 68, right: 68, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis', axisPointer: {type: 'shadow'}, valueFormatter: value => fmtUSD(value)},
    xAxis: {type: 'category', data: data.days.map(day => day.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: [
      {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtUSD(value)}},
      {type: 'value', splitLine: {show: false}, axisLabel: {color: TX, formatter: value => fmtUSD(value)}}
    ],
    series: [
      ...sources.map(source => ({
        name: source,
        type: 'bar',
        stack: 'cost',
        itemStyle: {color: C[source] || '#999', borderRadius: [6, 6, 0, 0]},
        data: data.days.map(day => +(day.cost_sources[source] || 0).toFixed(4))
      })),
      {
        name: t('seriesCumulative'),
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbolSize: 6,
        lineStyle: {width: 3, color: 'rgba(255,255,255,.75)'},
        itemStyle: {color: '#fff'},
        areaStyle: {color: 'rgba(255,255,255,.06)'},
        data: data.days.map(day => day.cost_cumulative)
      }
    ]
  });
}
