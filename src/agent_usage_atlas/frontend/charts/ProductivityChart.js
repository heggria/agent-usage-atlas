function renderProductivityChart(){
  const rows = data.working_patterns.daily_productivity;
  const chart = initChart('productivity-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 56, right: 24, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis'},
    xAxis: {type: 'category', data: rows.map(row => row.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: {type: 'value', min: 0, max: 1, splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    series: [{
      name: t('seriesProductivity'),
      type: 'line',
      smooth: true,
      symbolSize: 8,
      lineStyle: {width: 3, color: '#ffd43b'},
      itemStyle: {color: '#ffd43b'},
      areaStyle: {color: 'rgba(255,212,59,.14)'},
      data: rows.map(row => row.score)
    }]
  });
}
