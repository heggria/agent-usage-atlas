function renderSessionDurationChart(){
  const rows = data.session_deep_dive.duration_histogram;
  const chart = initChart('session-duration-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 48, right: 24, bottom: 44},
    xAxis: {type: 'category', data: rows.map(row => row.label), axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    series: [{type: 'bar', barMaxWidth: 30, data: rows.map(row => ({value: row.count, itemStyle: {color: '#51cf66', borderRadius: [6, 6, 0, 0]}}))}]
  });
}
