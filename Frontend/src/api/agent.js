import { apiFetch } from './client'

export const chatWithAgent = (token, { message, conversation_id, thread_id, workspace_id, context_limit, messages }) =>
  apiFetch('/chat', { method: 'POST', token, body: { message, conversation_id, thread_id, workspace_id, context_limit, messages } })

export const resumeAgent = (token, { thread_id, approved, edits }) =>
  apiFetch('/chat/resume', { method: 'POST', token, body: { thread_id, approved, edits } })
