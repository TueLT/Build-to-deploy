import { useEffect, useState } from 'react'
import PageHeader from '../../components/common/PageHeader'
import { getAIUsage } from '../../api/admin'
import { useAuth } from '../../context/AuthContext'

const number = value => value?.toLocaleString() ?? '—'
const cost = value => value == null ? '—' : `$${Number(value).toFixed(4)}`

export default function AdminAIUsagePage() {
  const { token } = useAuth()
  const [days, setDays] = useState(7)
  const [report, setReport] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { setError(''); getAIUsage(token, days).then(setReport).catch(err => setError(err.detail || 'Could not load usage.')) }, [token, days])
  const max = Math.max(...(report?.daily.map(row => row.total_tokens) || [0]), 1)
  return <div className="page-container admin-monitor-page">
    <PageHeader eyebrow="Platform admin" title="AI Usage" description="Token consumption and estimated model cost." action={<select className="form-select admin-range" value={days} onChange={event => setDays(Number(event.target.value))}><option value="7">7 days</option><option value="14">14 days</option><option value="30">30 days</option></select>} />
    {error && <div className="admin-notice error">{error}</div>}
    <div className="stats-grid"><div className="stat-card"><div><div className="stat-value">{number(report?.totals.total_tokens)}</div><div className="stat-label">Total tokens</div></div></div><div className="stat-card"><div><div className="stat-value">{number(report?.totals.prompt_tokens)}</div><div className="stat-label">Input tokens</div></div></div><div className="stat-card"><div><div className="stat-value">{number(report?.totals.completion_tokens)}</div><div className="stat-label">Output tokens</div></div></div><div className="stat-card"><div><div className="stat-value">{cost(report?.totals.estimated_cost_usd)}</div><div className="stat-label">Estimated cost</div></div></div></div>
    {(report?.totals.unpriced_tokens || 0) > 0 && <div className="admin-notice">{number(report.totals.unpriced_tokens)} tokens are unpriced and excluded from the estimate.</div>}
    <div className="admin-monitor-grid"><section className="admin-monitor-card"><h3>Daily usage</h3><div className="admin-usage-chart">{report?.daily.map(row => <div key={row.date}><span>{row.date}</span><i><b style={{ width: `${row.total_tokens / max * 100}%` }} /></i><strong>{number(row.total_tokens)}</strong></div>)}</div></section><section className="admin-monitor-card"><h3>Models</h3><div className="admin-model-list">{report?.models.map(row => <div key={`${row.provider}:${row.model}`}><span><strong>{row.model}</strong><small>{row.provider} · {number(row.request_count)} requests</small></span><em>{number(row.total_tokens)} tokens<br />{cost(row.estimated_cost_usd)}</em></div>)}</div></section></div>
  </div>
}
