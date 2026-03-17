function renderBubble(){
  const rows = data.session_deep_dive.complexity_scatter.slice(0, 50);
  const chart = initChart('bubble-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 30, left: 62, right: 24, bottom: 54},
    tooltip: {
      ...chartTheme().tooltip,
      formatter: params => `${params.seriesName}<br>${params.data.session}<br>${fmtShort(params.data.value[1])} tokens<br>${params.data.value[0]} min`
    },
    xAxis: {name: t('axisMinutes'), nameTextStyle: {color: TX}, splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    yAxis: {name: t('axisTokens'), nameTextStyle: {color: TX}, splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtShort(value)}},
    series: ['Codex', 'Claude', 'Cursor'].map(source => ({
      name: source,
      type: 'scatter',
      data: rows.filter(row => row.source === source).map(row => ({
        value: [Math.max(row.duration_minutes, 1), row.total_tokens, Math.max(12, Math.sqrt(row.cache_total || 1) / 180)],
        session: row.session_id.slice(0, 12) + '…'
      })),
      symbolSize: value => value[2],
      itemStyle: {color: C[source] || '#888', opacity: .82}
    }))
  });
}
