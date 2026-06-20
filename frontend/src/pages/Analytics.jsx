/**
 * Analytics Page — Incident trends, service breakdown, error distribution,
 * notification history, top recurring issues, and pipeline run history.
 */

import { useEffect, useState, useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, ArcElement, Tooltip, Legend, Filler,
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import {
  getIncidentTrend, getServiceBreakdown, getErrorDistribution,
  getNotificationHistory, getTopIssues, getLogVolume, getPipelineRuns,
} from '../services/api';

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, ArcElement, Tooltip, Legend, Filler
);

const COLORS = {
  p1: '#ef4444',
  p2: '#f59e0b',
  p3: '#10b981',
  info: '#06b6d4',
  warning: '#f59e0b',
  error: '#ef4444',
  critical: '#dc2626',
  frontdoor: '#6366f1',
  appgateway: '#8b5cf6',
  apim: '#06b6d4',
};

const CHART_OPTIONS_BASE = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: { color: '#94a3b8', font: { size: 12 } },
    },
  },
  scales: {
    x: {
      ticks: { color: '#64748b', maxRotation: 0 },
      grid: { color: 'rgba(255,255,255,0.05)' },
    },
    y: {
      ticks: { color: '#64748b' },
      grid: { color: 'rgba(255,255,255,0.05)' },
      beginAtZero: true,
    },
  },
};

function StatCard({ label, value, sub, color = 'cyan', icon }) {
  return (
    <div className="stat-card" style={{ flex: 1, minWidth: 140 }}>
      <div className={`stat-icon ${color}`}>{icon}</div>
      <div className="stat-info">
        <span className="stat-label">{label}</span>
        <span className="stat-value">{value ?? '—'}</span>
        {sub && <span style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>{sub}</span>}
      </div>
    </div>
  );
}

function SectionTitle({ children }) {
  return (
    <div className="section-title" style={{ marginBottom: 16 }}>{children}</div>
  );
}

export default function Analytics() {
  const [trend, setTrend] = useState(null);
  const [services, setServices] = useState([]);
  const [errorDist, setErrorDist] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [topIssues, setTopIssues] = useState([]);
  const [logVolume, setLogVolume] = useState(null);
  const [pipelineRuns, setPipelineRuns] = useState([]);
  const [trendDays, setTrendDays] = useState(7);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAll();
  }, [trendDays]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [trendRes, svcRes, distRes, notifRes, issueRes, volRes, runsRes] = await Promise.all([
        getIncidentTrend(trendDays),
        getServiceBreakdown(),
        getErrorDistribution(),
        getNotificationHistory(30),
        getTopIssues(8),
        getLogVolume(trendDays),
        getPipelineRuns(15),
      ]);
      setTrend(trendRes.data);
      setServices(svcRes.data.services || []);
      setErrorDist(distRes.data);
      setNotifications(notifRes.data.notifications || []);
      setTopIssues(issueRes.data.top_issues || []);
      setLogVolume(volRes.data);
      setPipelineRuns(runsRes.data.runs || []);
    } catch (err) {
      console.error('Analytics load error:', err);
    } finally {
      setLoading(false);
    }
  };

  // ---- Chart Data ----

  const incidentTrendData = trend ? {
    labels: trend.data.map(d => d.date.slice(5)), // MM-DD
    datasets: [
      {
        label: 'P1 Critical',
        data: trend.data.map(d => d.P1),
        borderColor: COLORS.p1,
        backgroundColor: 'rgba(239,68,68,0.15)',
        fill: true,
        tension: 0.4,
      },
      {
        label: 'P2 Warning',
        data: trend.data.map(d => d.P2),
        borderColor: COLORS.p2,
        backgroundColor: 'rgba(245,158,11,0.12)',
        fill: true,
        tension: 0.4,
      },
      {
        label: 'P3 Info',
        data: trend.data.map(d => d.P3),
        borderColor: COLORS.p3,
        backgroundColor: 'rgba(16,185,129,0.1)',
        fill: true,
        tension: 0.4,
      },
    ],
  } : null;

  const serviceChartData = services.length > 0 ? {
    labels: services.map(s => s.service?.replace('azure-', 'Azure ').replace('-', ' ') || s.service),
    datasets: [
      {
        label: 'P1',
        data: services.map(s => s.P1 || 0),
        backgroundColor: COLORS.p1,
        borderRadius: 4,
      },
      {
        label: 'P2',
        data: services.map(s => s.P2 || 0),
        backgroundColor: COLORS.p2,
        borderRadius: 4,
      },
      {
        label: 'P3',
        data: services.map(s => s.P3 || 0),
        backgroundColor: COLORS.p3,
        borderRadius: 4,
      },
    ],
  } : null;

  const errorDistData = errorDist?.distribution?.length > 0 ? {
    labels: errorDist.distribution.map(d => d.category),
    datasets: [{
      data: errorDist.distribution.map(d => d.count),
      backgroundColor: [
        '#6366f1', '#8b5cf6', '#06b6d4', '#10b981',
        '#f59e0b', '#ef4444', '#ec4899', '#84cc16',
      ],
      borderWidth: 0,
      hoverOffset: 8,
    }],
  } : null;

  const logVolumeData = logVolume ? {
    labels: logVolume.data.map(d => d.date.slice(5)),
    datasets: [
      {
        label: 'ERROR',
        data: logVolume.data.map(d => d.ERROR || 0),
        backgroundColor: 'rgba(239,68,68,0.7)',
        borderRadius: 3,
      },
      {
        label: 'WARNING',
        data: logVolume.data.map(d => d.WARNING || 0),
        backgroundColor: 'rgba(245,158,11,0.7)',
        borderRadius: 3,
      },
      {
        label: 'INFO',
        data: logVolume.data.map(d => d.INFO || 0),
        backgroundColor: 'rgba(6,182,212,0.5)',
        borderRadius: 3,
      },
    ],
  } : null;

  const formatDate = (s) => s ? new Date(s).toLocaleString() : '—';
  const priorityBadge = (p) => ({ P1: 'high', P2: 'medium', P3: 'low' }[p] || 'low');

  const totalIncidents = services.reduce((s, sv) => s + (sv.total || 0), 0);
  const totalNotifs = notifications.length;
  const successRuns = pipelineRuns.filter(r => r.status === 'SUCCESS').length;

  return (
    <div className="page-content">
      <div className="page-header animate-in">
        <h1>Analytics</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <select
            value={trendDays}
            onChange={e => setTrendDays(Number(e.target.value))}
            style={{
              background: 'var(--bg-secondary)', color: 'var(--text-primary)',
              border: '1px solid var(--border-default)', borderRadius: 8,
              padding: '6px 12px', fontSize: 13, cursor: 'pointer',
            }}
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
          </select>
          <button className="btn btn-secondary btn-sm" onClick={loadAll} disabled={loading}>
            {loading ? '⟳ Loading…' : '↻ Refresh'}
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="stats-grid animate-in animate-in-delay-1" style={{ marginBottom: 24 }}>
        <StatCard label="Total Incidents" value={totalIncidents} icon="📋" color="cyan" />
        <StatCard label="Notifications Sent" value={totalNotifs} icon="📧" color="indigo" sub="via ACS Email" />
        <StatCard label="Successful Runs" value={successRuns} icon="✅" color="emerald" sub={`of ${pipelineRuns.length} runs`} />
        <StatCard label="Services Monitored" value={services.length || 3} icon="☁️" color="blue" sub="Front Door · App GW · APIM" />
        <StatCard label="Error Logs" value={errorDist?.distribution?.find(d => d.category === 'Availability')?.count || 0} icon="⚠️" color="amber" />
        <StatCard label="Security Issues" value={errorDist?.distribution?.find(d => d.category === 'Security')?.count || 0} icon="🛡️" color="rose" />
        <StatCard label="Performance Issues" value={errorDist?.distribution?.find(d => d.category === 'Performance')?.count || 0} icon="📈" color="purple" />
        <StatCard label="API Issues" value={errorDist?.distribution?.find(d => d.category === 'API')?.count || 0} icon="🔌" color="cyan" />
      </div>

      {/* Row 1: Incident Trend + Log Volume */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        <div className="glass-card animate-in animate-in-delay-1">
          <SectionTitle>📈 Incident Trend (Last {trendDays} days)</SectionTitle>
          <div style={{ height: 240 }}>
            {incidentTrendData ? (
              <Line data={incidentTrendData} options={CHART_OPTIONS_BASE} />
            ) : (
              <div className="empty-state"><div className="empty-state-icon">📊</div><div className="empty-state-title">No trend data yet</div><div className="empty-state-text">Run the pipeline to generate incidents</div></div>
            )}
          </div>
        </div>

        <div className="glass-card animate-in animate-in-delay-2">
          <SectionTitle>📊 Log Volume by Level</SectionTitle>
          <div style={{ height: 240 }}>
            {logVolumeData ? (
              <Bar data={logVolumeData} options={{ ...CHART_OPTIONS_BASE, scales: { ...CHART_OPTIONS_BASE.scales, x: { ...CHART_OPTIONS_BASE.scales.x, stacked: true }, y: { ...CHART_OPTIONS_BASE.scales.y, stacked: true } } }} />
            ) : (
              <div className="empty-state"><div className="empty-state-icon">📊</div><div className="empty-state-title">No log data yet</div></div>
            )}
          </div>
        </div>
      </div>

      {/* Row 2: Service Breakdown + Error Distribution */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: 20, marginBottom: 20 }}>
        <div className="glass-card animate-in animate-in-delay-2">
          <SectionTitle>☁️ Service-wise Incident Breakdown</SectionTitle>
          {services.length > 0 ? (
            <>
              <div style={{ height: 220 }}>
                {serviceChartData && (
                  <Bar data={serviceChartData} options={{ ...CHART_OPTIONS_BASE, plugins: { ...CHART_OPTIONS_BASE.plugins, legend: { ...CHART_OPTIONS_BASE.plugins.legend, position: 'top' } } }} />
                )}
              </div>
              <div style={{ display: 'flex', gap: 12, marginTop: 16, flexWrap: 'wrap' }}>
                {services.map(svc => (
                  <div key={svc.service} style={{
                    flex: 1, minWidth: 160, background: 'rgba(255,255,255,0.03)',
                    borderRadius: 8, padding: '12px 16px', border: '1px solid var(--border-subtle)',
                  }}>
                    <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 6 }}>
                      {svc.service?.replace('azure-', '').replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </div>
                    <div style={{ display: 'flex', gap: 12 }}>
                      <span style={{ color: '#ef4444', fontWeight: 700, fontSize: 18 }}>{svc.P1 || 0}</span>
                      <span style={{ color: '#f59e0b', fontWeight: 700, fontSize: 18 }}>{svc.P2 || 0}</span>
                      <span style={{ color: '#10b981', fontWeight: 700, fontSize: 18 }}>{svc.P3 || 0}</span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>P1 · P2 · P3</div>
                    <div style={{ fontSize: 12, marginTop: 8 }}>
                      <span style={{ color: '#ef4444' }}>{svc.open || 0} open</span>
                      {' · '}
                      <span style={{ color: '#10b981' }}>{svc.resolved || 0} resolved</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">☁️</div>
              <div className="empty-state-title">No service data</div>
              <div className="empty-state-text">Run the pipeline after simulating logs to see service breakdown</div>
            </div>
          )}
        </div>

        <div className="glass-card animate-in animate-in-delay-3">
          <SectionTitle>🥧 Incident Category Distribution</SectionTitle>
          <div style={{ height: 220 }}>
            {errorDistData ? (
              <Doughnut data={errorDistData} options={{
                ...CHART_OPTIONS_BASE,
                scales: undefined,
                plugins: {
                  ...CHART_OPTIONS_BASE.plugins,
                  legend: { labels: { color: '#94a3b8', font: { size: 11 }, boxWidth: 12 }, position: 'bottom' },
                },
              }} />
            ) : (
              <div className="empty-state"><div className="empty-state-icon">🥧</div><div className="empty-state-title">No category data</div></div>
            )}
          </div>
        </div>
      </div>

      {/* Row 3: Top Issues + Notification History */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        <div className="glass-card animate-in animate-in-delay-3">
          <SectionTitle>🔁 Top Recurring Issues</SectionTitle>
          {topIssues.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {topIssues.map((issue, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '10px 14px', background: 'rgba(255,255,255,0.03)',
                  borderRadius: 8, border: '1px solid var(--border-subtle)',
                }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: '50%',
                    background: `hsl(${220 + i * 30}, 70%, 55%)`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 12, fontWeight: 700, flexShrink: 0,
                  }}>{i + 1}</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {issue.title}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>
                      {issue.category} · {issue.source_service?.replace('azure-', '') || 'unknown'} · {issue.last_seen ? new Date(issue.last_seen).toLocaleDateString() : '—'}
                    </div>
                  </div>
                  <div style={{
                    background: 'rgba(99,102,241,0.2)', color: '#818cf8',
                    borderRadius: 12, padding: '2px 10px', fontSize: 12, fontWeight: 700, flexShrink: 0,
                  }}>
                    ×{issue.count}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state"><div className="empty-state-icon">🔁</div><div className="empty-state-title">No recurring issues yet</div></div>
          )}
        </div>

        <div className="glass-card animate-in animate-in-delay-4">
          <SectionTitle>📧 Notification History</SectionTitle>
          {notifications.length > 0 ? (
            <div style={{ overflowY: 'auto', maxHeight: 340 }}>
              <table className="data-table" style={{ fontSize: 12 }}>
                <thead>
                  <tr>
                    <th>Priority</th>
                    <th>Incident</th>
                    <th>Sent At</th>
                    <th>Recipient</th>
                  </tr>
                </thead>
                <tbody>
                  {notifications.map(n => (
                    <tr key={n.incident_id}>
                      <td><span className={`priority-badge ${priorityBadge(n.priority)}`}>{n.priority}</span></td>
                      <td style={{ maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{n.title}</td>
                      <td style={{ color: 'var(--text-tertiary)' }}>{formatDate(n.email_sent_at)}</td>
                      <td style={{ color: 'var(--text-tertiary)' }}>{n.email_recipient || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">📧</div>
              <div className="empty-state-title">No notifications yet</div>
              <div className="empty-state-text">Notifications will appear here after P1/P2 incidents are processed</div>
            </div>
          )}
        </div>
      </div>

      {/* Pipeline Run History */}
      <div className="glass-card animate-in animate-in-delay-4" style={{ marginBottom: 24 }}>
        <SectionTitle>🔄 Pipeline Run History</SectionTitle>
        {pipelineRuns.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table" style={{ fontSize: 12 }}>
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Trigger</th>
                  <th>Logs</th>
                  <th>Incidents</th>
                  <th>P1</th>
                  <th>P2</th>
                  <th>P3</th>
                  <th>Emails</th>
                  <th>Duration</th>
                  <th>Sources</th>
                  <th>Started</th>
                </tr>
              </thead>
              <tbody>
                {pipelineRuns.map(run => (
                  <tr key={run.id}>
                    <td>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className={`status-dot ${run.status === 'RUNNING' ? 'running' : run.status === 'SUCCESS' ? 'success' : 'error'}`}></span>
                        {run.status}
                      </span>
                    </td>
                    <td>{run.trigger_type}</td>
                    <td>{run.logs_processed ?? '—'}</td>
                    <td>{run.incidents_created ?? '—'}</td>
                    <td style={{ color: run.p1_count > 0 ? '#ef4444' : 'var(--text-tertiary)' }}>{run.p1_count ?? 0}</td>
                    <td style={{ color: run.p2_count > 0 ? '#f59e0b' : 'var(--text-tertiary)' }}>{run.p2_count ?? 0}</td>
                    <td>{run.p3_count ?? 0}</td>
                    <td>{run.emails_sent ?? 0}</td>
                    <td style={{ color: 'var(--text-tertiary)' }}>{run.duration_seconds ? `${run.duration_seconds}s` : '—'}</td>
                    <td style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>
                      {run.sources_collected ? Object.entries(run.sources_collected).map(([k,v]) => `${k.replace('azure-','')}: ${v}`).join(', ') : '—'}
                    </td>
                    <td style={{ color: 'var(--text-tertiary)' }}>{formatDate(run.started_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state"><div className="empty-state-icon">🚀</div><div className="empty-state-title">No runs yet</div></div>
        )}
      </div>
    </div>
  );
}
