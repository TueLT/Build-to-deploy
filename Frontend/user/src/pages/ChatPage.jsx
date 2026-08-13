import { useEffect, useRef, useState } from 'react'
import { useLocation, useOutletContext } from 'react-router-dom'
import ConversationList from '../components/chat/ConversationList'
import ConversationHeader from '../components/chat/ConversationHeader'
import MessageArea from '../components/chat/MessageArea'
import AIPanel from '../components/chat/AIPanel'
import NewConversationModal from '../components/chat/NewConversationModal'
import { useAuth } from '../context/AuthContext'
import { useConversations } from '../hooks/useConversations'
import { useMessages } from '../hooks/useMessages'
import { getAiPermission, markRead, setAiPermission, setGroupAiPolicy } from '../api/chat'
import { useWorkspace } from '../context/WorkspaceContext'

export default function ChatPage() {
  const { token, user } = useAuth()
  const { workspaceId } = useWorkspace()
  const location = useLocation()
  const { sendJson, subscribe } = useOutletContext()
  const [mobileChat, setMobileChat] = useState(false)
  const [aiOpen, setAiOpen] = useState(false)
  const [newConvoOpen, setNewConvoOpen] = useState(false)
  const [selectedId, setSelectedId] = useState(() => location.state?.conversationId || null)
  const [aiGranted, setAiGranted] = useState(false)
  const [aiContributionAllowed, setAiContributionAllowed] = useState(false)
  const [aiMode, setAiMode] = useState('individual')
  const [canManageAi, setCanManageAi] = useState(false)
  const { conversations, setConversations } = useConversations(token, workspaceId)
  const { messages, setMessages } = useMessages(token, selectedId)

  // AI permission is per (conversation, user) on the backend - shared here so the header badge
  // and the AI panel's Grant/Revoke buttons always agree, instead of each fetching/toggling it
  // independently.
  useEffect(() => {
    if (!selectedId) { setAiGranted(false); setAiContributionAllowed(false); setAiMode('individual'); setCanManageAi(false); return }
    let cancelled = false
    getAiPermission(token, selectedId).then(res => {
      if (!cancelled) {
        setAiGranted(res.granted)
        setAiContributionAllowed(res.contribution_allowed)
        setAiMode(res.mode || 'individual')
        setCanManageAi(Boolean(res.can_manage))
      }
    }).catch(() => {})
    return () => { cancelled = true }
  }, [selectedId, token])

  const onToggleAi = (next) => {
    const update = aiMode === 'group_managed'
      ? setGroupAiPolicy(token, selectedId, next)
      : setAiPermission(token, selectedId, { granted: next })
    return update.then(res => {
      setAiGranted(res.granted)
      setAiContributionAllowed(res.contribution_allowed)
      setAiMode(res.mode || 'individual')
      setCanManageAi(Boolean(res.can_manage))
      if (res.mode === 'group_managed') {
        setConversations(prev => prev.map(c => c.id === selectedId ? { ...c, ai_enabled: res.granted } : c))
      }
      return res
    })
  }

  const onToggleContribution = (next) =>
    setAiPermission(token, selectedId, { contribution_allowed: next }).then(res => {
      setAiGranted(res.granted)
      setAiContributionAllowed(res.contribution_allowed)
      return res
    })

  const stateRef = useRef({ selectedId, userId: user?.id })
  stateRef.current = { selectedId, userId: user?.id }

  useEffect(() => {
    if (location.state?.conversationId) {
      setSelectedId(location.state.conversationId)
      setMobileChat(true)
    }
  }, [location.state?.conversationId])

  useEffect(() => {
    if (!conversations.length) return
    if (selectedId && conversations.some(conversation => conversation.id === selectedId)) return

    const fallbackId = conversations[0].id
    setSelectedId(fallbackId)
    setConversations(prev => prev.map(c => c.id === fallbackId ? { ...c, unread_count: 0 } : c))
    markRead(token, fallbackId).catch(() => {})
  }, [conversations, selectedId, setConversations, token])

  useEffect(() => subscribe((data) => {
    if (data.type === 'group_ai_policy_changed') {
      setConversations(prev => prev.map(c => c.id === data.conversation_id ? { ...c, ai_enabled: data.enabled } : c))
      if (data.conversation_id === stateRef.current.selectedId) {
        setAiGranted(data.enabled)
        setAiContributionAllowed(data.enabled)
      }
      return
    }
    if (data.type !== 'new_message') return
    const { selectedId, userId } = stateRef.current
    const msg = data.message
    if (msg.conversation_id === selectedId) setMessages(prev => [...prev, msg])
    setConversations(prev => {
      const idx = prev.findIndex(c => c.id === msg.conversation_id)
      if (idx === -1) return prev
      const bumpUnread = msg.conversation_id !== selectedId && msg.sender_id !== userId
      const updated = { ...prev[idx], last_message: msg, updated_at: msg.created_at, unread_count: bumpUnread ? (prev[idx].unread_count || 0) + 1 : prev[idx].unread_count }
      return [updated, ...prev.slice(0, idx), ...prev.slice(idx + 1)]
    })
  }), [subscribe, setMessages, setConversations])

  const selectedConversation = conversations.find(c => c.id === selectedId) || null

  const onSelect = (id) => {
    setSelectedId(id)
    setMobileChat(true)
    setConversations(prev => prev.map(c => c.id === id ? { ...c, unread_count: 0 } : c))
    markRead(token, id).catch(() => {})
  }

  const onSend = (content) => { if (selectedId) sendJson({ type: 'send_message', conversation_id: selectedId, content }) }

  const onCreated = (conv) => {
    setConversations(prev => [conv, ...prev.filter(c => c.id !== conv.id)])
    setSelectedId(conv.id)
    setMobileChat(true)
  }

  return (
    <div className={`chat-layout ${mobileChat ? 'show-chat' : ''}`}>
      <ConversationList conversations={conversations} selectedId={selectedId} onSelect={onSelect} onNewConversation={() => setNewConvoOpen(true)} />
      <section className="conversation-pane">
        {selectedConversation ? (
          <>
            <ConversationHeader conversation={selectedConversation} onBack={() => setMobileChat(false)} onAI={() => setAiOpen(true)} aiGranted={aiGranted} onToggleAi={onToggleAi} aiMode={aiMode} canManageAi={canManageAi} />
            <MessageArea conversation={selectedConversation} messages={messages} currentUserId={user?.id} onSend={onSend} />
          </>
        ) : (
          <div className="chat-empty-state"><i className="bi bi-chat-dots" /><p>Select a conversation or start a new one</p></div>
        )}
      </section>
      <AIPanel
        open={aiOpen}
        onClose={() => setAiOpen(false)}
        messages={messages}
        conversationId={selectedId}
        workspaceId={workspaceId}
        granted={aiGranted}
        contributionAllowed={aiContributionAllowed}
        onToggleGrant={onToggleAi}
        onToggleContribution={onToggleContribution}
        aiMode={aiMode}
        canManageAi={canManageAi}
      />
      <NewConversationModal open={newConvoOpen} onClose={() => setNewConvoOpen(false)} onCreated={onCreated} />
    </div>
  )
}
