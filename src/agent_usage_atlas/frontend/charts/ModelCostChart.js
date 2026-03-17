function renderModelCostChart(){
  const rows = data.trend_analysis.model_costs.slice(0, 10);
  const chart = initChart('model-cost-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 170, right: 60, bottom: 24},
    tooltip: {...chartTheme().tooltip, valueFormatter: value => fmtUSD(value)},
    xAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtUSD(value)}},
    yAxis: {type: 'category', data: rows.map(row => row.model).reverse(), axisLabel: {color: TX, width: 150, overflow: 'truncate', fontSize: 11}},
    series: [{
      type: 'bar',
      barMaxWidth: 22,
      data: rows.map((row, index) => ({value: row.cost, itemStyle: {color: ['#ff6b6b','#ff8a50','#ffa94d','#ffd43b','#a9e34b','#51cf66','#74c0fc','#748ffc','#b197fc','#e599f7'][index % 10], borderRadius: [0, 6, 6, 0]}})).reverse(),
      label: {show: true, position: 'right', color: TX, formatter: params => fmtUSD(params.value), fontSize: 11}
    }]
  });
}
