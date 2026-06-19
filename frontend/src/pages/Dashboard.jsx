/**
 * Dashboard Page — Management overview with P1/P2/P3 stats, pipeline controls,
 * live incident table, and run history.
 */

import { useEffect, useState } from 'react';
import { getDashboardSummary, getIncidents, getAgentHistory, togglePipeline, triggerManualRun } from '../services/api';
import useAppStore from '../store/useAppStore';

export default function Dashboard() {
  const { dashboard, setDashboard, pipelineEnabled, setPipelineEnabled } = useAppStore();
  const [recentIncidents, setRecentIncidents] = useState([]);
  const [recentRuns, setRecentRuns] = useState([]);
  const [toggling, setToggling] = useState(false);

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
    try {
      await triggerManualRun();
    } catch (err) {
      console.error('Manual run error:', err);
    }
  };

  const stats = [
    { label: 'Total Incidents', value: dashboard?.incidents?.total || 0, icon: '📋', color: 'cyan' },
    { label: 'Open Incidents', value: dashboard?.incidents?.open || 0, icon: '⚠️', color: 'amber' },
    { label: 'P1 Critical', value: dashboard?.incidents?.p1 || 0, icon: '🔴', color: 'rose' },
    { label: 'P2 Warning', value: dashboard?.incidents?.p2 || 0, icon: '🟡', color: 'amber' },
    { label: 'P3 Info', value: dashboard?.incidents?.p3 || 0, icon: '🟢', color: 'emerald' },
    { label: 'Resolved', value: dashboard?.incidents?.resolved || 0, icon: '✅', color: 'emerald' },
    { label: 'Avg Resolution', value: dashboard?.incidents?.avg_resolution_minutes ? `${dashboard.incidents.avg_resolution_minutes}m` : '—', icon: '⏱️', color: 'indigo' },
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

  return (
    <div className="page-content">
      <div className="page-header animate-in">
        <h1>Dashboard</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
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

          <button className="btn btn-primary btn-sm" onClick={handleManualRun} disabled={!pipelineEnabled}>
            ▶ Run Pipeline
          </button>

          <span style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>
            Next: {dashboard?.pipeline?.next_run_at ? formatDate(dashboard.pipeline.next_run_at) : 'Not scheduled'}
          </span>
        </div>
      </div>

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

      {/* Live Incident Table */}
      <div className="section animate-in animate-in-delay-2">
        <div className="section-title">⚠️ Live Incident Table</div>
        <div className="glass-card" style={{ padding: 0, overflow: 'auto' }}>
          {recentIncidents.length === 0 ? (
            <div className="empty-state" style={{ padding: '32px' }}>
              <div className="empty-state-icon">✅</div>
              <div className="empty-state-title">No incidents</div>
              <div className="empty-state-text">Run the pipeline to detect issues</div>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Title</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Time</th>
                  <th>Fix</th>
                </tr>
              </thead>
              <tbody>
                {recentIncidents.map((inc) => (
                  <tr key={inc.id}>
                    <td style={{ fontSize: 12 }}>{inc.source_service || inc.category || '—'}</td>
                    <td style={{ maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {inc.title}
                    </td>
                    <td>
                      <span className={`priority-badge ${priorityBadge(inc.priority)}`}>
                        {inc.priority}
                      </span>
                    </td>
                    <td>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className={`status-dot ${inc.status === 'OPEN' ? 'error' : inc.status === 'IN_PROGRESS' ? 'running' : 'success'}`}></span>
                        <span style={{ fontSize: 12 }}>{inc.status.replace('_', ' ')}</span>
                      </span>
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
              <div className="empty-state-text">Click "Run Pipeline" to start</div>
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
