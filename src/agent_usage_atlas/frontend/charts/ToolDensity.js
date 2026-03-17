function renderToolDensity(){
  const rows = data.working_patterns.hourly_tool_density;
  const chart = initChart('tool-density-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 48, right: 24, bottom: 44},
    xAxis: {type: 'category', data: rows.map(row => `${row.hour}h`), axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    series: [{type: 'bar', data: rows.map(row => ({value: row.count, itemStyle: {color: '#ffd43b', borderRadius: [6, 6, 0, 0]}}))}]
  });
}
