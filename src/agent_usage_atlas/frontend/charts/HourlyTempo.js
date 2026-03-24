function renderTempo(){
  const rows = data.working_patterns.hourly_source_totals;
  const chart = initChart('tempo-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {top: 4, textStyle: {color: TX}},
    grid: {top: 52, left: 56, right: 24, bottom: 46},
    xAxis: {type: 'category', data: rows.map(row => `${row.hour}`), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtShort(value)}},
    series: ['Codex', 'Claude', 'Hermit', 'Cursor'].map(source => ({
      name: source,
      type: source === 'Cursor' ? 'line' : 'bar',
      smooth: source === 'Cursor',
      barMaxWidth: 18,
      itemStyle: {color: C[source] || '#888'},
      lineStyle: {width: 2, color: C[source] || '#888'},
      data: rows.map(row => row[source] || 0)
    }))
  });
  const tnKey = lang === 'en' ? 'tempo_notes_en' : 'tempo_notes';
  document.getElementById('tempo-notes').innerHTML = (data.story[tnKey] || data.story.tempo_notes).map(txt => `<div class="note"><i class="fa-solid fa-clock"></i><div>${_escHtml(txt)}</div></div>`).join('');
}
