import { useEffect, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import PageHeader from '../components/common/PageHeader'
import NewEventModal from '../components/calendar/NewEventModal'
import { useAuth } from '../context/AuthContext'
import { listCalendarEvents } from '../api/calendar'
import { getColor } from '../utils/avatar'

export default function CalendarPage() {
  const { token } = useAuth()
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const [newEventOpen, setNewEventOpen] = useState(false)

  const refresh = () => {
    setLoading(true); setError('')
    listCalendarEvents(token)
      .then(list => setEvents(list.map(e => ({ ...e, color: getColor(e.id) }))))
      .catch(err => setError(err.detail || 'Could not load Google Calendar events.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { refresh() }, [token])

  const onCreated = (event) => setEvents(prev => [...prev, { ...event, color: getColor(event.id) }])

  return <div className="page-container calendar-page">
    <PageHeader eyebrow="Schedule" title="Calendar" description="Your Google Calendar events, all in one place." action={<button className="btn btn-primary" onClick={() => setNewEventOpen(true)}><i className="bi bi-plus-lg me-2"/>New event</button>}/>
    {error && <div className="auth-error mb-3">{error}</div>}
    {loading ? <p className="text-muted small">Loading calendar...</p> : (
      <div className="calendar-layout"><section className="content-card calendar-card"><FullCalendar plugins={[dayGridPlugin,timeGridPlugin,interactionPlugin]} initialView="dayGridMonth" headerToolbar={{left:'prev,next today',center:'title',right:'dayGridMonth,timeGridWeek,timeGridDay'}} events={events} eventClick={({event:e})=>setSelected(e)} height="auto"/></section>
        <aside className="detected-sidebar"><div className="detected-head"><span><i className="bi bi-stars"/></span><div><h3>AI-detected events</h3><p>Coming soon</p></div></div><p className="text-muted small">Agent chủ động phát hiện lịch hẹn từ tin nhắn sẽ có ở giai đoạn tiếp theo (xem ROADMAP.md).</p></aside>
      </div>
    )}
    {selected && <div className="modal-backdrop-custom" onClick={()=>setSelected(null)}><div className="event-modal" onClick={e=>e.stopPropagation()}><button className="icon-btn modal-close" onClick={()=>setSelected(null)}><i className="bi bi-x-lg"/></button><div className="event-modal-icon"><i className="bi bi-calendar-event"/></div><span className="eyebrow">Event details</span><h3>{selected.title}</h3><div className="event-detail-row"><i className="bi bi-clock"/><span><strong>{selected.start?.toLocaleString()}</strong>{selected.end && <small>{' → '}{selected.end.toLocaleString()}</small>}</span></div>{selected.url && <a className="btn btn-primary w-100 mt-3" href={selected.url} target="_blank" rel="noreferrer">Open in Google Calendar</a>}</div></div>}
    <NewEventModal open={newEventOpen} onClose={() => setNewEventOpen(false)} onCreated={onCreated} />
  </div>
}
