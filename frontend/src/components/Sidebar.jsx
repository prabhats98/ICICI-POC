/**
 * Sidebar Component - Navigation sidebar with branding and menu items.
 * Uses SVG icons from Icons.jsx — no emojis.
 */

import { NavLink } from 'react-router-dom';
import useAppStore from '../store/useAppStore';
import { ShieldIcon, ChartIcon, RefreshIcon, SearchIcon, AlertIcon } from './Icons';

// Settings gear SVG icon
const GearIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>
);

// File text icon for log explorer
const FileTextIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
    <line x1="16" y1="13" x2="8" y2="13"/>
    <line x1="16" y1="17" x2="8" y2="17"/>
    <polyline points="10 9 9 9 8 9"/>
  </svg>
);

export default function Sidebar() {
  const { dashboard, wsConnected } = useAppStore();
  const p1Count = dashboard?.incidents?.p1 || 0;

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon"><ShieldIcon size={18} /></div>
        <div>
          <div className="logo-text">CloudGuard</div>
          <div className="logo-subtitle">Azure Incident Pipeline</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="sidebar-section-label">Overview</div>
        <NavLink to="/dashboard" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} end>
          <span className="nav-icon"><ChartIcon size={18} /></span>
          Dashboard
        </NavLink>
        <NavLink to="/workflow" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="nav-icon"><RefreshIcon size={18} /></span>
          Agent Workflow
        </NavLink>

        <div className="sidebar-section-label">Data</div>
        <NavLink to="/logs" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="nav-icon"><FileTextIcon size={18} /></span>
          Log Explorer
        </NavLink>
        <NavLink to="/incidents" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="nav-icon"><AlertIcon size={18} /></span>
          Incidents
          {p1Count > 0 && <span className="nav-badge">{p1Count}</span>}
        </NavLink>
        <NavLink to="/analytics" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="nav-icon">📈</span>
          Analytics
        </NavLink>

        <div className="sidebar-section-label">System</div>
        <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="nav-icon"><GearIcon size={18} /></span>
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
