function renderTokenCalendar(){
  const chart = initChart('token-calendar-chart');
  const cells = data.days.map(day => [day.date, day.total_tokens]);
  chart.setOption({
    ...chartTheme(),
    tooltip: {...chartTheme().tooltip, formatter: params => `${params.value[0]}<br>${fmtInt(params.value[1])} tokens`},
    visualMap: {min: 0, max: Math.max(...data.days.map(day => day.total_tokens), 1), orient: 'horizontal', left: 'center', bottom: 8, textStyle: {color: TX}, inRange: {color: ['rgba(255,255,255,.03)','#3a4a2e','#51cf66','#a9e34b']}},
    calendar: {orient: 'vertical', top: 28, left: 36, right: 16, bottom: 48, cellSize: ['auto', 'auto'], range: [data.range.start_local.slice(0, 10), data.range.end_local.slice(0, 10)], yearLabel: {show: false}, monthLabel: {color: TX, nameMap: 'ZH', margin: 8}, dayLabel: {color: TX, firstDay: 1, nameMap: 'ZH'}, splitLine: {lineStyle: {color: AX}}, itemStyle: {borderWidth: 3, borderColor: '#0d1016', color: BG}},
    series: [{type: 'heatmap', coordinateSystem: 'calendar', data: cells}]
  });
}
