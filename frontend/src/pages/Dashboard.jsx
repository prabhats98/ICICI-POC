/**
 * Dashboard Page — Management overview with P1/P2/P3 stats, pipeline controls,
 * service-wise breakdown, live incident table, and run history.
 * Now includes Simulate Logs button for instant end-to-end testing.
 */

import { useEffect, useState } from 'react';
import { getDashboardSummary, getIncidents, getAgentHistory, togglePipeline, triggerManualRun } from '../services/api';
import useAppStore from '../store/useAppStore';

const SERVICE_LABELS = {
  'azure-front-door': { label: 'Front Door', icon: '🌐', color: '#6366f1' },
  'azure-app-gateway': { label: 'App Gateway', icon: '🔀', color: '#8b5cf6' },
  'azure-apim': { label: 'API Management', icon: '⚙️', color: '#06b6d4' },
  'azure-vm': { label: 'Virtual Machine', icon: '🖥️', color: '#10b981' },
};

export default function Dashboard() {
  const { dashboard, setDashboard, pipelineEnabled, setPipelineEnabled } = useAppStore();
  const [recentIncidents, setRecentIncidents] = useState([]);
  const [recentRuns, setRecentRuns] = useState([]);
  const [running, setRunning] = useState(false);
  const [lastLogAt, setLastLogAt] = useState(null);

  useEffect(() => {
    loadDashboard();
    const interval = setInterval(loadDashboard, 15000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboard = async () => {
    try {
      const [dashRes, incRes, runRes] = await Promise.all([
        getDashboardSummary(),
        getIncidents({ page_size: 8 }),
        getAgentHistory({ page_size: 5 }),
      ]);
      setDashboard(dashRes.data);
      setPipelineEnabled(dashRes.data?.pipeline?.enabled ?? true);
      setRecentIncidents(incRes.data.items || []);
      setRecentRuns(runRes.data.items || []);
      // Track last log ingested time
      const items = incRes.data.items || [];
      if (items.length > 0) setLastLogAt(items[0].created_at || items[0].updated_at);
    } catch (err) {
      console.error('Dashboard load error:', err);
    }
  };

  const handleToggle = async () => {
    setToggling(true);
    try {
      const res = await togglePipeline(!pipelineEnabled);
      setPipelineEnabled(res.data.enabled);
    } catch (err) {
      console.error('Toggle error:', err);
    } finally {
      setToggling(false);
    }
  };

  const handleManualRun = async () => {
    setRunning(true);
    try {
      await triggerManualRun();
      setTimeout(loadDashboard, 3000);
    } catch (err) {
      console.error('Manual run error:', err);
    } finally {
      setTimeout(() => setRunning(false), 2000);
    }
  };


  const stats = [
    { label: 'Total Incidents', value: dashboard?.incidents?.total || 0, icon: '📋', color: 'cyan' },
    { label: 'Open Incidents', value: dashboard?.incidents?.open || 0, icon: '⚠️', color: 'amber' },
    { label: 'P1 Critical', value: dashboard?.incidents?.p1 || 0, icon: '🔴', color: 'rose' },
    { label: 'P2 Warning', value: dashboard?.incidents?.p2 || 0, icon: '🟡', color: 'amber' },
    { label: 'P3 Info', value: dashboard?.incidents?.p3 || 0, icon: '🟢', color: 'emerald' },
    { label: 'Resolved', value: dashboard?.incidents?.resolved || 0, icon: '✅', color: 'emerald' },
    { label: 'Emails Sent', value: dashboard?.incidents?.emails_sent || 0, icon: '📧', color: 'indigo' },
    { label: 'Pipeline Runs', value: dashboard?.pipeline?.total_runs || 0, icon: '🔄', color: 'blue' },
  ];

  const formatDate = (dateStr) => {
    if (!dateStr || dateStr === 'None') return 'N/A';
    return new Date(dateStr).toLocaleString();
  };

  const priorityBadge = (p) => {
    const map = { P1: 'high', P2: 'medium', P3: 'low' };
    return map[p] || 'low';
  };

  const byService = dashboard?.incidents?.by_service || {};
  const totalLogs = dashboard?.logs?.total || 0;
  const rawLogs = dashboard?.raw_logs?.total || 0;

  return (
    <div className="page-content">
      <div className="page-header animate-in">
        <h1>Dashboard</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          {/* Live Source Badge */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.35)',
            borderRadius: 20, padding: '5px 14px',
          }}>
            <span style={{
              width: 8, height: 8, borderRadius: '50%', background: '#10b981',
              boxShadow: '0 0 8px #10b981',
              animation: 'pulse 2s infinite',
              display: 'inline-block',
            }} />
            <span style={{ fontSize: 12, fontWeight: 700, color: '#10b981', letterSpacing: '0.3px' }}>
              LIVE · Real Azure Logs
            </span>
          </div>

          {/* Last log received */}
          {lastLogAt && (
            <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
              Last log: {formatDate(lastLogAt)}
            </span>
          )}

          {/* Pipeline toggle */}
          <div
            className="pipeline-toggle"
            style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}
            onClick={handleToggle}
          >
            <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>Pipeline</span>
            <div className={`toggle-switch ${pipelineEnabled ? 'active' : ''}`} style={{
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

          <button className="btn btn-primary btn-sm" onClick={handleManualRun} disabled={!pipelineEnabled || running}>
            {running ? '⟳ Running…' : '▶ Run Pipeline'}
          </button>

          <span style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>
            Next: {dashboard?.pipeline?.next_run_at ? formatDate(dashboard.pipeline.next_run_at) : 'Not scheduled'}
          </span>
        </div>
      </div>

      {/* Simulate Result Banner */}
      {simResult && (
        <div style={{
          background: simResult.error ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)',
          border: `1px solid ${simResult.error ? '#ef4444' : '#10b981'}`,
          borderRadius: 10, padding: '12px 20px', marginBottom: 20,
          color: simResult.error ? '#ef4444' : '#10b981',
          animation: 'slideIn 0.3s ease',
        }}>
          {simResult.error ? (
            `❌ ${simResult.error}`
          ) : (
            `✅ ${simResult.message} — Front Door: ${simResult.per_source?.['azure-front-door'] || 0}, App Gateway: ${simResult.per_source?.['azure-app-gateway'] || 0}, APIM: ${simResult.per_source?.['azure-apim'] || 0}`
          )}
        </div>
      )}

      {/* Stat Cards */}
      <div className="stats-grid">
        {stats.map((stat, i) => (
          <div key={stat.label} className={`stat-card animate-in animate-in-delay-${i % 4 + 1}`}>
            <div className={`stat-icon ${stat.color}`}>{stat.icon}</div>
            <div className="stat-info">
              <span className="stat-label">{stat.label}</span>
              <span className="stat-value">{typeof stat.value === 'number' ? stat.value.toLocaleString() : stat.value}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Service-Wise Stats */}
      <div className="section animate-in animate-in-delay-2" style={{ marginTop: 24 }}>
        <div className="section-title">☁️ Azure Service-Wise Incident Summary</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {['azure-front-door', 'azure-app-gateway', 'azure-apim'].map(svcKey => {
            const meta = SERVICE_LABELS[svcKey];
            const count = byService[svcKey] || 0;
            const logCount = dashboard?.raw_logs?.[svcKey] || '—';
            return (
              <div key={svcKey} className="glass-card" style={{
                display: 'flex', flexDirection: 'column', gap: 12, padding: '20px 24px',
                borderLeft: `3px solid ${meta.color}`,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 24 }}>{meta.icon}</span>
                  <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{meta.label}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                  <div>
                    <div style={{ fontSize: 32, fontWeight: 800, color: meta.color }}>{count}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>Total Incidents</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-secondary)' }}>{rawLogs}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>Raw Logs</div>
                  </div>
                </div>
                <div style={{
                  display: 'flex', justifyContent: 'space-between',
                  padding: '8px 0', borderTop: '1px solid var(--border-subtle)',
                  fontSize: 12,
                }}>
                  <span style={{ color: 'var(--text-tertiary)' }}>
                    {totalLogs} processed logs
                  </span>
                  <span style={{ color: meta.color }}>{count > 0 ? `${count} incident${count > 1 ? 's' : ''}` : 'Healthy'}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Live Incident Table */}
      <div className="section animate-in animate-in-delay-2">
        <div className="section-title">⚠️ Live Incident Feed</div>
        <div className="glass-card" style={{ padding: 0, overflow: 'auto' }}>
          {recentIncidents.length === 0 ? (
            <div className="empty-state" style={{ padding: '32px' }}>
              <div className="empty-state-icon">✅</div>
              <div className="empty-state-title">No incidents</div>
              <div className="empty-state-text">Click "Simulate Logs" → "Run Pipeline" to generate incidents</div>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Title</th>
                  <th>Category</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Notified</th>
                  <th>Time</th>
                  <th>Resolution Snippet</th>
                </tr>
              </thead>
              <tbody>
                {recentIncidents.map((inc) => (
                  <tr key={inc.id}>
                    <td style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
                      {SERVICE_LABELS[inc.source_service]?.icon || '☁️'}{' '}
                      {SERVICE_LABELS[inc.source_service]?.label || inc.source_service || '—'}
                    </td>
                    <td style={{ maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {inc.title}
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{inc.category || '—'}</td>
                    <td>
                      <span className={`priority-badge ${priorityBadge(inc.priority)}`}>
                        {inc.priority}
                      </span>
                    </td>
                    <td>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className={`status-dot ${inc.status === 'OPEN' ? 'error' : inc.status === 'IN_PROGRESS' ? 'running' : 'success'}`}></span>
                        <span style={{ fontSize: 12 }}>{inc.status?.replace('_', ' ')}</span>
                      </span>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      {inc.email_sent ? '📧 Yes' : <span style={{ color: 'var(--text-tertiary)' }}>—</span>}
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--text-tertiary)', whiteSpace: 'nowrap' }}>
                      {formatDate(inc.created_at)}
                    </td>
                    <td style={{ fontSize: 12, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {inc.ai_solution ? inc.ai_solution.substring(0, 80) + '...' : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Run History */}
      <div className="section animate-in animate-in-delay-3">
        <div className="section-title">🔄 Recent Pipeline Runs</div>
        <div className="glass-card" style={{ padding: 0, overflow: 'auto' }}>
          {recentRuns.length === 0 ? (
            <div className="empty-state" style={{ padding: '32px' }}>
              <div className="empty-state-icon">🚀</div>
              <div className="empty-state-title">No runs yet</div>
              <div className="empty-state-text">Click "Run Pipeline" or "Simulate Logs" to start</div>
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
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((run) => (
                  <tr key={run.id}>
                    <td>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className={`status-dot ${run.status === 'RUNNING' ? 'running' : run.status === 'SUCCESS' ? 'success' : run.status === 'FAILED' ? 'error' : 'idle'}`}></span>
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
                    <td style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                      {formatDate(run.started_at)}
                    </td>
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
