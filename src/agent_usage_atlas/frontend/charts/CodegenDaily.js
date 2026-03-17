function renderCodegenDailyChart(){
  const ext = data.extended;
  if (!ext || !ext.cursor_codegen || !ext.cursor_codegen.total) return;
  const rows = ext.cursor_codegen.daily;
  const chart = initChart('codegen-daily-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 48, right: 24, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis'},
    xAxis: {type: 'category', data: rows.map(r => r.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    series: [{
      type: 'bar', barMaxWidth: 14,
      itemStyle: {color: '#748ffc', borderRadius: [4,4,0,0]},
      data: rows.map(r => r.count)
    }]
  });
}
