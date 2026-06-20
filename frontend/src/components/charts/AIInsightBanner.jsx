/**
 * AIInsightBanner — Auto-generated insight banner from dashboard data.
 * Detects anomalies client-side and shows actionable recommendations.
 */

import { useState, useMemo } from 'react';

function generateInsights(dashboardData, goldenSignals, trendData) {
  const insights = [];

  // Check for P1 spike
  const openP1 = dashboardData?.incidents?.p1 || 0;
  if (openP1 >= 3) {
    insights.push({
      type: 'critical',
      icon: '🚨',
      title: 'P1 Incident Surge',
      message: `${openP1} P1 critical incidents are currently open. Immediate attention required across your Azure infrastructure.`,
      color: '#ef4444',
    });
  }

  // Check error rate spike
  const errorRate = goldenSignals?.errors?.value || 0;
  if (errorRate > 30) {
    insights.push({
      type: 'warning',
      icon: '⚠️',
      title: 'High Error Rate Detected',
      message: `Error rate is at ${errorRate}% — significantly above normal levels. Check backend health and recent deployments.`,
      color: '#f59e0b',
    });
  }

  // Check trend spike (compare last 2 days of trend data)
  if (trendData && trendData.length >= 2) {
    const lastDay = trendData[trendData.length - 1];
    const prevDay = trendData[trendData.length - 2];
    const lastTotal = (lastDay?.P1 || 0) + (lastDay?.P2 || 0) + (lastDay?.P3 || 0);
    const prevTotal = (prevDay?.P1 || 0) + (prevDay?.P2 || 0) + (prevDay?.P3 || 0);
    if (prevTotal > 0 && lastTotal > prevTotal * 2) {
      insights.push({
        type: 'anomaly',
        icon: '📈',
        title: 'Incident Spike Detected',
        message: `Today's incident count (${lastTotal}) is ${Math.round(lastTotal / prevTotal)}x higher than yesterday (${prevTotal}). Investigate recent changes.`,
        color: '#8b5cf6',
      });
    }
  }

  // Pipeline health
  const pipelineRuns = dashboardData?.pipeline?.total_runs || 0;
  if (pipelineRuns === 0) {
    insights.push({
      type: 'info',
      icon: '🔧',
      title: 'Pipeline Not Active',
      message: 'No pipeline runs detected. Enable the pipeline and trigger a run to start monitoring.',
      color: '#06b6d4',
    });
  }

  // Traffic drop
  const trafficDelta = goldenSignals?.traffic?.delta_pct || 0;
  if (trafficDelta < -50) {
    insights.push({
      type: 'warning',
      icon: '📉',
      title: 'Traffic Drop',
      message: `Log throughput dropped by ${Math.abs(trafficDelta)}% compared to the previous hour. Possible ingestion issue or upstream outage.`,
      color: '#f59e0b',
    });
  }

  // All healthy
  if (insights.length === 0 && pipelineRuns > 0) {
    insights.push({
      type: 'healthy',
      icon: '✅',
      title: 'All Systems Nominal',
      message: 'No anomalies detected. Your Azure cloud infrastructure is operating within normal parameters.',
      color: '#10b981',
    });
  }

  return insights;
}

export default function AIInsightBanner({ dashboard, goldenSignals, trendData }) {
  const [dismissed, setDismissed] = useState(new Set());

  const insights = useMemo(
    () => generateInsights(dashboard, goldenSignals, trendData),
    [dashboard, goldenSignals, trendData]
  );

  const visibleInsights = insights.filter((_, i) => !dismissed.has(i));

  if (visibleInsights.length === 0) return null;

  // Show the most critical insight
  const insight = visibleInsights[0];
  const insightIdx = insights.indexOf(insight);

  return (
    <div className="ai-insight-banner" style={{
      borderColor: `${insight.color}33`,
      background: `linear-gradient(135deg, ${insight.color}0a, ${insight.color}05)`,
    }}>
      <div className="ai-insight-icon-container" style={{
        background: `${insight.color}18`,
        border: `1px solid ${insight.color}33`,
      }}>
        <span className="ai-insight-ai-badge">AI</span>
        <span className="ai-insight-icon">{insight.icon}</span>
      </div>
      <div className="ai-insight-body">
        <div className="ai-insight-title" style={{ color: insight.color }}>
          {insight.title}
        </div>
        <div className="ai-insight-message">{insight.message}</div>
      </div>
      <button
        className="ai-insight-dismiss"
        onClick={() => {
          const next = new Set(dismissed);
          next.add(insightIdx);
          setDismissed(next);
        }}
        title="Dismiss"
      >
        ✕
      </button>
      {visibleInsights.length > 1 && (
        <div className="ai-insight-count">
          +{visibleInsights.length - 1} more
        </div>
      )}
    </div>
  );
}
