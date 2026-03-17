function renderAiContributionChart(){
  const ext = data.extended;
  if (!ext || !ext.ai_contribution || !ext.ai_contribution.total_commits) return;
  const ai = ext.ai_contribution;
  const chart = initChart('ai-contribution-chart');
  chart.setOption({
    ...chartTheme(),
    tooltip: {...chartTheme().tooltip, trigger: 'item'},
    legend: {bottom: 0, textStyle: {color: TX}},
    series: [{
      type: 'pie', radius: ['40%', '68%'], center: ['50%', '44%'],
      label: {color: TX, formatter: '{b}\\n{c} lines ({d}%)'},
      data: [
        {value: ai.ai_lines_added, name: t('lblAiAdded'), itemStyle: {color: '#74c0fc'}},
        {value: ai.human_lines_added, name: t('lblHumanAdded'), itemStyle: {color: '#ffd43b'}},
        {value: ai.ai_lines_deleted, name: t('lblAiDeleted'), itemStyle: {color: '#b197fc'}},
        {value: ai.human_lines_deleted, name: t('lblHumanDeleted'), itemStyle: {color: '#ff6b6b'}}
      ].filter(d => d.value > 0)
    }]
  });
}
