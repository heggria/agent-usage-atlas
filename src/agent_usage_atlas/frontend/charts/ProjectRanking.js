function renderProjectRanking(){
  const rows = data.projects.ranking.slice(0, 15);
  const chart = initChart('project-ranking-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 140, right: 60, bottom: 24},
    tooltip: {...chartTheme().tooltip, valueFormatter: value => fmtShort(value)},
    xAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtShort(value)}},
    yAxis: {type: 'category', data: rows.map(row => row.project).reverse(), axisLabel: {color: TX, fontSize: 11}},
    series: [{
      type: 'bar',
      barMaxWidth: 22,
      data: rows.map(row => ({value: row.total_tokens, itemStyle: {color: '#74c0fc', borderRadius: [0, 6, 6, 0]}})).reverse(),
      label: {show: true, position: 'right', color: TX, fontSize: 11, formatter: params => fmtShort(params.value)}
    }]
  });
}
