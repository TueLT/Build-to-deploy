import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useWorkspace } from '../../context/WorkspaceContext'

const getInitials = (name) => (name || '?').trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()

export default function TopNavbar({ onMenu }) {
  const { user, logout } = useAuth()
  const { workspaces, workspaceId, selectWorkspace, createOrganization } = useWorkspace()
  const navigate = useNavigate()
  const [creating, setCreating] = useState(false)
  const onLogout = () => { logout(); navigate('/login') }
  const createTeam = async () => {
    const name = window.prompt('Team workspace name')
    if (!name?.trim()) return
    setCreating(true)
    try { await createOrganization(name.trim()) }
    catch (error) { window.alert(error.detail || 'Could not create team workspace') }
    finally { setCreating(false) }
  }
  return (
    <header className="top-navbar">
      <button className="icon-btn mobile-menu" onClick={onMenu} aria-label="Open menu"><i className="bi bi-list" /></button>
      <div className="workspace-switcher"><i className="bi bi-grid" /><select aria-label="Current workspace" value={workspaceId || ''} onChange={event => selectWorkspace(event.target.value)}>{workspaces.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><button type="button" onClick={createTeam} disabled={creating} title="Create team workspace"><i className="bi bi-plus-lg" /></button></div>
      <div className="nav-actions">
        <button className="icon-btn"><i className="bi bi-question-circle" /></button>
        <button className="icon-btn notification-btn"><i className="bi bi-bell" /><span /></button>
        <button className="nav-avatar">{getInitials(user?.display_name)}</button>
        <button className="icon-btn" onClick={onLogout} aria-label="Log out" title="Log out"><i className="bi bi-box-arrow-right" /></button>
      </div>
    </header>
  )
}
