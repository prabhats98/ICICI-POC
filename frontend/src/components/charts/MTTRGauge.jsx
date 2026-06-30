/**
 * MTTRGauge — Mean Time to Resolve breakdown by priority.
 */
export default function MTTRGauge({ mttrData }) {
  if (!mttrData) {
    return (
      <div className="empty-state" style={{ padding: 24 }}>
        <div className="empty-state-icon">⏱️</div>
        <div className="empty-state-title">No MTTR data</div>
      </div>
    );
  }

  const items = [
    { label: 'P1 Critical', value: mttrData.p1_avg_minutes, color: '#ef4444', bg: '#fef2f2' },
    { label: 'P2 High', value: mttrData.p2_avg_minutes, color: '#f59e0b', bg: '#fffbeb' },
    { label: 'P3 Medium', value: mttrData.p3_avg_minutes, color: '#10b981', bg: '#ecfdf5' },
  ];

  return (
    <div className="mttr-grid">
      {items.map((item) => (
        <div key={item.label} className="mttr-card" style={{ background: item.bg, borderColor: `${item.color}20` }}>
          <div className="mttr-value" style={{ color: item.color }}>
            {item.value != null ? `${Math.round(item.value)}m` : '—'}
          </div>
          <div className="mttr-label">{item.label}</div>
        </div>
      ))}
    </div>
  );
}
