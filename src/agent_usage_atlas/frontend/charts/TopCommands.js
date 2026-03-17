function renderTopCommands(){
  const rows = data.commands.top_commands.slice(0, 15);
  const chart = initChart('top-commands-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 110, right: 60, bottom: 24},
    xAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    yAxis: {type: 'category', data: rows.map(row => row.command).reverse(), axisLabel: {color: TX, fontSize: 11}},
    series: [{
      type: 'bar',
      barMaxWidth: 22,
      data: rows.map(row => ({
        value: row.count,
        itemStyle: {color: row.failure_rate > .3 ? '#ff6b6b' : '#51cf66', borderRadius: [0, 6, 6, 0]}
      })).reverse(),
      label: {show: true, position: 'right', color: TX, fontSize: 11}
    }]
  });
}
