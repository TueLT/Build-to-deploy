import { Link } from 'react-router-dom'
import PublicPageLayout, { PublicPageMeta } from '../components/public/PublicPageLayout'

const calendarCapabilities = [
  {
    icon: 'bi-calendar2-week',
    title: 'See your schedule in Orbit',
    detail: 'Orbit reads events from the connected account’s primary Google Calendar and displays them alongside your work.',
  },
  {
    icon: 'bi-arrow-left-right',
    title: 'Keep event changes in sync',
    detail: 'Events created, edited, or deleted in Orbit are written to Google Calendar. Changes made in Google Calendar are pulled back into Orbit.',
  },
  {
    icon: 'bi-shield-lock',
    title: 'Stay in control',
    detail: 'Each person authorizes their own Google account. OAuth credentials are encrypted, and Calendar access can be disconnected at any time.',
  },
]

export default function LandingPage() {
  return (
    <PublicPageLayout>
      <PublicPageMeta
        title="Orbit AI Calendar — Plan work with two-way Google Calendar sync"
        description="Orbit connects your work with your own Google Calendar so you can view and manage events with secure two-way synchronization."
      />

      <main>
        <section className="public-hero">
          <div className="public-hero-copy">
            <span className="public-kicker"><i className="bi bi-stars" /> AI-assisted planning</span>
            <h1>Turn conversations into action—and keep your calendar in sync.</h1>
            <p>
              Orbit helps you organize tasks, reminders, and meetings. Connect your own Google
              Calendar to view and manage events without sharing one account across the team.
            </p>
            <div className="public-hero-actions">
              <Link className="btn btn-primary btn-lg" to="/register">Create an account <i className="bi bi-arrow-right" /></Link>
              <Link className="btn btn-light btn-lg" to="/login">Sign in</Link>
            </div>
            <div className="public-trust-row">
              <span><i className="bi bi-person-lock" /> Per-user authorization</span>
              <span><i className="bi bi-key" /> Encrypted OAuth credentials</span>
              <span><i className="bi bi-check2-circle" /> Explicit confirmation for AI changes</span>
            </div>
          </div>

          <div className="public-calendar-preview" aria-label="Illustration of Orbit and Google Calendar synchronization">
            <div className="preview-orbit-card">
              <header><span><i className="bi bi-command" /></span><strong>Orbit schedule</strong><small>Today</small></header>
              <div><time>09:00</time><span className="preview-event purple"><b>Product sync</b><small>30 minutes</small></span></div>
              <div><time>11:30</time><span className="preview-event blue"><b>Design review</b><small>Google Calendar</small></span></div>
              <div><time>15:00</time><span className="preview-event amber"><b>Release planning</b><small>Awaiting confirmation</small></span></div>
            </div>
            <div className="preview-sync-badge"><i className="bi bi-arrow-repeat" /><span>Two-way event sync</span></div>
          </div>
        </section>

        <section className="public-section" id="calendar-sync">
          <div className="public-section-heading">
            <span>Google Calendar integration</span>
            <h2>Your events, synchronized in both directions</h2>
            <p>Orbit requests access to Calendar events only so it can provide the features below.</p>
          </div>
          <div className="public-feature-grid">
            {calendarCapabilities.map(capability => (
              <article key={capability.title}>
                <span><i className={`bi ${capability.icon}`} /></span>
                <h3>{capability.title}</h3>
                <p>{capability.detail}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="public-data-section">
          <div>
            <span className="public-kicker"><i className="bi bi-shield-check" /> Clear data use</span>
            <h2>Why Orbit requests Google Calendar access</h2>
            <p>
              Calendar event access is used to list your events, check scheduling conflicts, and
              perform event changes that you request. Orbit does not sell Google user data or use
              it for advertising.
            </p>
            <Link to="/privacy">Read the full Privacy Policy <i className="bi bi-arrow-right" /></Link>
          </div>
          <ul>
            <li><i className="bi bi-check-circle" /><span><strong>Read events</strong>Display schedules and find conflicts.</span></li>
            <li><i className="bi bi-check-circle" /><span><strong>Write events</strong>Create, update, or delete an event you choose.</span></li>
            <li><i className="bi bi-check-circle" /><span><strong>Disconnect anytime</strong>Revoke access and remove the stored Calendar credential.</span></li>
          </ul>
        </section>

        <section className="public-cta">
          <span><i className="bi bi-calendar-check" /></span>
          <div><h2>Bring your work and schedule together.</h2><p>Sign in, open Calendar, and connect the Google account you want to use.</p></div>
          <Link className="btn btn-primary btn-lg" to="/register">Get started</Link>
        </section>
      </main>
    </PublicPageLayout>
  )
}
