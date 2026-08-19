import { useEffect, useMemo, useState } from 'react'
import { AdminPageHeader, EmptyState, StatusBadge } from '../../components/AdminCommon'
import { useAuth } from '../../context/AuthContext'
import { listOrganizationWorkspaces, listUsers, provisionOrganizationWorkspace } from '../../api/admin'

const blankForm = { name: '', owner_email: '' }

export default function AdminWorkspacesPage() {
  const { token } = useAuth()
  const [organizations, setOrganizations] = useState([])
  const [users, setUsers] = useState([])
  const [form, setForm] = useState(blankForm)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const ownerCandidates = useMemo(
    () => users.filter(user => user.is_active && user.platform_role !== 'platform_admin'),
    [users],
  )

  useEffect(() => {
    setLoading(true)
    Promise.all([listOrganizationWorkspaces(token), listUsers(token)])
      .then(([workspaceItems, userItems]) => {
        setOrganizations(workspaceItems)
        setUsers(userItems)
      })
      .catch(err => setError(err.detail || 'Could not load organization workspaces.'))
      .finally(() => setLoading(false))
  }, [token])

  const submit = async event => {
    event.preventDefault(); setSaving(true); setError('')
    try {
      const created = await provisionOrganizationWorkspace(token, form)
      setOrganizations(items => [created, ...items])
      setForm(blankForm)
    } catch (err) { setError(err.detail || 'Could not provision organization workspace.') }
    finally { setSaving(false) }
  }

  return <div className="admin-page">
    <AdminPageHeader title="Organization workspaces" description="Provision enterprise tenants and assign their initial organization owner." />
    {error && <div className="admin-warning-banner"><i className="bi bi-exclamation-triangle" /><div><strong>Workspace action failed</strong><span>{error}</span></div></div>}
    <section className="admin-card admin-workspace-create">
      <div className="admin-section-heading"><span><i className="bi bi-buildings" /></span><div><strong>Provision an organization</strong><small>The selected owner manages departments and business memberships. Platform admins do not join the tenant.</small></div></div>
      <form onSubmit={submit} className="admin-workspace-form admin-organization-form">
        <label>Organization name<input required value={form.name} onChange={event => setForm(value => ({ ...value, name: event.target.value }))} placeholder="Orbit Demo Company" /></label>
        <label>Initial owner<select required value={form.owner_email} onChange={event => setForm(value => ({ ...value, owner_email: event.target.value }))}><option value="">Select owner</option>{ownerCandidates.map(user => <option key={user.id} value={user.email}>{user.display_name} — {user.email}</option>)}</select></label>
        <button className="admin-primary-button" disabled={saving}><i className="bi bi-plus-lg" />{saving ? 'Provisioning…' : 'Provision workspace'}</button>
      </form>
      <p className="admin-workspace-note"><i className="bi bi-shield-check" /> Department workspaces, leads and members are managed by the organization owner/admin in the user application.</p>
    </section>
    <section className="admin-card admin-table-card">
      <div className="admin-table-toolbar"><div><strong>Provisioned organizations</strong><small>{organizations.length} organization workspaces</small></div></div>
      <div className="admin-table-scroll"><table className="admin-table admin-workspace-table"><thead><tr><th>Organization</th><th>Owner</th><th>Agent workspaces</th><th>Status</th><th>Created</th></tr></thead><tbody>{organizations.map(item => <tr key={item.id}><td><strong>{item.name}</strong><small>{item.id}</small></td><td><strong>{item.owner_display_name || 'Not assigned'}</strong><small>{item.owner_email || '—'}</small></td><td>{item.agent_workspace_count}</td><td><StatusBadge value={item.status} /></td><td>{new Date(item.created_at).toLocaleDateString()}</td></tr>)}</tbody></table>{loading && <div className="admin-empty"><span className="spinner-border spinner-border-sm" /><strong>Loading workspaces…</strong></div>}{!loading && !organizations.length && <EmptyState text="No organizations provisioned" />}</div>
    </section>
  </div>
}
