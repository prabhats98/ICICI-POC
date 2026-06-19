/**
 * Sidebar Component - Navigation sidebar with branding and menu items.
 */

import { NavLink } from 'react-router-dom';
import useAppStore from '../store/useAppStore';

export default function Sidebar() {
  const { dashboard, wsConnected } = useAppStore();
  const highCount = dashboard?.incidents?.high_priority || 0;

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon">🛡️</div>
        <div>
          <div className="logo-text">CloudGuard</div>
          <div className="logo-subtitle">Banking Log Analyser</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="sidebar-section-label">Overview</div>
        <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} end>
          <span className="nav-icon">📊</span>
          Dashboard
        </NavLink>
        <NavLink to="/workflow" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="nav-icon">🔄</span>
          Agent Workflow
        </NavLink>

        <div className="sidebar-section-label">Data</div>
        <NavLink to="/logs" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="nav-icon">📝</span>
          Log Explorer
        </NavLink>
        <NavLink to="/incidents" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="nav-icon">⚠️</span>
          Incidents
          {highCount > 0 && <span className="nav-badge">{highCount}</span>}
        </NavLink>

        <div className="sidebar-section-label">System</div>
        <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="nav-icon">⚙️</span>
          Settings
        </NavLink>

        <div style={{ flex: 1 }} />

        {/* Connection status */}
        <div className="nav-item" style={{ cursor: 'default' }}>
          <span className={`status-dot ${wsConnected ? 'success' : 'error'}`}></span>
          <span style={{ fontSize: 12 }}>
            {wsConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </nav>
    </aside>
  );
}
