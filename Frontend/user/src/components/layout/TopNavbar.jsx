import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useWorkspace } from '../../context/WorkspaceContext'

const getInitials = (name) => (name || '?').trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()

export default function TopNavbar({ onMenu }) {
  const { user, logout } = useAuth()
  const { workspaces, workspaceId, selectWorkspace } = useWorkspace()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const organizationWorkspaces = workspaces.filter(workspace => workspace.type === 'organization')
  const organizationWorkspaceId = organizationWorkspaces.some(workspace => workspace.id === workspaceId)
    ? workspaceId
    : ''
  const isWorkspaceRoute = ['/chat', '/relationships', '/workspaces', '/groups', '/workspace-agent', '/delivery-agent']
    .some(path => pathname === path || pathname.startsWith(`${path}/`))
  const onLogout = () => { logout(); navigate('/login', { replace: true }) }
  return (
    <header className="top-navbar">
      <button className="icon-btn mobile-menu" onClick={onMenu} aria-label="Open menu"><i className="bi bi-list" /></button>
      {isWorkspaceRoute ? (
        <label className="workspace-switcher" aria-label="Không gian làm việc hiện tại">
          <i className="bi bi-buildings" />
          <select value={organizationWorkspaceId} onChange={event => selectWorkspace(event.target.value)}>
            {!organizationWorkspaces.length && <option value="">Chưa tham gia workspace</option>}
            {organizationWorkspaces.map(workspace => (
              <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
            ))}
          </select>
        </label>
      ) : (
        <div className="workspace-switcher" aria-label="Không gian cá nhân hiện tại">
          <i className="bi bi-person-lock" />
          <span>Không gian cá nhân</span>
        </div>
      )}
      <div className="nav-actions">
        <button className="icon-btn"><i className="bi bi-question-circle" /></button>
        <button className="icon-btn notification-btn"><i className="bi bi-bell" /><span /></button>
        <button className="nav-avatar">{getInitials(user?.display_name)}</button>
        <button className="icon-btn" onClick={onLogout} aria-label="Log out" title="Log out"><i className="bi bi-box-arrow-right" /></button>
      </div>
    </header>
  )
}
