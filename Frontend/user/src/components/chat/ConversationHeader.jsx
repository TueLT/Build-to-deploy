import Avatar from '../common/Avatar'
import { getInitials, getColor } from '../../utils/avatar'

export default function ConversationHeader({ conversation, onBack, onAI, aiGranted, onToggleAi, aiMode = 'individual', canManageAi = false }) {
  const handleToggleAi = () => {
    if (aiMode === 'group_managed' && !canManageAi) { onAI(); return }
    onToggleAi(!aiGranted).catch(() => {})
  }
  return (
    <header className="conversation-header">
      <button className="icon-btn chat-back" onClick={onBack}><i className="bi bi-arrow-left" /></button>
      <Avatar initials={getInitials(conversation.name)} color={getColor(conversation.id)} size={44} />
      <div className="conversation-meta">
        <div><h3>{conversation.name}</h3><span>{conversation.type === 'group' ? `${conversation.participants.length} members` : 'Direct message'}</span></div>
        <button
          type="button"
          className={`ai-active${aiGranted ? '' : ' off'}`}
          onClick={handleToggleAi}
          title={aiMode === 'group_managed' ? (canManageAi ? 'Manage the group-wide AI policy' : 'AI policy is managed by a conversation manager') : 'Manage your Assistant access'}
        >
          <i className={`bi ${aiGranted ? 'bi-stars' : 'bi-slash-circle'}`} />{aiGranted ? 'Assistant enabled' : 'Assistant disabled'}
        </button>
      </div>
      <div className="header-actions"><button className="icon-btn"><i className="bi bi-telephone" /></button><button className="icon-btn"><i className="bi bi-camera-video" /></button><button className="icon-btn ai-mobile-btn" onClick={onAI}><i className="bi bi-stars" /></button><button className="icon-btn"><i className="bi bi-three-dots-vertical" /></button></div>
    </header>
  )
}
