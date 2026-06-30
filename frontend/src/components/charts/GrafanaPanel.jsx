/**
 * GrafanaPanel — Reusable card wrapper for dashboard charts.
 * White theme with clean borders and shadows.
 */
export default function GrafanaPanel({ title, subtitle, children, loading, timeRange, onTimeRangeChange }) {
  const ranges = ['1d', '7d', '14d', '30d'];

  return (
    <div className="grafana-panel">
      <div className="grafana-panel-header">
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span className="grafana-panel-title">{title}</span>
          {subtitle && <span className="grafana-panel-subtitle">{subtitle}</span>}
        </div>
        {onTimeRangeChange && (
          <div className="panel-time-range">
            {ranges.map((r) => (
              <button key={r} className={timeRange === r ? 'active' : ''} onClick={() => onTimeRangeChange(r)}>
                {r}
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="grafana-panel-body">
        {loading ? (
          <div className="grafana-panel-loading">
            <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block', fontSize: 20 }}>⟳</span>
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
