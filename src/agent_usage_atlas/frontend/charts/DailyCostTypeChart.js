function renderDailyCostTypeChart(){
  const chart = initChart('daily-cost-type-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {top: 6, textStyle: {color: TX}},
    grid: {top: 58, left: 68, right: 24, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis', axisPointer: {type: 'shadow'}, valueFormatter: value => fmtUSD(value)},
    xAxis: {type: 'category', data: data.days.map(day => day.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtUSD(value)}},
    series: [
      {name: 'Input', type: 'bar', stack: 'cost-type', itemStyle: {color: C.uncached}, data: data.days.map(day => day.cost_input)},
      {name: 'Cache Read', type: 'bar', stack: 'cost-type', itemStyle: {color: C.cacheRead}, data: data.days.map(day => day.cost_cache_read)},
      {name: 'Cache Write', type: 'bar', stack: 'cost-type', itemStyle: {color: C.cacheWrite}, data: data.days.map(day => day.cost_cache_write)},
      {name: 'Output', type: 'bar', stack: 'cost-type', itemStyle: {color: C.output}, data: data.days.map(day => day.cost_output)},
      {name: 'Reasoning', type: 'bar', stack: 'cost-type', itemStyle: {color: C.reason, borderRadius: [6, 6, 0, 0]}, data: data.days.map(day => day.cost_reasoning)}
    ]
  });
}
