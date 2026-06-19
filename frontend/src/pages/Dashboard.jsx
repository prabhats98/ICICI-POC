/**
 * Dashboard Page - Overview with stat cards, recent incidents, and agent activity.
 */

import { useEffect, useState } from 'react';
import { getDashboardSummary, getIncidents, getAgentHistory } from '../services/api';
import useAppStore from '../store/useAppStore';

export default function Dashboard() {
  const { dashboard, setDashboard, isDashboardLoading, setDashboardLoading } = useAppStore();
  const [recentIncidents, setRecentIncidents] = useState([]);
  const [recentRuns, setRecentRuns] = useState([]);

  useEffect(() => {
    loadDashboard();
    const interval = setInterval(loadDashboard, 15000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboard = async () => {
    try {
      const [dashRes, incRes, runRes] = await Promise.all([
        getDashboardSummary(),
        getIncidents({ page_size: 5 }),
        getAgentHistory({ page_size: 5 }),
      ]);
      setDashboard(dashRes.data);
      setRecentIncidents(incRes.data.items || []);
      setRecentRuns(runRes.data.items || []);
    } catch (err) {
      console.error('Dashboard load error:', err);
      setDashboardLoading(false);
    }
  };

  const stats = [
    { label: 'Raw Logs', value: dashboard?.raw_logs?.total || 0, icon: '📦', color: 'cyan' },
    { label: 'Pending Segregation', value: dashboard?.raw_logs?.pending_segregation || 0, icon: '⏳', color: 'amber' },
    { label: 'Segregated Logs', value: dashboard?.logs?.total || 0, icon: '📊', color: 'indigo' },
    { label: 'Errors Detected', value: dashboard?.logs?.errors || 0, icon: '🔴', color: 'rose' },
    { label: 'Active Incidents', value: dashboard?.incidents?.open || 0, icon: '⚠️', color: 'blue' },
    { label: 'High Priority', value: dashboard?.incidents?.high_priority || 0, icon: '🚨', color: 'rose' },
    { label: 'Medium Priority', value: dashboard?.incidents?.medium_priority || 0, icon: '🟡', color: 'amber' },
    { label: 'Pipeline Runs', value: dashboard?.pipeline?.total_runs || 0, icon: '🔄', color: 'emerald' },
  ];

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="page-content">
      <div className="page-header animate-in">
        <h1>Dashboard</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>
            Next run: {dashboard?.pipeline?.next_run_at ? formatDate(dashboard.pipeline.next_run_at) : 'Not scheduled'}
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
              <span className="stat-value">{stat.value.toLocaleString()}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Two-column layout */}
      <div className="grid-2">
        {/* Recent Incidents */}
        <div className="section animate-in animate-in-delay-2">
          <div className="section-title">⚠️ Recent Incidents</div>
          <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
            {recentIncidents.length === 0 ? (
              <div className="empty-state" style={{ padding: '32px' }}>
                <div className="empty-state-icon">✅</div>
                <div className="empty-state-title">No incidents</div>
                <div className="empty-state-text">Run the pipeline to detect issues</div>
              </div>
            ) : (
              recentIncidents.map((inc) => (
                <div key={inc.id} className="incident-card" style={{ borderRadius: 0, border: 'none', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div className="incident-card-header">
                    <span className="incident-card-title">{inc.title}</span>
                    <span className={`priority-badge ${inc.priority.toLowerCase()}`}>
                      {inc.priority}
                    </span>
                  </div>
                  <div className="incident-card-body">
                    {inc.description?.substring(0, 120)}...
                  </div>
                  <div className="incident-card-meta">
                    <span>📁 {inc.category || 'Uncategorized'}</span>
                    <span>🕐 {formatDate(inc.created_at)}</span>
                    {inc.email_sent && <span>📧 Email sent</span>}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent Pipeline Runs */}
        <div className="section animate-in animate-in-delay-3">
          <div className="section-title">🔄 Recent Pipeline Runs</div>
          <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
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
                    <th>Incidents</th>
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
                      <td>{run.incidents_created}</td>
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
    </div>
  );
}
