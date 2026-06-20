/**
 * GoldenSignalsRow — 4-panel horizontal strip showing Google SRE Golden Signals:
 * Latency, Traffic, Errors, Saturation.
 * Each panel: metric name, current value, mini sparkline, trend arrow.
 */

import SparklineChart from './SparklineChart';

const SIGNAL_CONFIG = {
  latency: {
    icon: '⏱️',
    label: 'Latency',
    gradient: 'linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.08))',
    color: '#818cf8',
    border: 'rgba(99,102,241,0.2)',
  },
  traffic: {
    icon: '📊',
    label: 'Traffic',
    gradient: 'linear-gradient(135deg, rgba(6,182,212,0.12), rgba(59,130,246,0.08))',
    color: '#06b6d4',
    border: 'rgba(6,182,212,0.2)',
  },
  errors: {
    icon: '⚠️',
    label: 'Errors',
    gradient: 'linear-gradient(135deg, rgba(239,68,68,0.12), rgba(244,63,94,0.08))',
    color: '#ef4444',
    border: 'rgba(239,68,68,0.2)',
  },
  saturation: {
    icon: '📈',
    label: 'Saturation',
    gradient: 'linear-gradient(135deg, rgba(245,158,11,0.12), rgba(234,179,8,0.08))',
    color: '#f59e0b',
    border: 'rgba(245,158,11,0.2)',
  },
};

function getTrendArrow(delta) {
  if (delta > 5) return { arrow: '↑', color: '#ef4444', label: 'Up' };
  if (delta < -5) return { arrow: '↓', color: '#10b981', label: 'Down' };
  return { arrow: '→', color: '#64748b', label: 'Stable' };
}

function SignalPanel({ signalKey, data }) {
  const config = SIGNAL_CONFIG[signalKey];
  if (!config || !data) return null;

  const trend = getTrendArrow(data.delta_pct);
  // For errors/saturation, up is bad. For latency, up is bad. For traffic, up is good.
  const trendColor = signalKey === 'traffic'
    ? (data.delta_pct > 5 ? '#10b981' : data.delta_pct < -5 ? '#ef4444' : '#64748b')
    : trend.color;

  return (
    <div className="golden-signal-panel" style={{
      background: config.gradient,
      borderColor: config.border,
    }}>
      <div className="golden-signal-header">
        <span className="golden-signal-icon">{config.icon}</span>
        <span className="golden-signal-label">{data.label || config.label}</span>
      </div>
      <div className="golden-signal-body">
        <div className="golden-signal-value-row">
          <span className="golden-signal-value" style={{ color: config.color }}>
            {typeof data.value === 'number'
              ? (data.value % 1 !== 0 ? data.value.toFixed(1) : data.value)
              : data.value}
          </span>
          <span className="golden-signal-unit">{data.unit}</span>
        </div>
        <div className="golden-signal-trend" style={{ color: trendColor }}>
          <span className="golden-signal-arrow">{trend.arrow}</span>
          <span className="golden-signal-delta">
            {data.delta_pct > 0 ? '+' : ''}{data.delta_pct}%
          </span>
        </div>
      </div>
      {data.sparkline && data.sparkline.length > 2 && (
        <div className="golden-signal-sparkline">
          <SparklineChart
            data={data.sparkline}
            width={120}
            height={24}
            color={config.color}
          />
        </div>
      )}
    </div>
  );
}

export default function GoldenSignalsRow({ signals = {} }) {
  return (
    <div className="golden-signals-row">
      {['latency', 'traffic', 'errors', 'saturation'].map((key) => (
        <SignalPanel key={key} signalKey={key} data={signals[key]} />
      ))}
    </div>
  );
}
