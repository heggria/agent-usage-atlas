function renderDailyTurnDurChart(){
  const ext = data.extended;
  if (!ext || !ext.turn_durations) return;
  const rows = ext.turn_durations.daily.filter(r => r.count > 0);
  if (!rows.length) return;
  const chart = initChart('daily-turn-dur-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 56, right: 24, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis', valueFormatter: v => v == null ? '-' : (v/1000).toFixed(1)+'s'},
    xAxis: {type: 'category', data: rows.map(r => r.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: {type: 'value', name: 'ms', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: v => (v/1000).toFixed(0)+'s'}},
    series: [{
      type: 'line', smooth: true, symbolSize: 5,
      lineStyle: {width: 2, color: '#b197fc'}, itemStyle: {color: '#b197fc'},
      areaStyle: {color: 'rgba(177,151,252,.12)'},
      data: rows.map(r => r.median_ms)
    }]
  });
}
