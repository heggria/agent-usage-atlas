function renderCostPerToolChart(){
  const rows = data.trend_analysis.daily_cost_per_tool_call;
  const chart = initChart('cost-per-tool-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 56, right: 24, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis', valueFormatter: value => fmtUSD(value)},
    xAxis: {type: 'category', data: rows.map(row => row.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtUSD(value)}},
    series: [{
      type: 'line',
      smooth: true,
      symbolSize: 7,
      lineStyle: {width: 3, color: '#ff8a50'},
      itemStyle: {color: '#ff8a50'},
      areaStyle: {color: 'rgba(255,138,80,.14)'},
      data: rows.map(row => row.value)
    }]
  });
}
