import { apiFetch } from './client'

export const listUsers = (token, search, workspaceId) => {
  const params = new URLSearchParams()
  if (search) params.set('search', search)
  if (workspaceId) params.set('workspace_id', workspaceId)
  return apiFetch(`/users${params.toString() ? `?${params.toString()}` : ''}`, { token })
}

export const listConversations = (token, workspaceId) =>
  apiFetch(`/conversations${workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : ''}`, { token })

export const createConversation = (token, { type, participant_ids, name, workspace_id }) =>
  apiFetch('/conversations', { method: 'POST', token, body: { type, participant_ids, name, workspace_id } })

export const getMessages = (token, conversationId, { before, limit = 50 } = {}) => {
  const params = new URLSearchParams({ limit: String(limit) })
  if (before) params.set('before', before)
  return apiFetch(`/conversations/${conversationId}/messages?${params.toString()}`, { token })
}

export const sendMessage = (token, conversationId, content) =>
  apiFetch(`/conversations/${conversationId}/messages`, { method: 'POST', token, body: { content } })

export const markRead = (token, conversationId) =>
  apiFetch(`/conversations/${conversationId}/read`, { method: 'POST', token })
