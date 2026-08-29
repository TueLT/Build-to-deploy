import { apiFetch } from './client'

export const listTasks = (token) => apiFetch('/tasks', { token })

export const createTask = (token, { workspace_id, title, due_at, priority, conversation_id, source, source_message_ids, consent_scope_hash }) =>
  apiFetch('/tasks', { method: 'POST', token, body: { workspace_id, title, due_at, priority, conversation_id, source, source_message_ids, consent_scope_hash } })

export const updateTaskStatus = (token, taskId, status, { blocked_reason = null, expected_row_version = null } = {}) =>
  apiFetch(`/tasks/${taskId}/status`, {
    method: 'PATCH', token, body: { status, blocked_reason, expected_row_version },
  })

export const submitTask = (token, taskId, payload) =>
  apiFetch(`/tasks/${taskId}/submission`, { method: 'POST', token, body: payload })

export const deleteTask = (token, taskId) =>
  apiFetch(`/tasks/${taskId}`, { method: 'DELETE', token })
