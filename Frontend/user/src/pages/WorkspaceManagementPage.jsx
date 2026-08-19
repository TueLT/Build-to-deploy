import { useEffect, useMemo, useState } from 'react'
import PageHeader from '../components/common/PageHeader'
import { useAuth } from '../context/AuthContext'
import { useWorkspace } from '../context/WorkspaceContext'
import {
  addAgentWorkspaceMember,
  assignAgentWorkspaceLead,
  createAgentWorkspace,
  listAgentWorkspaceMembers,
  listAgentWorkspaces,
  listAvailableAgentWorkspaces,
  listWorkspaceMembers,
  revokeAgentWorkspaceMember,
  updateAgentWorkspace,
} from '../api/workspaces'

const blankWorkspace = { name: '', key: '', agent_profile: 'product_delivery', lead_email: '' }
const blankMember = { email: '', business_role: 'member' }
const profileName = profile => profile === 'quality_assurance' ? 'Quality Assurance' : 'Product Delivery'

export default function WorkspaceManagementPage() {
  const { token } = useAuth()
  const { workspaces } = useWorkspace()
  const organizations = useMemo(() => workspaces.filter(item => item.type === 'organization'), [workspaces])
  const [organizationId, setOrganizationId] = useState('')
  const organization = organizations.find(item => item.id === organizationId)
  const canManage = ['owner', 'admin'].includes(organization?.current_user_role)
  const [agents, setAgents] = useState([])
  const [organizationMembers, setOrganizationMembers] = useState([])
  const [selectedAgentId, setSelectedAgentId] = useState('')
  const [agentMembers, setAgentMembers] = useState([])
  const [workspaceForm, setWorkspaceForm] = useState(blankWorkspace)
  const [memberForm, setMemberForm] = useState(blankMember)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!organizationId && organizations.length) setOrganizationId(organizations[0].id)
    if (organizationId && !organizations.some(item => item.id === organizationId)) {
      setOrganizationId(organizations[0]?.id || '')
    }
  }, [organizations, organizationId])

  const refresh = async () => {
    if (!organizationId) { setAgents([]); setOrganizationMembers([]); setLoading(false); return }
    setLoading(true); setError('')
    try {
      const currentOrganization = organizations.find(item => item.id === organizationId)
      const manager = ['owner', 'admin'].includes(currentOrganization?.current_user_role)
      const [agentItems, memberItems] = await Promise.all([
        manager
          ? listAgentWorkspaces(token, organizationId)
          : listAvailableAgentWorkspaces(token, organizationId),
        manager ? listWorkspaceMembers(token, organizationId) : Promise.resolve([]),
      ])
      setAgents(agentItems)
      setOrganizationMembers(memberItems.filter(item => item.role !== 'guest'))
      setSelectedAgentId(current => agentItems.some(item => item.id === current) ? current : agentItems[0]?.id || '')
    } catch (err) { setError(err.detail || 'Could not load agent workspaces.') }
    finally { setLoading(false) }
  }
  useEffect(() => { refresh() }, [token, organizationId, canManage])

  const refreshAgentMembers = async () => {
    if (!canManage || !selectedAgentId) { setAgentMembers([]); return }
    try { setAgentMembers(await listAgentWorkspaceMembers(token, organizationId, selectedAgentId)) }
    catch (err) { setError(err.detail || 'Could not load workspace members.') }
  }
  useEffect(() => { refreshAgentMembers() }, [token, organizationId, selectedAgentId, canManage])

  const submitWorkspace = async event => {
    event.preventDefault(); setSaving(true); setError('')
    try {
      await createAgentWorkspace(token, organizationId, workspaceForm)
      setWorkspaceForm(blankWorkspace)
      await refresh()
    } catch (err) { setError(err.detail || 'Could not create agent workspace.') }
    finally { setSaving(false) }
  }

  const submitMember = async event => {
    event.preventDefault(); setSaving(true); setError('')
    try {
      await addAgentWorkspaceMember(token, organizationId, selectedAgentId, memberForm)
      setMemberForm(blankMember)
      await refreshAgentMembers()
    } catch (err) { setError(err.detail || 'Could not add workspace member.') }
    finally { setSaving(false) }
  }

  const changeLead = async (agent, email) => {
    setError('')
    try { await assignAgentWorkspaceLead(token, organizationId, agent.id, email); await refresh() }
    catch (err) { setError(err.detail || 'Could not assign workspace lead.') }
  }

  const toggleStatus = async agent => {
    setError('')
    try {
      await updateAgentWorkspace(token, organizationId, agent.id, {
        status: agent.status === 'active' ? 'suspended' : 'active',
      })
      await refresh()
    } catch (err) { setError(err.detail || 'Could not update workspace status.') }
  }

  const revokeMember = async member => {
    setError('')
    try {
      await revokeAgentWorkspaceMember(token, organizationId, selectedAgentId, member.id)
      await refreshAgentMembers()
    } catch (err) { setError(err.detail || 'Could not revoke workspace member.') }
  }

  return <div className="container-fluid py-4 px-3 px-lg-4">
    <PageHeader eyebrow="Enterprise workspace" title="Agent workspaces" description="Your assigned specialist workspaces and organization-level workspace administration." action={<select className="form-select" value={organizationId} onChange={event => setOrganizationId(event.target.value)}><option value="">Select organization</option>{organizations.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select>} />
    {error && <div className="alert alert-danger mt-3">{error}</div>}
    {!organizations.length && !loading && <div className="workspace-panel mt-4"><h3>No organization assigned</h3><p className="text-secondary mb-0">Ask a platform administrator to provision an organization and assign its owner.</p></div>}
    {organization && <>
      <div className="workspace-grid mt-4">{agents.map(agent => <article className="workspace-card" key={agent.id}><div className="workspace-card-head"><div><h3>{agent.name}</h3><small>{agent.key} · {profileName(agent.agent_profile)}</small></div><span className="workspace-role">{agent.current_user_business_role || agent.status}</span></div><div className="mt-3 small text-secondary">Lead: {agent.lead_display_name || agent.lead_email || 'Not assigned'}</div>{canManage && <><label className="form-label small mt-3">Primary lead<select className="form-select form-select-sm" value={agent.lead_email || ''} onChange={event => changeLead(agent, event.target.value)}>{organizationMembers.map(member => <option key={member.user_id} value={member.email}>{member.display_name} — {member.email}</option>)}</select></label><button className="btn btn-sm btn-outline-secondary mt-2" onClick={() => toggleStatus(agent)}>{agent.status === 'active' ? 'Suspend' : 'Activate'}</button></>}</article>)}</div>
      {!loading && !agents.length && <div className="workspace-panel mt-4"><h3>No agent workspace available</h3><p className="text-secondary mb-0">{canManage ? 'Create the first department workspace below.' : 'An organization admin must assign you to a department workspace.'}</p></div>}
      {canManage && <div className="row g-4 mt-1">
        <div className="col-xl-6"><section className="workspace-panel h-100"><h3>Create department workspace</h3><p className="text-secondary small">Choose a lead from existing organization members.</p><form className="workspace-form-grid" onSubmit={submitWorkspace}><label className="form-label">Name<input required className="form-control" value={workspaceForm.name} onChange={event => setWorkspaceForm(value => ({ ...value, name: event.target.value }))} /></label><label className="form-label">Key<input required className="form-control" value={workspaceForm.key} onChange={event => setWorkspaceForm(value => ({ ...value, key: event.target.value }))} /></label><label className="form-label">Profile<select className="form-select" value={workspaceForm.agent_profile} onChange={event => setWorkspaceForm(value => ({ ...value, agent_profile: event.target.value }))}><option value="product_delivery">Product Delivery</option><option value="quality_assurance">Quality Assurance</option></select></label><label className="form-label">Primary lead<select required className="form-select" value={workspaceForm.lead_email} onChange={event => setWorkspaceForm(value => ({ ...value, lead_email: event.target.value }))}><option value="">Select member</option>{organizationMembers.map(member => <option key={member.user_id} value={member.email}>{member.display_name} — {member.email}</option>)}</select></label><button className="btn btn-primary full" disabled={saving}>Create workspace</button></form></section></div>
        <div className="col-xl-6"><section className="workspace-panel h-100"><h3>Workspace members</h3><div className="mb-3"><select className="form-select" value={selectedAgentId} onChange={event => setSelectedAgentId(event.target.value)}>{agents.map(agent => <option key={agent.id} value={agent.id}>{agent.name}</option>)}</select></div>{selectedAgentId && <form className="d-flex gap-2 mb-3" onSubmit={submitMember}><select required className="form-select" value={memberForm.email} onChange={event => setMemberForm(value => ({ ...value, email: event.target.value }))}><option value="">Select organization member</option>{organizationMembers.map(member => <option key={member.user_id} value={member.email}>{member.display_name}</option>)}</select><select className="form-select" value={memberForm.business_role} onChange={event => setMemberForm(value => ({ ...value, business_role: event.target.value }))}><option value="member">Member</option><option value="executive_viewer">Executive viewer</option></select><button className="btn btn-primary" disabled={saving}>Add</button></form>}{agentMembers.map(member => <div className="workspace-member-row" key={member.id}><div><strong>{member.display_name}</strong><small>{member.email} · {member.business_role}</small></div><button className="btn btn-sm btn-outline-danger" disabled={member.business_role === 'lead'} onClick={() => revokeMember(member)}>Revoke</button></div>)}</section></div>
      </div>}
    </>}
  </div>
}
