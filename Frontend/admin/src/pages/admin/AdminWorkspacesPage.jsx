import { useEffect, useMemo, useState } from 'react'
import { AdminPageHeader, EmptyState, StatusBadge } from '../../components/AdminCommon'
import { useAuth } from '../../context/AuthContext'
import {
  assignAgentWorkspaceLead,
  createAgentWorkspace,
  listAgentWorkspaces,
  listOrganizationWorkspaces,
  listUsers,
  updateAgentWorkspace,
} from '../../api/admin'

const blankForm = { name: '', key: '', agent_profile: 'product_delivery', lead_email: '' }
const profileLabel = value => value === 'quality_assurance' ? 'Quality Assurance' : 'Product Delivery'

export default function AdminWorkspacesPage() {
  const { token } = useAuth()
  const [organizations, setOrganizations] = useState([])
  const [users, setUsers] = useState([])
  const [workspaceId, setWorkspaceId] = useState('')
  const [agentWorkspaces, setAgentWorkspaces] = useState([])
  const [form, setForm] = useState(blankForm)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const activeUsers = useMemo(() => users.filter(user => user.is_active && user.platform_role !== 'platform_admin'), [users])
  const selectedOrganization = organizations.find(item => item.id === workspaceId)

  useEffect(() => {
    setLoading(true)
    Promise.all([listOrganizationWorkspaces(token), listUsers(token)])
      .then(([workspaceItems, userItems]) => {
        setOrganizations(workspaceItems)
        setUsers(userItems)
        setWorkspaceId(current => current || workspaceItems[0]?.id || '')
      })
      .catch(err => setError(err.detail || 'Could not load workspace administration.'))
      .finally(() => setLoading(false))
  }, [token])

  const refreshAgents = async id => {
    if (!id) { setAgentWorkspaces([]); return }
    try { setAgentWorkspaces(await listAgentWorkspaces(token, id)) }
    catch (err) { setError(err.detail || 'Could not load agent workspaces.') }
  }
  useEffect(() => { refreshAgents(workspaceId) }, [token, workspaceId])

  const submit = async event => {
    event.preventDefault(); setSaving(true); setError('')
    try {
      const created = await createAgentWorkspace(token, workspaceId, form)
      setAgentWorkspaces(items => [...items, created].sort((a, b) => a.key.localeCompare(b.key)))
      setForm(blankForm)
      setOrganizations(items => items.map(item => item.id === workspaceId
        ? { ...item, agent_workspace_count: item.agent_workspace_count + 1 }
        : item))
    } catch (err) { setError(err.detail || 'Could not create agent workspace.') }
    finally { setSaving(false) }
  }

  const changeLead = async (item, email) => {
    setError('')
    try {
      const lead = await assignAgentWorkspaceLead(token, workspaceId, item.id, email)
      setAgentWorkspaces(items => items.map(entry => entry.id === item.id ? {
        ...entry, lead_user_id: lead.user_id, lead_email: lead.email, lead_display_name: lead.display_name,
      } : entry))
    } catch (err) { setError(err.detail || 'Could not assign the workspace lead.') }
  }

  const toggleStatus = async item => {
    const nextStatus = item.status === 'active' ? 'suspended' : 'active'
    setError('')
    try {
      const updated = await updateAgentWorkspace(token, workspaceId, item.id, { status: nextStatus })
      setAgentWorkspaces(items => items.map(entry => entry.id === item.id ? updated : entry))
    } catch (err) { setError(err.detail || 'Could not update the workspace status.') }
  }

  return <div className="admin-page">
    <AdminPageHeader title="Agent workspaces" description="Provision department workspaces and assign exactly one responsible lead." />
    {error && <div className="admin-warning-banner"><i className="bi bi-exclamation-triangle" /><div><strong>Workspace action failed</strong><span>{error}</span></div></div>}
    <section className="admin-card admin-workspace-create">
      <div className="admin-section-heading"><span><i className="bi bi-diagram-3" /></span><div><strong>Create an agent workspace</strong><small>Only platform admins can provision or change these workspaces.</small></div></div>
      <form onSubmit={submit} className="admin-workspace-form">
        <label>Organization<select required value={workspaceId} onChange={event => setWorkspaceId(event.target.value)}><option value="">Select organization</option>{organizations.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>Workspace name<input required value={form.name} onChange={event => setForm(value => ({ ...value, name: event.target.value }))} placeholder="Product Delivery" /></label>
        <label>Key<input required value={form.key} onChange={event => setForm(value => ({ ...value, key: event.target.value }))} placeholder="product-delivery" /></label>
        <label>Agent profile<select value={form.agent_profile} onChange={event => setForm(value => ({ ...value, agent_profile: event.target.value }))}><option value="product_delivery">Product Delivery</option><option value="quality_assurance">Quality Assurance</option></select></label>
        <label>Workspace lead<select required value={form.lead_email} onChange={event => setForm(value => ({ ...value, lead_email: event.target.value }))}><option value="">Select lead</option>{activeUsers.map(user => <option key={user.id} value={user.email}>{user.display_name} — {user.email}</option>)}</select></label>
        <button className="admin-primary-button" disabled={saving || !workspaceId}><i className="bi bi-plus-lg" />{saving ? 'Creating…' : 'Create workspace'}</button>
      </form>
      <p className="admin-workspace-note"><i className="bi bi-info-circle" /> Assigning a lead also adds that user to the organization as a member when needed.</p>
    </section>
    <section className="admin-card admin-table-card">
      <div className="admin-table-toolbar"><div><strong>{selectedOrganization?.name || 'Organization workspaces'}</strong><small>{selectedOrganization ? `${selectedOrganization.agent_workspace_count} configured · Owner: ${selectedOrganization.owner_display_name || selectedOrganization.owner_email || 'Not assigned'}` : 'Choose an organization above'}</small></div></div>
      <div className="admin-table-scroll"><table className="admin-table admin-workspace-table"><thead><tr><th>Workspace</th><th>Agent profile</th><th>Workspace lead</th><th>Status</th><th>Actions</th></tr></thead><tbody>{agentWorkspaces.map(item => <tr key={item.id}><td><strong>{item.name}</strong><small>{item.key}</small></td><td>{profileLabel(item.agent_profile)}</td><td><select className="admin-inline-select" value={item.lead_email || ''} onChange={event => changeLead(item, event.target.value)}>{!item.lead_email && <option value="">Select lead</option>}{activeUsers.map(user => <option key={user.id} value={user.email}>{user.display_name} — {user.email}</option>)}</select></td><td><StatusBadge value={item.status} /></td><td><button className={`admin-row-action ${item.status === 'active' ? '' : 'unlock'}`} onClick={() => toggleStatus(item)} title={item.status === 'active' ? 'Suspend workspace' : 'Activate workspace'}><i className={`bi ${item.status === 'active' ? 'bi-pause-circle' : 'bi-play-circle'}`} /></button></td></tr>)}</tbody></table>{loading && <div className="admin-empty"><span className="spinner-border spinner-border-sm" /><strong>Loading workspaces…</strong></div>}{!loading && !agentWorkspaces.length && <EmptyState text="No agent workspaces configured" />}</div>
    </section>
  </div>
}
