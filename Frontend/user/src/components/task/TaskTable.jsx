import { formatDateShort } from '../../utils/datetime'

const priorityClass = { High: 'danger', Medium: 'warning', Low: 'info' }
const statusClass = { Completed: 'success', Overdue: 'danger', Pending: 'secondary', 'In progress': 'primary', Blocked: 'danger', 'Awaiting review': 'warning', 'Changes requested': 'danger' }
const sourceLabel = { manual: 'Manual', proactive: 'AI suggestion' }

function displayStatus(task) {
  if (task.status === 'pending' && task.due_at && new Date(task.due_at) < new Date()) return 'Overdue'
  if (task.status === 'in_progress') return 'In progress'
  if (task.status === 'blocked') return 'Blocked'
  if (task.status === 'submitted') return 'Awaiting review'
  if (task.status === 'changes_requested') return 'Changes requested'
  if (task.status === 'completed') return 'Completed'
  return 'Pending'
}

export function formatDue(due_at) {
  if (!due_at) return 'No due date'
  return formatDateShort(due_at)
}

export default function TaskTable({ tasks, onStart, onBlock, onSubmit, onComplete, onDelete }) {
  return (
    <div className="table-responsive task-table-wrap"><table className="table task-table align-middle mb-0"><thead><tr><th><input type="checkbox"/></th><th>Task</th><th>Deadline</th><th>Priority</th><th>Status</th><th>Source</th><th/></tr></thead><tbody>
      {tasks.map(task => {
        const status = displayStatus(task)
        const canWork = ['pending', 'in_progress', 'blocked', 'changes_requested'].includes(task.status)
        return <tr key={task.id}><td><input type="checkbox" checked={task.status==='completed'} readOnly/></td><td><strong className={task.status==='completed'?'text-decoration-line-through text-muted':''}>{task.title}</strong>{task.requires_review && <small className="d-block text-muted"><i className="bi bi-shield-check me-1"/>Lead review required</small>}{task.review_note && task.status === 'changes_requested' && <small className="d-block text-danger">{task.review_note}</small>}</td><td><span className={status==='Overdue'?'text-danger':''}><i className="bi bi-calendar3 me-2"/>{formatDue(task.due_at)}</span></td><td><span className={`soft-badge ${priorityClass[task.priority]}`}><i/>{task.priority}</span></td><td><span className={`status-badge ${statusClass[status]}`}>{status}</span></td><td><span className="source-pill"><i className="bi bi-chat-left-text"/>{sourceLabel[task.source] || task.source}</span></td><td><div className="dropdown"><button className="icon-btn" data-bs-toggle="dropdown"><i className="bi bi-three-dots"/></button><ul className="dropdown-menu dropdown-menu-end">
          {['pending', 'blocked', 'changes_requested'].includes(task.status) && <li><button className="dropdown-item" onClick={() => onStart(task)}><i className="bi bi-play me-2"/>Start / resume</button></li>}
          {canWork && task.status !== 'blocked' && <li><button className="dropdown-item" onClick={() => onBlock(task)}><i className="bi bi-exclamation-octagon me-2"/>Mark blocked</button></li>}
          {canWork && task.requires_review && <li><button className="dropdown-item" onClick={() => onSubmit(task)}><i className="bi bi-send-check me-2"/>Submit evidence</button></li>}
          {canWork && !task.requires_review && <li><button className="dropdown-item" onClick={() => onComplete(task)}><i className="bi bi-check2 me-2"/>Complete</button></li>}
          {!['submitted'].includes(task.status) && <li><button className="dropdown-item text-danger" onClick={() => onDelete(task)}><i className="bi bi-trash me-2"/>Delete</button></li>}
        </ul></div></td></tr>
      })}
      {!tasks.length && <tr><td colSpan={7} className="text-center text-muted py-4">No tasks yet.</td></tr>}
    </tbody></table></div>
  )
}
