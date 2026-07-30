import { useState } from 'react'
import ConversationList from '../components/chat/ConversationList'
import ConversationHeader from '../components/chat/ConversationHeader'
import MessageArea from '../components/chat/MessageArea'
import AIPanel from '../components/chat/AIPanel'

export default function ChatPage() {
  const [mobileChat, setMobileChat] = useState(false)
  const [aiOpen, setAiOpen] = useState(false)
  return (
    <div className={`chat-layout ${mobileChat ? 'show-chat' : ''}`}>
      <ConversationList onSelect={()=>setMobileChat(true)}/>
      <section className="conversation-pane"><ConversationHeader onBack={()=>setMobileChat(false)} onAI={()=>setAiOpen(true)}/><MessageArea/></section>
      <AIPanel open={aiOpen} onClose={()=>setAiOpen(false)}/>
    </div>
  )
}
