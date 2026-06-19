/**
 * Header Component - Top bar with page title, search, and pipeline trigger.
 */

import { useLocation } from 'react-router-dom';
import useAppStore from '../store/useAppStore';
import { triggerPipeline, resetAndRunPipeline } from '../services/api';
import { useState } from 'react';

const PAGE_TITLES = {
  '/': 'Dashboard',
  '/workflow': 'Agent Workflow',
  '/logs': 'Log Explorer',
  '/incidents': 'Incident Panel',
  '/settings': 'Settings',
};

export default function Header() {
  const location = useLocation();
  const { isPipelineRunning, setPipelineRunning } = useAppStore();
  const [triggering, setTriggering] = useState(false);
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
            <>🔄 Reset & Re-run</>
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
            <>▶ Run Pipeline</>
          )}
        </button>
      </div>
    </header>
  );
}
