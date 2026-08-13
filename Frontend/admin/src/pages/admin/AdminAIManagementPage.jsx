import { useEffect, useState } from 'react'
import PageHeader from '../../components/common/PageHeader'
import { getAIManagement, getSystemHealth, updateAIManagement, updateDailyBudget } from '../../api/admin'
import { useAuth } from '../../context/AuthContext'

const statusLabel = { operational: 'Operational', degraded: 'Needs attention', down: 'Unavailable' }

export default function AdminAIManagementPage() {
  const { token } = useAuth()
  const [management, setManagement] = useState(null)
  const [health, setHealth] = useState(null)
  const [draft, setDraft] = useState({ provider: '', model: '', temperature: 0.7 })
  const [budget, setBudget] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  const load = async () => {
    setMessage('')
    try {
      const [config, systemHealth] = await Promise.all([getAIManagement(token), getSystemHealth(token)])
      setManagement(config)
      setHealth(systemHealth)
      setDraft({ provider: config.provider, model: config.model, temperature: config.temperature })
      setBudget(String(config.daily_token_budget))
    } catch (error) { setMessage(error.detail || 'Could not load AI configuration.') }
  }
  useEffect(() => { load() }, [token])

  const selectProvider = provider => {
    setDraft(current => ({ ...current, provider, model: management?.model_options?.[provider]?.[0]?.id || '' }))
  }
  const saveModel = async event => {
    event.preventDefault(); setBusy(true); setMessage('')
    try { const next = await updateAIManagement(token, draft); setManagement(next); setMessage('AI configuration updated.') }
    catch (error) { setMessage(error.detail || 'Could not update AI configuration.') }
    finally { setBusy(false) }
  }
  const saveBudget = async () => {
    setBusy(true); setMessage('')
    try { await updateDailyBudget(token, Number(budget)); await load(); setMessage('Daily token budget updated.') }
    catch (error) { setMessage(error.detail || 'Could not update token budget.') }
    finally { setBusy(false) }
  }
  const models = management?.model_options?.[draft.provider] || []
  const providerReady = management?.configured_providers?.includes(draft.provider)

  return <div className="page-container admin-monitor-page">
    <PageHeader eyebrow="Platform admin" title="AI Management" description="Control the runtime model, budget, consent safeguards, and service health." />
    {message && <div className="admin-notice">{message}</div>}
    <div className="admin-monitor-grid">
      <section className="admin-monitor-card"><h3>Runtime model</h3><form className="admin-model-form" onSubmit={saveModel}>
        <label>Provider<select className="form-select" value={draft.provider} onChange={event => selectProvider(event.target.value)}>{Object.keys(management?.model_options || {}).map(provider => <option key={provider} value={provider}>{provider}{management.configured_providers.includes(provider) ? '' : ' (API key missing)'}</option>)}</select></label>
        <label>Model<select className="form-select" value={draft.model} onChange={event => setDraft({ ...draft, model: event.target.value })}>{models.map(model => <option key={model.id} value={model.id}>{model.label}</option>)}</select></label>
        <label>Temperature: {Number(draft.temperature).toFixed(1)}<input type="range" min="0" max="2" step="0.1" value={draft.temperature} onChange={event => setDraft({ ...draft, temperature: Number(event.target.value) })} /></label>
        <button className="btn btn-primary" disabled={busy || !providerReady || !draft.model}>Apply model</button>
      </form></section>
      <section className="admin-monitor-card"><h3>Daily budget</h3><p>Set 0 for unlimited. Changes apply to the next AI request.</p><div className="admin-budget-row"><input className="form-control" type="number" min="0" value={budget} onChange={event => setBudget(event.target.value)} /><button className="btn btn-primary" disabled={busy || budget === ''} onClick={saveBudget}>Save</button></div><dl className="admin-summary"><div><dt>Human confirmation</dt><dd>Required</dd></div><div><dt>Conversation consent</dt><dd>Required</dd></div><div><dt>Active permissions</dt><dd>{management?.granted_permissions ?? '—'}</dd></div><div><dt>Revoked permissions</dt><dd>{management?.revoked_permissions ?? '—'}</dd></div></dl></section>
    </div>
    <section className="admin-monitor-card"><h3>System health</h3><div className="admin-health-list">{health?.components.map(component => <div key={component.key}><i className={`health-dot ${component.status}`} /><span><strong>{component.label}</strong><small>{component.detail}</small></span><em>{statusLabel[component.status]}</em></div>)}</div></section>
  </div>
}
