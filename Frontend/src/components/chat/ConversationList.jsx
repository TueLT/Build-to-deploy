import Avatar from '../common/Avatar'
import { conversations } from '../../data/mockData'

export default function ConversationList({ onSelect }) {
  return (
    <section className="conversation-list">
      <div className="conversation-title"><div><h2>Messages</h2><span>12 conversations</span></div><button className="icon-btn primary-soft"><i className="bi bi-pencil-square" /></button></div>
      <div className="conversation-search"><i className="bi bi-search"/><input placeholder="Search messages" /></div>
      <div className="conversation-filter"><button className="active">All</button><button>Unread</button><button>Groups</button></div>
      <div className="conversation-items">
        {conversations.map(c => (
          <button key={c.id} className={`chat-item ${c.active ? 'active' : ''}`} onClick={onSelect}>
            <Avatar initials={c.initials} color={c.color} size={44} status={c.id === 2}/>
            <span className="chat-item-body"><span className="chat-item-top"><strong>{c.name}</strong><time>{c.time}</time></span><span className="chat-item-bottom"><span>{c.message}</span>{c.unread > 0 && <b>{c.unread}</b>}</span></span>
          </button>
        ))}
      </div>
    </section>
  )
}
