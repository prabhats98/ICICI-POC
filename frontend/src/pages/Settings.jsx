/**
 * Settings Page — Pipeline configuration, agent status, and run history.
 */

import { useEffect, useState } from 'react';
import { getAgentStatus, getAgentHistory, togglePipeline, getPipelineStatus } from '../services/api';
import useAppStore from '../store/useAppStore';

export default function Settings() {
  const [status, setStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const { pipelineEnabled, setPipelineEnabled } = useAppStore();

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const [statusRes, historyRes, pipelineRes] = await Promise.all([
        getAgentStatus(),
        getAgentHistory({ page_size: 10 }),
        getPipelineStatus(),
      ]);
      setStatus(statusRes.data);
      setHistory(historyRes.data.items || []);
      setPipelineEnabled(pipelineRes.data?.pipeline_enabled ?? true);
    } catch (err) {
      console.error('Settings load error:', err);
    }
  };

  const handleToggle = async () => {
    try {
      const res = await togglePipeline(!pipelineEnabled);
      setPipelineEnabled(res.data.enabled);
    } catch (err) {
      console.error('Toggle error:', err);
    }
  };

  const formatDate = (d) => d && d !== 'None' ? new Date(d).toLocaleString() : 'N/A';

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
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Pipeline Enabled</span>
              <div
                style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}
                onClick={handleToggle}
              >
                <div style={{
                  width: 40, height: 22, borderRadius: 11, position: 'relative',
                  background: pipelineEnabled ? 'var(--accent-emerald)' : 'var(--bg-tertiary)',
                  transition: 'background 0.3s', border: '1px solid var(--border-default)',
                }}>
                  <div style={{
                    width: 16, height: 16, borderRadius: '50%', background: '#fff',
                    position: 'absolute', top: 2,
                    left: pipelineEnabled ? 21 : 3,
                    transition: 'left 0.3s',
                  }} />
                </div>
                <span style={{ fontSize: 12, fontWeight: 600, color: pipelineEnabled ? 'var(--accent-emerald)' : 'var(--text-tertiary)' }}>
                  {pipelineEnabled ? 'ON' : 'OFF'}
                </span>
              </div>
            </div>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-tertiary)', display: 'block', marginBottom: 4 }}>Scheduler Interval</label>
              <input className="header-search" type="text" value="Every 6 hours" readOnly style={{ width: '100%' }} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-tertiary)', display: 'block', marginBottom: 4 }}>Gemini Model</label>
              <input className="header-search" type="text" value="gemini-2.5-flash" readOnly style={{ width: '100%' }} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-tertiary)', display: 'block', marginBottom: 4 }}>Database</label>
              <input className="header-search" type="text" value="Azure Database for PostgreSQL" readOnly style={{ width: '100%' }} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-tertiary)', display: 'block', marginBottom: 4 }}>Log Sources</label>
              <input className="header-search" type="text" value="Front Door, App Gateway, APIM, VM" readOnly style={{ width: '100%' }} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-tertiary)', display: 'block', marginBottom: 4 }}>Notification Channel</label>
              <input className="header-search" type="text" value="SMTP (configurable via .env)" readOnly style={{ width: '100%' }} />
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
                      <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Incidents</span>
                      <span style={{ fontSize: 13 }}>{status.last_run.incidents_created}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>P1 / P2 / P3</span>
                      <span style={{ fontSize: 13 }}>
                        <span style={{ color: 'var(--priority-high)' }}>{status.last_run.p1_count}</span>
                        {' / '}
                        <span style={{ color: 'var(--priority-medium)' }}>{status.last_run.p2_count}</span>
                        {' / '}
                        <span>{status.last_run.p3_count}</span>
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Emails Sent</span>
                      <span style={{ fontSize: 13 }}>{status.last_run.emails_sent}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Duration</span>
                      <span style={{ fontSize: 13 }}>{status.last_run.duration_seconds ? `${status.last_run.duration_seconds}s` : '—'}</span>
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
                  <th>P1</th>
                  <th>P2</th>
                  <th>P3</th>
                  <th>Emails</th>
                  <th>Duration</th>
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
                    <td style={{ color: run.p1_count > 0 ? 'var(--priority-high)' : 'var(--text-tertiary)' }}>{run.p1_count}</td>
                    <td style={{ color: run.p2_count > 0 ? 'var(--priority-medium)' : 'var(--text-tertiary)' }}>{run.p2_count}</td>
                    <td>{run.p3_count}</td>
                    <td>{run.emails_sent}</td>
                    <td style={{ fontSize: 12 }}>{run.duration_seconds ? `${run.duration_seconds}s` : '—'}</td>
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
