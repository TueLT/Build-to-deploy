import { apiFetch } from './client'

export const getStats = (token) => apiFetch('/admin/stats', { token })

export const listUsers = (token, q) =>
  apiFetch(`/admin/users${q ? `?q=${encodeURIComponent(q)}` : ''}`, { token })

export const updateUserRole = (token, userId, role) =>
  apiFetch(`/admin/users/${userId}/role`, { method: 'PATCH', token, body: { role } })

export const updateUserStatus = (token, userId, is_active) =>
  apiFetch(`/admin/users/${userId}/status`, { method: 'PATCH', token, body: { is_active } })

export const listConversations = (token) => apiFetch('/admin/conversations', { token })

export const getConversationMessages = (token, conversationId) =>
  apiFetch(`/admin/conversations/${conversationId}/messages`, { token })

export const deleteConversation = (token, conversationId) =>
  apiFetch(`/admin/conversations/${conversationId}`, { method: 'DELETE', token })

const scopedParams = (workspaceId, ownerId) => {
  const params = new URLSearchParams({ workspace_id: workspaceId })
  if (ownerId) params.set('owner_id', ownerId)
  return params.toString()
}

export const listTasks = (token, workspaceId, ownerId) =>
  apiFetch(`/admin/tasks?${scopedParams(workspaceId, ownerId)}`, { token })

export const deleteTask = (token, workspaceId, taskId) =>
  apiFetch(`/admin/tasks/${taskId}?workspace_id=${encodeURIComponent(workspaceId)}`, { method: 'DELETE', token })

export const listReminders = (token, workspaceId, ownerId) =>
  apiFetch(`/admin/reminders?${scopedParams(workspaceId, ownerId)}`, { token })

export const deleteReminder = (token, workspaceId, reminderId) =>
  apiFetch(`/admin/reminders/${reminderId}?workspace_id=${encodeURIComponent(workspaceId)}`, { method: 'DELETE', token })

export const listMemories = (token, workspaceId, ownerId) =>
  apiFetch(`/admin/memories?${scopedParams(workspaceId, ownerId)}`, { token })

export const deleteMemory = (token, workspaceId, memoryId) =>
  apiFetch(`/admin/memories/${memoryId}?workspace_id=${encodeURIComponent(workspaceId)}`, { method: 'DELETE', token })
