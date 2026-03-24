function renderToolBigramChart(){
  const rows = data.tooling.bigram_chord;
  const chart = initChart('tool-bigram-chart');
  chart.setOption({
    ...chartTheme(),
    series: [{
      type: 'graph',
      layout: 'circular',
      layoutAnimation: false,
      force: {friction: 0.6},
      circular: {rotateLabel: true},
      roam: true,
      label: {show: true, color: TX},
      lineStyle: {color: 'source', opacity: .4, width: 2, curveness: .2},
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: [0, 8],
      data: rows.nodes.map((node, index) => ({
        name: node.name,
        value: node.value,
        symbolSize: 18 + Math.min(node.value * 1.5, 36),
        itemStyle: {color: ['#ffd43b','#ff8a50','#74c0fc','#51cf66','#b197fc','#e599f7','#ffa94d','#94d82d'][index % 8]}
      })),
      links: rows.links.map(link => ({source: link.source, target: link.target, value: link.value, lineStyle: {width: 1 + Math.log2(link.value + 1)}}))
    }]
  });
}
