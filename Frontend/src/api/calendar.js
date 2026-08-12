import { apiFetch } from './client'

export const listCalendarEvents = (token, workspaceId, { time_min, time_max } = {}) => {
  const params = new URLSearchParams()
  params.set('workspace_id', workspaceId)
  if (time_min) params.set('time_min', time_min)
  if (time_max) params.set('time_max', time_max)
  const qs = params.toString()
  return apiFetch(`/calendar/events${qs ? `?${qs}` : ''}`, { token })
}

export const createCalendarEvent = (token, { workspace_id, summary, start_iso, end_iso, description, attendees }) =>
  apiFetch('/calendar/events', { method: 'POST', token, body: { workspace_id, summary, start_iso, end_iso, description, attendees } })

export const updateCalendarEvent = (token, workspaceId, eventId, { summary, start_iso, end_iso, description } = {}) =>
  apiFetch(`/calendar/events/${eventId}?workspace_id=${encodeURIComponent(workspaceId)}`, { method: 'PATCH', token, body: { summary, start_iso, end_iso, description } })

export const deleteCalendarEvent = (token, eventId) =>
  apiFetch(`/calendar/events/${eventId}`, { method: 'DELETE', token })

export const getCalendarConnection = (token) => apiFetch('/calendar/connection', { token })

// Returns Google's consent-screen URL to open (window.open) - the connection itself finishes
// server-side at the OAuth callback route, not via any request this frontend makes directly.
export const getCalendarOAuthUrl = (token) => apiFetch('/calendar/oauth/url', { token })

export const disconnectCalendar = (token) =>
  apiFetch('/calendar/connection', { method: 'DELETE', token })
