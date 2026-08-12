import { apiFetch } from './client'

export const listReminders = (token, workspaceId) =>
  apiFetch(`/reminders?workspace_id=${encodeURIComponent(workspaceId)}`, { token })

export const createReminder = (token, { workspace_id, title, due_at_iso, lead_minutes, message }) =>
  apiFetch('/reminders', { method: 'POST', token, body: { workspace_id, title, due_at_iso, lead_minutes, message } })

export const cancelReminder = (token, workspaceId, reminderId) =>
  apiFetch(`/reminders/${reminderId}?workspace_id=${encodeURIComponent(workspaceId)}`, { method: 'DELETE', token })
