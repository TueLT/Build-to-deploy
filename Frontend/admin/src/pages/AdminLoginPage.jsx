import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function AdminLoginPage() {
  const { user, isAdmin, login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  if (user && isAdmin) return <Navigate to="/admin" replace />

  const submit = async (event) => {
    event.preventDefault(); setSubmitting(true); setError('')
    try { await login(email, password); navigate('/admin', { replace: true }) }
    catch (err) { setError(err.detail || err.message || 'Could not sign in.') }
    finally { setSubmitting(false) }
  }

  return (
    <main className="auth-page"><section className="auth-card"><div className="auth-brand"><span><i className="bi bi-command" /></span><strong>Orbit Admin</strong></div><h1>Administrator sign in</h1><p>Use a platform administrator account.</p>{error && <div className="auth-error">{error}</div>}<form onSubmit={submit}><label>Email<input className="form-control" type="email" value={email} onChange={event=>setEmail(event.target.value)} required /></label><label>Password<input className="form-control" type="password" value={password} onChange={event=>setPassword(event.target.value)} required /></label><button className="btn btn-primary w-100" disabled={submitting}>{submitting ? 'Signing in...' : 'Sign in'}</button></form><a className="d-block text-center mt-3" href={import.meta.env.VITE_USER_APP_URL || 'http://localhost:5173'}>Back to Orbit</a></section></main>
  )
}
