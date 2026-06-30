/**
 * GoldenSignalsRow — SRE Golden Signals displayed in a grid.
 * Handles API format: each signal = { value, unit, delta_pct, label }
 */
export default function GoldenSignalsRow({ signals = {} }) {
  const safe = (v, decimals = 0) => {
    const n = Number(v);
    return isFinite(n) ? n.toFixed(decimals) : null;
  };

  const getVal = (key) => {
    const s = signals[key];
    if (!s) return null;
    return typeof s === 'object' ? s.value : s;
  };

  const getUnit = (key) => {
    const s = signals[key];
    return typeof s === 'object' ? s.unit : '';
  };

  const getLabel = (key, fallback) => {
    const s = signals[key];
    return typeof s === 'object' ? (s.label || fallback) : fallback;
  };

  const items = [
    {
      label: getLabel('errors', 'Error Rate'),
      value: safe(getVal('errors') ?? getVal('error_rate'), 1),
      unit: getUnit('errors') || '%',
      icon: '🔴', color: '#ef4444', bg: '#fef2f2',
    },
    {
      label: getLabel('latency', 'Latency'),
      value: safe(getVal('latency') ?? getVal('latency_p99'), 1),
      unit: getUnit('latency') || 's',
      icon: '⏱️', color: '#f59e0b', bg: '#fffbeb',
    },
    {
      label: getLabel('traffic', 'Traffic'),
      value: safe(getVal('traffic'), 0),
      unit: getUnit('traffic') || 'req/s',
      icon: '📊', color: '#3b82f6', bg: '#eff6ff',
    },
    {
      label: getLabel('saturation', 'Saturation'),
      value: safe(getVal('saturation'), 1),
      unit: getUnit('saturation') || '%',
      icon: '📈', color: '#8b5cf6', bg: '#f5f3ff',
    },
  ];

  return (
    <div className="golden-signals-grid">
      {items.map((item) => (
        <div key={item.label} className="golden-signal-card" style={{ background: item.bg, borderColor: `${item.color}20` }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>{item.icon}</div>
          <div className="golden-signal-value" style={{ color: item.color }}>
            {item.value != null ? `${item.value}${item.unit}` : '—'}
          </div>
          <div className="golden-signal-label">{item.label}</div>
        </div>
      ))}
    </div>
  );
}
