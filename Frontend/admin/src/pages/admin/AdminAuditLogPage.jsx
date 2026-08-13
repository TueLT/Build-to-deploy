import { useEffect, useState } from 'react'
import PageHeader from '../../components/common/PageHeader'
import { listAuditLog } from '../../api/admin'
import { useAuth } from '../../context/AuthContext'

const label = value => value?.replace(/[._]/g, ' ').replace(/\b\w/g, letter => letter.toUpperCase()) || '—'

export default function AdminAuditLogPage() {
  const { token } = useAuth()
  const [query, setQuery] = useState('')
  const [actorType, setActorType] = useState('')
  const [result, setResult] = useState({ total: 0, items: [] })
  const [error, setError] = useState('')
  const load = () => { setError(''); listAuditLog(token, { q: query.trim(), actorType }).then(setResult).catch(err => setError(err.detail || 'Could not load audit events.')) }
  useEffect(() => { load() }, [token, actorType])
  return <div className="page-container admin-monitor-page"><PageHeader eyebrow="Platform admin" title="Audit Log" description="Review administrative changes without exposing raw conversation or memory content." />{error && <div className="admin-notice error">{error}</div>}<section className="content-card"><form className="admin-audit-toolbar" onSubmit={event => { event.preventDefault(); load() }}><input className="form-control" value={query} onChange={event => setQuery(event.target.value)} placeholder="Search action, target, or actor" /><select className="form-select" value={actorType} onChange={event => setActorType(event.target.value)}><option value="">All actors</option><option value="platform_admin">Platform admin</option><option value="user">User</option><option value="system">System</option></select><button className="btn btn-primary">Search</button><span>{result.total.toLocaleString()} events</span></form><div className="table-responsive"><table className="table admin-audit-table"><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Target</th><th>Workspace</th><th>Metadata</th></tr></thead><tbody>{result.items.map(item => <tr key={item.id}><td>{new Date(item.created_at).toLocaleString()}</td><td>{item.actor_display_name || label(item.actor_type)}<small>{item.actor_email}</small></td><td>{label(item.action)}</td><td>{label(item.target_type)}<small>{item.target_id}</small></td><td><code>{item.workspace_id || '—'}</code></td><td><code>{Object.keys(item.metadata).length ? JSON.stringify(item.metadata) : '—'}</code></td></tr>)}{!result.items.length && <tr><td colSpan="6" className="text-center text-muted py-4">No audit events found.</td></tr>}</tbody></table></div></section></div>
}
