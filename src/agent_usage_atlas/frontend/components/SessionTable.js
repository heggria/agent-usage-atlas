function renderSessionTable(){
  document.getElementById('session-table').innerHTML = `
    <thead>
      <tr><th>${t('tblSource')}</th><th>${t('tblSession')}</th><th>${t('tblTokens')}</th><th>${t('tblCost')}</th><th>${t('tblTools')}</th><th>${t('tblModel')}</th><th>${t('tblWindow')}</th></tr>
    </thead>
    <tbody>
      ${data.top_sessions.map(row => `
        <tr>
          <td><strong style="color:var(--text)">${row.source}</strong><div class="tiny">${t('tblEvents', {n: fmtInt(row.messages)})}</div></td>
          <td><strong style="color:var(--text)">${row.session_id.slice(0, 10)}…</strong><div class="tiny">${t('tblMin', {n: row.minutes})}</div></td>
          <td>${fmtShort(row.total)}</td>
          <td style="color:var(--cost);font-weight:700">${fmtUSD(row.cost)}</td>
          <td>${fmtInt(row.tool_calls)}</td>
          <td style="font-size:11px">${row.top_model}</td>
          <td><div style="font-size:11px">${row.first_local}</div><div class="tiny">→ ${row.last_local}</div></td>
        </tr>
      `).join('')}
    </tbody>`;
}
