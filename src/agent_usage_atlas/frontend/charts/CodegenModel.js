function renderCodegenModelChart(){
  const ext = data.extended;
  if (!ext || !ext.cursor_codegen || !ext.cursor_codegen.total) return;
  const rows = ext.cursor_codegen.by_model.slice(0, 8);
  const chart = initChart('codegen-model-chart');
  const colors = ['#ff8a50','#ffd43b','#74c0fc','#51cf66','#b197fc','#e599f7','#ff6b6b','#f4b183'];
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 8, right: 24, bottom: 44, containLabel: true},
    tooltip: {...chartTheme().tooltip, trigger: 'axis'},
    xAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    yAxis: {type: 'category', data: rows.map(r => r.model).reverse(), axisLabel: {color: TX, fontSize: 10, width: 140, overflow: 'truncate'}},
    series: [{
      type: 'bar', barMaxWidth: 22,
      data: rows.map((r,i) => ({value: r.count, itemStyle: {color: colors[i%8], borderRadius: [0,6,6,0]}})).reverse()
    }]
  });
}
