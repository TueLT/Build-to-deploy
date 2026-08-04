import { apiFetch } from './client'

export const listWorkspaces = (token) => apiFetch('/workspaces', { token })

export const createWorkspace = (token, name) =>
  apiFetch('/workspaces', { method: 'POST', token, body: { name } })

export const listWorkspaceMembers = (token, workspaceId) =>
  apiFetch(`/workspaces/${workspaceId}/members`, { token })

export const addWorkspaceMember = (token, workspaceId, email, role = 'member') =>
  apiFetch(`/workspaces/${workspaceId}/members`, {
    method: 'POST',
    token,
    body: { email, role },
  })
