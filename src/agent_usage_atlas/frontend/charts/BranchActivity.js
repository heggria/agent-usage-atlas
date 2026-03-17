function renderBranchActivityChart(){
  const rows = data.projects.branch_activity.slice(0, 12);
  const chart = initChart('branch-activity-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 120, right: 60, bottom: 24},
    xAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    yAxis: {type: 'category', data: rows.map(row => row.branch).reverse(), axisLabel: {color: TX, fontSize: 11}},
    series: [{
      type: 'bar',
      barMaxWidth: 22,
      data: rows.map(row => ({value: row.sessions, itemStyle: {color: '#b197fc', borderRadius: [0, 6, 6, 0]}})).reverse(),
      label: {show: true, position: 'right', color: TX, fontSize: 11}
    }]
  });
}
