function renderTaskRateChart(){
  const ext = data.extended;
  if (!ext || !ext.task_events) return;
  const te = ext.task_events;
  if (!te.started) return;
  const chart = initChart('task-rate-chart');
  const failed = te.started - te.completed;
  chart.setOption({
    ...chartTheme(),
    tooltip: {...chartTheme().tooltip, trigger: 'item'},
    legend: {bottom: 0, textStyle: {color: TX}},
    series: [{
      type: 'pie', radius: ['40%', '68%'], center: ['50%', '44%'],
      label: {color: TX, formatter: '{b}: {c} ({d}%)'},
      data: [
        {value: te.completed, name: t('lblCompleted'), itemStyle: {color: '#51cf66'}},
        {value: failed, name: t('lblIncomplete'), itemStyle: {color: '#ff6b6b'}}
      ]
    }]
  });
}
