import { apiFetch } from './client'

export const chatWithAgent = (token, { message, thread_id, messages, conversation_id, scope, workspace_id, context_limit }) =>
  apiFetch('/chat', { method: 'POST', token, body: { message, thread_id, messages, conversation_id, scope, workspace_id, context_limit } })

export const resumeAgent = (token, { thread_id, approved, edits }) =>
  apiFetch('/chat/resume', { method: 'POST', token, body: { thread_id, approved, edits } })
