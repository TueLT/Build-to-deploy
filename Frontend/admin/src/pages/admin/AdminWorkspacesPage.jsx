import { useEffect, useMemo, useState } from 'react'
import { AdminPageHeader, EmptyState, StatusBadge } from '../../components/AdminCommon'
import { useAuth } from '../../context/AuthContext'
import {
  addManagedWorkspaceMember,
  assignManagedWorkspaceLead,
  createManagedWorkspace,
  listManagedWorkspaceMembers,
  listManagedWorkspaces,
  listOrganizationWorkspaces,
  listUsers,
  provisionOrganizationWorkspace,
  revokeManagedWorkspaceMember,
  updateManagedWorkspace,
} from '../../api/admin'

const blankOrganization = { name: '', owner_email: '' }
const blankWorkspace = {
  name: '', key: '', agent_profile: 'product_delivery', lead_email: '',
}
const blankMember = { email: '', business_role: 'member' }

const profileLabel = profile => (
  profile === 'quality_assurance' ? 'Quality Assurance Agent' : 'Product Delivery Agent'
)

export default function AdminWorkspacesPage() {
  const { token } = useAuth()
  const [organizations, setOrganizations] = useState([])
  const [users, setUsers] = useState([])
  const [organizationId, setOrganizationId] = useState('')
  const [workspaces, setWorkspaces] = useState([])
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState('')
  const [workspaceMembers, setWorkspaceMembers] = useState([])
  const [organizationForm, setOrganizationForm] = useState(blankOrganization)
  const [workspaceForm, setWorkspaceForm] = useState(blankWorkspace)
  const [memberForm, setMemberForm] = useState(blankMember)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const businessUsers = useMemo(
    () => users.filter(user => user.is_active && user.platform_role !== 'platform_admin'),
    [users],
  )

  const refreshOrganizations = async () => {
    const [organizationItems, userItems] = await Promise.all([
      listOrganizationWorkspaces(token),
      listUsers(token),
    ])
    setOrganizations(organizationItems)
    setUsers(userItems)
    setOrganizationId(current => (
      organizationItems.some(item => item.id === current) ? current : organizationItems[0]?.id || ''
    ))
  }

  const refreshWorkspaces = async () => {
    if (!organizationId) {
      setWorkspaces([])
      setSelectedWorkspaceId('')
      return
    }
    const items = await listManagedWorkspaces(token, organizationId)
    setWorkspaces(items)
    setSelectedWorkspaceId(current => (
      items.some(item => item.id === current) ? current : items[0]?.id || ''
    ))
  }

  const refreshMembers = async () => {
    if (!organizationId || !selectedWorkspaceId) {
      setWorkspaceMembers([])
      return
    }
    setWorkspaceMembers(
      await listManagedWorkspaceMembers(token, organizationId, selectedWorkspaceId),
    )
  }

  useEffect(() => {
    setLoading(true)
    refreshOrganizations()
      .catch(err => setError(err.detail || 'Could not load workspace administration.'))
      .finally(() => setLoading(false))
  }, [token])

  useEffect(() => {
    refreshWorkspaces().catch(err => setError(err.detail || 'Could not load workspaces.'))
  }, [token, organizationId])

  useEffect(() => {
    refreshMembers().catch(err => setError(err.detail || 'Could not load workspace members.'))
  }, [token, organizationId, selectedWorkspaceId])

  const provisionOrganization = async event => {
    event.preventDefault(); setSaving(true); setError('')
    try {
      await provisionOrganizationWorkspace(token, organizationForm)
      setOrganizationForm(blankOrganization)
      await refreshOrganizations()
    } catch (err) { setError(err.detail || 'Could not provision organization.') }
    finally { setSaving(false) }
  }

  const createWorkspace = async event => {
    event.preventDefault(); setSaving(true); setError('')
    try {
      await createManagedWorkspace(token, organizationId, workspaceForm)
      setWorkspaceForm(blankWorkspace)
      await Promise.all([refreshWorkspaces(), refreshOrganizations()])
    } catch (err) { setError(err.detail || 'Could not create workspace.') }
    finally { setSaving(false) }
  }

  const changeLead = async (workspace, email) => {
    setError('')
    try {
      await assignManagedWorkspaceLead(token, organizationId, workspace.id, email)
      await Promise.all([refreshWorkspaces(), refreshMembers()])
    } catch (err) { setError(err.detail || 'Could not assign workspace lead.') }
  }

  const toggleStatus = async workspace => {
    setError('')
    try {
      await updateManagedWorkspace(token, organizationId, workspace.id, {
        status: workspace.status === 'active' ? 'suspended' : 'active',
      })
      await refreshWorkspaces()
    } catch (err) { setError(err.detail || 'Could not update workspace status.') }
  }

  const addMember = async event => {
    event.preventDefault(); setSaving(true); setError('')
    try {
      await addManagedWorkspaceMember(
        token, organizationId, selectedWorkspaceId, memberForm,
      )
      setMemberForm(blankMember)
      await refreshMembers()
    } catch (err) { setError(err.detail || 'Could not add workspace member.') }
    finally { setSaving(false) }
  }

  const revokeMember = async member => {
    setError('')
    try {
      await revokeManagedWorkspaceMember(
        token, organizationId, selectedWorkspaceId, member.id,
      )
      await refreshMembers()
    } catch (err) { setError(err.detail || 'Could not revoke workspace member.') }
  }

  return <div className="admin-page">
    <AdminPageHeader
      title="Workspace administration"
      description="Create company workspaces, attach the supporting agent, appoint a lead and assign members."
    />
    {error && <div className="admin-warning-banner"><i className="bi bi-exclamation-triangle" /><div><strong>Workspace action failed</strong><span>{error}</span></div></div>}

    <section className="admin-card admin-workspace-create">
      <div className="admin-section-heading"><span><i className="bi bi-buildings" /></span><div><strong>1. Provision an organization</strong><small>The organization is the company security boundary. Its owner is the initial business sponsor.</small></div></div>
      <form onSubmit={provisionOrganization} className="admin-workspace-form admin-organization-form">
        <label>Organization name<input required value={organizationForm.name} onChange={event => setOrganizationForm(value => ({ ...value, name: event.target.value }))} placeholder="Orbit Demo Company" /></label>
        <label>Initial owner<select required value={organizationForm.owner_email} onChange={event => setOrganizationForm(value => ({ ...value, owner_email: event.target.value }))}><option value="">Select owner</option>{businessUsers.map(user => <option key={user.id} value={user.email}>{user.display_name} — {user.email}</option>)}</select></label>
        <button className="admin-primary-button" disabled={saving}><i className="bi bi-plus-lg" />{saving ? 'Saving…' : 'Provision organization'}</button>
      </form>
    </section>

    <section className="admin-card admin-workspace-create">
      <div className="admin-section-heading"><span><i className="bi bi-diagram-3" /></span><div><strong>2. Create a workspace and attach its agent</strong><small>Admin appoints the workspace lead. The selected user is enrolled in the organization if needed.</small></div></div>
      <div className="admin-workspace-form">
        <label>Organization<select value={organizationId} onChange={event => setOrganizationId(event.target.value)}><option value="">Select organization</option>{organizations.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      </div>
      {organizationId && <form onSubmit={createWorkspace} className="admin-workspace-form">
        <label>Workspace name<input required value={workspaceForm.name} onChange={event => setWorkspaceForm(value => ({ ...value, name: event.target.value }))} placeholder="Product Delivery" /></label>
        <label>Workspace key<input required value={workspaceForm.key} onChange={event => setWorkspaceForm(value => ({ ...value, key: event.target.value }))} placeholder="product-delivery" /></label>
        <label>Supporting agent<select value={workspaceForm.agent_profile} onChange={event => setWorkspaceForm(value => ({ ...value, agent_profile: event.target.value }))}><option value="product_delivery">Product Delivery Agent</option><option value="quality_assurance">Quality Assurance Agent</option></select></label>
        <label>Workspace lead<select required value={workspaceForm.lead_email} onChange={event => setWorkspaceForm(value => ({ ...value, lead_email: event.target.value }))}><option value="">Select lead</option>{businessUsers.map(user => <option key={user.id} value={user.email}>{user.display_name} — {user.email}</option>)}</select></label>
        <button className="admin-primary-button" disabled={saving}><i className="bi bi-plus-lg" />{saving ? 'Creating…' : 'Create workspace'}</button>
      </form>}
    </section>

    <section className="admin-card admin-table-card">
      <div className="admin-table-toolbar"><div><strong>Workspaces in selected organization</strong><small>{workspaces.length} configured workspaces</small></div></div>
      <div className="admin-table-scroll"><table className="admin-table admin-workspace-table"><thead><tr><th>Workspace</th><th>Supporting agent</th><th>Lead</th><th>Status</th><th>Action</th></tr></thead><tbody>{workspaces.map(item => <tr key={item.id}><td><strong>{item.name}</strong><small>{item.key}</small></td><td>{profileLabel(item.agent_profile)}</td><td><select value={item.lead_email || ''} onChange={event => changeLead(item, event.target.value)}>{businessUsers.map(user => <option key={user.id} value={user.email}>{user.display_name}</option>)}</select><small>{item.lead_email}</small></td><td><StatusBadge value={item.status} /></td><td><button className="admin-secondary-button" onClick={() => toggleStatus(item)}>{item.status === 'active' ? 'Suspend' : 'Activate'}</button></td></tr>)}</tbody></table>{loading && <div className="admin-empty"><span className="spinner-border spinner-border-sm" /><strong>Loading workspaces…</strong></div>}{!loading && organizationId && !workspaces.length && <EmptyState text="No workspaces created for this organization" />}</div>
    </section>

    {workspaces.length > 0 && <section className="admin-card admin-workspace-create">
      <div className="admin-section-heading"><span><i className="bi bi-people" /></span><div><strong>3. Assign workspace members</strong><small>Members receive access only to the selected workspace and its supporting agent.</small></div></div>
      <div className="admin-workspace-form">
        <label>Workspace<select value={selectedWorkspaceId} onChange={event => setSelectedWorkspaceId(event.target.value)}>{workspaces.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      </div>
      <form onSubmit={addMember} className="admin-workspace-form">
        <label>User<select required value={memberForm.email} onChange={event => setMemberForm(value => ({ ...value, email: event.target.value }))}><option value="">Select user</option>{businessUsers.map(user => <option key={user.id} value={user.email}>{user.display_name} — {user.email}</option>)}</select></label>
        <label>Workspace role<select value={memberForm.business_role} onChange={event => setMemberForm(value => ({ ...value, business_role: event.target.value }))}><option value="member">Member</option><option value="executive_viewer">Executive viewer</option></select></label>
        <button className="admin-primary-button" disabled={saving}>Add member</button>
      </form>
      <div className="admin-table-scroll"><table className="admin-table"><thead><tr><th>Member</th><th>Role</th><th>Status</th><th>Action</th></tr></thead><tbody>{workspaceMembers.map(member => <tr key={member.id}><td><strong>{member.display_name}</strong><small>{member.email}</small></td><td>{member.business_role}</td><td><StatusBadge value={member.status} /></td><td><button className="admin-secondary-button" disabled={member.business_role === 'lead'} onClick={() => revokeMember(member)}>Revoke</button></td></tr>)}</tbody></table></div>
    </section>}
  </div>
}
