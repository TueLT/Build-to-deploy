import { apiFetch } from './client'

export const chatWithAgent = (token, { message, conversation_id, thread_id, messages }) =>
  apiFetch('/chat', { method: 'POST', token, body: { message, conversation_id, thread_id, messages } })

export const resumeAgent = (token, { thread_id, approved, edits }) =>
  apiFetch('/chat/resume', { method: 'POST', token, body: { thread_id, approved, edits } })
