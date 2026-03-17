function renderCommandSuccessChart(){
  const rows = data.commands.daily_success;
  const chart = initChart('command-success-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {top: 4, textStyle: {color: TX}},
    grid: {top: 52, left: 56, right: 24, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis'},
    xAxis: {type: 'category', data: rows.map(row => row.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    series: [
      {name: t('seriesSuccess'), type: 'line', smooth: true, areaStyle: {color: 'rgba(81,207,102,.2)'}, itemStyle: {color: '#51cf66'}, lineStyle: {width: 3, color: '#51cf66'}, data: rows.map(row => row.successes)},
      {name: t('seriesFail'), type: 'line', smooth: true, areaStyle: {color: 'rgba(255,107,107,.16)'}, itemStyle: {color: '#ff6b6b'}, lineStyle: {width: 3, color: '#ff6b6b'}, data: rows.map(row => row.failures)}
    ]
  });
}
