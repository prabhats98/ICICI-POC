/**
 * SLOWidget — SLO compliance tracking with progress bars.
 */
export default function SLOWidget({ sloData }) {
  if (!sloData) {
    return (
      <div className="empty-state" style={{ padding: 24 }}>
        <div className="empty-state-icon">🎯</div>
        <div className="empty-state-title">No SLO data</div>
      </div>
    );
  }

  const items = [
    { label: 'Availability', value: sloData.availability || 99.9, target: 99.9, color: '#10b981' },
    { label: 'Latency P95', value: sloData.latency_p95_compliance || 95, target: 95, color: '#3b82f6' },
    { label: 'Error Budget', value: sloData.error_budget_remaining || 80, target: 100, color: '#8b5cf6' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {items.map((item) => {
        const pct = Math.min((item.value / item.target) * 100, 100);
        const isGood = pct >= 90;
        return (
          <div key={item.label}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#334155' }}>{item.label}</span>
              <span style={{ fontSize: 13, fontWeight: 700, color: isGood ? '#10b981' : '#ef4444' }}>
                {item.value.toFixed(1)}%
              </span>
            </div>
            <div className="slo-bar-track">
              <div className="slo-bar-fill" style={{
                width: `${pct}%`,
                background: `linear-gradient(90deg, ${item.color}, ${item.color}cc)`,
              }} />
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
              Target: {item.target}%
            </div>
          </div>
        );
      })}
    </div>
  );
}
