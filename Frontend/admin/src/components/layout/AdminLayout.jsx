import { Outlet } from 'react-router-dom'
import AdminSidebar from './AdminSidebar'

export default function AdminLayout() {
  return <div className="app-shell"><AdminSidebar /><div className="app-column"><header className="top-navbar"><strong>Platform administration</strong></header><main className="app-main"><Outlet /></main></div></div>
}
