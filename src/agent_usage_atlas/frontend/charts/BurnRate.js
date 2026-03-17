function renderBurnRateChart(){
  const history = data.trend_analysis.burn_rate_30d.history;
  const projection = data.trend_analysis.burn_rate_30d.projection;
  const labels = [...history.map(row => row.label), ...projection.map(row => row.label)];
  const actualSeries = [...history.map(row => row.cumulative_cost), ...projection.map(() => null)];
  const projectedSeries = [
    ...history.map((row, index) => index === history.length - 1 ? row.cumulative_cost : null),
    ...projection.map(row => row.projected_cumulative_cost)
  ];
  const chart = initChart('burn-rate-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {top: 4, textStyle: {color: TX}},
    grid: {top: 52, left: 56, right: 24, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis', valueFormatter: value => value == null ? '-' : fmtUSD(value)},
    xAxis: {type: 'category', data: labels, axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtUSD(value)}},
    series: [
      {name: t('seriesActualCum'), type: 'line', smooth: true, symbolSize: 6, lineStyle: {width: 3, color: '#74c0fc'}, itemStyle: {color: '#74c0fc'}, data: actualSeries},
      {name: t('seriesProjCum'), type: 'line', smooth: true, symbolSize: 6, lineStyle: {width: 3, type: 'dashed', color: '#ff8a50'}, itemStyle: {color: '#ff8a50'}, data: projectedSeries}
    ]
  });
}
