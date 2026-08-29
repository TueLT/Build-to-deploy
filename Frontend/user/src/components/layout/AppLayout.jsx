import { Suspense, useCallback, useRef, useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import Sidebar from './Sidebar'
import TopNavbar from './TopNavbar'
import ReminderToast from './ReminderToast'
import TaskSuggestedToast from './TaskSuggestedToast'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { useChatSocket } from '../../api/useWebSocket'
import { getNotificationPermission, notifyTaskSuggested } from '../../utils/browserNotifications'

function ContentFallback() {
  return (
    <div className="route-content-fallback" role="status" aria-live="polite">
      <span className="spinner-border spinner-border-sm text-primary" />
      <span>&#272;ang m&#7903; trang&hellip;</span>
    </div>
  )
}

export default function AppLayout() {
  const [open, setOpen] = useState(false)
  const { token, user } = useAuth()
  const { pushToast } = useToast()
  const navigate = useNavigate()
  const handlersRef = useRef(new Set())
  const [toastReminder, setToastReminder] = useState(null)
  const [toastTask, setToastTask] = useState(null)

  const subscribe = useCallback((handler) => {
    handlersRef.current.add(handler)
    return () => handlersRef.current.delete(handler)
  }, [])

  const { sendJson } = useChatSocket(token, (data) => {
    handlersRef.current.forEach(handler => handler(data))
    if (data.type === 'reminder_fired') setToastReminder(data.reminder)
    if (data.type === 'task_suggested') {
      setToastTask(data.task)
      if (
        user?.preferences?.ai_suggestion_alerts === true &&
        document.visibilityState !== 'visible' &&
        getNotificationPermission() === 'granted'
      ) notifyTaskSuggested(data.task, { onClick: () => navigate('/tasks') })
    }
    if (data.type === 'usage_budget_alert') pushToast(data.message || 'AI usage budget alert')
  })

  return (
    <div className="app-shell">
      <Sidebar open={open} onClose={() => setOpen(false)} />
      <div className="app-column"><TopNavbar onMenu={() => setOpen(true)} /><main className="app-main"><Suspense fallback={<ContentFallback />}><Outlet context={{ sendJson, subscribe }} /></Suspense></main></div>
      {toastReminder && <ReminderToast reminder={toastReminder} onClose={() => setToastReminder(null)} />}
      {toastTask && <TaskSuggestedToast task={toastTask} onClose={() => setToastTask(null)} />}
    </div>
  )
}
