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

export const deleteCalendarEvent = (token, workspaceId, eventId) =>
  apiFetch(`/calendar/events/${eventId}?workspace_id=${encodeURIComponent(workspaceId)}`, { method: 'DELETE', token })

export const listEventCandidates = (token, conversationId) =>
  apiFetch(`/calendar/candidates?conversation_id=${encodeURIComponent(conversationId)}`, { token })

export const confirmEventCandidate = (token, candidateId) =>
  apiFetch(`/calendar/candidates/${candidateId}/confirm`, { method: 'POST', token })

export const dismissEventCandidate = (token, candidateId) =>
  apiFetch(`/calendar/candidates/${candidateId}/dismiss`, { method: 'POST', token })

export const backfillEventCandidates = (token, conversationId, batchSize = 200) =>
  apiFetch(`/conversations/${conversationId}/event-backfill`, { method: 'POST', token, body: { batch_size: batchSize } })
