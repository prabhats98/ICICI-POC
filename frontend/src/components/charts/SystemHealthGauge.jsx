/**
 * SystemHealthGauge — Shows overall system health score.
 */
export default function SystemHealthGauge({ score = 0, status = 'HEALTHY', factors }) {
  const getColor = (s) => {
    if (s === 'CRITICAL' || score < 50) return 'critical';
    if (s === 'DEGRADED' || score < 80) return 'degraded';
    return 'healthy';
  };

  const colorClass = getColor(status);
  const colorMap = { healthy: '#10b981', degraded: '#f59e0b', critical: '#ef4444' };
  const bgMap = { healthy: '#ecfdf5', degraded: '#fffbeb', critical: '#fef2f2' };

  return (
    <div className="health-gauge">
      <div style={{
        width: 140, height: 140, borderRadius: '50%',
        background: bgMap[colorClass],
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        border: `4px solid ${colorMap[colorClass]}`,
        boxShadow: `0 0 20px ${colorMap[colorClass]}22`,
      }}>
        <div style={{ textAlign: 'center' }}>
          <div className={`health-score ${colorClass}`}>{Math.round(score)}</div>
          <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>/ 100</div>
        </div>
      </div>
      <div className="health-status" style={{ color: colorMap[colorClass], marginTop: 12 }}>
        {status}
      </div>
      {factors && (
        <div style={{ display: 'flex', gap: 12, marginTop: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
          {Object.entries(factors).slice(0, 4).map(([key, val]) => (
            <div key={key} style={{
              fontSize: 11, color: '#64748b', background: '#f1f5f9',
              padding: '4px 10px', borderRadius: 20, fontWeight: 500,
            }}>
              {key}: {typeof val === 'number' ? val.toFixed(0) : val}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
