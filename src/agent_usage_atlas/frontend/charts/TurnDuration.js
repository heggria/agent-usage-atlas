function renderTurnDurChart(){
  const ext = data.extended;
  if (!ext || !ext.turn_durations) return;
  const rows = ext.turn_durations.histogram;
  const chart = initChart('turn-dur-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 48, right: 24, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis'},
    xAxis: {type: 'category', data: rows.map(r => r.label), axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    series: [{
      type: 'bar', barMaxWidth: 30,
      data: rows.map(r => ({value: r.count, itemStyle: {color: '#74c0fc', borderRadius: [6,6,0,0]}}))
    }]
  });
}
