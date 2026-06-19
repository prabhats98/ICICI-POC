/**
 * Settings Page - Agent configuration and scheduler settings.
 */

import { useEffect, useState } from 'react';
import { getAgentStatus, getAgentHistory } from '../services/api';

export default function Settings() {
  const [status, setStatus] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const [statusRes, historyRes] = await Promise.all([
        getAgentStatus(),
        getAgentHistory({ page_size: 10 }),
      ]);
      setStatus(statusRes.data);
      setHistory(historyRes.data.items || []);
    } catch (err) {
      console.error('Settings load error:', err);
    }
  };

  const formatDate = (d) => d ? new Date(d).toLocaleString() : 'N/A';

  return (
    <div className="page-content">
      <div className="page-header animate-in">
        <h1>Settings</h1>
      </div>

      <div className="grid-2">
        {/* Pipeline Configuration */}
        <div className="glass-card animate-in animate-in-delay-1">
          <div className="section-title">⚙️ Pipeline Configuration</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 16 }}>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-tertiary)', display: 'block', marginBottom: 4 }}>Scheduler Interval</label>
              <input className="header-search" type="text" value="Every 5 minutes" readOnly style={{ width: '100%' }} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-tertiary)', display: 'block', marginBottom: 4 }}>Gemini Model</label>
              <input className="header-search" type="text" value="gemini-2.5-flash" readOnly style={{ width: '100%' }} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-tertiary)', display: 'block', marginBottom: 4 }}>GCP Project</label>
              <input className="header-search" type="text" value="gen-ai-poc-onboarding" readOnly style={{ width: '100%' }} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-tertiary)', display: 'block', marginBottom: 4 }}>Database</label>
              <input className="header-search" type="text" value="PostgreSQL (banking_log_analyser)" readOnly style={{ width: '100%' }} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-tertiary)', display: 'block', marginBottom: 4 }}>Email Alerts</label>
              <input className="header-search" type="text" value="production-manager@example.com (demo)" readOnly style={{ width: '100%' }} />
            </div>
          </div>
        </div>

        {/* Agent Status */}
        <div className="glass-card animate-in animate-in-delay-2">
          <div className="section-title">🤖 Agent Status</div>
          <div style={{ marginTop: 16 }}>
            {status ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Pipeline Status</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span className={`status-dot ${status.is_running ? 'running' : 'idle'}`}></span>
                    <span style={{ fontSize: 13 }}>{status.is_running ? 'Running' : 'Idle'}</span>
                  </span>
                </div>
                {status.last_run && (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Last Run Status</span>
                      <span style={{ fontSize: 13 }}>{status.last_run.status}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Logs Processed</span>
                      <span style={{ fontSize: 13 }}>{status.last_run.logs_processed}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Incidents Created</span>
                      <span style={{ fontSize: 13 }}>{status.last_run.incidents_created}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Emails Sent</span>
                      <span style={{ fontSize: 13 }}>{status.last_run.emails_sent}</span>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <div className="empty-state" style={{ padding: 20 }}>
                <div className="empty-state-text">Loading status...</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Run History */}
      <div className="section animate-in animate-in-delay-3" style={{ marginTop: 24 }}>
        <div className="section-title">📜 Pipeline Run History</div>
        <div className="glass-card" style={{ padding: 0, overflow: 'auto' }}>
          {history.length === 0 ? (
            <div className="empty-state" style={{ padding: 40 }}>
              <div className="empty-state-text">No pipeline runs yet</div>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Trigger</th>
                  <th>Logs</th>
                  <th>High</th>
                  <th>Medium</th>
                  <th>Low</th>
                  <th>Emails</th>
                  <th>Started</th>
                  <th>Completed</th>
                </tr>
              </thead>
              <tbody>
                {history.map((run) => (
                  <tr key={run.id}>
                    <td>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className={`status-dot ${run.status === 'RUNNING' ? 'running' : run.status === 'SUCCESS' ? 'success' : 'error'}`}></span>
                        {run.status}
                      </span>
                    </td>
                    <td>{run.trigger_type}</td>
                    <td>{run.logs_processed}</td>
                    <td style={{ color: run.high_priority_count > 0 ? 'var(--priority-high)' : 'var(--text-tertiary)' }}>{run.high_priority_count}</td>
                    <td style={{ color: run.medium_priority_count > 0 ? 'var(--priority-medium)' : 'var(--text-tertiary)' }}>{run.medium_priority_count}</td>
                    <td>{run.low_priority_count}</td>
                    <td>{run.emails_sent}</td>
                    <td style={{ fontSize: 12 }}>{formatDate(run.started_at)}</td>
                    <td style={{ fontSize: 12 }}>{formatDate(run.completed_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
