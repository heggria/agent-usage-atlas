function renderToolRanking(){
  const rows = data.tooling.ranking.slice(0, 20);
  const chart = initChart('tool-ranking-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 120, right: 60, bottom: 24},
    xAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    yAxis: {type: 'category', data: rows.map(row => row.name).reverse(), axisLabel: {color: TX, fontSize: 11}},
    series: [{
      type: 'bar',
      barMaxWidth: 22,
      data: rows.map(row => ({value: row.count, itemStyle: {color: '#ffd43b', borderRadius: [0, 6, 6, 0]}})).reverse(),
      label: {show: true, position: 'right', color: TX, fontSize: 11}
    }]
  });
}
