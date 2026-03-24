/* ── i18n ── */
let lang = localStorage.getItem('atlas-lang') || 'zh';
let _tLookup = null; /* merged lookup for current lang — rebuilt on lang change */
/* ── Debounced localStorage writer ── */
const _lsPending = {};
function _debouncedLSWrite(key, value) {
  if (_lsPending[key]) clearTimeout(_lsPending[key]);
  _lsPending[key] = setTimeout(() => { localStorage.setItem(key, value); delete _lsPending[key]; }, 250);
}
const I18N = {
  zh: {
    /* ── Hero & overview ── */
    heroTitle: 'Agent 使用全景仪表盘',
    heroCopyTpl: '统计窗口 {start} → {end}。累计处理 {tokens} tokens，估算花费 {cost}，缓存命中率 {cache}。这不是简单的用量报告，而是 Agent 生产力的赛后复盘。',
    heroWaiting: '正在等待 API 返回数据… 若服务未启动，请先运行 --serve。',
    heroNoData: '暂无可用数据。',

    /* ── Chips ── */
    chipTokens: ' tokens', chipCost: ' cost', chipCached: ' cached', chipTools: ' tool calls',

    /* ── Stat labels & hints ── */
    lblTotalTokens: 'Token 总量', lblEstCost: '估算花费', lblCacheStack: '缓存用量', lblMedianSession: '中位会话',
    hintTotalTokens: '日均 {avg}，峰值 {peak}',
    hintEstCost: '日均 {avg}，30 天投影 {proj}',
    hintCacheStack: '节省 {save}，命中率 {rate}',
    hintMedianSession: '{min} 分钟 / {cost}',
    lblHeroSessions: '会话', lblHeroProjects: '项目', lblHeroDays: '天数', lblHeroAvgBurn: '日均花费',
    lblHeroSessionsCtx: '{sessions} 个会话，横跨 {projects} 个项目',
    lblHeroAcrossProjects: '横跨 {n} 个项目',

    /* ── Cost cards ── */
    lblTotalCost: '总花费', lblDailyAvg: '日均花费', lblCostPerMsg: '每消息花费', lblCacheSavings: '缓存节省',
    hintTotalCost: '{days} 天累计',
    hintDailyAvg: '峰值 {peak}：{cost}',
    hintCostPerMsg: '中位会话 {cost}',
    hintCacheSavings: '节省 {pct}',

    /* ── Source cards ── */
    pillTokenTracked: '含 Token 统计', pillActivityOnly: '仅活动统计',
    subTrackedTokens: '已跟踪 Token', subMessagesOnly: '仅消息计数',
    lblSessions: '会话', lblCost: '花费', lblTopModel: '主力模型', lblCache: '缓存',

    /* ── Section dividers ── */
    divSources: '数据来源', divCostTokens: '花费与 Token', divActivitySessions: '活跃与会话',
    divToolingProjects: '工具与项目', divLeaderboard: '会话排行榜', divInsights: '洞察与提示',

    /* ── Show more / less ── */
    showMore: '展开更多', showLess: '收起',

    /* ── Navigation ── */
    navSources: '来源', navCostTokens: '花费', navActivity: '活跃', navTooling: '工具',
    navInsights: '洞察', navLeaderboard: '排行',

    /* ── Chart titles & subtitles — Cost & Tokens ── */
    chartDailyCost: '每日花费趋势', chartDailyCostSub: '按来源堆叠 + 累计花费线',
    chartCostBreakdown: '花费结构拆解', chartCostBreakdownSub: '钱花在哪种 Token 上',
    chartModelCost: '模型花费排行', chartModelCostSub: '哪些模型最烧钱',
    chartCostSankey: '来源花费桑基图', chartCostSankeySub: '从来源流向各类花费',
    chartDailyCostType: '每日花费结构', chartDailyCostTypeSub: '按 Token 类型拆分每日花费',
    chartCostCalendar: '花费日历', chartCostCalendarSub: '每天花了多少钱',
    chartStory: '数据摘要', chartStorySub: '把数字翻译成人话',
    chartRose: '来源玫瑰图', chartRoseSub: '体量与特征一览',
    chartGauge: '效率仪表盘', chartGaugeSub: '缓存 · 推理 · 节省',
    chartDailyToken: '每日 Token 结构', chartDailyTokenSub: '堆叠柱状图 + 累计线',
    chartTokenSankey: 'Token 流向桑基图', chartTokenSankeySub: '从来源流向各类 Token 桶',
    chartTokenBurn: 'Token 燃烧曲线', chartTokenBurnSub: '多时间粒度查看 Token 消耗节奏',

    /* ── Chart titles — Activity & Sessions ── */
    chartHeatmap: '活跃热力图', chartHeatmapSub: '星期 × 小时，颜色越深越忙',
    chartSourceRadar: '来源能力雷达', chartSourceRadarSub: '体量、缓存、输出、活跃度四维对比',
    chartTokenCalendar: 'Token 日历', chartTokenCalendarSub: '标记高峰日',
    chartTimeline: '时间线', chartTimelineSub: '峰值、拐点与累计趋势',
    chartBubble: '会话气泡图', chartBubbleSub: 'x=时长, y=Token, 气泡大小=缓存',
    chartTempo: '小时节奏图', chartTempoSub: '24 小时中哪些时段最活跃',
    chartSessionDur: '会话时长分布', chartSessionDurSub: '各时长区间的会话数量',
    chartModelRadar: '模型雷达对比', chartModelRadarSub: 'Top 5 模型五维对比',
    chartTurnDur: '响应时间分布', chartTurnDurSub: '单轮响应耗时直方图',
    chartDailyTurnDur: '每日响应时间', chartDailyTurnDurSub: '中位数趋势',
    chartTaskRate: '任务完成率', chartTaskRateSub: 'Codex 任务启动与完成对比',
    chartCodegenModel: 'Cursor 代码生成 · 模型', chartCodegenModelSub: '按模型的生成次数',
    chartCodegenDaily: 'Cursor 代码生成 · 趋势', chartCodegenDailySub: '每日生成次数',
    chartAiContrib: 'AI 代码贡献度', chartAiContribSub: 'AI vs 人工代码行数',

    /* ── Chart titles — Tooling & Projects ── */
    chartToolRank: '工具排行', chartToolRankSub: '按调用次数排序',
    chartToolDensity: '工具时段密度', chartToolDensitySub: '24 小时调用分布',
    chartToolBigram: '工具跳转弦图', chartToolBigramSub: '工具间的跳转关系',
    chartTopCmd: '高频命令', chartTopCmdSub: '最常使用的命令',
    chartCmdSuccess: '命令成功率', chartCmdSuccessSub: '按天统计成功 vs 失败',
    chartEfficiency: '效率指标', chartEfficiencySub: '推理比、缓存命中率、每消息 Token',
    chartProjectRank: '项目排行', chartProjectRankSub: '按 Token 消耗量排序',
    chartFileTypes: '文件类型分布', chartFileTypesSub: '最常接触的文件扩展名',
    chartBranch: '分支活跃度', chartBranchSub: '按会话数排列活跃分支',
    chartProductivity: '生产力评分', chartProductivitySub: '0.3/0.2/0.3/0.2 加权复合分',
    chartBurnRate: '消耗速率投影', chartBurnRateSub: '基于近 7 天均值投影 30 天',
    chartCostPerTool: '每次调用花费', chartCostPerToolSub: '每天每次工具调用的平均花费',

    /* ── Chart titles — Insights ── */
    chartVagueList: '模糊提示排行', chartVagueListSub: '最常见的低效提示',
    chartExpensive: '最贵提示排行', chartExpensiveSub: '按响应花费排序',

    /* ── Series names ── */
    seriesBurnRate: '消耗量', seriesBurnCost: '花费',
    seriesBurnMA: 'MA', burnInterval1: '1 分钟', burnInterval3: '3 分钟', burnInterval5: '5 分钟',
    burnInterval15: '15 分钟', burnInterval30: '30 分钟', burnInterval60: '1 小时',
    seriesCumulative: '累计', seriesDailyTotal: '每日合计',
    seriesSuccess: '成功', seriesFail: '失败',
    seriesReasonRatio: '推理占比', seriesCacheHitRate: '缓存命中率', seriesTokensPerMsg: '每消息 Token',
    seriesActualCum: '实际累计', seriesProjCum: '投影累计',
    seriesProductivity: '生产力',

    /* ── Axis labels ── */
    axisMinutes: '分钟', axisTokens: 'Tokens',

    /* ── Radar dimensions ── */
    radarTotal: '总量', radarCache: '缓存', radarOutput: '输出', radarSessions: '会话',
    radarInput: '输入', radarCost: '花费', radarMsgs: '消息',

    /* ── Legend ── */
    legendUncached: '未缓存输入', legendCacheRead: '缓存读取', legendCacheWrite: '缓存写入', legendOutputReason: '输出 + 推理',

    /* ── Leaderboard table ── */
    tblSource: '来源', tblSession: '会话', tblTokens: 'Tokens', tblCost: '花费', tblTools: '工具', tblModel: '模型', tblWindow: '时间窗口', tblDuration: '时长',
    tblEvents: '{n} 条事件', tblMin: '{n} 分钟',
    lblCompleted: '已完成', lblIncomplete: '未完成',
    lblAiAdded: 'AI 新增', lblHumanAdded: '人工新增', lblAiDeleted: 'AI 删除', lblHumanDeleted: '人工删除',

    /* ── Insights ── */
    lblVagueCount: '模糊提示数', lblVagueRatio: '模糊占比',
    lblWastedTokens: '浪费 Token', lblWastedCost: '浪费花费',
    hintVagueCount: '共 {total} 条用户消息',
    hintVagueRatio: '{count} / {total}',
    hintWastedTokens: '因模糊提示消耗',
    hintWastedCost: '可优化的浪费',
    tblRank: '#', tblPrompt: '提示', tblPromptTokens: 'Tokens', tblPromptCost: '花费', tblPromptModel: '模型', tblPromptSource: '来源', tblPromptCostPct: '占比',
    vagueEmptyTitle: '提示质量很好！', vagueEmptyHint: '没有检测到模糊提示，继续保持。',
    storyEmpty: '暂无活动数据可叙述',
    storyShowMore: '展开更多故事 ({count})',
    storyShowLess: '收起故事',
    insightAction: '建议',
    lblInsightCritical: '严重', lblInsightHigh: '高', lblInsightMedium: '中', lblInsightLow: '低', lblInsightInfo: '提示',
    insightAllClear: '一切正常！', insightAllClearSub: '未发现需要关注的问题。',

    /* ── Footer ── */
    footerText: '数据源：Codex <code>~/.codex</code> · Claude <code>~/.claude/projects</code> · Cursor transcript 仅统计活动消息<br>花费为基于公开 API 定价的估算值 · 图表由 <code>Apache ECharts</code> 渲染',

    /* ── Range tabs ── */
    rangeFrom: '从 {since}', rangeDays: '{days} 天', rangeWeek: '近 7 天', range3Day: '近 3 天', rangeToday: '今日',

    /* ── Live badge ── */
    badgeLive: '实时', badgeOffline: '离线', badgeStatic: '静态', badgeReconnecting: '重连中…', badgeConnecting: '连接中…',

    /* ── Toast notifications ── */
    toastRefreshFail: '刷新失败：{err}', toastRefreshEmpty: '刷新返回的数据为空或格式异常',
    toastPollOk: '轮询连接正常', toastPollFallback: '当前环境不支持 EventSource，已回退为轮询更新。',
    toastSseInit: 'SSE 已连接，等待实时更新。', toastSseReconnect: '实时连接中断，正在自动重连…',
    toastSseOk: 'SSE 连接正常', toastSseParseFail: 'SSE 数据解析失败：{err}',
    toastSseInitFail: 'SSE 初始化失败：{err}，已回退为轮询更新。',
    toastSwitchFail: '切换失败：{err}',

    /* ── New feature: Token Economy Score ── */
    tesBadge: 'Token 经济评分',
    tesGrade: '评级',
    tesLabel: 'Token Economy Score',

    /* ── New feature: Tool Intelligence ── */
    toolDiversity: '工具多样性',
    markovModel: '马尔可夫模型',

    /* ── New feature: What-If Simulator ── */
    whatIfTitle: '假设模拟器',
    whatIfSavings: '预计可节省',

    /* ── New feature: Budget ── */
    budgetTitle: '预算管理',
    budgetRemaining: '剩余预算',
    budgetExhaust: '预计耗尽日期',

    /* ── New feature: Complexity ── */
    complexityScore: '复杂度评分',
    complexityTrivial: '简单',
    complexityModerate: '中等',
    complexityComplex: '复杂',
    complexityExtreme: '极高',

    /* ── New feature: Anti-patterns ── */
    antiPatternTitle: '反模式检测',
    healthScore: '健康评分',

    /* ── New feature: Session Cost ── */
    costWaterfall: '花费瀑布图',
    cacheSavings: '缓存节省额',

    /* ── New feature: Diversity ── */
    diversityScore: '多样性指数',
    diversityTrend: '多样性趋势',

    /* ── Command Palette ── */
    cmdPaletteHint: '按 Cmd+K 打开命令面板',

    /* ── Empty states ── */
    emptyNoData: '该时段暂无数据',
    emptyNoInsights: '一切正常！未检测到问题。',
    emptyNoSessions: '暂无会话记录',

    /* ── Trend indicators ── */
    trendUp: '\u2191 较上期 {pct}%',
    trendDown: '\u2193 较上期 {pct}%',
    trendFlat: '\u2192 持平',

    /* ── Empty/Error states ── */
    errorSomethingWrong: '出了点问题',
    errorRetry: '重试',
    sparklineDay: '第 {n} 天',
    emptyAdjustDateRange: '调整日期范围或等待新数据',
    emptyPromptCost: '暂无提示花费数据',
    emptyActivitySubtitle: '开始使用 AI 编程助手后数据将在此显示',

    /* ── Search/Input ── */
    searchSessionsPlaceholder: '搜索会话、模型、来源…',
    clearSearch: '清除搜索',
    dismissToast: '关闭',

    /* ── Tables ── */
    sessionShowingCount: '显示 {count} / {total} 个会话',
    sessionShowMore: '再加载 {n} 个',
    sessionRemaining: '剩余',
    dayLabel: '第{n}天',

    /* ── Cost cards ── */
    savingsRatio: '节省比率',

    /* ── Tooltips ── */
    tokenInput: '输入',
    tokenOutput: '输出',
    tokenReasoning: '推理',

    /* ── Accessibility ── */
    skipToContent: '跳转到内容',
    backToTop: '返回顶部',
    loadingDashboard: '正在加载仪表板…',
  },
  en: {
    /* ── Hero & overview ── */
    heroTitle: 'Agent Stack Scoreboard',
    heroCopyTpl: 'Window {start} → {end}. Processed {tokens} tokens, est. cost {cost}, cache hit ratio {cache}. Not a usage report — a post-game analysis of Agent productivity.',
    heroWaiting: 'Waiting for API data... If server is not running, start with --serve.',
    heroNoData: 'No data available.',

    /* ── Chips ── */
    chipTokens: ' tokens', chipCost: ' cost', chipCached: ' cached', chipTools: ' tool calls',

    /* ── Stat labels & hints ── */
    lblTotalTokens: 'Total Tokens', lblEstCost: 'Estimated Cost', lblCacheStack: 'Cache Stack', lblMedianSession: 'Median Session',
    hintTotalTokens: 'daily avg {avg}, peak {peak}',
    hintEstCost: 'daily avg {avg}, 30d projection {proj}',
    hintCacheStack: 'saved {save}, hit rate {rate}',
    hintMedianSession: '{min} min / {cost}',
    lblHeroSessions: 'Sessions', lblHeroProjects: 'Projects', lblHeroDays: 'Days', lblHeroAvgBurn: 'Avg Burn',
    lblHeroSessionsCtx: '{sessions} sessions across {projects} projects',
    lblHeroAcrossProjects: 'across {n} projects',

    /* ── Cost cards ── */
    lblTotalCost: 'Total Cost', lblDailyAvg: 'Daily Average', lblCostPerMsg: 'Cost / Message', lblCacheSavings: 'Cache Savings',
    hintTotalCost: '{days} days total',
    hintDailyAvg: 'peak {peak}: {cost}',
    hintCostPerMsg: 'median session {cost}',
    hintCacheSavings: 'saved {pct}',

    /* ── Source cards ── */
    pillTokenTracked: 'token-tracked', pillActivityOnly: 'activity-only',
    subTrackedTokens: 'tracked tokens', subMessagesOnly: 'messages only',
    lblSessions: 'Sessions', lblCost: 'Cost', lblTopModel: 'Top Model', lblCache: 'Cache',

    /* ── Section dividers ── */
    divSources: 'Sources', divCostTokens: 'Cost & Tokens', divActivitySessions: 'Activity & Sessions',
    divToolingProjects: 'Tooling & Projects', divLeaderboard: 'Session Leaderboard', divInsights: 'Insights & Prompts',

    /* ── Show more / less ── */
    showMore: 'Show more', showLess: 'Show less',

    /* ── Navigation ── */
    navSources: 'Sources', navCostTokens: 'Cost', navActivity: 'Activity', navTooling: 'Tooling',
    navInsights: 'Insights', navLeaderboard: 'Board',

    /* ── Chart titles & subtitles — Cost & Tokens ── */
    chartDailyCost: 'Daily Cost Trend', chartDailyCostSub: 'stacked by source + cumulative line',
    chartCostBreakdown: 'Cost Breakdown', chartCostBreakdownSub: 'where the money goes by token type',
    chartModelCost: 'Model Cost Ranking', chartModelCostSub: 'which models cost the most',
    chartCostSankey: 'Source Cost Sankey', chartCostSankeySub: 'flow from source to cost category',
    chartDailyCostType: 'Daily Cost by Type', chartDailyCostTypeSub: 'which token type costs the most',
    chartCostCalendar: 'Cost Calendar', chartCostCalendarSub: 'daily spending heatmap',
    chartStory: 'Story Summary', chartStorySub: 'numbers translated to words',
    chartRose: 'Source Rose Chart', chartRoseSub: 'volume + character at a glance',
    chartGauge: 'Efficiency Gauges', chartGaugeSub: 'cache · reasoning · savings',
    chartDailyToken: 'Daily Token Breakdown', chartDailyTokenSub: 'stacked bars + cumulative line',
    chartTokenSankey: 'Token Flow Sankey', chartTokenSankeySub: 'flow from source to token bucket',
    chartTokenBurn: 'Token Burn Curve', chartTokenBurnSub: 'multi-interval token consumption rhythm',

    /* ── Chart titles — Activity & Sessions ── */
    chartHeatmap: 'Activity Heatmap', chartHeatmapSub: 'weekday × hour, darker = busier',
    chartSourceRadar: 'Source Radar', chartSourceRadarSub: 'volume, cache, output, sessions comparison',
    chartTokenCalendar: 'Token Calendar', chartTokenCalendarSub: 'pin peak days on the calendar',
    chartTimeline: 'Timeline', chartTimelineSub: 'peaks, inflections & cumulative climb',
    chartBubble: 'Session Bubble Chart', chartBubbleSub: 'x=duration, y=tokens, bubble=cache',
    chartTempo: 'Hourly Rhythm', chartTempoSub: 'who works at which hour',
    chartSessionDur: 'Session Duration Histogram', chartSessionDurSub: 'session length distribution',
    chartModelRadar: 'Model Radar Comparison', chartModelRadarSub: 'top 5 models on 5 axes',
    chartTurnDur: 'Response Time Distribution', chartTurnDurSub: 'turn duration histogram',
    chartDailyTurnDur: 'Daily Response Time', chartDailyTurnDurSub: 'median trend',
    chartTaskRate: 'Task Completion Rate', chartTaskRateSub: 'Codex task started vs completed',
    chartCodegenModel: 'Cursor Codegen · Model', chartCodegenModelSub: 'generation count by model',
    chartCodegenDaily: 'Cursor Codegen · Trend', chartCodegenDailySub: 'daily generation count',
    chartAiContrib: 'AI Code Contribution', chartAiContribSub: 'AI vs Human lines in commits',

    /* ── Chart titles — Tooling & Projects ── */
    chartToolRank: 'Tool Ranking', chartToolRankSub: 'by call count',
    chartToolDensity: 'Tool Hour Density', chartToolDensitySub: '24h distribution',
    chartToolBigram: 'Tool Bigram Chord', chartToolBigramSub: 'tool transition graph',
    chartTopCmd: 'Top Commands', chartTopCmdSub: 'most used commands',
    chartCmdSuccess: 'Command Success Rate', chartCmdSuccessSub: 'daily success vs fail',
    chartEfficiency: 'Efficiency Metrics', chartEfficiencySub: 'reasoning ratio, cache hit, tokens/message',
    chartProjectRank: 'Project Ranking', chartProjectRankSub: 'by token volume',
    chartFileTypes: 'File Type Distribution', chartFileTypesSub: 'most touched extensions',
    chartBranch: 'Branch Activity', chartBranchSub: 'top branches by session count',
    chartProductivity: 'Productivity Score', chartProductivitySub: '0.3/0.2/0.3/0.2 composite',
    chartBurnRate: 'Burn Rate Projection', chartBurnRateSub: '30-day projection from 7-day avg',
    chartCostPerTool: 'Cost / Tool Call', chartCostPerToolSub: 'daily cost per tool invocation',

    /* ── Chart titles — Insights ── */
    chartVagueList: 'Top Vague Prompts', chartVagueListSub: 'most common low-effort prompts',
    chartExpensive: 'Most Expensive Prompts', chartExpensiveSub: 'ranked by response cost',

    /* ── Series names ── */
    seriesBurnRate: 'Burn Rate', seriesBurnCost: 'Cost',
    seriesBurnMA: 'MA', burnInterval1: '1 min', burnInterval3: '3 min', burnInterval5: '5 min',
    burnInterval15: '15 min', burnInterval30: '30 min', burnInterval60: '1 hour',
    seriesCumulative: 'Cumulative', seriesDailyTotal: 'Daily Total',
    seriesSuccess: 'Success', seriesFail: 'Fail',
    seriesReasonRatio: 'Reasoning Ratio', seriesCacheHitRate: 'Cache Hit Rate', seriesTokensPerMsg: 'Tokens / Message',
    seriesActualCum: 'Actual Cumulative', seriesProjCum: 'Projected Cumulative',
    seriesProductivity: 'Productivity',

    /* ── Axis labels ── */
    axisMinutes: 'Minutes', axisTokens: 'Tokens',

    /* ── Radar dimensions ── */
    radarTotal: 'Total', radarCache: 'Cache', radarOutput: 'Output', radarSessions: 'Sessions',
    radarInput: 'Input', radarCost: 'Cost', radarMsgs: 'Msgs',

    /* ── Legend ── */
    legendUncached: 'Uncached Input', legendCacheRead: 'Cache Read', legendCacheWrite: 'Cache Write', legendOutputReason: 'Output + Reason',

    /* ── Leaderboard table ── */
    tblSource: 'Source', tblSession: 'Session', tblTokens: 'Tokens', tblCost: 'Cost', tblTools: 'Tools', tblModel: 'Model', tblWindow: 'Window', tblDuration: 'Duration',
    tblEvents: '{n} events', tblMin: '{n} min',
    lblCompleted: 'Completed', lblIncomplete: 'Incomplete',
    lblAiAdded: 'AI Added', lblHumanAdded: 'Human Added', lblAiDeleted: 'AI Deleted', lblHumanDeleted: 'Human Deleted',

    /* ── Insights ── */
    lblVagueCount: 'Vague Prompts', lblVagueRatio: 'Vague Ratio',
    lblWastedTokens: 'Wasted Tokens', lblWastedCost: 'Wasted Cost',
    hintVagueCount: '{total} total user messages',
    hintVagueRatio: '{count} / {total}',
    hintWastedTokens: 'consumed by vague prompts',
    hintWastedCost: 'optimization opportunity',
    tblRank: '#', tblPrompt: 'Prompt', tblPromptTokens: 'Tokens', tblPromptCost: 'Cost', tblPromptModel: 'Model', tblPromptSource: 'Source', tblPromptCostPct: '% of Total',
    vagueEmptyTitle: 'Great prompt hygiene!', vagueEmptyHint: 'No vague prompts detected. Keep it up.',
    storyEmpty: 'No activity data to narrate',
    storyShowMore: 'Show more stories ({count})',
    storyShowLess: 'Show fewer stories',
    insightAction: 'Suggestion',
    lblInsightCritical: 'Critical', lblInsightHigh: 'High', lblInsightMedium: 'Medium', lblInsightLow: 'Low', lblInsightInfo: 'Info',
    insightAllClear: 'All clear!', insightAllClearSub: 'No issues detected.',

    /* ── Footer ── */
    footerText: 'Data: Codex <code>~/.codex</code> · Claude <code>~/.claude/projects</code> · Cursor transcript counts activity messages only<br>Costs are estimates based on public API pricing · Charts rendered with <code>Apache ECharts</code>',

    /* ── Range tabs ── */
    rangeFrom: 'From {since}', rangeDays: '{days} days', rangeWeek: 'Last 7 days', range3Day: 'Last 3 days', rangeToday: 'Today',

    /* ── Live badge ── */
    badgeLive: 'Live', badgeOffline: 'Offline', badgeStatic: 'Static', badgeReconnecting: 'Reconnecting...', badgeConnecting: 'Connecting...',

    /* ── Toast notifications ── */
    toastRefreshFail: 'Refresh failed: {err}', toastRefreshEmpty: 'Refresh returned empty or malformed data',
    toastPollOk: 'Polling connected', toastPollFallback: 'EventSource unavailable, falling back to polling.',
    toastSseInit: 'SSE connected, awaiting updates.', toastSseReconnect: 'Connection lost, reconnecting…',
    toastSseOk: 'SSE connected', toastSseParseFail: 'SSE parse error: {err}',
    toastSseInitFail: 'SSE init failed: {err}, falling back to polling.',
    toastSwitchFail: 'Switch failed: {err}',

    /* ── New feature: Token Economy Score ── */
    tesBadge: 'Token Economy Score',
    tesGrade: 'Grade',
    tesLabel: 'Token Economy Score',

    /* ── New feature: Tool Intelligence ── */
    toolDiversity: 'Tool Diversity',
    markovModel: 'Markov Model',

    /* ── New feature: What-If Simulator ── */
    whatIfTitle: 'What-If Simulator',
    whatIfSavings: 'Estimated Savings',

    /* ── New feature: Budget ── */
    budgetTitle: 'Budget',
    budgetRemaining: 'Remaining Budget',
    budgetExhaust: 'Projected Exhaustion',

    /* ── New feature: Complexity ── */
    complexityScore: 'Complexity Score',
    complexityTrivial: 'Trivial',
    complexityModerate: 'Moderate',
    complexityComplex: 'Complex',
    complexityExtreme: 'Extreme',

    /* ── New feature: Anti-patterns ── */
    antiPatternTitle: 'Anti-pattern Detection',
    healthScore: 'Health Score',

    /* ── New feature: Session Cost ── */
    costWaterfall: 'Cost Waterfall',
    cacheSavings: 'Cache Savings',

    /* ── New feature: Diversity ── */
    diversityScore: 'Diversity Index',
    diversityTrend: 'Diversity Trend',

    /* ── Command Palette ── */
    cmdPaletteHint: 'Press Cmd+K to open command palette',

    /* ── Empty states ── */
    emptyNoData: 'No data available for this period',
    emptyNoInsights: 'All clear! No issues detected.',
    emptyNoSessions: 'No sessions recorded yet',

    /* ── Trend indicators ── */
    trendUp: '\u2191 {pct}% vs previous',
    trendDown: '\u2193 {pct}% vs previous',
    trendFlat: '\u2192 No change',

    /* ── Empty/Error states ── */
    errorSomethingWrong: 'Something went wrong',
    errorRetry: 'Retry',
    sparklineDay: 'Day {n}',
    emptyAdjustDateRange: 'Try adjusting the date range or wait for new data',
    emptyPromptCost: 'No prompt cost data available',
    emptyActivitySubtitle: 'Data will appear here once you start using AI coding agents',

    /* ── Search/Input ── */
    searchSessionsPlaceholder: 'Search sessions, models, sources\u2026',
    clearSearch: 'Clear search',
    dismissToast: 'Dismiss',

    /* ── Tables ── */
    sessionShowingCount: 'Showing {count} of {total} sessions',
    sessionShowMore: 'Show {n} more',
    sessionRemaining: 'remaining',
    dayLabel: 'Day {n}',

    /* ── Cost cards ── */
    savingsRatio: 'Savings Ratio',

    /* ── Tooltips ── */
    tokenInput: 'Input',
    tokenOutput: 'Output',
    tokenReasoning: 'Reasoning',

    /* ── Accessibility ── */
    skipToContent: 'Skip to content',
    backToTop: 'Back to top',
    loadingDashboard: 'Loading dashboard\u2026',
  }
};
function _rebuildLookup() { _tLookup = Object.assign({}, I18N.zh, I18N[lang]); }
_rebuildLookup();
document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
function t(key, params) {
  const s = _tLookup[key] || key;
  if (!params) return s;
  return s.replace(/\{(\w+)\}/g, (_, k) => params[k] !== undefined ? params[k] : _);
}
function applyI18n() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const val = t(key);
    if (el.hasAttribute('data-i18n-html')) el.innerHTML = val;
    else el.textContent = val;
  });
}
function toggleLang() {
  lang = lang === 'zh' ? 'en' : 'zh';
  _rebuildLookup();
  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  _debouncedLSWrite('atlas-lang', lang);
  document.getElementById('lang-btn').textContent = '\u{1F310} ' + lang.toUpperCase();
  _numPrevValues = new WeakMap();
  isFirstRender = false;
  /* Force re-create DOM elements by clearing containers */
  ['hero-chips','hero-stats','source-bar','summary-side','source-cards','cost-cards','vague-stats','vague-list','expensive-table','insight-cards'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = '';
  });
  renderRangeTabs();
  renderDashboard();
}

/* ── Theme toggle ── */
function _systemTheme() {
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}
let currentTheme = localStorage.getItem('atlas-theme') || _systemTheme();
function applyTheme() {
  if (currentTheme === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
}
function toggleTheme() {
  currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
  _debouncedLSWrite('atlas-theme', currentTheme);
  applyTheme();
  refreshPalette();
  /* Re-apply theme colors to existing chart instances without destroy+recreate */
  refreshChartThemes();
}
applyTheme();
/* Follow system theme changes when user hasn't explicitly chosen */
if (window.matchMedia) {
  window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', (e) => {
    if (localStorage.getItem('atlas-theme')) return; /* user made explicit choice */
    currentTheme = e.matches ? 'light' : 'dark';
    applyTheme();
    refreshPalette();
    refreshChartThemes();
  });
}
