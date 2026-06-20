/**
 * Dashboard Page — Enterprise-grade Grafana-inspired observability dashboard.
 * Features KPI stat cards, stacked area charts, doughnut charts, horizontal
 * bar charts, live incident feed, and pipeline run history — all wrapped in
 * Grafana-style panel chrome with dark theme.
 */

import { useEffect, useState, useCallback } from 'react';
import {
  getDashboardSummary,
  getIncidents,
  getAgentHistory,
  togglePipeline,
  triggerManualRun,
  getIncidentTrend,
  getLogVolume,
  getErrorDistribution,
  getServiceBreakdown,
  getTopIssues,
  getMTTR,
} from '../services/api';
import useAppStore from '../store/useAppStore';

import GrafanaPanel from '../components/charts/GrafanaPanel';
import IncidentTrendChart from '../components/charts/IncidentTrendChart';
import LogVolumeChart from '../components/charts/LogVolumeChart';
import ErrorDistributionChart from '../components/charts/ErrorDistributionChart';
import ServiceHealthChart from '../components/charts/ServiceHealthChart';
import TopIssuesChart from '../components/charts/TopIssuesChart';

const SERVICE_LABELS = {
  'azure-front-door': { label: 'Front Door', icon: '🌐', color: '#6366f1' },
  'azure-app-gateway': { label: 'App Gateway', icon: '🔀', color: '#8b5cf6' },
  'azure-apim': { label: 'API Management', icon: '⚙️', color: '#06b6d4' },
  'azure-vm': { label: 'Virtual Machine', icon: '🖥️', color: '#10b981' },
};

const parseDays = (rangeStr) => parseInt(rangeStr, 10);

export default function Dashboard() {
  const { dashboard, setDashboard, pipelineEnabled, setPipelineEnabled } = useAppStore();
  const [recentIncidents, setRecentIncidents] = useState([]);
  const [recentRuns, setRecentRuns] = useState([]);
  const [running, setRunning] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [simResult, setSimResult] = useState(null);
  const [lastLogAt, setLastLogAt] = useState(null);

  // Chart data state
  const [trendData, setTrendData] = useState([]);
  const [logVolumeData, setLogVolumeData] = useState([]);
  const [errorDist, setErrorDist] = useState({ distribution: [], total: 0 });
  const [serviceData, setServiceData] = useState([]);
  const [topIssuesData, setTopIssuesData] = useState([]);
  const [mttrData, setMttrData] = useState(null);

  // Time range selectors
  const [trendRange, setTrendRange] = useState('7d');
  const [logVolumeRange, setLogVolumeRange] = useState('7d');

  // Loading states
  const [chartsLoading, setChartsLoading] = useState(true);

  // Incident detail modal
  const [selectedIncident, setSelectedIncident] = useState(null);

  const loadDashboard = useCallback(async () => {
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
  }, [setDashboard, setPipelineEnabled]);

  const loadCharts = useCallback(async () => {
    try {
      const [trendRes, logVolRes, errDistRes, svcRes, topRes, mttrRes] =
        await Promise.allSettled([
          getIncidentTrend(parseDays(trendRange)),
          getLogVolume(parseDays(logVolumeRange)),
          getErrorDistribution(),
          getServiceBreakdown(),
          getTopIssues(10),
          getMTTR(),
        ]);

      if (trendRes.status === 'fulfilled') setTrendData(trendRes.value.data.data || []);
      if (logVolRes.status === 'fulfilled') setLogVolumeData(logVolRes.value.data.data || []);
      if (errDistRes.status === 'fulfilled') setErrorDist(errDistRes.value.data || { distribution: [], total: 0 });
      if (svcRes.status === 'fulfilled') setServiceData(svcRes.value.data.services || []);
      if (topRes.status === 'fulfilled') setTopIssuesData(topRes.value.data.top_issues || []);
      if (mttrRes.status === 'fulfilled') setMttrData(mttrRes.value.data);
    } catch (err) {
      console.error('Charts load error:', err);
    } finally {
      setChartsLoading(false);
    }
  }, [trendRange, logVolumeRange]);

  useEffect(() => {
    loadDashboard();
    loadCharts();
    const interval = setInterval(() => {
      loadDashboard();
      loadCharts();
    }, 15000);
    return () => clearInterval(interval);
  }, [loadDashboard, loadCharts]);

  // Reload trend chart on range change
  useEffect(() => {
    getIncidentTrend(parseDays(trendRange))
      .then((res) => setTrendData(res.data.data || []))
      .catch(console.error);
  }, [trendRange]);

  // Reload log volume on range change
  useEffect(() => {
    getLogVolume(parseDays(logVolumeRange))
      .then((res) => setLogVolumeData(res.data.data || []))
      .catch(console.error);
  }, [logVolumeRange]);

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
      setTimeout(() => {
        loadDashboard();
        loadCharts();
      }, 3000);
    } catch (err) {
      console.error('Manual run error:', err);
    } finally {
      setTimeout(() => setRunning(false), 2000);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr || dateStr === 'None') return 'N/A';
    return new Date(dateStr).toLocaleString();
  };

  const priorityBadge = (p) => {
    const map = { P1: 'high', P2: 'medium', P3: 'low' };
    return map[p] || 'low';
  };

  // KPI data
  const mttrValue = mttrData?.overall_avg_minutes
    ? `${Math.round(mttrData.overall_avg_minutes)}m`
    : '—';

  const kpiCards = [
    { label: 'Total Incidents', value: dashboard?.incidents?.total || 0, icon: '📋', color: 'cyan' },
    { label: 'Open', value: dashboard?.incidents?.open || 0, icon: '⚠️', color: 'amber' },
    { label: 'P1 Critical', value: dashboard?.incidents?.p1 || 0, icon: '🔴', color: 'rose' },
    { label: 'P2 Warning', value: dashboard?.incidents?.p2 || 0, icon: '🟡', color: 'amber' },
    { label: 'P3 Info', value: dashboard?.incidents?.p3 || 0, icon: '🟢', color: 'emerald' },
    { label: 'Resolved', value: dashboard?.incidents?.resolved || 0, icon: '✅', color: 'emerald' },
    { label: 'Avg MTTR', value: mttrValue, icon: '⏱️', color: 'violet', isText: true },
    { label: 'Pipeline Runs', value: dashboard?.pipeline?.total_runs || 0, icon: '🔄', color: 'blue' },
  ];

  return (
    <div className="page-content">
      {/* ── Page Header ── */}
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

      {/* ── Row 1: KPI Stat Cards ── */}
      <div className="grafana-kpi-grid animate-in">
        {kpiCards.map((kpi, i) => (
          <div
            key={kpi.label}
            className={`grafana-kpi-card kpi-${kpi.color} animate-in animate-in-delay-${(i % 4) + 1}`}
          >
            <div className="grafana-kpi-header">
              <span className="grafana-kpi-label">{kpi.label}</span>
              <span className="grafana-kpi-icon">{kpi.icon}</span>
            </div>
            <div className="grafana-kpi-value">
              {kpi.isText ? kpi.value : (typeof kpi.value === 'number' ? kpi.value.toLocaleString() : kpi.value)}
            </div>
          </div>
        ))}
      </div>

      {/* ── Row 2: Incident Trend + Error Distribution ── */}
      <div className="grafana-grid animate-in animate-in-delay-2">
        <div className="grafana-grid-row row-60-40">
          <GrafanaPanel
            title="Incident Trend"
            subtitle="by priority"
            timeRange={trendRange}
            onTimeRangeChange={setTrendRange}
            loading={chartsLoading}
          >
            <IncidentTrendChart data={trendData} />
          </GrafanaPanel>

          <GrafanaPanel
            title="Error Distribution"
            subtitle="by category"
            loading={chartsLoading}
          >
            <ErrorDistributionChart
              distribution={errorDist.distribution}
              total={errorDist.total}
            />
          </GrafanaPanel>
        </div>
      </div>

      {/* ── Row 3: Log Volume + Service Health ── */}
      <div className="grafana-grid animate-in animate-in-delay-3">
        <div className="grafana-grid-row row-50-50">
          <GrafanaPanel
            title="Log Volume"
            subtitle="by level"
            timeRange={logVolumeRange}
            onTimeRangeChange={setLogVolumeRange}
            loading={chartsLoading}
          >
            <LogVolumeChart data={logVolumeData} />
          </GrafanaPanel>

          <GrafanaPanel
            title="Service Health Matrix"
            subtitle="incidents per service"
            loading={chartsLoading}
          >
            <ServiceHealthChart services={serviceData} />
          </GrafanaPanel>
        </div>
      </div>

      {/* ── Row 4: Top Recurring Issues ── */}
      <div className="grafana-grid animate-in animate-in-delay-4">
        <GrafanaPanel
          title="Top Recurring Issues"
          subtitle={`${topIssuesData.length} patterns detected`}
          loading={chartsLoading}
        >
          {topIssuesData.length === 0 ? (
            <div className="empty-state" style={{ padding: '24px' }}>
              <div className="empty-state-icon">🔍</div>
              <div className="empty-state-title">No patterns yet</div>
              <div className="empty-state-text">Run the pipeline to detect recurring issues</div>
            </div>
          ) : (
            <TopIssuesChart issues={topIssuesData} />
          )}
        </GrafanaPanel>
      </div>

      {/* ── Row 5: Live Incident Feed ── */}
      <div className="grafana-grid animate-in animate-in-delay-2">
        <GrafanaPanel
          title="Live Incident Feed"
          subtitle={`${recentIncidents.length} recent`}
        >
          <div style={{ margin: '-16px -20px -20px', overflow: 'auto' }}>
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
                    <tr key={inc.id} onClick={() => setSelectedIncident(inc)} style={{ cursor: 'pointer' }}>
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
        </GrafanaPanel>
      </div>

      {/* ── Row 6: Pipeline Run History ── */}
      <div className="grafana-grid animate-in animate-in-delay-3">
        <GrafanaPanel
          title="Pipeline Run History"
          subtitle={`${recentRuns.length} recent runs`}
        >
          <div style={{ margin: '-16px -20px -20px', overflow: 'auto' }}>
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
        </GrafanaPanel>
      </div>

      {/* ── Incident Detail Modal ── */}
      {selectedIncident && (
        <div className="ncm-overlay" onClick={() => setSelectedIncident(null)}>
          <div
            className="ncm-modal"
            style={{ width: 620 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="ncm-header">
              <div>
                <div className="ncm-title">Incident Details</div>
                <div className="ncm-description">{selectedIncident.title}</div>
              </div>
              <button className="ncm-close" onClick={() => setSelectedIncident(null)}>✕</button>
            </div>
            <div className="ncm-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Priority + Status row */}
              <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                <span className={`priority-badge ${priorityBadge(selectedIncident.priority)}`}>
                  {selectedIncident.priority}
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span className={`status-dot ${selectedIncident.status === 'OPEN' ? 'error' : selectedIncident.status === 'IN_PROGRESS' ? 'running' : 'success'}`}></span>
                  <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{selectedIncident.status?.replace('_', ' ')}</span>
                </span>
              </div>

              {/* Detail grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <DetailField label="Service" value={
                  `${SERVICE_LABELS[selectedIncident.source_service]?.icon || '☁️'} ${SERVICE_LABELS[selectedIncident.source_service]?.label || selectedIncident.source_service || '—'}`
                } />
                <DetailField label="Category" value={selectedIncident.category || '—'} />
                <DetailField label="Created" value={formatDate(selectedIncident.created_at)} />
                <DetailField label="Updated" value={formatDate(selectedIncident.updated_at)} />
                <DetailField label="Email Notified" value={selectedIncident.email_sent ? '📧 Yes' : 'No'} />
                <DetailField label="Email Recipient" value={selectedIncident.email_recipient || '—'} />
                {selectedIncident.email_sent_at && (
                  <DetailField label="Email Sent At" value={formatDate(selectedIncident.email_sent_at)} />
                )}
                {selectedIncident.resolved_at && (
                  <DetailField label="Resolved At" value={formatDate(selectedIncident.resolved_at)} />
                )}
              </div>

              {/* Recommended Resolution */}
              {selectedIncident.ai_solution && (
                <div>
                  <div style={{
                    fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)',
                    textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 6,
                  }}>Recommended Resolution</div>
                  <div style={{
                    background: 'var(--bg-glass)', border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)', padding: '12px 16px',
                    fontSize: 13, lineHeight: 1.6, color: 'var(--text-secondary)',
                    maxHeight: 200, overflowY: 'auto', whiteSpace: 'pre-wrap',
                  }}>
                    {selectedIncident.ai_solution}
                  </div>
                </div>
              )}

              {/* Raw Description */}
              {selectedIncident.description && (
                <div>
                  <div style={{
                    fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)',
                    textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 6,
                  }}>Description</div>
                  <div style={{
                    background: 'var(--bg-glass)', border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)', padding: '12px 16px',
                    fontSize: 13, lineHeight: 1.6, color: 'var(--text-secondary)',
                    maxHeight: 160, overflowY: 'auto', whiteSpace: 'pre-wrap',
                  }}>
                    {selectedIncident.description}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/** Small helper for modal detail fields */
function DetailField({ label, value }) {
  return (
    <div>
      <div style={{
        fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 2,
      }}>{label}</div>
      <div style={{ fontSize: 13, color: 'var(--text-primary)' }}>{value}</div>
    </div>
  );
}
