import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../components/common/PageHeader'
import { useAuth } from '../context/AuthContext'
import { useWorkspace } from '../context/WorkspaceContext'
import { useAvailableAgentsQuery, useConversationsQuery } from '../hooks/useWorkspaceData'
import { getInitials, getColor } from '../utils/avatar'

const formatUpdatedAt = value => {
  if (!value) return 'Chưa có hoạt động'
  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
  }).format(new Date(value))
}

export default function WorkspaceGroupsPage() {
  const { token } = useAuth()
  const { workspace, workspaceId } = useWorkspace()
  const navigate = useNavigate()
  const conversationsQuery = useConversationsQuery(token, workspaceId)
  const agentsQuery = useAvailableAgentsQuery(token, workspace?.type === 'organization' ? workspaceId : null)
  const conversations = conversationsQuery.data?.conversations || []
  const deliveryWorkspace = (agentsQuery.data || []).find(agent => agent.agent_profile === 'product_delivery')
  const deliveryRole = deliveryWorkspace?.current_user_business_role || null
  const deliveryWorkspaceName = deliveryWorkspace?.name || 'Product Delivery Workspace'
  const loading = conversationsQuery.isPending || (workspace?.type === 'organization' && agentsQuery.isPending)
  const requestError = conversationsQuery.error || agentsQuery.error
  const error = requestError?.detail || (requestError ? 'Không thể tải danh sách nhóm của workspace.' : '')

  const groups = useMemo(
    () => conversations.filter(conversation => conversation.type === 'group'),
    [conversations],
  )
  const unreadCount = groups.reduce((total, group) => total + (group.unread_count || 0), 0)
  const isLead = deliveryRole === 'lead'

  return (
    <div className="page-container workspace-groups-page">
      <PageHeader
        eyebrow="Workspace collaboration"
        title={isLead ? 'Các nhóm Delivery đang quản lý' : 'Nhóm của tôi'}
        description={isLead
          ? 'Theo dõi thành viên, hoạt động và mở chat của từng nhóm trong phạm vi Lead.'
          : 'Các nhóm bạn tham gia trong workspace hiện tại. Bạn chỉ nhìn thấy dữ liệu đã được cấp quyền.'}
      />

      <div className="group-overview-strip">
        <div><i className="bi bi-buildings" /><span><small>Product Delivery Workspace</small><strong>{deliveryWorkspaceName}</strong></span></div>
        <div><i className="bi bi-person-badge" /><span><small>Vai trò Delivery</small><strong>{isLead ? 'Lead' : deliveryRole === 'member' ? 'Member' : 'Chưa được gán'}</strong></span></div>
        <div><i className="bi bi-people" /><span><small>Nhóm có quyền truy cập</small><strong>{groups.length}</strong></span></div>
        <div><i className="bi bi-chat-left-text" /><span><small>Tin chưa đọc</small><strong>{unreadCount}</strong></span></div>
      </div>

      {workspace?.type !== 'organization' && (
        <div className="alert alert-info">Hãy chọn workspace tổ chức trên thanh phía trên để xem các nhóm doanh nghiệp.</div>
      )}
      {error && <div className="alert alert-warning">{error}</div>}
      {loading && <div className="groups-loading"><span className="spinner-border spinner-border-sm" /> Đang tải nhóm…</div>}

      {!loading && workspace?.type === 'organization' && !groups.length && !error && (
        <div className="groups-empty-state">
          <i className="bi bi-people" />
          <h2>Bạn chưa tham gia nhóm nào</h2>
          <p>Liên hệ Lead hoặc quản trị workspace để được thêm vào nhóm phù hợp.</p>
        </div>
      )}

      <div className="workspace-group-grid">
        {groups.map(group => (
          <article className="workspace-group-card" key={group.id}>
            <header>
              <span className="workspace-group-icon" style={{ background: getColor(group.id) }}>{getInitials(group.name)}</span>
              <div><h2>{group.name}</h2><p>Cập nhật {formatUpdatedAt(group.last_message?.created_at || group.updated_at)}</p></div>
              {group.unread_count > 0 && <b className="group-unread">{group.unread_count}</b>}
            </header>
            <div className="group-card-badges">
              <span className={group.my_resource_role === 'manager' ? 'manager' : ''}>
                <i className="bi bi-shield-check" /> {group.my_resource_role === 'manager' ? 'Quản lý nhóm' : 'Thành viên'}
              </span>
              <span className={group.ai_enabled ? 'ai-on' : ''}>
                <i className={`bi ${group.ai_enabled ? 'bi-stars' : 'bi-shield-lock'}`} /> AI {group.ai_enabled ? 'đang bật' : 'đang tắt'}
              </span>
            </div>
            <section className="group-members-preview">
              <div className="group-member-stack">
                {group.participants.slice(0, 5).map(participant => (
                  <span key={participant.id} title={participant.display_name} style={{ background: getColor(participant.id) }}>{getInitials(participant.display_name)}</span>
                ))}
              </div>
              <strong>{group.participants.length} thành viên</strong>
            </section>
            <div className="group-last-message">
              <i className="bi bi-chat-quote" />
              <span><small>{group.last_message?.sender_name || 'Chưa có tin nhắn'}</small><p>{group.last_message?.content || 'Bắt đầu trao đổi công việc trong nhóm.'}</p></span>
            </div>
            <button type="button" className="btn btn-primary w-100" onClick={() => navigate('/chat', { state: { conversationId: group.id } })}>
              <i className="bi bi-chat-dots me-2" />Mở chat nhóm
            </button>
          </article>
        ))}
      </div>
    </div>
  )
}
