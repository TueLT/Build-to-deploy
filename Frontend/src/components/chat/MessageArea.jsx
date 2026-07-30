import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { messages } from '../../data/mockData'
import MessageBubble from './MessageBubble'

export default function MessageArea() {
  const [draft, setDraft] = useState('')
  const [sent, setSent] = useState([])
  const submit = (e) => { e.preventDefault(); if (!draft.trim()) return; setSent([...sent, { id: Date.now(), text: draft, own: true, time: 'Now' }]); setDraft('') }
  return (
    <div className="message-area">
      <div className="messages-scroll">
        <div className="date-divider"><span>Today</span></div>
        {messages.map(m => <MessageBubble key={m.id} message={m}/>) }
        <AnimatePresence>{sent.map(m => <motion.div key={m.id} initial={{opacity:0,y:8}} animate={{opacity:1,y:0}}><MessageBubble message={m}/></motion.div>)}</AnimatePresence>
        <div className="typing"><span/><span/><span/> Maya is typing</div>
      </div>
      <form className="composer" onSubmit={submit}>
        <div className="composer-main"><button type="button" className="icon-btn"><i className="bi bi-paperclip" /></button><input value={draft} onChange={e=>setDraft(e.target.value)} placeholder="Message Product Launch..."/><button type="button" className="icon-btn"><i className="bi bi-emoji-smile" /></button><button className="send-btn" aria-label="Send"><i className="bi bi-send-fill" /></button></div>
        <div className="composer-help"><span><i className="bi bi-stars"/> Type <strong>@orbit</strong> to ask AI</span><span>Enter to send</span></div>
      </form>
    </div>
  )
}
