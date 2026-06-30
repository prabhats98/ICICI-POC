/**
 * Dashboard — Enterprise Security Operations Center
 * 
 * Features:
 *   - Real-time Azure service health checks (HTTP status, response time)
 *   - Enterprise charts using Chart.js (Radar, Polar, Horizontal Bar, etc.)
 *   - Service-centric incident correlation
 *   - Root Cause Analysis deep dive
 */

import React, { useEffect, useState, useCallback } from 'react';
import { Bar, Doughnut, Line, Radar, PolarArea } from 'react-chartjs-2';
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement,
  PointElement, LineElement, ArcElement, RadialLinearScale,
  Tooltip, Legend, Filler,
} from 'chart.js';
import {
  getDashboardSummary, getIncidents, getAgentHistory,
  togglePipeline, triggerManualRun,
  getIncidentTrend, getLogVolume, getErrorDistribution,
  getServiceBreakdown, getTopIssues, getMTTR,
  getGoldenSignals, getSystemHealth, getSLOStatus,
  getServiceUptime, getKPITrends,
  getIncidentGroups, getRCADetails,
  getServiceHealthChecks, getHealthHistory, sendDowntimeNotification,
} from '../services/api';
import useAppStore from '../store/useAppStore';

const API_URL = window.location.hostname === 'localhost'
  ? 'http://localhost:8001'
  : `http://${window.location.hostname}`;

// Chart components
import GrafanaPanel from '../components/charts/GrafanaPanel';
import AnimatedCounter from '../components/charts/AnimatedCounter';
import SparklineChart from '../components/charts/SparklineChart';
import InfraFlowDiagram from '../components/charts/InfraFlowDiagram';

ChartJS.register(
  CategoryScale, LinearScale, BarElement,
  PointElement, LineElement, ArcElement, RadialLinearScale,
  Tooltip, Legend, Filler
);

/* ─── Constants ─── */
const CHART_COLORS = {
  blue: '#3b82f6', indigo: '#6366f1', violet: '#8b5cf6',
  cyan: '#06b6d4', teal: '#14b8a6', emerald: '#10b981',
  amber: '#f59e0b', orange: '#f97316', rose: '#ef4444',
  pink: '#ec4899', slate: '#64748b',
};

const TOOLTIP = {
  backgroundColor: '#0f172a', titleColor: '#fff', bodyColor: '#e2e8f0',
  padding: 14, cornerRadius: 10, titleFont: { size: 13, weight: '700' },
  bodyFont: { size: 12 }, borderColor: '#334155', borderWidth: 1,
};

const GRID_LIGHT = { color: 'rgba(0,0,0,0.04)' };
const TICK_STYLE = { color: '#64748b', font: { size: 11 } };
const LEGEND_STYLE = { color: '#334155', font: { size: 12, weight: '600' }, padding: 14, usePointStyle: true, pointStyleWidth: 8 };

const formatDate = (d) => (!d || d === 'None') ? 'N/A' : new Date(d).toLocaleString();
const parseDays = (s) => parseInt(s, 10);

/* ═════════════════════════════════════════
   MAIN DASHBOARD
   ═════════════════════════════════════════ */
export default function Dashboard() {
  const { dashboard, setDashboard, pipelineEnabled, setPipelineEnabled } = useAppStore();
  const [recentIncidents, setRecentIncidents] = useState([]);
  const [recentRuns, setRecentRuns] = useState([]);
  const [running, setRunning] = useState(false);
  const [lastLogAt, setLastLogAt] = useState(null);

  // Chart data
  const [trendData, setTrendData] = useState([]);
  const [logVolumeData, setLogVolumeData] = useState([]);
  const [errorDist, setErrorDist] = useState({ distribution: [], total: 0 });
  const [topIssuesData, setTopIssuesData] = useState([]);
  const [mttrData, setMttrData] = useState(null);
  const [goldenSignals, setGoldenSignals] = useState(null);
  const [healthData, setHealthData] = useState(null);
  const [sloData, setSloData] = useState(null);
  const [uptimeData, setUptimeData] = useState(null);
  const [kpiTrends, setKpiTrends] = useState([]);

  // Service-level data
  const [serviceBreakdown, setServiceBreakdown] = useState([]);
  const [incidentGroups, setIncidentGroups] = useState([]);
  const [rcaDetails, setRcaDetails] = useState([]);

  // Real health checks from backend
  const [healthChecks, setHealthChecks] = useState(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthLastUpdated, setHealthLastUpdated] = useState(null);
  const [healthCountdown, setHealthCountdown] = useState(15);
  const [healthHistory, setHealthHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [notifySending, setNotifySending] = useState(false);
  const [notifyResult, setNotifyResult] = useState(null);

  const [trendRange, setTrendRange] = useState('7d');
  const [logVolumeRange, setLogVolumeRange] = useState('7d');
  const [chartsLoading, setChartsLoading] = useState(true);
  const [selectedIncident, setSelectedIncident] = useState(null);

  /* ─── Data Loading ─── */
  const loadAll = useCallback(async () => {
    // Load dashboard summary (public endpoint, no auth required)
    try {
      const dashRes = await getDashboardSummary();
      setDashboard(dashRes.data);
      setPipelineEnabled(dashRes.data?.pipeline?.enabled ?? true);
    } catch { }

    // Load auth-protected data (agents, incidents) — don't block if 401
    try {
      const runRes = await getAgentHistory({ page_size: 10 });
      setRecentRuns(runRes.data.items || []);
    } catch { }

    try {
      const res = await getIncidents({ page_size: 15 });
      const items = res.data.items || [];
      setRecentIncidents(items);
      if (items.length) setLastLogAt(items[0].created_at);
    } catch { }

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
      const v = (r) => (r.status === 'fulfilled' ? r.value.data : null);
      try { setTrendData(v(results[0])?.data || []); } catch(e) { console.error('setTrendData err:', e); }
      try { setLogVolumeData(v(results[1])?.data || []); } catch(e) { console.error('setLogVolumeData err:', e); }
      try { setErrorDist(v(results[2]) || { distribution: [], total: 0 }); } catch(e) { console.error('setErrorDist err:', e); }
      try { setTopIssuesData(v(results[3])?.top_issues || []); } catch(e) { console.error('setTopIssuesData err:', e); }
      try { setMttrData(v(results[4])); } catch(e) { console.error('setMttrData err:', e); }
      try { setGoldenSignals(v(results[5])); } catch(e) { console.error('setGoldenSignals err:', e); }
      try { setHealthData(v(results[6])); } catch(e) { console.error('setHealthData err:', e); }
      try { setSloData(v(results[7])); } catch(e) { console.error('setSloData err:', e); }
      try { setUptimeData(v(results[8])); } catch(e) { console.error('setUptimeData err:', e); }
      try { setKpiTrends(v(results[9])?.data || []); } catch(e) { console.error('setKpiTrends err:', e); }
      try { setServiceBreakdown(v(results[10])?.services || []); } catch(e) { console.error('setServiceBreakdown err:', e); }
    } catch(e) { console.error('[Dashboard] charts loadData error:', e); }

    // ─── Incident Intelligence (direct fetch, bypasses axios interceptors) ───
    try {
      const [gResp, rResp] = await Promise.all([
        fetch(`${API_URL}/api/analytics/incident-groups?days=30`),
        fetch(`${API_URL}/api/analytics/rca-details?days=30`),
      ]);
      if (gResp.ok) {
        const gJson = await gResp.json();
        const gData = gJson?.data || [];
        console.log('[Dashboard] ✅ Incident Groups loaded:', gData.length, 'items');
        setIncidentGroups(gData);
      } else {
        console.error('[Dashboard] ❌ Incident Groups API error:', gResp.status, gResp.statusText);
      }
      if (rResp.ok) {
        const rJson = await rResp.json();
        const rData = rJson?.data || [];
        console.log('[Dashboard] ✅ RCA Details loaded:', rData.length, 'items');
        setRcaDetails(rData);
      } else {
        console.error('[Dashboard] ❌ RCA API error:', rResp.status, rResp.statusText);
      }
    } catch(e) { console.error('[Dashboard] ❌ incident intelligence fetch error:', e); }
    setChartsLoading(false);
  }, [trendRange, logVolumeRange, setDashboard, setPipelineEnabled]);

  const loadHealthChecks = useCallback(async () => {
    setHealthLoading(true);
    try {
      const res = await getServiceHealthChecks();
      setHealthChecks(res.data);
      setHealthLastUpdated(new Date());
      setHealthCountdown(15);
    } catch { }
    // Load history in background
    try {
      const hRes = await getHealthHistory();
      setHealthHistory(hRes.data?.history || []);
    } catch { }
    setHealthLoading(false);
  }, []);

  const handleSendAlert = useCallback(async () => {
    setNotifySending(true);
    setNotifyResult(null);
    try {
      const res = await sendDowntimeNotification();
      setNotifyResult(res.data);
    } catch (e) {
      setNotifyResult({ sent: false, message: 'Failed to send notification.' });
    }
    setNotifySending(false);
    setTimeout(() => setNotifyResult(null), 8000); // Clear message after 8s
  }, []);

  useEffect(() => {
    loadAll(); loadHealthChecks();
    const i1 = setInterval(loadAll, 20000);
    const i2 = setInterval(loadHealthChecks, 15000); // Health checks every 15s for real-time
    const i3 = setInterval(() => setHealthCountdown(c => c > 0 ? c - 1 : 15), 1000); // countdown tick
    return () => { clearInterval(i1); clearInterval(i2); clearInterval(i3); };
  }, [loadAll, loadHealthChecks]);

  /* ─── Controls ─── */
  const handleToggle = async () => { try { const r = await togglePipeline(!pipelineEnabled); setPipelineEnabled(r.data.enabled); } catch { } };
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [dateRange, setDateRange] = useState({ start: '', end: '' });

  const handleManualRun = async (customRange = null) => {
    setRunning(true);
    try {
      const payload = customRange
        ? { start_date: customRange.start, end_date: customRange.end }
        : {};
      const resp = await triggerManualRun(payload);
      if (resp?.data?.status === 'error') {
        alert('Pipeline Error: ' + (resp.data.message || 'Unknown error'));
        setRunning(false);
        return;
      }
      const pollInterval = setInterval(async () => {
        try {
          const dash = await getDashboardSummary();
          const isRunning = dash?.data?.pipeline?.is_running;
          if (!isRunning) {
            clearInterval(pollInterval);
            setRunning(false);
            loadAll();
            loadHealthChecks(); // Refresh topology with incident data
          }
        } catch { }
      }, 5000);
      setTimeout(() => { clearInterval(pollInterval); setRunning(false); loadAll(); loadHealthChecks(); }, 600000);
    } catch (err) {
      const msg = err?.response?.data?.message || err?.message || 'Failed to trigger pipeline';
      alert('Pipeline Error: ' + msg);
      setRunning(false);
    }
  };

  /* ─── KPI Data ─── */
  const kpiCards = [
    { label: 'Total Logs', value: dashboard?.logs?.total || 0, icon: '📋', color: 'cyan' },
    { label: 'Active Incidents', value: dashboard?.incidents?.open || dashboard?.incidents?.total || 0, icon: '⚠️', color: 'amber' },
    { label: 'P1 Critical', value: dashboard?.incidents?.p1 || 0, icon: '🔴', color: 'rose' },
    { label: 'P2 High', value: dashboard?.incidents?.p2 || 0, icon: '🟡', color: 'amber' },
    { label: 'P3 Medium', value: dashboard?.incidents?.p3 || 0, icon: '🟢', color: 'emerald' },
    { label: 'Emails Sent', value: dashboard?.incidents?.emails_sent || 0, icon: '✉️', color: 'blue' },
    { label: 'Avg MTTR', value: mttrData?.overall_avg_minutes ? `${Math.round(mttrData.overall_avg_minutes)}m` : '—', icon: '⏱️', color: 'violet', isText: true },
    { label: 'Pipeline Runs', value: dashboard?.pipeline?.total_runs || 0, icon: '🔄', color: 'indigo' },
  ];

  const services = healthChecks?.services || [];
  const summary = healthChecks?.summary || {};

  return (
    <div className="page-content">

      {/* ═══ COMMAND BAR ═══ */}
      <div className="page-header animate-in">
        <h1>Security Operations Center</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div className="live-badge">
            <span className="live-dot" />
            <span style={{ fontSize: 12, fontWeight: 700, color: '#10b981' }}>LIVE</span>
          </div>
          {lastLogAt && <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>Last: {formatDate(lastLogAt)}</span>}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }} onClick={handleToggle}>
            <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>Pipeline</span>
            <div className={`toggle-switch ${pipelineEnabled ? 'on' : ''}`}>
              <div className="toggle-thumb" />
            </div>
          </div>
          <button className="btn btn-primary btn-sm" onClick={() => handleManualRun()} disabled={!pipelineEnabled || running}
            style={{ borderRadius: '8px 0 0 8px', borderRight: '1px solid rgba(255,255,255,0.3)' }}>
            {running ? '⟳ Running…' : '▶ Run Now'}
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => setShowDatePicker(true)} disabled={!pipelineEnabled || running}
            style={{ borderRadius: '0 8px 8px 0', padding: '6px 10px' }}
            title="Select date range">
            📅
          </button>
        </div>
      </div>

      {/* ═══ DATE RANGE PICKER MODAL ═══ */}
      {showDatePicker && (
        <DateRangePickerModal
          onRun={(range) => { setShowDatePicker(false); setDateRange(range); handleManualRun(range); }}
          onClose={() => setShowDatePicker(false)}
          running={running}
        />
      )}

      {/* ═══ AI INSIGHT ═══ */}
      <AIInsightBar dashboard={dashboard} goldenSignals={goldenSignals} healthSummary={summary} />

      {/* ---- SECTION 1: INFRASTRUCTURE HEALTH ---- */}
      <div className="section-divider" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
          <div className="section-divider-icon" style={{ background: 'rgba(59,130,246,0.12)' }}>
            <span>{'🏗️'}</span>
          </div>
          <div className="section-divider-text">
            <h3 style={{ color: '#3b82f6' }}>Infrastructure Health</h3>
            <p>Real-time service monitoring, topology & system health</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          {notifyResult && (
            <span style={{ fontSize: 11, fontWeight: 600, color: notifyResult.sent ? '#166534' : '#166534', background: '#dcfce7', padding: '4px 10px', borderRadius: 6, border: '1px solid #86efac' }}>
              {notifyResult.sent ? '✅ Alert sent!' : `✅ No incident found in last refresh at ${new Date().toLocaleTimeString()}`}
            </span>
          )}
          <button onClick={handleSendAlert} disabled={notifySending}
            style={{
              fontSize: 12, padding: '7px 18px', background: 'linear-gradient(135deg, #ef4444, #dc2626)',
              color: 'white', border: 'none', borderRadius: 8, fontWeight: 700,
              cursor: notifySending ? 'wait' : 'pointer', boxShadow: '0 2px 8px rgba(239,68,68,0.3)',
              transition: 'all 0.2s ease', display: 'flex', alignItems: 'center', gap: 6,
            }}>
            {notifySending ? '⟳ Sending…' : '📧 Send Alert'}
          </button>
        </div>
      </div>

      {/* ═══ REQUEST FLOW TOPOLOGY ═══ */}
      <div className="animate-in animate-in-delay-1">
        <GrafanaPanel title="🔗 Request Flow — Live Infrastructure Topology" subtitle="real-time service chain · animated data flow">
          <InfraFlowDiagram services={services} />
        </GrafanaPanel>
      </div>

      {/* ═══ REAL-TIME AZURE SERVICE HEALTH ═══ */}
      <div className="animate-in animate-in-delay-1">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
              🏗️ Azure Infrastructure — Live Health Status
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                background: 'rgba(16,185,129,0.12)', color: '#10b981',
                padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
              }}>
                <span style={{
                  width: 7, height: 7, borderRadius: '50%', background: '#10b981',
                  animation: 'pulse-live 1.5s ease-in-out infinite',
                }} />
                LIVE
              </span>
            </h2>
            <p style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 2 }}>
              Real-time ping + Azure Monitor · Auto-refreshes every 15s
              {healthLastUpdated && (
                <span style={{ marginLeft: 8, color: '#64748b' }}>
                  · Updated {healthLastUpdated.toLocaleTimeString()} · Next in {healthCountdown}s
                </span>
              )}
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <HealthSummaryPill label="Healthy" count={summary.healthy || 0} color="#10b981" />
            <HealthSummaryPill label="Down" count={summary.unhealthy || 0} color="#ef4444" />
            <HealthSummaryPill label="Unknown" count={summary.unknown || 0} color="#94a3b8" />
            <button className="btn btn-sm" onClick={() => setShowHistory(!showHistory)}
              style={{ fontSize: 11, padding: '4px 10px', background: showHistory ? '#3b82f6' : undefined, color: showHistory ? 'white' : undefined, border: showHistory ? 'none' : undefined, borderRadius: 6 }}>
              📋 {showHistory ? 'Hide History' : 'History'}
            </button>
            <button className="btn btn-sm" onClick={loadHealthChecks} style={{ fontSize: 11, padding: '4px 10px' }}>
              ↻ Refresh
            </button>
          </div>
        </div>

        <div className="infra-health-grid">
          {healthLoading && services.length === 0 ? (
            Array.from({ length: 8 }).map((_, i) => <div key={i} className="loading-shimmer" style={{ height: 160, borderRadius: 14 }} />)
          ) : (
            services.map((svc) => <LiveServiceCard key={svc.id} service={svc} incidentGroups={incidentGroups} />)
          )}
        </div>

        {/* ═══ HEALTH CHECK HISTORY ═══ */}
        {showHistory && (
          <div style={{ marginTop: 16, padding: '16px 18px', background: 'var(--card-bg)', borderRadius: 12, border: '1px solid var(--border-primary)' }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 12 }}>
              📋 Health Check History — Last {healthHistory.length} Checks
            </h3>
            {healthHistory.length === 0 ? (
              <p style={{ fontSize: 12, color: '#94a3b8' }}>No history yet. Checks are recorded every 15 seconds.</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                  <thead>
                    <tr style={{ background: 'rgba(0,0,0,0.03)', borderBottom: '2px solid var(--border-primary)' }}>
                      <th style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 700, color: '#475569' }}>Time</th>
                      {healthHistory[0]?.services?.map(s => (
                        <th key={s.id} style={{ padding: '8px 6px', textAlign: 'center', fontWeight: 700, color: '#475569', minWidth: 70 }}>
                          {s.short_name}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[...healthHistory].reverse().slice(0, 20).map((snap, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(0,0,0,0.04)' }}>
                        <td style={{ padding: '6px 10px', fontFamily: 'monospace', color: '#64748b', whiteSpace: 'nowrap' }}>
                          {new Date(snap.timestamp).toLocaleTimeString()}
                        </td>
                        {snap.services.map(s => (
                          <td key={s.id} style={{ padding: '6px', textAlign: 'center' }}>
                            <span style={{
                              display: 'inline-block', padding: '2px 8px', borderRadius: 10, fontSize: 10, fontWeight: 700,
                              background: s.healthy === true ? '#dcfce7' : s.healthy === false ? '#fef2f2' : '#f1f5f9',
                              color: s.healthy === true ? '#166534' : s.healthy === false ? '#991b1b' : '#64748b',
                            }}>
                              {s.healthy === true ? `✓ ${s.response_time_ms}ms` : s.healthy === false ? '✗ DOWN' : '—'}
                            </span>
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ═══ KPI METRICS ═══ */}
      <div className="grafana-kpi-grid animate-in animate-in-delay-2">
        {kpiCards.map((kpi, i) => (
          <div key={kpi.label} className={`grafana-kpi-card kpi-${kpi.color}`}>
            <div className="grafana-kpi-header">
              <span className="grafana-kpi-label">{kpi.label}</span>
              <span className="grafana-kpi-icon">{kpi.icon}</span>
            </div>
            <div className="grafana-kpi-value">
              {kpi.isText ? kpi.value : <AnimatedCounter value={typeof kpi.value === 'number' ? kpi.value : 0} />}
            </div>
          </div>
        ))}
      </div>

      {/* ═══ SYSTEM HEALTH RADAR + GOLDEN SIGNALS ═══ */}
      <div className="grafana-grid animate-in animate-in-delay-2">
        <div className="grafana-grid-row row-40-60">
          <GrafanaPanel title="Real-Time Service Health Radar" subtitle="live health scores from 8 Azure services (updated every 15s)">
            <SystemRadarChart healthData={healthData} goldenSignals={goldenSignals} services={services} />
          </GrafanaPanel>
          <GrafanaPanel title="Service Incident Correlation" subtitle="incidents vs response time">
            <ServiceCorrelationChart services={services} incidentGroups={incidentGroups} />
          </GrafanaPanel>
        </div>
      </div>

      {/* ---- SECTION 2: INCIDENT INTELLIGENCE ---- */}
      <SectionHeader icon="🛡️" color="#8b5cf6" title="Incident Intelligence" desc="Threat detection, categorization, root cause analysis & response timeline" />

      {/* ═══ INCIDENT TREND + AFFECTED SERVICES ═══ */}
      <div className="grafana-grid animate-in animate-in-delay-3">
        <div className="grafana-grid-row row-60-40">
          <GrafanaPanel title="Incident Trend" subtitle="by priority over time" timeRange={trendRange} onTimeRangeChange={setTrendRange}>
            <EnterpriseIncidentChart data={trendData} />
          </GrafanaPanel>
          <GrafanaPanel title="🔎 Affected Services & Errors" subtitle="from latest pipeline run">
            <AffectedServicesPanel incidents={recentIncidents} />
          </GrafanaPanel>
        </div>
      </div>

      {/* ═══ INCIDENT INTELLIGENCE — Two Panel Layout ═══ */}
      {(
        <div className="animate-in animate-in-delay-2">

          <IncidentSummaryBar groups={incidentGroups} rcaList={rcaDetails} incidents={recentIncidents} />

          {/* Full-width Error Logs Table Below */}
          {recentIncidents.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <GrafanaPanel title="📋 Real-Time Error Logs" subtitle={`${recentIncidents.length} incidents from Azure`}>
                <ErrorLogsTableEnterprise incidents={recentIncidents} />
              </GrafanaPanel>
            </div>
          )}
        </div>
      )}

      {/* ═══ INCIDENT DISTRIBUTION + ERROR LOGS TABLE ═══ */}
      <div className="grafana-grid animate-in animate-in-delay-2">
        <div className="grafana-grid-row row-40-60">
          <GrafanaPanel title="🎯 Incident Distribution" subtitle="by priority & status">
            <IncidentCategoryDonut incidents={recentIncidents} dashboard={dashboard} />
          </GrafanaPanel>
          <GrafanaPanel title="📋 Error Logs — Incident Source" subtitle={`${recentIncidents.length} incidents detected`}>
            {recentIncidents.length === 0 ? (
              <EmptyState icon="📋" title="No incidents" text="Run the pipeline to detect incidents" />
            ) : (
              <ErrorLogsTable incidents={recentIncidents} />
            )}
          </GrafanaPanel>
        </div>
      </div>

      {/* ═══ INCIDENT TIMELINE + TOP ISSUES ═══ */}
      <div className="grafana-grid animate-in animate-in-delay-2">
        <div className="grafana-grid-row row-50-50">
          <GrafanaPanel title="⏱️ Incident Timeline" subtitle="chronological event flow">
            {recentIncidents.length === 0 ? (
              <EmptyState icon="⏱️" title="No events" text="Run the pipeline to see the timeline" />
            ) : (
              <IncidentTimeline incidents={recentIncidents} />
            )}
          </GrafanaPanel>
          <GrafanaPanel title="Top Recurring Issues" subtitle={`${topIssuesData.length} patterns`}>
            {topIssuesData.length === 0 ? (
              <EmptyState icon="🔍" title="No patterns" text="Run the pipeline to detect patterns" />
            ) : (
              <TopIssuesHorizontalBar issues={topIssuesData} />
            )}
          </GrafanaPanel>
        </div>
      </div>

      {/* ---- SECTION 3: PERFORMANCE ANALYTICS ---- */}
      <SectionHeader icon="📊" color="#06b6d4" title="Performance Analytics" desc="Log volume, response times, SLO tracking & resolution metrics" />

      {/* ═══ LOG VOLUME + RESPONSE TIME ═══ */}
      <div className="grafana-grid animate-in animate-in-delay-3">
        <div className="grafana-grid-row row-50-50">
          <GrafanaPanel title="Log Ingestion Volume" subtitle="by level" timeRange={logVolumeRange} onTimeRangeChange={setLogVolumeRange}>
            <LogVolumeAreaChart data={logVolumeData} />
          </GrafanaPanel>
          <GrafanaPanel title="Response Time Distribution" subtitle="across services">
            <ResponseTimeChart services={services} />
          </GrafanaPanel>
        </div>
      </div>

      {/* ═══ SLO + MTTR ═══ */}
      <div className="grafana-grid animate-in animate-in-delay-2">
        <div className="grafana-grid-row row-50-50">
          <GrafanaPanel title="SLO Compliance" subtitle="error budget tracking">
            <SLOProgressChart sloData={sloData} />
          </GrafanaPanel>
          <GrafanaPanel title="MTTR by Priority" subtitle="mean time to resolve">
            <MTTRBarChart mttrData={mttrData} />
          </GrafanaPanel>
        </div>
      </div>

      {/* ---- SECTION 4: OPERATIONS LOG ---- */}
      <SectionHeader icon="📋" color="#f59e0b" title="Operations Log" desc="Pipeline execution history & audit trail" />

      {/* ═══ PIPELINE RUN HISTORY ═══ */}
      <div className="grafana-grid animate-in animate-in-delay-3">
        <GrafanaPanel title="Pipeline Run History" subtitle={`${recentRuns.length} runs`}>
          {recentRuns.length === 0 ? (
            <EmptyState icon="🚀" title="No pipeline runs" text="Click 'Run Pipeline' to start" />
          ) : (
            <div style={{ margin: '-16px -20px -20px', overflow: 'auto' }}>
              <table className="data-table">
                <thead><tr><th>Status</th><th>Trigger</th><th>Logs</th><th>P1</th><th>P2</th><th>P3</th><th>Emails</th><th>Duration</th><th>Time</th></tr></thead>
                <tbody>
                  {recentRuns.map((run) => (
                    <tr key={run.id}>
                      <td><span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span className={`status-dot ${run.status === 'SUCCESS' ? 'success' : run.status === 'FAILED' ? 'error' : 'running'}`} />{run.status}</span></td>
                      <td>{run.trigger_type}</td>
                      <td>{run.logs_processed}</td>
                      <td style={{ color: run.p1_count > 0 ? '#ef4444' : '#94a3b8', fontWeight: run.p1_count > 0 ? 700 : 400 }}>{run.p1_count}</td>
                      <td style={{ color: run.p2_count > 0 ? '#f59e0b' : '#94a3b8', fontWeight: run.p2_count > 0 ? 700 : 400 }}>{run.p2_count}</td>
                      <td>{run.p3_count}</td>
                      <td>{run.emails_sent}</td>
                      <td>{run.duration_seconds ? `${run.duration_seconds}s` : '—'}</td>
                      <td style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{formatDate(run.started_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </GrafanaPanel>
      </div>

      {/* ═══ INCIDENT MODAL ═══ */}
      {selectedIncident && <IncidentModal incident={selectedIncident} onClose={() => setSelectedIncident(null)} />}
    </div>
  );
}


/* ═════════════════════════════════════════════════
   SUB-COMPONENTS — Charts & Cards
   ═════════════════════════════════════════════════ */

/* ─── AI Insight Bar ─── */
function AIInsightBar({ dashboard, goldenSignals, healthSummary }) {
  const logs = dashboard?.logs?.total || 0;
  const incidents = dashboard?.incidents?.total || 0;
  const p1 = dashboard?.incidents?.p1 || 0;
  const down = healthSummary?.unhealthy || 0;

  let msg = '';
  if (down > 0) msg += `⛔ ${down} service(s) are currently DOWN. `;
  if (p1 > 0) msg += `🔴 ${p1} critical P1 incident(s) require immediate attention. `;
  if (incidents > 0) msg += `${incidents} incident(s) from ${logs.toLocaleString()} logs analyzed. `;
  if (!msg) msg = '✅ All systems healthy — no critical issues detected.';

  return (
    <div className="ai-insight-banner animate-in">
      <div className="ai-insight-icon">🤖</div>
      <div className="ai-insight-text"><strong>AI Analysis</strong> — {msg}</div>
    </div>
  );
}

/* ─── Health Summary Pill ─── */
function HealthSummaryPill({ label, count, color }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: `${color}10`, border: `1px solid ${color}30`, borderRadius: 20, padding: '4px 12px' }}>
      <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
      <span style={{ fontSize: 12, fontWeight: 700, color }}>{count}</span>
      <span style={{ fontSize: 11, color: '#64748b' }}>{label}</span>
    </div>
  );
}

/* ─── Affected Services Panel (replaces broken Error Category Breakdown) ─── */
function AffectedServicesPanel({ incidents }) {
  if (!incidents || incidents.length === 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 200, color: '#94a3b8' }}>
        <div style={{ fontSize: 32, marginBottom: 8 }}>🔍</div>
        <div style={{ fontSize: 13, fontWeight: 600 }}>No incidents detected</div>
        <div style={{ fontSize: 11, marginTop: 4 }}>Run the pipeline to analyze logs</div>
      </div>
    );
  }

  const PRIORITY_COLORS = { P1: '#ef4444', P2: '#f59e0b', P3: '#10b981' };
  const PRIORITY_ICONS = { P1: '🔴', P2: '🟡', P3: '🟢' };

  // Group by affected service
  const serviceMap = {};
  incidents.forEach((inc) => {
    const svc = inc.source_service || 'Unknown Service';
    if (!serviceMap[svc]) serviceMap[svc] = { count: 0, incidents: [], priorities: new Set() };
    serviceMap[svc].count++;
    serviceMap[svc].incidents.push(inc);
    serviceMap[svc].priorities.add(inc.priority);
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 320, overflowY: 'auto' }}>
      {/* Service summary pills */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 4 }}>
        {Object.entries(serviceMap).map(([svc, data]) => {
          const topPriority = data.priorities.has('P1') ? 'P1' : data.priorities.has('P2') ? 'P2' : 'P3';
          const color = PRIORITY_COLORS[topPriority];
          return (
            <div key={svc} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: `${color}10`, border: `1px solid ${color}30`,
              borderRadius: 8, padding: '4px 10px', fontSize: 11, fontWeight: 600, color,
            }}>
              <span style={{ fontSize: 10 }}>☁️</span> {svc} <span style={{ background: color, color: '#fff', borderRadius: 10, padding: '1px 6px', fontSize: 10 }}>{data.count}</span>
            </div>
          );
        })}
      </div>

      {/* Incident cards */}
      {incidents.slice(0, 8).map((inc, idx) => {
        const pColor = PRIORITY_COLORS[inc.priority] || '#94a3b8';
        const desc = inc.description || '';
        // Extract the actual error text (after "Actual error samples:" if present)
        const errorPreview = desc.includes('Actual error samples:')
          ? desc.split('Actual error samples:')[1]?.trim()?.split('\n').slice(0, 2).join(' | ')
          : desc.slice(0, 120);
        return (
          <div key={inc.id || idx} style={{
            display: 'flex', flexDirection: 'column', gap: 4,
            background: '#fafbfc', borderRadius: 10, padding: '10px 12px',
            borderLeft: `3px solid ${pColor}`, transition: 'all 0.2s',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 12 }}>{PRIORITY_ICONS[inc.priority] || '⚪'}</span>
                <span style={{ fontSize: 12, fontWeight: 700, color: '#0f172a' }}>{inc.title || 'Incident'}</span>
              </div>
              <span style={{
                fontSize: 10, fontWeight: 700, color: '#3b82f6',
                background: '#eff6ff', padding: '2px 8px', borderRadius: 6,
              }}>{inc.source_service || 'Unknown'}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10, color: '#64748b' }}>
              <span>📁 {inc.category || 'N/A'}</span>
              <span>•</span>
              <span style={{ color: pColor, fontWeight: 600 }}>{inc.priority}</span>
              <span>•</span>
              <span>{inc.status || 'OPEN'}</span>
            </div>
            {errorPreview && (
              <div style={{
                fontSize: 10, color: '#ef4444', background: '#fef2f2',
                padding: '4px 8px', borderRadius: 6, marginTop: 2,
                fontFamily: 'monospace', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              }}>
                ⚠ {errorPreview}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
/* ─── Live Service Card (Real HTTP health check) ─── */
function LiveServiceCard({ service, incidentGroups }) {
  const { status_code, status_text, response_time_ms, healthy, last_checked, short_name, description, category, incident_count, incident_severity, metrics } = service;
  const [expanded, setExpanded] = useState(false);

  const isConfigured = healthy !== null;
  const hasIncident = (incident_count || 0) > 0;

  // Health status is purely real-time (green/red). Incidents are informational (amber).
  const borderColor = !isConfigured ? '#cbd5e1' : healthy ? (hasIncident ? '#f59e0b' : '#10b981') : '#ef4444';
  const bgColor = !isConfigured ? '#f8fafc' : healthy ? (hasIncident ? '#fffbeb' : '#f0fdf4') : '#fef2f2';
  const statusColor = !isConfigured ? '#94a3b8' : healthy ? '#10b981' : '#ef4444';

  // Status label shows real-time health
  const statusLabel = !isConfigured ? 'NOT CONFIGURED' : healthy ? 'ONLINE' : 'DOWN';

  // Find related incidents from incidentGroups
  const relatedIncidents = (incidentGroups || []).filter((g) => {
    const src = (g.source_service || '').toLowerCase();
    const sid = service.id.toLowerCase();
    return src.includes(sid.replace('azure-', '').replace('-', ' ')) ||
      (sid === 'azure-front-door' && (src.includes('front door') || src.includes('cdn'))) ||
      (sid === 'azure-waf' && src.includes('waf')) ||
      (sid === 'azure-app-service' && (src.includes('app service') || src.includes('appservice'))) ||
      (sid === 'azure-blob-storage' && (src.includes('blob') || src.includes('storage'))) ||
      (sid === 'azure-app-gateway' && src.includes('app gateway'));
  }).sort((a, b) => {
    const sevOrder = { P1: 0, P2: 1, P3: 2 };
    return (sevOrder[a.http_status_code] || 3) - (sevOrder[b.http_status_code] || 3) || (b.total_occurrences || 0) - (a.total_occurrences || 0);
  });
  const incidentCount = hasIncident ? incident_count : relatedIncidents.reduce((s, g) => s + (g.total_occurrences || 0), 0);

  const ICONS = { globe: '🌐', shuffle: '🔀', settings: '⚙️', server: '🖥️', database: '📦', shield: '🛡️', activity: '📊', cpu: '💻' };
  const SEV_COLORS = { P1: '#ef4444', P2: '#f59e0b', P3: '#64748b' };

  return (
    <div className="infra-card" style={{
      background: bgColor, border: `2px solid ${borderColor}`, borderRadius: 14,
      padding: '16px 18px', position: 'relative', overflow: 'hidden',
      cursor: relatedIncidents.length > 0 ? 'pointer' : 'default',
    }} onClick={() => relatedIncidents.length > 0 && setExpanded(!expanded)}>
      {/* Top accent */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: statusColor }} />

      {/* Animated pulse for down services */}
      {healthy === false && (
        <div style={{ position: 'absolute', top: 10, right: 10, width: 10, height: 10, borderRadius: '50%', background: '#ef4444', boxShadow: '0 0 12px #ef4444', animation: 'pulse 1.2s infinite' }} />
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <div>
          <div style={{ fontSize: 22, marginBottom: 4 }}>{ICONS[service.icon] || '☁️'}</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#0f172a' }}>{short_name}</div>
          <div style={{ fontSize: 11, color: '#64748b' }}>{description}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          {/* Status badge */}
          <div style={{
            padding: '3px 10px', borderRadius: 20, fontSize: 10, fontWeight: 800,
            background: `${statusColor}15`, color: statusColor,
            border: `1px solid ${statusColor}30`,
            letterSpacing: '0.5px',
          }}>
            {statusLabel}
          </div>
          {/* Incident count badge (amber info, not a health indicator) */}
          {hasIncident && healthy && (
            <div style={{
              padding: '2px 8px', borderRadius: 12, fontSize: 9, fontWeight: 700,
              background: '#fef3c7', color: '#92400e', marginTop: 4,
              border: '1px solid #fcd34d',
            }}>
              ⚠ {incident_count} LOG EVENTS
            </div>
          )}
        </div>
      </div>

      {/* HTTP Status + Response Time */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
        {isConfigured && (
          <>
            <span style={{
              fontSize: 11, padding: '3px 8px', borderRadius: 6, fontWeight: 700, fontFamily: 'monospace',
              background: (status_code >= 200 && status_code < 400) ? '#dcfce7' : status_code > 0 ? '#fecaca' : '#f1f5f9',
              color: (status_code >= 200 && status_code < 400) ? '#166534' : status_code > 0 ? '#991b1b' : '#64748b',
            }}>
              {status_code > 0 ? `HTTP ${status_code}` : (metrics?.state || '—')}
            </span>
            {response_time_ms > 0 && (
              <span style={{
                fontSize: 11, padding: '3px 8px', borderRadius: 6, fontWeight: 600,
                background: response_time_ms < 200 ? '#dbeafe' : response_time_ms < 1000 ? '#fef3c7' : '#fecaca',
                color: response_time_ms < 200 ? '#1d4ed8' : response_time_ms < 1000 ? '#92400e' : '#991b1b',
              }}>
                {response_time_ms}ms
              </span>
            )}
          </>
        )}
        <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 6, background: '#f1f5f9', color: '#64748b', fontWeight: 500 }}>
          {category}
        </span>
      </div>

      {/* Status text */}
      {isConfigured && (
        <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {status_text}
        </div>
      )}

      {/* Incident summary — clickable to expand */}
      {incidentCount > 0 && (
        <div style={{ marginTop: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 4 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#ef4444' }}>
              ⚠️ {incidentCount} incident events
            </span>
            {relatedIncidents.length > 0 && (
              <span style={{ fontSize: 10, color: '#94a3b8', fontWeight: 500 }}>
                {expanded ? '▲ collapse' : '▼ details'}
              </span>
            )}
          </div>

          {/* Expanded incident details */}
          {expanded && relatedIncidents.length > 0 && (
            <div style={{
              marginTop: 8, padding: '8px 10px', borderRadius: 8,
              background: 'rgba(0,0,0,0.03)', border: '1px solid rgba(0,0,0,0.06)',
              maxHeight: 180, overflowY: 'auto',
            }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#475569', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Detected Incidents:
              </div>
              {relatedIncidents.slice(0, 8).map((g, i) => {
                const sev = g.http_status_code || 'P3';
                return (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'flex-start', gap: 6, marginBottom: 5,
                    padding: '4px 0', borderBottom: i < relatedIncidents.length - 1 ? '1px solid rgba(0,0,0,0.04)' : 'none',
                  }}>
                    <span style={{
                      fontSize: 9, fontWeight: 800, padding: '1px 6px', borderRadius: 4, flexShrink: 0,
                      background: `${SEV_COLORS[sev] || '#94a3b8'}18`,
                      color: SEV_COLORS[sev] || '#94a3b8',
                      border: `1px solid ${SEV_COLORS[sev] || '#94a3b8'}30`,
                    }}>
                      {sev}
                    </span>
                    <div style={{ fontSize: 10, color: '#334155', lineHeight: 1.3 }}>
                      {g.category_name || g.description || g.error_signature || 'Unknown incident'}
                      {g.total_occurrences > 1 && (
                        <span style={{ color: '#94a3b8', marginLeft: 4 }}>({g.total_occurrences}x)</span>
                      )}
                    </div>
                  </div>
                );
              })}
              {relatedIncidents.length > 8 && (
                <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 4 }}>
                  +{relatedIncidents.length - 8} more...
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Last checked */}
      {last_checked && (
        <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 4 }}>
          Checked: {new Date(last_checked).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}

/* ─── System Health Radar Chart — Real-Time Service Health ─── */
function SystemRadarChart({ healthData, goldenSignals, services }) {
  const [selectedAxis, setSelectedAxis] = useState(null);

  // Build radar axes from real health check services
  const svcIcons = { 'Front Door': '🌐', 'WAF': '🛡️', 'App Gateway': '⚙️', 'APIM': '🖥️', 'App Service': '📦', 'Blob Storage': '💾', 'Log Analytics': '📊', 'CloudGuard API': '💻' };
  const svcColors = { 'Front Door': '#6366f1', 'WAF': '#10b981', 'App Gateway': '#f59e0b', 'APIM': '#3b82f6', 'App Service': '#8b5cf6', 'Blob Storage': '#0ea5e9', 'Log Analytics': '#ec4899', 'CloudGuard API': '#14b8a6' };

  const computeServiceScore = (svc) => {
    if (svc.healthy === null) return 50;
    if (!svc.healthy) return 0;
    const ms = svc.response_time_ms || 0;
    const m = svc.metrics || {};
    const err5xx = m.error_rate_5xx || 0;
    const failPct = m.failure_pct || 0;
    const avail = m.availability_pct;
    let score = 100;
    if (ms > 500) score -= 30;
    else if (ms > 200) score -= 15;
    else if (ms > 100) score -= 5;
    if (err5xx > 5) score -= 40;
    else if (err5xx > 1) score -= 15;
    if (failPct > 10) score -= 30;
    else if (failPct > 2) score -= 10;
    if (avail !== undefined && avail < 99) score -= 30;
    return Math.max(0, Math.min(100, score));
  };

  const axisDetails = (services || []).filter(s => s.id !== 'cloudguard-backend').map(svc => {
    const name = svc.short_name || svc.name;
    const score = computeServiceScore(svc);
    const ms = svc.response_time_ms || 0;
    const m = svc.metrics || {};
    const isUp = svc.healthy === true;
    const isDown = svc.healthy === false;

    const metrics = [
      { label: 'Status', value: isUp ? 'ONLINE' : isDown ? 'DOWN' : 'N/A', status: isUp ? 'good' : isDown ? 'critical' : 'info' },
      { label: 'Response', value: ms > 0 ? `${ms}ms` : '-', status: ms < 100 ? 'good' : ms < 500 ? 'warning' : 'critical' },
      { label: 'Health Score', value: `${score}/100`, status: score >= 80 ? 'good' : score >= 50 ? 'warning' : 'critical' },
    ];
    if (m.request_count !== undefined) metrics.push({ label: 'Requests', value: m.request_count.toLocaleString(), status: 'info' });
    if (m.error_rate_5xx !== undefined) metrics.push({ label: '5xx Rate', value: `${m.error_rate_5xx}%`, status: m.error_rate_5xx < 1 ? 'good' : m.error_rate_5xx < 5 ? 'warning' : 'critical' });
    if (m.availability_pct !== undefined) metrics.push({ label: 'Availability', value: `${m.availability_pct}%`, status: m.availability_pct >= 99 ? 'good' : 'critical' });
    if (m.healthy_backends !== undefined) metrics.push({ label: 'Backends', value: `${m.healthy_backends} up, ${m.unhealthy_backends || 0} down`, status: (m.unhealthy_backends || 0) === 0 ? 'good' : 'critical' });
    if (m.query_latency_ms !== undefined) metrics.push({ label: 'Query Time', value: `${m.query_latency_ms}ms`, status: m.query_latency_ms < 500 ? 'good' : 'warning' });

    return {
      key: svc.id, label: name, icon: svcIcons[name] || '📡',
      color: svcColors[name] || '#6366f1', score,
      description: `Real-time health check for ${name} (${svc.category || 'Azure'}). Checked via ${svc.id.includes('front-door') || svc.id.includes('waf') ? 'HTTP ping to www.icicipruamc.com' : svc.id.includes('apim') ? 'HTTP ping to APIM Front Door' : svc.id.includes('app-service') || svc.id.includes('app-gateway') ? 'Azure Resource State API' : svc.id.includes('blob') ? 'Azure Monitor Availability Metrics' : svc.id.includes('log-analytics') ? 'Live KQL query execution' : 'Direct ping'}. Status: ${svc.status_text || 'Unknown'}.`,
      metrics,
      interpretation: isDown ? `${name} is currently DOWN. Status: ${svc.status_text}. Immediate attention required.` :
        score >= 80 ? `${name} is healthy and performing well. Response time: ${ms}ms.` :
        score >= 50 ? `${name} is operational but showing some degradation. Monitor closely.` :
        `${name} has significant issues. Check Azure Portal for details.`,
      recommendation: isDown ? `Check Azure Portal for ${name} status. Verify network connectivity and resource provisioning state.` :
        score >= 80 ? 'No action needed. Service is performing within normal parameters.' :
        `Review ${name} metrics in Azure Portal. Check for configuration changes or upstream issues.`,
    };
  });

  // If no services yet, show loading
  if (!axisDetails.length) {
    return <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>Loading health check data...</div>;
  }

  const overallScore = Math.round(axisDetails.reduce((s, a) => s + a.score, 0) / axisDetails.length);
  const downCount = axisDetails.filter(a => a.score === 0).length;

  const data = {
    labels: axisDetails.map(a => a.label),
    datasets: [{
      label: 'Health Score',
      data: axisDetails.map(a => a.score),
      backgroundColor: downCount > 0 ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
      borderColor: downCount > 0 ? '#ef4444' : '#10b981',
      borderWidth: 2,
      pointBackgroundColor: axisDetails.map(a => a.score >= 80 ? '#10b981' : a.score >= 50 ? '#f59e0b' : '#ef4444'),
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
      pointRadius: 7,
      pointHoverRadius: 10,
    }],
  };

  const options = {
    responsive: true, maintainAspectRatio: false,
    scales: {
      r: {
        angleLines: { color: 'rgba(0,0,0,0.06)' },
        grid: { color: 'rgba(0,0,0,0.06)' },
        pointLabels: { color: '#334155', font: { size: 11, weight: '600' } },
        ticks: { display: false },
        min: 0, max: 100,
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: { ...TOOLTIP, callbacks: { label: (ctx) => { const a = axisDetails[ctx.dataIndex]; return `${a.label}: ${a.score}/100 ${a.score === 0 ? '(DOWN)' : ''}`; } } },
    },
    onClick: (_event, elements) => { if (elements.length > 0) setSelectedAxis(axisDetails[elements[0].index]); },
  };

  const statusColors = { good: '#10b981', warning: '#f59e0b', critical: '#ef4444', info: '#6366f1' };
  const statusBgs = { good: '#f0fdf4', warning: '#fffbeb', critical: '#fef2f2', info: '#eef2ff' };
  const statusLabels = { good: 'Healthy', warning: 'Warning', critical: 'Critical', info: 'Info' };

  return (
    <div style={{ position: 'relative' }}>
      {/* Overall score badge */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: 12, marginBottom: 6 }}>
        <div style={{ padding: '4px 14px', borderRadius: 20, fontSize: 12, fontWeight: 700, background: overallScore >= 80 ? '#f0fdf4' : overallScore >= 50 ? '#fffbeb' : '#fef2f2', color: overallScore >= 80 ? '#10b981' : overallScore >= 50 ? '#f59e0b' : '#ef4444', border: `1px solid ${overallScore >= 80 ? '#10b981' : overallScore >= 50 ? '#f59e0b' : '#ef4444'}25` }}>
          Overall: {overallScore}/100
        </div>
        {downCount > 0 && (
          <div style={{ padding: '4px 14px', borderRadius: 20, fontSize: 12, fontWeight: 700, background: '#fef2f2', color: '#ef4444', border: '1px solid #fecaca' }}>
            {downCount} service(s) DOWN
          </div>
        )}
      </div>

      {/* Chart */}
      <div style={{ height: 280, cursor: 'pointer' }}>
        <Radar data={data} options={options} />
      </div>

      {/* Legend */}
      <div style={{ textAlign: 'center', fontSize: 10, color: '#94a3b8', marginTop: 2 }}>
        <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: '#10b981', marginRight: 3 }}></span> Healthy (80-100)
        <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: '#f59e0b', marginRight: 3, marginLeft: 10 }}></span> Degraded (50-79)
        <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: '#ef4444', marginRight: 3, marginLeft: 10 }}></span> Down (0-49)
      </div>

      {/* Click hint */}
      {!selectedAxis && (
        <div style={{ textAlign: 'center', fontSize: 10, color: '#94a3b8', marginTop: 4, fontStyle: 'italic' }}>
          Click any service point on the radar to see live metrics and details
        </div>
      )}

      {/* ─── Service Drill-Down Panel ─── */}
      {selectedAxis && (
        <div style={{ marginTop: 12, background: 'linear-gradient(135deg, #fafbff, #f8fafc)', border: `2px solid ${selectedAxis.color}20`, borderRadius: 14, padding: '18px 20px', position: 'relative', animation: 'fadeIn 0.3s ease' }}>
          <button onClick={() => setSelectedAxis(null)} style={{ position: 'absolute', top: 10, right: 12, background: 'none', border: 'none', fontSize: 18, cursor: 'pointer', color: '#94a3b8', lineHeight: 1 }}>✕</button>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: `${selectedAxis.color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20 }}>{selectedAxis.icon}</div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 800, color: '#0f172a' }}>{selectedAxis.label}</div>
              <div style={{ fontSize: 11, color: '#64748b' }}>{selectedAxis.description.split('.')[0]}.</div>
            </div>
            <div style={{ marginLeft: 'auto', padding: '6px 14px', borderRadius: 20, background: selectedAxis.score >= 80 ? '#f0fdf4' : selectedAxis.score >= 50 ? '#fffbeb' : '#fef2f2', border: `1px solid ${selectedAxis.score >= 80 ? '#10b981' : selectedAxis.score >= 50 ? '#f59e0b' : '#ef4444'}30`, fontSize: 18, fontWeight: 800, color: selectedAxis.score >= 80 ? '#10b981' : selectedAxis.score >= 50 ? '#f59e0b' : '#ef4444' }}>
              {Math.round(selectedAxis.score)}<span style={{ fontSize: 11, fontWeight: 600 }}>/100</span>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(selectedAxis.metrics.length, 4)}, 1fr)`, gap: 8, marginBottom: 14 }}>
            {selectedAxis.metrics.map((m, i) => (
              <div key={i} style={{ background: statusBgs[m.status], border: `1px solid ${statusColors[m.status]}20`, borderRadius: 10, padding: '8px 10px', textAlign: 'center' }}>
                <div style={{ fontSize: 16, fontWeight: 800, color: statusColors[m.status] }}>{m.value}</div>
                <div style={{ fontSize: 9, fontWeight: 600, color: '#64748b', marginTop: 2, textTransform: 'uppercase' }}>{m.label}</div>
              </div>
            ))}
          </div>

          <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 10, padding: '10px 14px', marginBottom: 10 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>How we check this service</div>
            <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5 }}>{selectedAxis.description}</div>
          </div>

          <div style={{ background: selectedAxis.score >= 80 ? '#f0fdf408' : '#fef2f208', border: `1px solid ${selectedAxis.score >= 80 ? '#10b981' : '#ef4444'}15`, borderRadius: 10, padding: '10px 14px' }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: selectedAxis.score >= 80 ? '#10b981' : '#ef4444', textTransform: 'uppercase', marginBottom: 4 }}>Assessment</div>
            <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5 }}>{selectedAxis.interpretation}</div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Service Correlation Chart (Bubble-style bar) ─── */
function ServiceCorrelationChart({ services, incidentGroups }) {
  const svcNames = services.filter((s) => s.healthy !== null).map((s) => s.short_name);
  const responseTimes = services.filter((s) => s.healthy !== null).map((s) => s.response_time_ms || 0);
  const incidents = services.filter((s) => s.healthy !== null).map((s) => {
    const related = (incidentGroups || []).filter((g) => {
      const src = (g.source_service || '').toLowerCase();
      return src.includes(s.id.replace('azure-', '').replace('-', ' '));
    });
    return related.reduce((sum, g) => sum + (g.total_occurrences || 0), 0);
  });

  const data = {
    labels: svcNames,
    datasets: [
      {
        label: 'Response Time (ms)',
        data: responseTimes,
        backgroundColor: responseTimes.map((t) => t < 200 ? 'rgba(16,185,129,0.7)' : t < 500 ? 'rgba(245,158,11,0.7)' : 'rgba(239,68,68,0.7)'),
        borderRadius: 6, barPercentage: 0.5,
        yAxisID: 'y',
      },
      {
        label: 'Incident Events',
        data: incidents,
        backgroundColor: 'rgba(99,102,241,0.8)',
        borderRadius: 6, barPercentage: 0.5,
        yAxisID: 'y1',
      },
    ],
  };

  const options = {
    responsive: true, maintainAspectRatio: false, indexAxis: 'y',
    plugins: { legend: { labels: LEGEND_STYLE }, tooltip: TOOLTIP },
    scales: {
      x: { ticks: TICK_STYLE, grid: GRID_LIGHT, border: { color: '#e2e8f0' } },
      y: { ticks: { ...TICK_STYLE, font: { size: 12, weight: '600' } }, grid: { display: false }, border: { color: '#e2e8f0' } },
      y1: { display: false },
    },
  };

  if (svcNames.length === 0) return <EmptyState icon="📊" title="No service data" text="Health checks will populate this chart" />;
  return <div style={{ height: 300 }}><Bar data={data} options={options} /></div>;
}

/* ─── Enterprise Incident Chart (Stacked gradient bars) ─── */
function EnterpriseIncidentChart({ data = [] }) {
  if (!data.length) return <EmptyState icon="📊" title="No trend data" text="Run the pipeline to generate incident trends" />;

  const labels = data.map((d) => { const dt = new Date(d.date); return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }); });
  const chartData = {
    labels,
    datasets: [
      { label: 'P1 Critical', data: data.map((d) => d.P1 || 0), backgroundColor: 'rgba(239,68,68,0.85)', borderColor: '#ef4444', borderWidth: 1, borderRadius: 4, barPercentage: 0.7, stack: 'incidents' },
      { label: 'P2 High', data: data.map((d) => d.P2 || 0), backgroundColor: 'rgba(245,158,11,0.85)', borderColor: '#f59e0b', borderWidth: 1, borderRadius: 4, barPercentage: 0.7, stack: 'incidents' },
      { label: 'P3 Medium', data: data.map((d) => d.P3 || 0), backgroundColor: 'rgba(16,185,129,0.85)', borderColor: '#10b981', borderWidth: 1, borderRadius: 4, barPercentage: 0.7, stack: 'incidents' },
    ],
  };

  const options = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { labels: LEGEND_STYLE }, tooltip: TOOLTIP },
    scales: {
      x: { stacked: true, ticks: TICK_STYLE, grid: GRID_LIGHT, border: { color: '#e2e8f0' } },
      y: { stacked: true, ticks: { ...TICK_STYLE, stepSize: 1 }, grid: GRID_LIGHT, border: { color: '#e2e8f0' }, beginAtZero: true },
    },
  };

  return <div style={{ height: 280 }}><Bar data={chartData} options={options} /></div>;
}

/* ─── Error Polar Area Chart ─── */
function ErrorPolarChart({ distribution = [], total = 0 }) {
  if (!distribution.length) return <EmptyState icon="📋" title="No errors" text="Errors will appear after pipeline runs" />;

  const colors = [CHART_COLORS.blue, CHART_COLORS.rose, CHART_COLORS.amber, CHART_COLORS.emerald, CHART_COLORS.violet, CHART_COLORS.cyan, CHART_COLORS.orange, CHART_COLORS.pink];
  const data = {
    labels: distribution.map((d) => d.category || 'Unknown'),
    datasets: [{
      data: distribution.map((d) => d.count),
      backgroundColor: colors.slice(0, distribution.length).map((c) => c + 'bb'),
      borderColor: colors.slice(0, distribution.length),
      borderWidth: 2,
    }],
  };

  const options = {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { ...LEGEND_STYLE, padding: 10 } },
      tooltip: {
        ...TOOLTIP,
        callbacks: { label: (ctx) => { const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0; return ` ${ctx.label}: ${ctx.parsed} (${pct}%)`; } },
      },
    },
    scales: {
      r: { ticks: { display: false }, grid: { color: 'rgba(0,0,0,0.04)' } },
    },
  };

  return <div style={{ height: 280 }}><PolarArea data={data} options={options} /></div>;
}

/* ─── Log Volume Area Chart ─── */
function LogVolumeAreaChart({ data = [] }) {
  if (!data.length) return <EmptyState icon="📈" title="No volume data" text="Log volume appears after ingestion" />;

  const labels = data.map((d) => new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
  const chartData = {
    labels,
    datasets: [
      { label: 'Error', data: data.map((d) => d.ERROR || 0), borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.12)', fill: true, tension: 0.4, borderWidth: 2, pointRadius: 3, pointBackgroundColor: '#ef4444' },
      { label: 'Warning', data: data.map((d) => d.WARNING || 0), borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.1)', fill: true, tension: 0.4, borderWidth: 2, pointRadius: 3, pointBackgroundColor: '#f59e0b' },
      { label: 'Info', data: data.map((d) => d.INFO || 0), borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.08)', fill: true, tension: 0.4, borderWidth: 2, pointRadius: 3, pointBackgroundColor: '#3b82f6' },
    ],
  };

  return (
    <div style={{ height: 260 }}>
      <Line data={chartData} options={{
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: LEGEND_STYLE }, tooltip: TOOLTIP },
        scales: {
          x: { ticks: TICK_STYLE, grid: GRID_LIGHT, border: { color: '#e2e8f0' } },
          y: { ticks: TICK_STYLE, grid: GRID_LIGHT, border: { color: '#e2e8f0' }, beginAtZero: true },
        },
      }} />
    </div>
  );
}

/* ─── Response Time Chart ─── */
function ResponseTimeChart({ services }) {
  const configured = services.filter((s) => s.healthy !== null && s.response_time_ms > 0);
  if (!configured.length) return <EmptyState icon="⏱️" title="No response data" text="Health checks will populate this" />;

  const data = {
    labels: configured.map((s) => s.short_name),
    datasets: [{
      label: 'Response Time (ms)',
      data: configured.map((s) => s.response_time_ms),
      backgroundColor: configured.map((s) => s.response_time_ms < 200 ? 'rgba(16,185,129,0.75)' : s.response_time_ms < 500 ? 'rgba(245,158,11,0.75)' : 'rgba(239,68,68,0.75)'),
      borderColor: configured.map((s) => s.response_time_ms < 200 ? '#10b981' : s.response_time_ms < 500 ? '#f59e0b' : '#ef4444'),
      borderWidth: 1, borderRadius: 8, barPercentage: 0.6,
    }],
  };

  return (
    <div style={{ height: 260 }}>
      <Bar data={data} options={{
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: TOOLTIP },
        scales: {
          x: { ticks: { ...TICK_STYLE, font: { size: 11, weight: '600' } }, grid: { display: false }, border: { color: '#e2e8f0' } },
          y: { ticks: TICK_STYLE, grid: GRID_LIGHT, border: { color: '#e2e8f0' }, beginAtZero: true },
        },
      }} />
    </div>
  );
}

/* ─── SLO Progress Chart ─── */
function SLOProgressChart({ sloData }) {
  if (!sloData) return <EmptyState icon="🎯" title="No SLO data" />;

  const items = [
    { label: 'Availability', value: sloData.availability || 99.9, target: 99.9, color: '#10b981' },
    { label: 'Latency P95', value: sloData.latency_p95_compliance || 95, target: 95, color: '#3b82f6' },
    { label: 'Error Budget', value: sloData.error_budget_remaining || 80, target: 100, color: '#8b5cf6' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 22, padding: '8px 0' }}>
      {items.map((item) => {
        const pct = Math.min((item.value / item.target) * 100, 100);
        return (
          <div key={item.label}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#334155' }}>{item.label}</span>
              <span style={{ fontSize: 13, fontWeight: 700, color: pct >= 90 ? '#10b981' : '#ef4444' }}>{item.value.toFixed(1)}%</span>
            </div>
            <div style={{ height: 10, borderRadius: 5, background: '#f1f5f9', overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${pct}%`, borderRadius: 5, background: `linear-gradient(90deg, ${item.color}, ${item.color}cc)`, transition: 'width 1s ease' }} />
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>Target: {item.target}%</div>
          </div>
        );
      })}
    </div>
  );
}

/* ─── MTTR Bar Chart ─── */
function MTTRBarChart({ mttrData }) {
  if (!mttrData) return <EmptyState icon="⏱️" title="No MTTR data" />;

  const items = [
    { label: 'P1 Critical', value: mttrData.p1_avg_minutes || 0, color: '#ef4444', bg: '#fef2f2' },
    { label: 'P2 High', value: mttrData.p2_avg_minutes || 0, color: '#f59e0b', bg: '#fffbeb' },
    { label: 'P3 Medium', value: mttrData.p3_avg_minutes || 0, color: '#10b981', bg: '#ecfdf5' },
  ];

  return (
    <div style={{ display: 'flex', gap: 16, justifyContent: 'center', padding: '16px 0' }}>
      {items.map((item) => (
        <div key={item.label} style={{ flex: 1, textAlign: 'center', background: item.bg, borderRadius: 14, padding: '20px 16px', border: `1px solid ${item.color}20` }}>
          <div style={{ fontSize: 28, fontWeight: 800, color: item.color }}>{item.value ? `${Math.round(item.value)}m` : '—'}</div>
          <div style={{ fontSize: 12, color: '#64748b', fontWeight: 600, marginTop: 6 }}>{item.label}</div>
        </div>
      ))}
    </div>
  );
}

/* --- Incident Summary Stats Bar --- */
function IncidentSummaryBar({ groups, rcaList, incidents }) {
  const totalEvents = (groups || []).reduce((s, g) => s + (g.total_occurrences || 0), 0);
  const p1Count = (incidents || []).filter(i => i.priority === 'P1').length;
  const p2Count = (incidents || []).filter(i => i.priority === 'P2').length;

  const stats = [
    { label: 'Error Clusters', value: (groups || []).length, icon: '📁', color: '#6366f1' },
    { label: 'Total Events', value: totalEvents.toLocaleString(), icon: '📊', color: '#3b82f6' },
    { label: 'RCA Findings', value: (rcaList || []).length, icon: '🧠', color: '#8b5cf6' },
    { label: 'P1 Critical', value: p1Count, icon: '🔴', color: '#ef4444' },
    { label: 'P2 High', value: p2Count, icon: '🟡', color: '#f59e0b' },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 16 }}>
      {stats.map((s, i) => (
        <div key={i} style={{
          background: `linear-gradient(135deg, ${s.color}08, ${s.color}03)`,
          border: `1px solid ${s.color}18`,
          borderRadius: 12, padding: '14px 16px', textAlign: 'center',
        }}>
          <div style={{ fontSize: 12, marginBottom: 3 }}>{s.icon}</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: s.color, lineHeight: 1.1 }}>{s.value}</div>
          <div style={{ fontSize: 10, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.4px', marginTop: 3 }}>{s.label}</div>
        </div>
      ))}
    </div>
  );
}

/* --- Self-Loading Wrappers (fetch data independently as failsafe) --- */
function SelfLoadingErrorClusters({ parentData, incidents }) {
  const [localData, setLocalData] = useState([]);
  useEffect(() => {
    if (parentData && parentData.length > 0) {
      setLocalData(parentData);
      return;
    }
    // Parent didn't provide data — fetch directly
    fetch(`${API_URL}/api/analytics/incident-groups?days=30`)
      .then(r => r.json())
      .then(json => {
        const items = json?.data || [];
        console.log('[SelfLoad] Error Clusters fetched:', items.length);
        setLocalData(items);
      })
      .catch(e => console.error('[SelfLoad] Error Clusters fetch failed:', e));
  }, [parentData]);

  const data = (parentData && parentData.length > 0) ? parentData : localData;
  return <ErrorClustersPanel groups={data} incidents={incidents} />;
}

function SelfLoadingRCA({ parentData }) {
  const [localData, setLocalData] = useState([]);
  useEffect(() => {
    if (parentData && parentData.length > 0) {
      setLocalData(parentData);
      return;
    }
    fetch(`${API_URL}/api/analytics/rca-details?days=30`)
      .then(r => r.json())
      .then(json => {
        const items = json?.data || [];
        console.log('[SelfLoad] RCA fetched:', items.length);
        setLocalData(items);
      })
      .catch(e => console.error('[SelfLoad] RCA fetch failed:', e));
  }, [parentData]);

  const data = (parentData && parentData.length > 0) ? parentData : localData;
  return <RCAPanelEnterprise rcaList={data} />;
}

/* --- Error Clusters Panel (Left Rectangle) — self-contained --- */
function ErrorClustersPanel({ groups: parentGroups, incidents }) {
  const [expandedId, setExpandedId] = useState(null);
  const [ownData, setOwnData] = useState([]);
  const [loaded, setLoaded] = useState(false);

  // Always fetch our own data to guarantee display
  useEffect(() => {
    fetch(`${API_URL}/api/analytics/incident-groups?days=30`)
      .then(r => r.json())
      .then(json => { setOwnData(json?.data || []); setLoaded(true); })
      .catch(() => setLoaded(true));
  }, []);

  const groups = (parentGroups && parentGroups.length > 0) ? parentGroups : ownData;
  const sorted = [...(groups || [])].sort((a, b) => (b.total_occurrences || 0) - (a.total_occurrences || 0));
  const severityColor = (occ) => occ > 200 ? '#ef4444' : occ > 50 ? '#f59e0b' : '#3b82f6';
  const severityLabel = (occ) => occ > 200 ? 'CRITICAL' : occ > 50 ? 'HIGH' : 'MEDIUM';
  const severityBg = (occ) => occ > 200 ? '#fef2f2' : occ > 50 ? '#fffbeb' : '#eff6ff';
  const fmtDate = (d) => d ? new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';

  if (!loaded && sorted.length === 0) return <div style={{ padding: 20, textAlign: 'center', color: '#94a3b8' }}>⟳ Loading error clusters...</div>;
  if (sorted.length === 0) return <EmptyState icon="📁" title="No error clusters" text="Run the pipeline to detect error patterns" />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 520, overflowY: 'auto' }}>
      {sorted.map((g) => {
        const maxOcc = sorted[0]?.total_occurrences || 1;
        const pct = ((g.total_occurrences || 0) / maxOcc) * 100;
        const sc = severityColor(g.total_occurrences);
        const isExpanded = expandedId === g.id;
        const relatedLogs = (incidents || []).filter(inc => {
          const src = (inc.source_service || '').toLowerCase();
          const gSrc = (g.source_service || '').toLowerCase();
          return gSrc && src.includes(gSrc.replace('azure ', '').split('(')[0].trim().toLowerCase());
        }).slice(0, 4);

        return (
          <div key={g.id} style={{
            background: '#fff', border: '1px solid #e2e8f0', borderRadius: 10,
            overflow: 'hidden', transition: 'box-shadow 0.3s',
            boxShadow: isExpanded ? '0 4px 16px rgba(0,0,0,0.08)' : 'none',
          }}>
            <div style={{ height: 3, background: `linear-gradient(90deg, ${sc}, ${sc}40)`, width: `${pct}%`, transition: 'width 0.8s ease' }} />
            <div onClick={() => setExpandedId(isExpanded ? null : g.id)} style={{ padding: '10px 12px', cursor: 'pointer' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 0 }}>
                  <span style={{ padding: '3px 8px', borderRadius: 5, fontSize: 11, fontWeight: 800, background: severityBg(g.total_occurrences), color: sc, letterSpacing: '0.4px', flexShrink: 0 }}>
                    {severityLabel(g.total_occurrences)}
                  </span>
                  <span style={{ fontSize: 14, fontWeight: 700, color: '#0f172a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {g.category_name || g.error_type || 'Unknown'}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 18, fontWeight: 800, color: sc, lineHeight: 1 }}>{(g.total_occurrences || 0).toLocaleString()}</div>
                    <div style={{ fontSize: 9, color: '#94a3b8', fontWeight: 600 }}>EVENTS</div>
                  </div>
                  <span style={{ fontSize: 12, color: '#94a3b8', transition: 'transform 0.3s', transform: isExpanded ? 'rotate(180deg)' : 'rotate(0)' }}>&#9660;</span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {g.source_service && <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 6, background: '#eff6ff', color: '#2563eb', fontWeight: 600 }}>{'☁'} {g.source_service}</span>}
                {g.first_seen && <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 6, background: '#f0fdf4', color: '#166534', fontWeight: 600 }}>{'🕐'} {fmtDate(g.first_seen)}</span>}
              </div>
              {g.description && (
                <div style={{ fontSize: 12, color: '#475569', marginTop: 4, lineHeight: 1.4, overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: isExpanded ? 10 : 2, WebkitBoxOrient: 'vertical' }}>
                  {g.description}
                </div>
              )}
            </div>
            {isExpanded && (
              <div style={{ borderTop: '1px solid #f1f5f9', background: '#fafbff', padding: '10px 14px' }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#6366f1', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 8 }}>
                  Related Error Logs
                </div>
                {relatedLogs.length > 0 ? relatedLogs.map((log, i) => {
                  const pc = { P1: '#ef4444', P2: '#f59e0b', P3: '#10b981' };
                  return (
                    <div key={i} style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '8px 12px', marginBottom: 6, borderLeft: `3px solid ${pc[log.priority] || '#94a3b8'}` }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                        <span style={{ padding: '1px 6px', borderRadius: 4, fontSize: 9, fontWeight: 800, background: `${pc[log.priority] || '#94a3b8'}12`, color: pc[log.priority] || '#94a3b8' }}>{log.priority}</span>
                        <span style={{ fontSize: 11, fontWeight: 700, color: '#0f172a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{(log.title || 'Error').substring(0, 55)}</span>
                      </div>
                      {log.root_cause && (
                        <div style={{ fontSize: 10, color: '#475569', background: '#f8fafc', padding: '4px 8px', borderRadius: 5, fontFamily: 'monospace', lineHeight: 1.4 }}>
                          RCA: {log.root_cause.substring(0, 120)}{log.root_cause.length > 120 ? '...' : ''}
                        </div>
                      )}
                    </div>
                  );
                }) : (
                  <div style={{ fontSize: 11, color: '#94a3b8', fontStyle: 'italic', padding: '6px 0' }}>No specific error logs for this cluster</div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* --- RCA Panel Enterprise (Right Rectangle) — self-contained --- */
function RCAPanelEnterprise({ rcaList: parentList }) {
  const [ownData, setOwnData] = useState([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/api/analytics/rca-details?days=30`)
      .then(r => r.json())
      .then(json => { setOwnData(json?.data || []); setLoaded(true); })
      .catch(() => setLoaded(true));
  }, []);

  const rcaList = (parentList && parentList.length > 0) ? parentList : ownData;
  const sorted = [...(rcaList || [])].sort((a, b) => (b.confidence_score || 0) - (a.confidence_score || 0));
  const fmtDate = (d) => d ? new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';

  if (!loaded && sorted.length === 0) return <div style={{ padding: 20, textAlign: 'center', color: '#94a3b8' }}>⟳ Loading AI analysis...</div>;
  if (sorted.length === 0) return <EmptyState icon="🧠" title="No RCA data" text="AI will analyze root causes after pipeline run" />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 520, overflowY: 'auto' }}>
      {sorted.map((rca) => {
        const pct = Math.round((rca.confidence_score || 0) * 100);
        const cc = pct >= 80 ? '#10b981' : pct >= 50 ? '#f59e0b' : pct >= 20 ? '#3b82f6' : '#94a3b8';
        const ccBg = pct >= 80 ? '#f0fdf4' : pct >= 50 ? '#fffbeb' : '#eff6ff';

        return (
          <div key={rca.id} style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, overflow: 'hidden' }}>
            <div style={{ height: 3, background: `linear-gradient(90deg, ${cc}, ${cc}30)`, width: `${Math.max(pct, 5)}%`, transition: 'width 1s ease' }} />
            <div style={{ padding: '14px 16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
                    <span style={{ padding: '3px 10px', borderRadius: 6, fontSize: 11, fontWeight: 700, background: `${cc}12`, color: cc }}>
                      {rca.root_cause_category || 'Uncategorized'}
                    </span>
                    {rca.analysis_method && (
                      <span style={{ padding: '3px 8px', borderRadius: 6, fontSize: 9, fontWeight: 700, background: '#f5f3ff', color: '#7c3aed' }}>
                        AI: {rca.analysis_method}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5, marginBottom: 8 }}>
                    {(rca.root_cause || 'Analysis pending').substring(0, 200)}
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {rca.affected_component && <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 6, background: '#eff6ff', color: '#2563eb', fontWeight: 600 }}>{rca.affected_component}</span>}
                    {rca.supporting_log_count > 0 && <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 6, background: '#fef3c7', color: '#92400e', fontWeight: 600 }}>{rca.supporting_log_count} logs</span>}
                    {rca.created_at && <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 6, background: '#f1f5f9', color: '#64748b', fontWeight: 600 }}>{fmtDate(rca.created_at)}</span>}
                  </div>
                  {rca.evidence_summary && (
                    <div style={{ marginTop: 8, fontSize: 11, color: '#475569', background: '#f8fafc', padding: '8px 12px', borderRadius: 8, borderLeft: `3px solid ${cc}`, lineHeight: 1.4, fontStyle: 'italic' }}>
                      Evidence: {rca.evidence_summary.substring(0, 150)}
                    </div>
                  )}
                </div>
                <div style={{ textAlign: 'center', flexShrink: 0, width: 70 }}>
                  <div style={{ width: 56, height: 56, borderRadius: '50%', border: `3px solid ${cc}`, display: 'flex', alignItems: 'center', justifyContent: 'center', background: ccBg, margin: '0 auto' }}>
                    <span style={{ fontSize: 16, fontWeight: 800, color: cc }}>{pct}%</span>
                  </div>
                  <div style={{ fontSize: 8, color: '#94a3b8', marginTop: 4, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px' }}>CONFIDENCE</div>
                  <div style={{ fontSize: 9, fontWeight: 700, color: cc, marginTop: 1 }}>{pct >= 80 ? 'HIGH' : pct >= 50 ? 'MEDIUM' : pct >= 20 ? 'LOW' : 'PENDING'}</div>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* --- Error Logs Table Enterprise (Full Width) --- */
function ErrorLogsTableEnterprise({ incidents }) {
  const fmtDate = (d) => d ? new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';
  const pc = { P1: '#ef4444', P2: '#f59e0b', P3: '#10b981' };

  return (
    <div style={{ maxHeight: 400, overflowY: 'auto' }}>
      <div style={{
        display: 'grid', gridTemplateColumns: '55px 1fr 180px 140px 90px',
        gap: 8, padding: '8px 14px', background: '#f8fafc', borderRadius: 8,
        fontSize: 10, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.4px',
        position: 'sticky', top: 0, zIndex: 1,
      }}>
        <span>Sev</span><span>Incident</span><span>Service</span><span>Root Cause</span><span>Time</span>
      </div>
      {(incidents || []).slice(0, 25).map((inc, i) => {
        const c = pc[inc.priority] || '#94a3b8';
        return (
          <div key={i} style={{
            display: 'grid', gridTemplateColumns: '55px 1fr 180px 140px 90px',
            gap: 8, padding: '9px 14px', borderRadius: 6,
            background: i % 2 === 0 ? '#fff' : '#fafbff',
            border: '1px solid transparent',
            transition: 'all 0.15s', cursor: 'default', alignItems: 'center',
          }}
            onMouseEnter={e => { e.currentTarget.style.background = '#f1f5f9'; e.currentTarget.style.borderColor = '#e2e8f0'; }}
            onMouseLeave={e => { e.currentTarget.style.background = i % 2 === 0 ? '#fff' : '#fafbff'; e.currentTarget.style.borderColor = 'transparent'; }}
          >
            <span style={{ padding: '2px 8px', borderRadius: 6, fontSize: 10, fontWeight: 800, background: `${c}12`, color: c, textAlign: 'center' }}>{inc.priority}</span>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#0f172a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{inc.title || 'Incident'}</span>
            <span style={{ fontSize: 11, color: '#64748b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{inc.source_service || '-'}</span>
            <span style={{ fontSize: 10, padding: '2px 7px', borderRadius: 5, background: '#f5f3ff', color: '#7c3aed', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{(inc.root_cause_category || '-').substring(0, 20)}</span>
            <span style={{ fontSize: 10, color: '#94a3b8', fontFamily: 'monospace' }}>{fmtDate(inc.created_at)}</span>
          </div>
        );
      })}
    </div>
  );
}

/* ─── Incident Groups Chart (Horizontal Bar) ─── */
function IncidentGroupsChart({ groups }) {
  const sorted = [...groups].sort((a, b) => (b.total_occurrences || 0) - (a.total_occurrences || 0));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {sorted.map((g) => {
        const maxOcc = sorted[0]?.total_occurrences || 1;
        const pct = ((g.total_occurrences || 0) / maxOcc) * 100;
        const isHigh = (g.total_occurrences || 0) > 100;

        return (
          <div key={g.id} style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '14px 18px', borderLeft: `4px solid ${isHigh ? '#ef4444' : '#3b82f6'}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#0f172a' }}>{g.category_name || g.error_type || 'Unknown'}</div>
              <div style={{ fontSize: 18, fontWeight: 800, color: isHigh ? '#ef4444' : '#3b82f6' }}>{g.total_occurrences || 0}</div>
            </div>
            <div style={{ height: 6, borderRadius: 3, background: '#f1f5f9', overflow: 'hidden', marginBottom: 8 }}>
              <div style={{ height: '100%', width: `${pct}%`, borderRadius: 3, background: isHigh ? 'linear-gradient(90deg, #ef4444, #f97316)' : 'linear-gradient(90deg, #3b82f6, #6366f1)', transition: 'width 0.8s ease' }} />
            </div>
            <div style={{ display: 'flex', gap: 12, fontSize: 11, color: '#64748b' }}>
              {g.source_service && <span>☁️ {g.source_service}</span>}
              {g.description && <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 400 }}>💡 {g.description}</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ─── Top Issues Horizontal Bar ─── */
function TopIssuesHorizontalBar({ issues }) {
  const top = issues.slice(0, 8);
  const data = {
    labels: top.map((i) => (i.title || i.category || i.error_signature || 'Unknown').substring(0, 35)),
    datasets: [{
      label: 'Events',
      data: top.map((i) => i.count || i.total_occurrences || 0),
      backgroundColor: top.map((_, idx) => [CHART_COLORS.rose, CHART_COLORS.amber, CHART_COLORS.blue, CHART_COLORS.emerald, CHART_COLORS.violet, CHART_COLORS.cyan, CHART_COLORS.orange, CHART_COLORS.pink][idx % 8] + 'cc'),
      borderRadius: 6, barPercentage: 0.7,
    }],
  };

  return (
    <div style={{ height: 300 }}>
      <Bar data={data} options={{
        indexAxis: 'y', responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: TOOLTIP },
        scales: {
          x: { ticks: TICK_STYLE, grid: GRID_LIGHT, border: { color: '#e2e8f0' }, beginAtZero: true },
          y: { ticks: { ...TICK_STYLE, font: { size: 11 } }, grid: { display: false }, border: { color: '#e2e8f0' } },
        },
      }} />
    </div>
  );
}

/* ─── RCA Card ─── */
function RCACard({ rca }) {
  const cc = rca.confidence_score >= 0.8 ? '#10b981' : rca.confidence_score >= 0.5 ? '#f59e0b' : '#ef4444';
  const pct = Math.round((rca.confidence_score || 0) * 100);

  return (
    <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '18px 22px', borderLeft: `4px solid ${cc}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#0f172a', marginBottom: 4 }}>{rca.root_cause_category || 'Unknown'}</div>
          <div style={{ fontSize: 13, color: '#475569', lineHeight: 1.5 }}>{rca.root_cause}</div>
        </div>
        <div style={{ textAlign: 'center', marginLeft: 16 }}>
          <div style={{ width: 52, height: 52, borderRadius: '50%', border: `3px solid ${cc}`, display: 'flex', alignItems: 'center', justifyContent: 'center', background: `${cc}10` }}>
            <span style={{ fontSize: 14, fontWeight: 800, color: cc }}>{pct}%</span>
          </div>
          <div style={{ fontSize: 9, color: '#94a3b8', marginTop: 4, fontWeight: 600 }}>CONFIDENCE</div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {rca.affected_component && <span style={{ fontSize: 11, padding: '3px 10px', borderRadius: 8, background: '#eff6ff', color: '#2563eb', fontWeight: 600 }}>🎯 {rca.affected_component}</span>}
        {rca.supporting_log_count && <span style={{ fontSize: 11, padding: '3px 10px', borderRadius: 8, background: '#fef3c7', color: '#92400e', fontWeight: 600 }}>📊 {rca.supporting_log_count} logs</span>}
        {rca.analysis_method && <span style={{ fontSize: 11, padding: '3px 10px', borderRadius: 8, background: '#f5f3ff', color: '#7c3aed', fontWeight: 600 }}>🤖 {rca.analysis_method}</span>}
      </div>
      {rca.evidence_summary && <div style={{ marginTop: 10, fontSize: 12, color: '#64748b', fontStyle: 'italic', background: '#f8fafc', padding: '8px 12px', borderRadius: 8 }}>💡 {rca.evidence_summary}</div>}
    </div>
  );
}

/* ─── Incident Row ─── */
function IncidentRow({ incident, onClick }) {
  const pc = { P1: '#ef4444', P2: '#f59e0b', P3: '#10b981' };
  return (
    <div onClick={onClick} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', borderBottom: '1px solid #f1f5f9', cursor: 'pointer', transition: 'background 0.2s' }}
      onMouseEnter={(e) => { e.currentTarget.style.background = '#f8fafc'; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}>
      <span style={{ padding: '2px 8px', borderRadius: 12, fontSize: 10, fontWeight: 700, background: `${pc[incident.priority] || '#94a3b8'}15`, color: pc[incident.priority] || '#94a3b8' }}>{incident.priority}</span>
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#0f172a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{incident.title || 'Incident'}</div>
        <div style={{ fontSize: 11, color: '#94a3b8' }}>{incident.source_service || 'Azure'} · {formatDate(incident.created_at)}</div>
      </div>
    </div>
  );
}

/* --- Section Header --- */
function SectionHeader({ icon, color, title, desc }) {
  const hexToRgba = (hex, alpha) => {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${alpha})`;
  };
  return (
    <div className="section-divider">
      <div className="section-divider-icon" style={{ background: hexToRgba(color, 0.12) }}>
        <span>{icon}</span>
      </div>
      <div className="section-divider-text">
        <h3 style={{ color }}>{title}</h3>
        <p>{desc}</p>
      </div>
      <div className="section-divider-line" />
    </div>
  );
}

/* --- Incident Modal --- */
function IncidentModal({ incident, onClose }) {
  return (
    <div className="ncm-overlay" onClick={onClose}>
      <div className="ncm-modal" style={{ width: 620 }} onClick={(e) => e.stopPropagation()}>
        <div className="ncm-header">
          <div><div className="ncm-title">Incident Details</div><div className="ncm-description">{incident.title}</div></div>
          <button className="ncm-close" onClick={onClose}>✕</button>
        </div>
        <div className="ncm-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <DetailField label="Priority" value={incident.priority} />
            <DetailField label="Service" value={incident.source_service || '—'} />
            <DetailField label="Created" value={formatDate(incident.created_at)} />
            <DetailField label="Category" value={incident.category || '—'} />
          </div>
          {incident.ai_solution && (
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: 6 }}>AI Resolution</div>
              <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 10, padding: '12px 16px', fontSize: 13, lineHeight: 1.6, maxHeight: 200, overflowY: 'auto', whiteSpace: 'pre-wrap' }}>{incident.ai_solution}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DetailField({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 13, color: 'var(--text-primary)' }}>{value}</div>
    </div>
  );
}

function EmptyState({ icon, title, text }) {
  return (
    <div className="empty-state" style={{ padding: 24 }}>
      <div className="empty-state-icon">{icon}</div>
      <div className="empty-state-title">{title}</div>
      {text && <div className="empty-state-text">{text}</div>}
    </div>
  );
}

/* ─── Date Range Picker Modal ─── */
function DateRangePickerModal({ onRun, onClose, running }) {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedPreset, setSelectedPreset] = useState(null);

  const presets = [
    { label: 'Last 2 Hours', hours: 2, icon: '⏱️' },
    { label: 'Last 6 Hours', hours: 6, icon: '🕐' },
    { label: 'Last 24 Hours', hours: 24, icon: '📅' },
    { label: 'Last 2 Days', hours: 48, icon: '📆' },
    { label: 'Last 7 Days', hours: 168, icon: '📊' },
    { label: 'Last 15 Days', hours: 360, icon: '📈' },
    { label: 'Last 30 Days', hours: 720, icon: '🗓️' },
  ];

  const selectPreset = (p) => {
    setSelectedPreset(p.hours);
    const end = new Date();
    const start = new Date(end.getTime() - p.hours * 60 * 60 * 1000);
    setStartDate(start.toISOString().slice(0, 16));
    setEndDate(end.toISOString().slice(0, 16));
  };

  const canRun = startDate && endDate && new Date(startDate) < new Date(endDate);

  return (
    <div className="ncm-overlay" onClick={onClose} style={{ zIndex: 1000 }}>
      <div onClick={(e) => e.stopPropagation()} style={{
        background: '#fff', borderRadius: 20, width: 520, maxWidth: '95vw',
        boxShadow: '0 25px 80px rgba(0,0,0,0.15), 0 10px 30px rgba(0,0,0,0.1)',
        overflow: 'hidden', animation: 'slideUp 0.3s ease',
      }}>
        {/* Header */}
        <div style={{
          background: 'linear-gradient(135deg, #6366f1, #8b5cf6, #a78bfa)',
          padding: '24px 28px', color: '#fff',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.3px' }}>🚀 Run Pipeline</div>
              <div style={{ fontSize: 12, opacity: 0.85, marginTop: 4 }}>Select a time range to analyze Azure error logs</div>
            </div>
            <button onClick={onClose} style={{
              background: 'rgba(255,255,255,0.2)', border: 'none', borderRadius: '50%',
              width: 32, height: 32, color: '#fff', fontSize: 16, cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'background 0.2s',
            }} onMouseEnter={(e) => { e.target.style.background = 'rgba(255,255,255,0.3)'; }}
              onMouseLeave={(e) => { e.target.style.background = 'rgba(255,255,255,0.2)'; }}>
              ✕
            </button>
          </div>
        </div>

        <div style={{ padding: '20px 28px 28px' }}>
          {/* Quick Presets */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 10 }}>
              Quick Select
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {presets.map((p) => (
                <button key={p.hours} onClick={() => selectPreset(p)} style={{
                  padding: '8px 14px', borderRadius: 10, border: `2px solid ${selectedPreset === p.hours ? '#6366f1' : '#e2e8f0'}`,
                  background: selectedPreset === p.hours ? '#eff6ff' : '#fff',
                  color: selectedPreset === p.hours ? '#6366f1' : '#475569',
                  fontWeight: 600, fontSize: 12, cursor: 'pointer',
                  transition: 'all 0.2s ease', display: 'flex', alignItems: 'center', gap: 6,
                }}
                  onMouseEnter={(e) => { if (selectedPreset !== p.hours) e.target.style.borderColor = '#a5b4fc'; }}
                  onMouseLeave={(e) => { if (selectedPreset !== p.hours) e.target.style.borderColor = '#e2e8f0'; }}>
                  <span>{p.icon}</span> {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Divider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
            <div style={{ flex: 1, height: 1, background: '#e2e8f0' }} />
            <span style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600 }}>OR CUSTOM RANGE</span>
            <div style={{ flex: 1, height: 1, background: '#e2e8f0' }} />
          </div>

          {/* Custom Date Inputs */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 22 }}>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#475569', display: 'block', marginBottom: 6 }}>Start Date & Time</label>
              <input type="datetime-local" value={startDate} onChange={(e) => { setStartDate(e.target.value); setSelectedPreset(null); }}
                style={{
                  width: '100%', padding: '10px 12px', borderRadius: 10, border: '2px solid #e2e8f0',
                  fontSize: 13, color: '#0f172a', outline: 'none', background: '#f8fafc',
                  transition: 'border-color 0.2s', fontFamily: 'Inter, sans-serif',
                }}
                onFocus={(e) => { e.target.style.borderColor = '#6366f1'; }}
                onBlur={(e) => { e.target.style.borderColor = '#e2e8f0'; }} />
            </div>
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#475569', display: 'block', marginBottom: 6 }}>End Date & Time</label>
              <input type="datetime-local" value={endDate} onChange={(e) => { setEndDate(e.target.value); setSelectedPreset(null); }}
                style={{
                  width: '100%', padding: '10px 12px', borderRadius: 10, border: '2px solid #e2e8f0',
                  fontSize: 13, color: '#0f172a', outline: 'none', background: '#f8fafc',
                  transition: 'border-color 0.2s', fontFamily: 'Inter, sans-serif',
                }}
                onFocus={(e) => { e.target.style.borderColor = '#6366f1'; }}
                onBlur={(e) => { e.target.style.borderColor = '#e2e8f0'; }} />
            </div>
          </div>

          {/* Selected Range Summary */}
          {canRun && (
            <div style={{
              background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 12,
              padding: '12px 16px', marginBottom: 18, display: 'flex', alignItems: 'center', gap: 10,
            }}>
              <span style={{ fontSize: 16 }}>📊</span>
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#166534' }}>Selected Range</div>
                <div style={{ fontSize: 11, color: '#15803d' }}>
                  {new Date(startDate).toLocaleString()} → {new Date(endDate).toLocaleString()}
                  <span style={{ marginLeft: 8, opacity: 0.8 }}>
                    ({Math.round((new Date(endDate) - new Date(startDate)) / 3600000)}h)
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: 12 }}>
            <button onClick={onClose} style={{
              flex: 1, padding: '12px', borderRadius: 12, border: '2px solid #e2e8f0',
              background: '#fff', color: '#475569', fontWeight: 700, fontSize: 13,
              cursor: 'pointer', transition: 'all 0.2s',
            }}>
              Cancel
            </button>
            <button onClick={() => onRun({ start: startDate, end: endDate })} disabled={!canRun || running}
              style={{
                flex: 2, padding: '12px', borderRadius: 12, border: 'none',
                background: canRun ? 'linear-gradient(135deg, #6366f1, #8b5cf6)' : '#e2e8f0',
                color: canRun ? '#fff' : '#94a3b8', fontWeight: 800, fontSize: 14,
                cursor: canRun ? 'pointer' : 'not-allowed',
                transition: 'all 0.3s', letterSpacing: '0.3px',
                boxShadow: canRun ? '0 4px 15px rgba(99,102,241,0.35)' : 'none',
              }}
              onMouseEnter={(e) => { if (canRun) e.target.style.transform = 'translateY(-1px)'; }}
              onMouseLeave={(e) => { e.target.style.transform = 'translateY(0)'; }}>
              {running ? '⟳ Running…' : '🚀 Run Pipeline'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Incident Category Donut ─── */
function IncidentCategoryDonut({ incidents, dashboard }) {
  const p1 = dashboard?.incidents?.p1 || 0;
  const p2 = dashboard?.incidents?.p2 || 0;
  const p3 = dashboard?.incidents?.p3 || 0;
  const total = p1 + p2 + p3;

  // Count by status
  const statusCounts = {};
  incidents.forEach((inc) => { statusCounts[inc.status || 'OPEN'] = (statusCounts[inc.status || 'OPEN'] || 0) + 1; });

  const priorityData = {
    labels: ['P1 — Critical', 'P2 — High', 'P3 — Medium'],
    datasets: [{
      data: [p1, p2, p3],
      backgroundColor: ['#ef4444', '#f59e0b', '#10b981'],
      borderColor: '#fff',
      borderWidth: 3,
      hoverOffset: 8,
    }],
  };

  const priorityOpts = {
    responsive: true, maintainAspectRatio: false,
    cutout: '72%',
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#0f172a', titleColor: '#fff', bodyColor: '#e2e8f0',
        padding: 12, cornerRadius: 10, displayColors: true,
      },
    },
  };

  const statusColors = { OPEN: '#ef4444', INVESTIGATING: '#f59e0b', RESOLVED: '#10b981', CLOSED: '#6366f1' };

  return (
    <div style={{ display: 'flex', gap: 20, alignItems: 'center', height: 220 }}>
      {/* Donut */}
      <div style={{ position: 'relative', width: 180, height: 180, flex: '0 0 180px' }}>
        <Doughnut data={priorityData} options={priorityOpts} />
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
          <div style={{ fontSize: 32, fontWeight: 800, color: '#0f172a', lineHeight: 1 }}>{total}</div>
          <div style={{ fontSize: 10, color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>Incidents</div>
        </div>
      </div>

      {/* Legend + Status Bars */}
      <div style={{ flex: 1 }}>
        {/* Priority Legend */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 8 }}>By Priority</div>
          {[{ label: 'P1 Critical', count: p1, color: '#ef4444', pct: total ? (p1 / total * 100) : 0 },
          { label: 'P2 High', count: p2, color: '#f59e0b', pct: total ? (p2 / total * 100) : 0 },
          { label: 'P3 Medium', count: p3, color: '#10b981', pct: total ? (p3 / total * 100) : 0 }].map((item) => (
            <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <div style={{ width: 10, height: 10, borderRadius: 3, background: item.color, flex: '0 0 10px' }} />
              <span style={{ fontSize: 12, color: '#475569', flex: '0 0 85px' }}>{item.label}</span>
              <div style={{ flex: 1, height: 6, background: '#f1f5f9', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ width: `${item.pct}%`, height: '100%', background: item.color, borderRadius: 3, transition: 'width 0.8s ease' }} />
              </div>
              <span style={{ fontSize: 12, fontWeight: 700, color: item.color, flex: '0 0 40px', textAlign: 'right' }}>{item.count}</span>
            </div>
          ))}
        </div>

        {/* Status Breakdown */}
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 8 }}>By Status</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {Object.entries(statusCounts).map(([status, count]) => (
              <div key={status} style={{
                display: 'flex', alignItems: 'center', gap: 6, background: `${statusColors[status] || '#6366f1'}10`,
                border: `1px solid ${statusColors[status] || '#6366f1'}30`, borderRadius: 8, padding: '4px 10px',
              }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: statusColors[status] || '#6366f1' }} />
                <span style={{ fontSize: 11, fontWeight: 700, color: statusColors[status] || '#6366f1' }}>{count}</span>
                <span style={{ fontSize: 10, color: '#64748b' }}>{status}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Service × Category Heatmap ─── */
function ServiceCategoryHeatmap({ incidents, incidentGroups, serviceBreakdown }) {
  // Build heatmap from incident data
  const serviceMap = {};
  const categorySet = new Set();

  incidents.forEach((inc) => {
    const svc = inc.source_service || 'Unknown';
    const cat = inc.category || inc.error_type || 'Uncategorized';
    categorySet.add(cat);
    if (!serviceMap[svc]) serviceMap[svc] = {};
    serviceMap[svc][cat] = (serviceMap[svc][cat] || 0) + 1;
  });

  // Also include incident groups
  (incidentGroups || []).forEach((g) => {
    const svc = g.source_service || 'Unknown';
    const cat = g.category_name || g.error_type || 'Uncategorized';
    categorySet.add(cat);
    if (!serviceMap[svc]) serviceMap[svc] = {};
    serviceMap[svc][cat] = (serviceMap[svc][cat] || 0) + (g.total_occurrences || 1);
  });

  const services = Object.keys(serviceMap);
  const categories = [...categorySet].slice(0, 8);

  const maxVal = Math.max(1, ...services.flatMap((s) => categories.map((c) => serviceMap[s]?.[c] || 0)));

  const getColor = (val) => {
    if (!val) return '#f8fafc';
    const intensity = val / maxVal;
    if (intensity > 0.7) return '#ef4444';
    if (intensity > 0.4) return '#f59e0b';
    if (intensity > 0.15) return '#fb923c';
    return '#fde68a';
  };

  if (services.length === 0 || categories.length === 0) {
    return <EmptyState icon="🗺️" title="No data" text="Run the pipeline to see the heatmap" />;
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <div style={{ display: 'grid', gridTemplateColumns: `120px repeat(${categories.length}, 1fr)`, gap: 2, fontSize: 11 }}>
        {/* Header row */}
        <div style={{ padding: '8px 6px', fontWeight: 700, color: '#64748b' }}></div>
        {categories.map((cat) => (
          <div key={cat} style={{
            padding: '6px 4px', fontWeight: 600, color: '#475569', textAlign: 'center',
            fontSize: 10, background: '#f1f5f9', borderRadius: 6, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {cat.length > 14 ? cat.slice(0, 12) + '…' : cat}
          </div>
        ))}

        {/* Data rows */}
        {services.map((svc) => (
          <React.Fragment key={svc}>
            <div style={{
              padding: '8px 6px', fontWeight: 600, color: '#0f172a', fontSize: 11,
              display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>
              {svc.length > 16 ? svc.slice(0, 14) + '…' : svc}
            </div>
            {categories.map((cat) => {
              const val = serviceMap[svc]?.[cat] || 0;
              return (
                <div key={`${svc}-${cat}`} style={{
                  padding: '8px 4px', textAlign: 'center', borderRadius: 6,
                  background: getColor(val), color: val > maxVal * 0.4 ? '#fff' : '#475569',
                  fontWeight: val > 0 ? 700 : 400, transition: 'all 0.3s ease',
                  cursor: val > 0 ? 'pointer' : 'default', position: 'relative',
                }}
                  title={`${svc}: ${cat} — ${val} incident(s)`}>
                  {val || '·'}
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 14, justifyContent: 'center' }}>
        <span style={{ fontSize: 10, color: '#94a3b8' }}>Low</span>
        {['#fde68a', '#fb923c', '#f59e0b', '#ef4444'].map((c, i) => (
          <div key={i} style={{ width: 24, height: 8, borderRadius: 2, background: c }} />
        ))}
        <span style={{ fontSize: 10, color: '#94a3b8' }}>High</span>
      </div>
    </div>
  );
}

/* ─── Error Logs Table ─── */
function ErrorLogsTable({ incidents }) {
  const PRIORITY_COLORS = { P1: '#ef4444', P2: '#f59e0b', P3: '#10b981', P4: '#6366f1' };
  const STATUS_COLORS = { OPEN: '#ef4444', INVESTIGATING: '#f59e0b', RESOLVED: '#10b981', CLOSED: '#94a3b8' };

  return (
    <div style={{ maxHeight: 400, overflowY: 'auto', margin: '-12px -16px -16px', borderRadius: '0 0 14px 14px' }}>
      <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 0, fontSize: 12 }}>
        <thead>
          <tr style={{ position: 'sticky', top: 0, zIndex: 5 }}>
            {['Severity', 'Incident Title', 'Source Service', 'HTTP', 'Category', 'Status', 'Detected At'].map((h) => (
              <th key={h} style={{
                padding: '10px 12px', background: '#f8fafc', color: '#475569', fontWeight: 700,
                textAlign: 'left', borderBottom: '2px solid #e2e8f0', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.3px',
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {incidents.map((inc, idx) => {
            const pColor = PRIORITY_COLORS[inc.priority] || '#94a3b8';
            const sColor = STATUS_COLORS[inc.status] || '#94a3b8';
            return (
              <tr key={inc.id || idx} style={{
                background: idx % 2 === 0 ? '#fff' : '#fafbfc',
                transition: 'background 0.15s',
              }}
                onMouseEnter={(e) => { e.currentTarget.style.background = '#f0f4ff'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = idx % 2 === 0 ? '#fff' : '#fafbfc'; }}>
                {/* Severity bar + badge */}
                <td style={{ padding: '10px 12px', position: 'relative' }}>
                  <div style={{ position: 'absolute', left: 0, top: 4, bottom: 4, width: 4, borderRadius: 2, background: pColor }} />
                  <span style={{
                    display: 'inline-flex', alignItems: 'center', gap: 4,
                    background: `${pColor}15`, color: pColor, fontWeight: 800, fontSize: 11,
                    padding: '3px 8px', borderRadius: 6, border: `1px solid ${pColor}30`,
                  }}>
                    {inc.priority === 'P1' ? '🔴' : inc.priority === 'P2' ? '🟡' : '🟢'} {inc.priority}
                  </span>
                </td>

                {/* Title */}
                <td style={{ padding: '10px 12px', maxWidth: 280 }}>
                  <div style={{ fontWeight: 600, color: '#0f172a', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {inc.title || inc.error_signature || 'Unnamed Incident'}
                  </div>
                  {inc.description && (
                    <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 260 }}>
                      {inc.description}
                    </div>
                  )}
                </td>

                {/* Source Service */}
                <td style={{ padding: '10px 12px' }}>
                  <span style={{
                    background: '#eff6ff', color: '#3b82f6', fontWeight: 600, fontSize: 10,
                    padding: '3px 8px', borderRadius: 6, border: '1px solid #bfdbfe',
                  }}>
                    {inc.source_service || 'Unknown'}
                  </span>
                </td>

                {/* HTTP Status */}
                <td style={{ padding: '10px 12px' }}>
                  {inc.http_status_code ? (
                    <span style={{
                      fontWeight: 700, fontSize: 12,
                      color: inc.http_status_code >= 500 ? '#ef4444' : inc.http_status_code >= 400 ? '#f59e0b' : '#10b981',
                    }}>
                      {inc.http_status_code}
                    </span>
                  ) : <span style={{ color: '#cbd5e1' }}>—</span>}
                </td>

                {/* Category */}
                <td style={{ padding: '10px 12px' }}>
                  <span style={{ fontSize: 11, color: '#64748b', fontWeight: 500 }}>
                    {inc.category || inc.error_type || '—'}
                  </span>
                </td>

                {/* Status */}
                <td style={{ padding: '10px 12px' }}>
                  <span style={{
                    display: 'inline-flex', alignItems: 'center', gap: 4,
                    fontSize: 10, fontWeight: 700, color: sColor,
                    background: `${sColor}10`, padding: '2px 8px', borderRadius: 10,
                  }}>
                    <span style={{ width: 5, height: 5, borderRadius: '50%', background: sColor }} />
                    {inc.status || 'OPEN'}
                  </span>
                </td>

                {/* Timestamp */}
                <td style={{ padding: '10px 12px', fontSize: 11, color: '#94a3b8', whiteSpace: 'nowrap' }}>
                  {inc.created_at ? new Date(inc.created_at).toLocaleString() : '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ─── Incident Timeline ─── */
function IncidentTimeline({ incidents }) {
  const sorted = [...incidents].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 12);
  const COLORS = { P1: '#ef4444', P2: '#f59e0b', P3: '#10b981' };
  const ICONS = { P1: '🔴', P2: '🟡', P3: '🟢' };

  return (
    <div style={{ position: 'relative', paddingLeft: 32 }}>
      {/* Vertical line */}
      <div style={{
        position: 'absolute', left: 14, top: 8, bottom: 8, width: 2,
        background: 'linear-gradient(to bottom, #6366f1, #a78bfa, #e2e8f0)',
      }} />

      {sorted.map((inc, idx) => {
        const pColor = COLORS[inc.priority] || '#94a3b8';
        const timeDiff = idx < sorted.length - 1
          ? Math.round((new Date(sorted[idx].created_at) - new Date(sorted[idx + 1].created_at)) / 60000)
          : null;

        return (
          <div key={inc.id || idx} style={{ position: 'relative', marginBottom: 12 }}>
            {/* Timeline dot */}
            <div style={{
              position: 'absolute', left: -24, top: 12, width: 16, height: 16, borderRadius: '50%',
              background: pColor, border: '3px solid #fff', boxShadow: `0 0 0 2px ${pColor}40`,
              display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2,
            }}>
              {inc.priority === 'P1' && (
                <div style={{
                  position: 'absolute', width: 24, height: 24, borderRadius: '50%',
                  border: `2px solid ${pColor}`, animation: 'pulse-ring 2s infinite', opacity: 0.4,
                }} />
              )}
            </div>

            {/* Card */}
            <div style={{
              background: '#fff', border: `1px solid ${pColor}20`, borderRadius: 12, padding: '12px 16px',
              borderLeft: `4px solid ${pColor}`, transition: 'all 0.2s ease',
              boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
            }}
              onMouseEnter={(e) => { e.currentTarget.style.boxShadow = `0 4px 16px ${pColor}20`; e.currentTarget.style.transform = 'translateX(4px)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.boxShadow = '0 1px 4px rgba(0,0,0,0.04)'; e.currentTarget.style.transform = 'translateX(0)'; }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{
                      background: `${pColor}15`, color: pColor, fontWeight: 800, fontSize: 10,
                      padding: '2px 6px', borderRadius: 4, border: `1px solid ${pColor}30`,
                    }}>
                      {ICONS[inc.priority]} {inc.priority}
                    </span>
                    <span style={{
                      background: '#f1f5f9', color: '#475569', fontWeight: 600, fontSize: 10,
                      padding: '2px 6px', borderRadius: 4,
                    }}>
                      {inc.source_service || 'Unknown'}
                    </span>
                    {inc.http_status_code && (
                      <span style={{
                        fontWeight: 700, fontSize: 10,
                        color: inc.http_status_code >= 500 ? '#ef4444' : '#f59e0b',
                      }}>
                        HTTP {inc.http_status_code}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#0f172a', lineHeight: 1.3 }}>
                    {(inc.title || inc.error_signature || 'Unnamed Incident').slice(0, 80)}
                  </div>
                </div>
                <div style={{ fontSize: 11, color: '#94a3b8', whiteSpace: 'nowrap', marginLeft: 12 }}>
                  {inc.created_at ? new Date(inc.created_at).toLocaleString() : '—'}
                </div>
              </div>
            </div>

            {/* Time gap indicator */}
            {timeDiff !== null && timeDiff > 0 && (
              <div style={{
                position: 'absolute', left: -38, top: '100%', marginTop: 2,
                fontSize: 9, color: '#a5b4fc', fontWeight: 600, whiteSpace: 'nowrap',
              }}>
                {timeDiff < 60 ? `${timeDiff}m` : `${Math.round(timeDiff / 60)}h`}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}




