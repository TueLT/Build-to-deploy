import { apiFetch } from './client'

export const getSystemHealth = (token) => apiFetch('/admin/system-health', { token })

export const getAIManagement = (token) => apiFetch('/admin/ai-management', { token })

export const updateAIManagement = (token, configuration) =>
  apiFetch('/admin/ai-management', { method: 'PATCH', token, body: configuration })

export const getAIUsage = (token, days = 7) => apiFetch(`/admin/ai-usage?days=${days}`, { token })

export const listAuditLog = (token, { q = '', actorType = '', limit = 50, offset = 0 } = {}) => {
  const params = new URLSearchParams({ limit, offset })
  if (q) params.set('q', q)
  if (actorType) params.set('actor_type', actorType)
  return apiFetch(`/admin/audit-log?${params}`, { token })
}

export const listUsers = (token, q) =>
  apiFetch(`/admin/users${q ? `?q=${encodeURIComponent(q)}` : ''}`, { token })

export const updateUserRole = (token, userId, role) =>
  apiFetch(`/admin/users/${userId}/role`, { method: 'PATCH', token, body: { role } })

export const updateUserStatus = (token, userId, is_active) =>
  apiFetch(`/admin/users/${userId}/status`, { method: 'PATCH', token, body: { is_active } })
