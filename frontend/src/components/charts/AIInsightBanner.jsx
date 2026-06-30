/**
 * AIInsightBanner — Shows AI-generated insight summary.
 */
export default function AIInsightBanner({ dashboard, goldenSignals, trendData }) {
  const totalLogs = dashboard?.logs?.total || dashboard?.raw_logs?.total || 0;
  const totalIncidents = dashboard?.incidents?.total || 0;
  const p1Count = dashboard?.incidents?.p1 || 0;
  const p2Count = dashboard?.incidents?.p2 || 0;
  const pipelineStatus = dashboard?.pipeline?.last_run_status || 'N/A';
  const errorRate = goldenSignals?.error_rate?.toFixed(1) || '0';

  let insight = '';
  if (p1Count > 0) {
    insight = `⚠️ ${p1Count} critical P1 incident(s) detected requiring immediate attention. `;
  } else if (totalIncidents > 0) {
    insight = `${totalIncidents} incident(s) detected from ${totalLogs} logs analyzed. `;
  } else {
    insight = 'All systems are operating normally. No critical incidents detected. ';
  }

  if (totalLogs > 0) {
    insight += `Pipeline processed ${totalLogs} error logs with ${errorRate}% error rate.`;
  }

  return (
    <div className="ai-insight-banner">
      <div className="ai-insight-icon">🤖</div>
      <div className="ai-insight-text">
        <strong>AI Analysis Summary</strong> — {insight}
        {pipelineStatus === 'SUCCESS' && (
          <span style={{ color: '#10b981', fontWeight: 600 }}> Pipeline healthy ✓</span>
        )}
      </div>
    </div>
  );
}
