import { apiFetch } from './client'

export const listMemories = (token, workspaceId) =>
  apiFetch(`/memories?workspace_id=${encodeURIComponent(workspaceId)}`, { token })

export const createMemory = (token, { workspace_id, category, title, detail }) =>
  apiFetch('/memories', { method: 'POST', token, body: { workspace_id, category, title, detail } })

export const updateMemory = (token, memoryId, updates) =>
  apiFetch(`/memories/${memoryId}`, { method: 'PATCH', token, body: updates })

export const deleteMemory = (token, memoryId) =>
  apiFetch(`/memories/${memoryId}`, { method: 'DELETE', token })
