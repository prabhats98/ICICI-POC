/**
 * Header Component - Top bar with page title, search, pipeline trigger, and user profile.
 * All icons are inline SVGs — no emojis.
 */

import { useLocation, useNavigate } from 'react-router-dom';
import useAppStore from '../store/useAppStore';
import useAuthStore from '../store/useAuthStore';
import { triggerPipeline, resetAndRunPipeline } from '../services/api';
import { useState } from 'react';
import {
  RefreshIcon, PlayIcon, LogOutIcon, ChevronDownIcon, ChevronUpIcon,
} from '../components/Icons';

const PAGE_TITLES = {
  '/dashboard': 'Dashboard',
  '/workflow': 'Agent Workflow',
  '/logs': 'Log Explorer',
  '/incidents': 'Incident Panel',
  '/settings': 'Settings',
};

export default function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isPipelineRunning, setPipelineRunning, pipelineEnabled } = useAppStore();
  const { user, logout } = useAuthStore();
  const [triggering, setTriggering] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const title = PAGE_TITLES[location.pathname] || 'Dashboard';

  const handleTriggerPipeline = async (resetFirst = false) => {
    if (isPipelineRunning || triggering) return;
    setTriggering(true);
    setPipelineRunning(true);
    try {
      if (resetFirst) {
        await resetAndRunPipeline();
      } else {
        await triggerPipeline();
      }
    } catch (err) {
      console.error('Failed to trigger pipeline:', err);
      setPipelineRunning(false);
    } finally {
      setTriggering(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <header className="header">
      <div className="header-left">
        <h1 className="header-title">{title}</h1>
        {isPipelineRunning && (
          <span style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--accent-blue)' }}>
            <span className="status-dot running"></span>
            Pipeline running...
          </span>
        )}
        {!isPipelineRunning && (
          <span style={{
            fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 6,
            background: pipelineEnabled ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
            color: pipelineEnabled ? '#10b981' : '#ef4444',
          }}>
            {pipelineEnabled ? 'PIPELINE ON' : 'PIPELINE OFF'}
          </span>
        )}
      </div>
      <div className="header-right">
        <input className="header-search" type="text" placeholder="Search logs, incidents..." />
        <button
          className="btn btn-secondary"
          onClick={() => handleTriggerPipeline(true)}
          disabled={triggering || isPipelineRunning}
          title="Reset all processing flags and re-run pipeline from scratch"
        >
          {isPipelineRunning ? (
            <><span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }}></span> Resetting</>
          ) : (
            <><RefreshIcon size={14} /> Reset & Re-run</>
          )}
        </button>
        <button
          className="btn btn-primary"
          onClick={() => handleTriggerPipeline(false)}
          disabled={triggering || isPipelineRunning}
        >
          {isPipelineRunning ? (
            <><span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }}></span> Running</>
          ) : (
            <><PlayIcon size={14} /> Run Pipeline</>
          )}
        </button>

        {/* User profile & logout */}
        <div className="header-user" id="header-user">
          <button
            className="header-user-btn"
            id="user-menu-btn"
            onClick={() => setShowUserMenu(!showUserMenu)}
          >
            <div className="header-avatar">
              {user?.name?.[0]?.toUpperCase() || 'A'}
            </div>
            <span className="header-user-name">{user?.name || 'Admin'}</span>
            {showUserMenu ? <ChevronUpIcon size={12} /> : <ChevronDownIcon size={12} />}
          </button>
          {showUserMenu && (
            <div className="header-user-menu" id="user-dropdown">
              <div className="header-user-menu-info">
                <div className="header-user-menu-name">{user?.name || 'Admin'}</div>
                <div className="header-user-menu-email">{user?.email || 'admin@krelixir.com'}</div>
                <div className="header-user-menu-role">{user?.role || 'admin'}</div>
              </div>
              <div className="header-user-menu-divider" />
              <button className="header-user-menu-item" id="logout-btn" onClick={handleLogout}>
                <LogOutIcon size={15} /> Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
