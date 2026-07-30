import Avatar from '../common/Avatar'

export default function MessageBubble({ message }) {
  if (message.own) return (
    <div className="message-row own"><div className="message-content"><div className="message-bubble">{message.text}</div><div className="message-time">{message.time} <i className="bi bi-check2-all" /></div>{message.reaction && <button className="reaction">{message.reaction}</button>}</div></div>
  )
  return (
    <div className="message-row"><Avatar initials={message.initials} color={message.color} size={34}/><div className="message-content"><div className="message-sender">{message.sender}</div><div className="message-bubble">{message.text}</div><div className="message-time">{message.time}</div></div></div>
  )
}
