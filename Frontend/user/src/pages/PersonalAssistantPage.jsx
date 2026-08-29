import { useCallback, useEffect, useState } from 'react'
import AssistantSessionList from '../components/ai/AssistantSessionList'
import PersonalAIChat from '../components/ai/PersonalAIChat'
import AssistantContextPanel from '../components/ai/AssistantContextPanel'

export default function PersonalAssistantPage(){
  const [contextOpen,setContextOpen]=useState(false)
  const [contextCollapsed,setContextCollapsed]=useState(() => window.localStorage.getItem('orbit-assistant-context-collapsed') === 'true')
  const [contextWidth,setContextWidth]=useState(() => {
    const saved = Number(window.localStorage.getItem('orbit-assistant-context-width'))
    return Number.isFinite(saved) && saved >= 300 && saved <= 520 ? saved : 350
  })
  const [resizing,setResizing]=useState(false)
  // Lifted here (not owned by PersonalAIChat) so the left "Gần đây" sidebar and the chat panel stay
  // in sync: clicking a past session sets this, which the chat panel then loads history for.
  const [activeThreadId,setActiveThreadId]=useState(null)
  // Bumped after every completed chat turn so AssistantSessionList re-fetches - a new/updated
  // thread should show up (or move to the top) without a manual page refresh.
  const [threadsVersion,setThreadsVersion]=useState(0)

  useEffect(() => {
    window.localStorage.setItem('orbit-assistant-context-width', String(contextWidth))
  }, [contextWidth])

  useEffect(() => {
    window.localStorage.setItem('orbit-assistant-context-collapsed', String(contextCollapsed))
  }, [contextCollapsed])

  useEffect(() => {
    if (!resizing) return undefined
    const onMove = event => setContextWidth(Math.max(300, Math.min(520, window.innerWidth - event.clientX)))
    const onUp = () => setResizing(false)
    document.body.classList.add('assistant-is-resizing')
    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp, { once: true })
    return () => {
      document.body.classList.remove('assistant-is-resizing')
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerup', onUp)
    }
  }, [resizing])

  const openContext = useCallback(() => {
    setContextCollapsed(false)
    setContextOpen(true)
  }, [])

  const collapseContext = useCallback(() => setContextCollapsed(true), [])

  return <div className={`personal-assistant-layout ${resizing ? 'resizing' : ''} ${contextCollapsed ? 'context-collapsed' : ''}`} style={{ '--assistant-context-width': `${contextWidth}px` }}>
    <AssistantSessionList
      activeThreadId={activeThreadId}
      onSelectThread={setActiveThreadId}
      onNewThread={()=>setActiveThreadId(null)}
      refreshSignal={threadsVersion}
    />
    <PersonalAIChat
      onContext={openContext}
      contextCollapsed={contextCollapsed}
      threadId={activeThreadId}
      onThreadIdChange={setActiveThreadId}
      onActivity={()=>setThreadsVersion(v=>v+1)}
    />
    <AssistantContextPanel
      open={contextOpen}
      width={contextWidth}
      resizing={resizing}
      onClose={()=>setContextOpen(false)}
      onCollapse={collapseContext}
      onResizeStart={event=>{ event.preventDefault(); setResizing(true) }}
    />
  </div>
}
