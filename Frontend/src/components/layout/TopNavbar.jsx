export default function TopNavbar({ onMenu }) {
  return (
    <header className="top-navbar">
      <button className="icon-btn mobile-menu" onClick={onMenu} aria-label="Open menu"><i className="bi bi-list" /></button>
      <div className="global-search"><i className="bi bi-search" /><input aria-label="Search" placeholder="Search anything..."/><kbd>⌘ K</kbd></div>
      <div className="nav-actions">
        <button className="icon-btn"><i className="bi bi-question-circle" /></button>
        <button className="icon-btn notification-btn"><i className="bi bi-bell" /><span /></button>
        <button className="nav-avatar">AR</button>
      </div>
    </header>
  )
}
