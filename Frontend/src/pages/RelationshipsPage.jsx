import { useEffect, useMemo, useState } from 'react'
import PageHeader from '../components/common/PageHeader'
import { useAuth } from '../context/AuthContext'
import { useWorkspace } from '../context/WorkspaceContext'
import { listUsers } from '../api/chat'
import { addWorkspaceMember, listWorkspaceMembers } from '../api/workspaces'
import {
  archiveRelationship,
  createExternalContact,
  createRelationship,
  listExternalContacts,
  listRelationships,
  updateRelationship,
} from '../api/relationships'

const RELATIONSHIP_TYPES = [
  ['colleague', 'Colleague'],
  ['manager', 'Manager'],
  ['direct_report', 'Direct report'],
  ['client', 'Client'],
  ['partner', 'Partner'],
  ['vendor', 'Vendor'],
  ['friend', 'Friend'],
  ['mentor', 'Mentor'],
  ['other', 'Other'],
]

const TYPE_LABELS = Object.fromEntries(RELATIONSHIP_TYPES)
const EMPTY_FORM = { subject: '', relationship_type: 'colleague', custom_label: '', strength: 3, notes: '' }
const EMPTY_CONTACT = { display_name: '', email: '', organization: '' }
const EMPTY_MEMBER = { email: '', role: 'member' }

const initials = (name) => (name || '?').trim().split(/\s+/).map(word => word[0]).slice(0, 2).join('').toUpperCase()

function RelationshipModal({ open, editing, people, form, setForm, onClose, onSubmit, submitting, onNewContact }) {
  if (!open) return null
  return (
    <div className="relationship-modal-backdrop" onClick={onClose}>
      <div className="relationship-modal" onClick={event => event.stopPropagation()}>
        <div className="relationship-modal-head">
          <div><span>{editing ? 'Update connection' : 'Add connection'}</span><h3>{editing ? editing.display_name : 'Who do you know?'}</h3></div>
          <button className="icon-btn" onClick={onClose}><i className="bi bi-x-lg" /></button>
        </div>
        <form onSubmit={onSubmit}>
          {!editing && <label className="relationship-field"><span>Person</span><select className="form-select" value={form.subject} onChange={event => setForm({...form, subject:event.target.value})} required><option value="">Select a person</option>{people.map(person => <option key={`${person.kind}:${person.id}`} value={`${person.kind}:${person.id}`}>{person.display_name} · {person.kind === 'workspace_user' ? 'Workspace' : 'External'}</option>)}</select><button type="button" className="relationship-inline-action" onClick={onNewContact}><i className="bi bi-person-plus" /> Add someone outside this workspace</button></label>}
          <div className="relationship-form-grid">
            <label className="relationship-field"><span>Relationship</span><select className="form-select" value={form.relationship_type} onChange={event => setForm({...form, relationship_type:event.target.value})}>{RELATIONSHIP_TYPES.map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label className="relationship-field"><span>How well do you know them?</span><select className="form-select" value={form.strength} onChange={event => setForm({...form, strength:Number(event.target.value)})}><option value="1">Just met</option><option value="2">A little</option><option value="3">Regular contact</option><option value="4">Know well</option><option value="5">Very close</option></select></label>
          </div>
          {form.relationship_type === 'other' && <label className="relationship-field"><span>Your label</span><input className="form-control" maxLength="80" value={form.custom_label} onChange={event => setForm({...form, custom_label:event.target.value})} placeholder="For example: Advisor" required /></label>}
          <label className="relationship-field"><span>Private note <small>Only you can see this</small></span><textarea className="form-control" maxLength="2000" value={form.notes} onChange={event => setForm({...form, notes:event.target.value})} placeholder="What is useful to remember about this person?" /></label>
          <div className="relationship-modal-actions"><button type="button" className="btn btn-light" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={submitting || (!editing && !form.subject)}>{submitting ? 'Saving...' : 'Save relationship'}</button></div>
        </form>
      </div>
    </div>
  )
}

function ExternalContactModal({ open, form, setForm, onClose, onSubmit, submitting }) {
  if (!open) return null
  return <div className="relationship-modal-backdrop relationship-modal-nested" onClick={onClose}><div className="relationship-modal relationship-contact-modal" onClick={event => event.stopPropagation()}><div className="relationship-modal-head"><div><span>External contact</span><h3>Add a person</h3></div><button className="icon-btn" onClick={onClose}><i className="bi bi-x-lg" /></button></div><form onSubmit={onSubmit}><label className="relationship-field"><span>Name</span><input className="form-control" required maxLength="120" value={form.display_name} onChange={event => setForm({...form,display_name:event.target.value})} /></label><label className="relationship-field"><span>Email</span><input className="form-control" type="email" required value={form.email} onChange={event => setForm({...form,email:event.target.value})} /></label><label className="relationship-field"><span>Company or organization</span><input className="form-control" maxLength="160" value={form.organization} onChange={event => setForm({...form,organization:event.target.value})} /></label><div className="relationship-modal-actions"><button type="button" className="btn btn-light" onClick={onClose}>Back</button><button className="btn btn-primary" disabled={submitting}>{submitting ? 'Adding...' : 'Add person'}</button></div></form></div></div>
}

function TeamModal({ open, members, canManage, form, setForm, onClose, onSubmit, submitting }) {
  if (!open) return null
  return <div className="relationship-modal-backdrop" onClick={onClose}><div className="relationship-modal" onClick={event => event.stopPropagation()}><div className="relationship-modal-head"><div><span>Team workspace</span><h3>Members</h3></div><button className="icon-btn" onClick={onClose}><i className="bi bi-x-lg" /></button></div><div className="relationship-member-list">{members.map(member => <div key={member.id}><div className="relationship-avatar">{initials(member.display_name)}</div><span><strong>{member.display_name}</strong><small>{member.email}</small></span><em>{member.role.replace('_', ' ')}</em></div>)}</div>{canManage ? <form onSubmit={onSubmit} className="relationship-member-form"><h4>Add a registered user</h4><label className="relationship-field"><span>Email</span><input className="form-control" type="email" required value={form.email} onChange={event => setForm({...form,email:event.target.value})} placeholder="name@company.com" /></label><label className="relationship-field"><span>Access</span><select className="form-select" value={form.role} onChange={event => setForm({...form,role:event.target.value})}><option value="member">Member</option><option value="admin">Workspace admin</option><option value="guest">Guest</option></select></label><div className="relationship-modal-actions"><button type="button" className="btn btn-light" onClick={onClose}>Close</button><button className="btn btn-primary" disabled={submitting}>{submitting ? 'Adding...' : 'Add member'}</button></div></form> : <div className="relationship-notice"><i className="bi bi-info-circle" /><div><strong>Member directory</strong><span>Only workspace owners and admins can add people.</span></div></div>}</div></div>
}

export default function RelationshipsPage() {
  const { token } = useAuth()
  const { workspaces, workspace, workspaceId, selectWorkspace } = useWorkspace()
  const [relationships, setRelationships] = useState([])
  const [users, setUsers] = useState([])
  const [contacts, setContacts] = useState([])
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [contactOpen, setContactOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [contactForm, setContactForm] = useState(EMPTY_CONTACT)
  const [submitting, setSubmitting] = useState(false)
  const [teamOpen, setTeamOpen] = useState(false)
  const [members, setMembers] = useState([])
  const [memberForm, setMemberForm] = useState(EMPTY_MEMBER)

  const load = async () => {
    if (!token || !workspaceId) return
    setLoading(true); setError('')
    try {
      const [relationshipItems, externalItems, userItems] = await Promise.all([
        listRelationships(token, workspaceId),
        listExternalContacts(token, workspaceId),
        listUsers(token, '', workspaceId).catch(() => []),
      ])
      setRelationships(relationshipItems); setContacts(externalItems); setUsers(userItems)
    } catch (requestError) { setError(requestError.detail || 'Could not load people.') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [token, workspaceId])

  const people = useMemo(() => [
    ...users.map(user => ({...user, kind:'workspace_user'})),
    ...contacts.map(contact => ({...contact, kind:'external_contact'})),
  ], [users, contacts])

  const visible = useMemo(() => relationships.filter(item => {
    const matchesQuery = `${item.display_name} ${item.email} ${item.organization || ''} ${item.custom_label || ''}`.toLowerCase().includes(query.toLowerCase())
    const matchesFilter = filter === 'all' || (filter === 'external' ? item.subject_kind === 'external_contact' : item.relationship_type === filter)
    return matchesQuery && matchesFilter
  }), [relationships, query, filter])

  const openCreate = () => { setEditing(null); setForm(EMPTY_FORM); setModalOpen(true); setError('') }
  const openEdit = (item) => { setEditing(item); setForm({subject:'',relationship_type:item.relationship_type,custom_label:item.custom_label || '',strength:item.strength,notes:item.notes || ''}); setModalOpen(true); setError('') }

  const submitRelationship = async event => {
    event.preventDefault(); setSubmitting(true); setError('')
    try {
      const body = {relationship_type:form.relationship_type,custom_label:form.relationship_type === 'other' ? form.custom_label : null,strength:form.strength,notes:form.notes || null}
      if (editing) await updateRelationship(token, workspaceId, editing.id, body)
      else {
        const [subject_kind, subject_id] = form.subject.split(':')
        await createRelationship(token, workspaceId, {...body,subject_kind,subject_id})
      }
      setModalOpen(false); await load()
    } catch (requestError) { setError(requestError.detail || 'Could not save relationship.') }
    finally { setSubmitting(false) }
  }

  const submitContact = async event => {
    event.preventDefault(); setSubmitting(true); setError('')
    try {
      const created = await createExternalContact(token, workspaceId, {...contactForm,organization:contactForm.organization || null})
      setContacts(current => [...current, created]); setForm(current => ({...current,subject:`external_contact:${created.id}`})); setContactOpen(false); setContactForm(EMPTY_CONTACT)
    } catch (requestError) { setError(requestError.detail || 'Could not add person.') }
    finally { setSubmitting(false) }
  }

  const archive = async item => {
    if (!window.confirm(`Archive your relationship with ${item.display_name}?`)) return
    try { await archiveRelationship(token, workspaceId, item.id); setRelationships(current => current.filter(value => value.id !== item.id)) }
    catch (requestError) { setError(requestError.detail || 'Could not archive relationship.') }
  }

  const openTeam = async () => {
    setError(''); setTeamOpen(true)
    try { setMembers(await listWorkspaceMembers(token, workspaceId)) }
    catch (requestError) { setTeamOpen(false); setError(requestError.detail || 'You do not have access to the member directory.') }
  }

  const submitMember = async event => {
    event.preventDefault(); setSubmitting(true); setError('')
    try {
      const created = await addWorkspaceMember(token, workspaceId, memberForm.email, memberForm.role)
      setMembers(current => [...current, created]); setMemberForm(EMPTY_MEMBER); await load()
    } catch (requestError) { setError(requestError.detail || 'Could not add member.') }
    finally { setSubmitting(false) }
  }

  const strongCount = relationships.filter(item => item.strength >= 4).length
  const externalCount = relationships.filter(item => item.subject_kind === 'external_contact').length
  const canManageTeam = ['owner', 'admin'].includes(workspace?.current_user_role)

  return <div className="page-container relationships-page">
    <PageHeader eyebrow="People" title="My relationships" description="Keep useful context about the people you work with. Notes are private to you." action={<div className="relationship-header-actions"><select className="form-select" value={workspaceId || ''} onChange={event => selectWorkspace(event.target.value)}>{workspaces.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select>{workspace?.type === 'organization' && <button className="btn btn-light" onClick={openTeam}><i className="bi bi-people me-2" />Members</button>}<button className="btn btn-primary" onClick={openCreate} disabled={!workspaceId}><i className="bi bi-person-plus me-2" />Add relationship</button></div>} />
    {workspace?.type === 'personal' && <div className="relationship-notice"><i className="bi bi-info-circle" /><div><strong>Personal workspace</strong><span>Add external contacts here. Select an organization workspace to connect with internal members.</span></div></div>}
    {error && <div className="auth-error mb-3">{error}</div>}
    <div className="relationship-stats"><div><span><i className="bi bi-people" /></span><strong>{relationships.length}</strong><small>People</small></div><div><span><i className="bi bi-heart" /></span><strong>{strongCount}</strong><small>Close connections</small></div><div><span><i className="bi bi-building" /></span><strong>{relationships.length - externalCount}</strong><small>Workspace</small></div><div><span><i className="bi bi-person-badge" /></span><strong>{externalCount}</strong><small>External</small></div></div>
    <div className="relationship-toolbar"><div className="relationship-search"><i className="bi bi-search" /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search people, email or company" /></div><select className="form-select" value={filter} onChange={event => setFilter(event.target.value)}><option value="all">All relationships</option><option value="colleague">Colleagues</option><option value="client">Clients</option><option value="partner">Partners</option><option value="friend">Friends</option><option value="external">External contacts</option></select></div>
    {loading ? <div className="relationship-empty"><span className="spinner-border spinner-border-sm" /><p>Loading your people...</p></div> : visible.length ? <div className="relationship-grid">{visible.map(item => <article className="relationship-card" key={item.id}><div className="relationship-card-top"><div className={`relationship-avatar ${item.subject_kind === 'external_contact' ? 'external' : ''}`}>{initials(item.display_name)}</div><div><h3>{item.display_name}</h3><p>{item.email}</p></div><div className="dropdown ms-auto"><button className="icon-btn" data-bs-toggle="dropdown"><i className="bi bi-three-dots" /></button><ul className="dropdown-menu dropdown-menu-end"><li><button className="dropdown-item" onClick={() => openEdit(item)}><i className="bi bi-pencil me-2" />Edit</button></li><li><button className="dropdown-item text-danger" onClick={() => archive(item)}><i className="bi bi-archive me-2" />Archive</button></li></ul></div></div><div className="relationship-tags"><span>{item.custom_label || TYPE_LABELS[item.relationship_type]}</span>{item.subject_kind === 'external_contact' && <span className="external-tag">External</span>}</div>{item.organization && <p className="relationship-organization"><i className="bi bi-building" />{item.organization}</p>}<div className="relationship-strength"><span>Connection</span><div>{[1,2,3,4,5].map(value => <i key={value} className={`bi bi-circle-fill ${value <= item.strength ? 'active' : ''}`} />)}</div></div><p className={`relationship-note ${item.notes ? '' : 'empty'}`}>{item.notes || 'No private note yet.'}</p><footer><span><i className="bi bi-shield-lock" /> Private</span><button onClick={() => openEdit(item)}>View details</button></footer></article>)}</div> : <div className="relationship-empty"><div><i className="bi bi-people" /></div><h3>{query || filter !== 'all' ? 'No matching people' : 'Build your people list'}</h3><p>{query || filter !== 'all' ? 'Try another search or filter.' : 'Add a colleague, client or friend and keep the context that matters.'}</p>{!query && filter === 'all' && <button className="btn btn-primary" onClick={openCreate}>Add your first relationship</button>}</div>}
    <RelationshipModal open={modalOpen} editing={editing} people={people} form={form} setForm={setForm} onClose={() => setModalOpen(false)} onSubmit={submitRelationship} submitting={submitting} onNewContact={() => setContactOpen(true)} />
    <ExternalContactModal open={contactOpen} form={contactForm} setForm={setContactForm} onClose={() => setContactOpen(false)} onSubmit={submitContact} submitting={submitting} />
    <TeamModal open={teamOpen} members={members} canManage={canManageTeam} form={memberForm} setForm={setMemberForm} onClose={() => setTeamOpen(false)} onSubmit={submitMember} submitting={submitting} />
  </div>
}
