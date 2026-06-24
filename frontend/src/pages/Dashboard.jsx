/**
 * Dashboard Page — FAANG-level Enterprise Observability Command Center.
 * Features: AI Insight Banner, System Health Gauge, Golden Signals (SRE),
 * Enhanced KPI cards with sparklines & animated counters, SLO/Error Budget
 * widget, MTTR breakdown gauges, Incident Trend & Error Distribution charts,
 * Log Volume chart, Service Uptime Heatmap, Incident Timeline,
 * Pipeline Health Ring, Top Recurring Issues, Live Incident Feed,
 * and Pipeline Run History.
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
  getGoldenSignals,
  getSystemHealth,
  getSLOStatus,
  getServiceUptime,
  getKPITrends,
} from '../services/api';
import useAppStore from '../store/useAppStore';

// Chart components
import GrafanaPanel from '../components/charts/GrafanaPanel';
import IncidentTrendChart from '../components/charts/IncidentTrendChart';
import LogVolumeChart from '../components/charts/LogVolumeChart';
import ErrorDistributionChart from '../components/charts/ErrorDistributionChart';
import TopIssuesChart from '../components/charts/TopIssuesChart';

// NEW enterprise components
import AIInsightBanner from '../components/charts/AIInsightBanner';
import SystemHealthGauge from '../components/charts/SystemHealthGauge';
import GoldenSignalsRow from '../components/charts/GoldenSignalsRow';
import AnimatedCounter from '../components/charts/AnimatedCounter';
import SparklineChart from '../components/charts/SparklineChart';
import SLOWidget from '../components/charts/SLOWidget';
import MTTRGauge from '../components/charts/MTTRGauge';
import ServiceUptimeHeatmap from '../components/charts/ServiceUptimeHeatmap';
import IncidentTimeline from '../components/charts/IncidentTimeline';
import PipelineHealthRing from '../components/charts/PipelineHealthRing';

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
  const [lastLogAt, setLastLogAt] = useState(null);

  // Existing chart data
  const [trendData, setTrendData] = useState([]);
  const [logVolumeData, setLogVolumeData] = useState([]);
  const [errorDist, setErrorDist] = useState({ distribution: [], total: 0 });
  const [topIssuesData, setTopIssuesData] = useState([]);
  const [mttrData, setMttrData] = useState(null);

  // NEW enterprise data
  const [goldenSignals, setGoldenSignals] = useState(null);
  const [healthData, setHealthData] = useState(null);
  const [sloData, setSloData] = useState(null);
  const [uptimeData, setUptimeData] = useState(null);
  const [kpiTrends, setKpiTrends] = useState([]);
  const [serviceData, setServiceData] = useState([]);

  // Time range selectors
  const [trendRange, setTrendRange] = useState('7d');
  const [logVolumeRange, setLogVolumeRange] = useState('7d');

  // Loading states
  const [chartsLoading, setChartsLoading] = useState(true);

  // Incident detail modal
  const [selectedIncident, setSelectedIncident] = useState(null);

  // Time range picker state (GMT)
  const [trDate, setTrDate] = useState('');
  const [trStartTime, setTrStartTime] = useState('');
  const [trEndTime, setTrEndTime] = useState('');

  // No-logs toast popup
  const [noLogsToast, setNoLogsToast] = useState(null);
  const noLogsTimerRef = useState(null);

  const loadDashboard = useCallback(async () => {
    try {
      const [dashRes, incRes, runRes] = await Promise.all([
        getDashboardSummary(),
        getIncidents({ page_size: 12 }),
        getAgentHistory({ page_size: 10 }),
      ]);
      setDashboard(dashRes.data);
      setPipelineEnabled(dashRes.data?.pipeline?.enabled ?? true);
      setRecentIncidents(incRes.data.items || []);
      setRecentRuns(runRes.data.items || []);
      const items = incRes.data.items || [];
      if (items.length > 0) setLastLogAt(items[0].created_at || items[0].updated_at);
    } catch (err) {
      console.error('Dashboard load error:', err);
    }
  }, [setDashboard, setPipelineEnabled]);

  const loadCharts = useCallback(async () => {
    try {
      const results = await Promise.allSettled([
        getIncidentTrend(parseDays(trendRange)),
        getLogVolume(parseDays(logVolumeRange)),
        getErrorDistribution(),
        getTopIssues(10),
        getMTTR(),
        getGoldenSignals(),
        getSystemHealth(),
        getSLOStatus(),
        getServiceUptime(30),
        getKPITrends(7),
        getServiceBreakdown(),
      ]);

      const [trendRes, logVolRes, errDistRes, topRes, mttrRes, gsRes, healthRes, sloRes, uptimeRes, kpiRes, svcRes] = results;

      if (trendRes.status === 'fulfilled') setTrendData(trendRes.value.data.data || []);
      if (logVolRes.status === 'fulfilled') setLogVolumeData(logVolRes.value.data.data || []);
      if (errDistRes.status === 'fulfilled') setErrorDist(errDistRes.value.data || { distribution: [], total: 0 });
      if (topRes.status === 'fulfilled') setTopIssuesData(topRes.value.data.top_issues || []);
      if (mttrRes.status === 'fulfilled') setMttrData(mttrRes.value.data);
      if (gsRes.status === 'fulfilled') setGoldenSignals(gsRes.value.data);
      if (healthRes.status === 'fulfilled') setHealthData(healthRes.value.data);
      if (sloRes.status === 'fulfilled') setSloData(sloRes.value.data);
      if (uptimeRes.status === 'fulfilled') setUptimeData(uptimeRes.value.data);
      if (kpiRes.status === 'fulfilled') setKpiTrends(kpiRes.value.data.data || []);
      if (svcRes.status === 'fulfilled') setServiceData(svcRes.value.data.services || []);
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

  useEffect(() => {
    getIncidentTrend(parseDays(trendRange))
      .then((res) => setTrendData(res.data.data || []))
      .catch(console.error);
  }, [trendRange]);

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
      // Build time range payload if all fields are filled
      const payload = {};
      if (trDate && trStartTime && trEndTime) {
        payload.start_time = `${trDate}T${trStartTime}:00Z`;
        payload.end_time = `${trDate}T${trEndTime}:00Z`;
      }
      const res = await triggerManualRun(payload);

      // Check for synchronous no-logs response (if pipeline completes very fast)
      if (res.data?.no_logs_found) {
        showNoLogsToast();
      }

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

  // Show no-logs toast and auto-dismiss after 6s
  const showNoLogsToast = () => {
    const timeLabel = (trDate && trStartTime && trEndTime)
      ? `${trDate} ${trStartTime} — ${trEndTime} (GMT)`
      : 'the selected time range';
    setNoLogsToast(`No logs found for ${timeLabel}`);
    setTimeout(() => setNoLogsToast(null), 6000);
  };

  // Listen for no-logs WebSocket notification
  const notifications = useAppStore((s) => s.notifications);
  useEffect(() => {
    const latest = notifications[0];
    if (latest && latest.type === 'warning' && latest.message?.includes('No logs found')) {
      showNoLogsToast();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notifications]);

  const formatDate = (dateStr) => {
    if (!dateStr || dateStr === 'None') return 'N/A';
    return new Date(dateStr).toLocaleString();
  };

  const priorityBadge = (p) => {
    const map = { P1: 'high', P2: 'medium', P3: 'low' };
    return map[p] || 'low';
  };

  // KPI data with sparkline trends
  const mttrValue = mttrData?.overall_avg_minutes
    ? `${Math.round(mttrData.overall_avg_minutes)}m`
    : '—';

  const kpiCards = [
    { label: 'Total Incidents', value: dashboard?.incidents?.total || 0, icon: '📋', color: 'cyan', trendKey: 'total' },
    { label: 'Open', value: dashboard?.incidents?.open || 0, icon: '⚠️', color: 'amber', trendKey: 'open' },
    { label: 'P1 Critical', value: dashboard?.incidents?.p1 || 0, icon: '🔴', color: 'rose', trendKey: 'P1' },
    { label: 'P2 Warning', value: dashboard?.incidents?.p2 || 0, icon: '🟡', color: 'amber', trendKey: 'P2' },
    { label: 'P3 Info', value: dashboard?.incidents?.p3 || 0, icon: '🟢', color: 'emerald', trendKey: 'P3' },
    { label: 'Resolved', value: dashboard?.incidents?.resolved || 0, icon: '✅', color: 'emerald', trendKey: 'resolved' },
    { label: 'Avg MTTR', value: mttrValue, icon: '⏱️', color: 'violet', isText: true },
    { label: 'Pipeline Runs', value: dashboard?.pipeline?.total_runs || 0, icon: '🔄', color: 'blue', trendKey: 'pipeline_runs' },
  ];

  // Compute delta % for KPI cards
  const getDelta = (key) => {
    if (!kpiTrends || kpiTrends.length < 2) return null;
    const today = kpiTrends[kpiTrends.length - 1]?.[key] || 0;
    const yesterday = kpiTrends[kpiTrends.length - 2]?.[key] || 0;
    if (yesterday === 0) return today > 0 ? 100 : 0;
    return Math.round(((today - yesterday) / yesterday) * 100);
  };

  return (
    <>
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

          {/* Time Range Picker (GMT) */}
          <div className="time-range-picker">
            <div className="time-range-picker-label">
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Time Range (GMT)</span>
            </div>
            <div className="time-range-picker-inputs">
              <input
                type="date"
                id="tr-date"
                className="time-range-input"
                value={trDate}
                onChange={(e) => setTrDate(e.target.value)}
                title="Select date (GMT)"
              />
              <input
                type="time"
                id="tr-start"
                className="time-range-input"
                value={trStartTime}
                onChange={(e) => setTrStartTime(e.target.value)}
                title="Start time (GMT)"
                placeholder="Start"
              />
              <span style={{ color: 'var(--text-tertiary)', fontSize: 12, fontWeight: 600 }}>→</span>
              <input
                type="time"
                id="tr-end"
                className="time-range-input"
                value={trEndTime}
                onChange={(e) => setTrEndTime(e.target.value)}
                title="End time (GMT)"
                placeholder="End"
              />
              {(trDate || trStartTime || trEndTime) && (
                <button
                  className="time-range-clear-btn"
                  onClick={() => { setTrDate(''); setTrStartTime(''); setTrEndTime(''); }}
                  title="Clear time range"
                >
                  ✕
                </button>
              )}
            </div>
          </div>

          <button className="btn btn-primary btn-sm" onClick={handleManualRun} disabled={!pipelineEnabled || running}>
            {running ? '⟳ Running…' : '▶ Run Pipeline'}
          </button>

          <span style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>
            Next: {dashboard?.pipeline?.next_run_at ? formatDate(dashboard.pipeline.next_run_at) : 'Not scheduled'}
          </span>
        </div>
      </div>

      {/* ── Row 0: AI Insight Banner ── */}
      <div className="animate-in">
        <AIInsightBanner
          dashboard={dashboard}
          goldenSignals={goldenSignals}
          trendData={trendData}
        />
      </div>

      {/* ── Row 1: System Health Gauge + Golden Signals ── */}
      <div className="enterprise-hero-row animate-in animate-in-delay-1">
        <div className="enterprise-health-panel">
          <GrafanaPanel title="System Health" subtitle="composite score" loading={chartsLoading}>
            <SystemHealthGauge
              score={healthData?.score ?? 0}
              status={healthData?.status ?? 'HEALTHY'}
              factors={healthData?.factors}
            />
          </GrafanaPanel>
        </div>
        <div className="enterprise-signals-panel">
          <GrafanaPanel title="Golden Signals" subtitle="Google SRE methodology" loading={chartsLoading}>
            <GoldenSignalsRow signals={goldenSignals || {}} />
          </GrafanaPanel>
        </div>
      </div>

      {/* ── Row 1.5: Service Status Cards ── */}
      <div className="service-status-grid animate-in animate-in-delay-1">
        {(['azure-front-door', 'azure-app-gateway', 'azure-apim', 'azure-vm']).map((svcKey) => {
          const svc = serviceData.find(s => s.service === svcKey) || { service: svcKey, total: 0, P1: 0, P2: 0, P3: 0, open: 0, resolved: 0, has_errors: false, health: 'healthy', recent_errors: [] };
          const meta = SERVICE_LABELS[svcKey] || { label: svcKey, icon: '📦', color: '#6366f1' };
          const healthClass = svc.health || 'healthy';
          const hasErrors = svc.has_errors;

          return (
            <div key={svcKey} className={`service-status-card ${healthClass}`} id={`svc-card-${svcKey}`}>
              {/* Glow effect for error state */}
              {hasErrors && <div className="service-status-card-glow" />}

              <div className="service-status-header">
                <div className="service-status-icon" style={{ background: hasErrors ? 'rgba(239,68,68,0.2)' : `${meta.color}22`, color: hasErrors ? '#ef4444' : meta.color }}>
                  {meta.icon}
                </div>
                <div className="service-status-info">
                  <div className="service-status-name">{meta.label}</div>
                  <div className={`service-status-badge ${healthClass}`}>
                    <span className="service-status-dot" />
                    {healthClass === 'critical' ? 'Critical' : healthClass === 'warning' ? 'Warning' : healthClass === 'degraded' ? 'Degraded' : 'Healthy'}
                  </div>
                </div>
                {svc.open > 0 && (
                  <div className="service-status-open-badge">{svc.open} open</div>
                )}
              </div>

              {/* Priority breakdown pills */}
              <div className="service-status-priority-row">
                <span className={`service-priority-pill ${svc.P1 > 0 ? 'p1-active' : ''}`}>🔴 P1: {svc.P1}</span>
                <span className={`service-priority-pill ${svc.P2 > 0 ? 'p2-active' : ''}`}>🟡 P2: {svc.P2}</span>
                <span className={`service-priority-pill ${svc.P3 > 0 ? 'p3-active' : ''}`}>🟢 P3: {svc.P3}</span>
                <span className="service-priority-pill total">{svc.total} total</span>
              </div>

              {/* Recent error descriptions */}
              {hasErrors && svc.recent_errors?.length > 0 && (
                <div className="service-status-errors">
                  <div className="service-status-errors-label">Active Errors</div>
                  {svc.recent_errors.map((err, i) => (
                    <div key={i} className="service-status-error-item">
                      <span className={`service-error-priority-dot priority-${err.priority?.toLowerCase()}`} />
                      <span className="service-error-title">{err.title}</span>
                      {err.category && <span className="service-error-category">{err.category}</span>}
                    </div>
                  ))}
                </div>
              )}

              {/* Resolved count footer */}
              {svc.total > 0 && (
                <div className="service-status-footer">
                  <span className="service-resolved-count">✓ {svc.resolved} resolved</span>
                  <span className="service-total-count">{svc.total} incidents</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── Row 2: Enhanced KPI Stat Cards with Sparklines ── */}
      <div className="grafana-kpi-grid animate-in animate-in-delay-2">
        {kpiCards.map((kpi, i) => {
          const sparkData = kpi.trendKey
            ? kpiTrends.map((d) => d[kpi.trendKey] || 0)
            : [];
          const delta = kpi.trendKey ? getDelta(kpi.trendKey) : null;
          const sparkColor = kpi.color === 'rose' ? '#ef4444'
            : kpi.color === 'amber' ? '#f59e0b'
            : kpi.color === 'emerald' ? '#10b981'
            : kpi.color === 'violet' ? '#8b5cf6'
            : kpi.color === 'blue' ? '#3b82f6'
            : '#06b6d4';

          return (
            <div
              key={kpi.label}
              className={`grafana-kpi-card kpi-${kpi.color} animate-in animate-in-delay-${(i % 4) + 1}`}
            >
              <div className="grafana-kpi-header">
                <span className="grafana-kpi-label">{kpi.label}</span>
                <span className="grafana-kpi-icon">{kpi.icon}</span>
              </div>
              <div className="grafana-kpi-value">
                {kpi.isText ? kpi.value : (
                  <AnimatedCounter value={typeof kpi.value === 'number' ? kpi.value : 0} />
                )}
              </div>
              <div className="grafana-kpi-footer">
                {sparkData.length > 2 && (
                  <SparklineChart data={sparkData} width={64} height={22} color={sparkColor} />
                )}
                {delta !== null && delta !== 0 && (
                  <span className={`grafana-kpi-delta ${delta > 0 ? 'delta-up' : 'delta-down'}`}>
                    {delta > 0 ? '↑' : '↓'} {Math.abs(delta)}%
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Row 3: SLO/Error Budget + MTTR Breakdown ── */}
      <div className="grafana-grid animate-in animate-in-delay-2">
        <div className="grafana-grid-row row-50-50">
          <GrafanaPanel title="SLO Compliance" subtitle="error budget tracking" loading={chartsLoading}>
            <SLOWidget sloData={sloData} />
          </GrafanaPanel>
          <GrafanaPanel title="MTTR Breakdown" subtitle="by priority" loading={chartsLoading}>
            <MTTRGauge mttrData={mttrData} />
          </GrafanaPanel>
        </div>
      </div>

      {/* ── Row 4: Incident Trend + Error Distribution ── */}
      <div className="grafana-grid animate-in animate-in-delay-3">
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

      {/* ── Row 5: Log Volume + Service Uptime Heatmap ── */}
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
            title="Service Uptime (30 Days)"
            subtitle="incident severity heatmap"
            loading={chartsLoading}
          >
            <ServiceUptimeHeatmap
              heatmapData={uptimeData?.heatmap || []}
              services={uptimeData?.services || []}
              days={uptimeData?.days || 30}
            />
          </GrafanaPanel>
        </div>
      </div>

      {/* ── Row 6: Incident Timeline + Pipeline Health Ring ── */}
      <div className="grafana-grid animate-in animate-in-delay-2">
        <div className="grafana-grid-row row-60-40">
          <GrafanaPanel
            title="Incident Timeline"
            subtitle={`${recentIncidents.length} recent events`}
          >
            <IncidentTimeline incidents={recentIncidents} />
          </GrafanaPanel>

          <GrafanaPanel
            title="Pipeline Health"
            subtitle={`${recentRuns.length} recent runs`}
            loading={chartsLoading}
          >
            <PipelineHealthRing runs={recentRuns} />
          </GrafanaPanel>
        </div>
      </div>

      {/* ── Row 7: Top Recurring Issues ── */}
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

      {/* ── Row 8: Live Incident Feed ── */}
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

      {/* ── Row 9: Pipeline Run History ── */}
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
              <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                <span className={`priority-badge ${priorityBadge(selectedIncident.priority)}`}>
                  {selectedIncident.priority}
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span className={`status-dot ${selectedIncident.status === 'OPEN' ? 'error' : selectedIncident.status === 'IN_PROGRESS' ? 'running' : 'success'}`}></span>
                  <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{selectedIncident.status?.replace('_', ' ')}</span>
                </span>
              </div>
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

    {/* ── No Logs Found Toast Popup ── */}
    {noLogsToast && (
      <div className="no-logs-toast" key={noLogsToast}>
        <div className="no-logs-toast-icon">⚠️</div>
        <div className="no-logs-toast-content">
          <div className="no-logs-toast-title">No Logs Found</div>
          <div className="no-logs-toast-message">{noLogsToast}</div>
        </div>
        <button className="no-logs-toast-close" onClick={() => setNoLogsToast(null)}>✕</button>
      </div>
    )}
    </>
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
