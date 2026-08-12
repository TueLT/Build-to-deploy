import { useEffect, useState } from 'react'
import PageHeader from '../../src/components/common/PageHeader'
import { useAuth } from '../../src/context/AuthContext'
import { getStats } from '../../src/api/admin'

const cards = [
  ['total_users', 'Total users', 'bi-people', 'primary'],
  ['new_users_last_7_days', 'New users (7d)', 'bi-person-plus', 'success'],
  ['total_conversations', 'Conversations', 'bi-chat-dots', 'info'],
  ['total_messages', 'Messages', 'bi-envelope', 'warning'],
  ['tokens_used_today', 'AI tokens today', 'bi-cpu', 'primary'],
  ['requests_today', 'AI requests today', 'bi-stars', 'info'],
]

export default function AdminDashboardPage() {
  const { token } = useAuth()
  const [stats, setStats] = useState(null)
  useEffect(() => { getStats(token).then(setStats).catch(() => setStats(null)) }, [token])
  const format = key => key === 'tokens_used_today' ? (stats?.[key] == null ? '—' : stats[key].toLocaleString()) : (stats?.[key] ?? '—')

  return <div className="page-container admin-dashboard-page"><PageHeader eyebrow="Platform admin" title="Dashboard" description="Monitor accounts, conversations, and AI activity across Orbit." /><div className="stats-grid">{cards.map(([key, label, icon, color]) => <div className="stat-card" key={key}><div className={`stat-icon bg-${color}-subtle text-${color}`}><i className={`bi ${icon}`} /></div><div><div className="stat-value">{format(key)}</div><div className="stat-label">{label}</div></div></div>)}</div>{stats && <div className="admin-budget-card"><i className="bi bi-shield-check" /><div><strong>AI budget status</strong><p>{stats.budget_used_pct}% of the daily token budget used ({stats.tokens_used_today.toLocaleString()} / {stats.daily_token_budget.toLocaleString()}).</p></div></div>}</div>
}
