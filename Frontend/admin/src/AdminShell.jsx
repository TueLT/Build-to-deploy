import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../src/context/AuthContext'

const links = [
  ['/', 'bi-speedometer2', 'Dashboard'],
  ['/users', 'bi-people', 'Users'],
  ['/conversations', 'bi-chat-square-text', 'Conversations'],
  ['/user-data', 'bi-database', 'User data'],
]

export default function AdminShell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const signOut = () => { logout(); navigate('/login', { replace: true }) }

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-sidebar-brand"><span><i className="bi bi-command" /></span><strong>Orbit</strong><small>PLATFORM ADMIN</small></div>
        <div className="admin-sidebar-caption">Management</div>
        <nav>{links.map(([to, icon, label]) => <NavLink key={to} to={to} end={to === '/'}><i className={`bi ${icon}`} /><span>{label}</span></NavLink>)}</nav>
        <div className="admin-sidebar-footer"><div className="admin-identity"><i className="bi bi-person-circle" /><span><strong>{user?.display_name}</strong><small>{user?.email}</small></span></div><button onClick={signOut}><i className="bi bi-box-arrow-right" /> Sign out</button></div>
      </aside>
      <div className="admin-content"><header className="admin-topbar"><div><span className="admin-topbar-kicker">Platform control center</span><strong>Administration</strong></div><span className="admin-secure-badge"><i className="bi bi-shield-check" /> Admin only</span></header><main className="admin-main"><Outlet /></main></div>
    </div>
  )
}
