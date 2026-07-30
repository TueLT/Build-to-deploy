import Avatar from '../common/Avatar'

export default function ConversationHeader({ onBack, onAI }) {
  return (
    <header className="conversation-header">
      <button className="icon-btn chat-back" onClick={onBack}><i className="bi bi-arrow-left" /></button>
      <div className="group-avatar-wrap"><Avatar initials="PL" color="#635bff" size={44}/><span className="mini-avatar one">MC</span><span className="mini-avatar two">TG</span></div>
      <div className="conversation-meta"><div><h3>Product Launch</h3><span><i className="online-dot"/> 6 members • 4 online</span></div><span className="ai-active"><i className="bi bi-stars"/> AI enabled</span></div>
      <div className="header-actions"><button className="icon-btn"><i className="bi bi-telephone"/></button><button className="icon-btn"><i className="bi bi-camera-video"/></button><button className="icon-btn ai-mobile-btn" onClick={onAI}><i className="bi bi-stars"/></button><button className="icon-btn"><i className="bi bi-three-dots-vertical"/></button></div>
    </header>
  )
}
