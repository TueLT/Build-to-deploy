import { useAuth } from '../context/AuthContext'

export default function AccessDeniedPage() {
  const { logout } = useAuth()
  return <main className="auth-page"><section className="auth-card text-center"><i className="bi bi-shield-lock fs-1 text-danger" /><h1>Access denied</h1><p>This application is restricted to platform administrators.</p><button className="btn btn-primary" onClick={logout}>Sign out</button></section></main>
}
