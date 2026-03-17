function renderCostBreakdownChart(){
  const T = data.totals;
  const items = [
    {name: 'Uncached Input', value: T.cost_input, color: C.uncached},
    {name: 'Cache Read', value: T.cost_cache_read, color: C.cacheRead},
    {name: 'Cache Write', value: T.cost_cache_write, color: C.cacheWrite},
    {name: 'Output', value: T.cost_output, color: C.output},
    {name: 'Reasoning', value: T.cost_reasoning, color: C.reason}
  ].filter(item => item.value > 0);
  const chart = initChart('cost-breakdown-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {bottom: 0, textStyle: {color: TX}},
    tooltip: {...chartTheme().tooltip, formatter: params => `${params.name}<br>${fmtUSD(params.value)} (${params.percent}%)`},
    series: [{
      type: 'pie',
      radius: ['40%', '74%'],
      center: ['50%', '45%'],
      itemStyle: {borderRadius: 10, borderColor: 'rgba(13,16,22,.95)', borderWidth: 3},
      label: {color: TX, formatter: params => `${params.name}\n${params.percent}%`},
      data: items.map(item => ({name: item.name, value: +item.value.toFixed(4), itemStyle: {color: item.color}}))
    }]
  });
}
