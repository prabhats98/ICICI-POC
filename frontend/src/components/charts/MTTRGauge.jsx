/**
 * MTTRGauge — 3 mini gauges for P1/P2/P3 Mean Time To Resolution.
 * Shows target reference line and resolution count.
 */

import { useRef, useEffect } from 'react';

const PRIORITY_CONFIG = {
  P1: { color: '#ef4444', target: 30, label: 'P1 Critical' },
  P2: { color: '#f59e0b', target: 60, label: 'P2 Warning' },
  P3: { color: '#10b981', target: 120, label: 'P3 Info' },
};

function MiniGauge({ priority, avgMinutes, resolvedCount, target }) {
  const canvasRef = useRef(null);
  const config = PRIORITY_CONFIG[priority] || PRIORITY_CONFIG.P3;
  const maxValue = target * 2;
  const pct = avgMinutes != null ? Math.min((avgMinutes / maxValue) * 100, 100) : 0;
  const isOverTarget = avgMinutes != null && avgMinutes > target;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const size = 100;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, size, size);

    const cx = size / 2;
    const cy = size / 2 + 5;
    const radius = 38;
    const lineWidth = 7;
    const startAngle = Math.PI * 0.8;
    const endAngle = Math.PI * 2.2;
    const totalArc = endAngle - startAngle;

    // Background
    ctx.beginPath();
    ctx.arc(cx, cy, radius, startAngle, endAngle);
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Target line
    const targetPct = Math.min((target / maxValue) * 100, 100);
    const targetAngle = startAngle + (targetPct / 100) * totalArc;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, targetAngle - 0.02, targetAngle + 0.02);
    ctx.strokeStyle = 'rgba(255,255,255,0.25)';
    ctx.lineWidth = lineWidth + 4;
    ctx.lineCap = 'butt';
    ctx.stroke();

    // Value arc
    if (pct > 0) {
      const valueAngle = startAngle + (pct / 100) * totalArc;
      const color = isOverTarget ? '#ef4444' : config.color;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, startAngle, valueAngle);
      ctx.strokeStyle = color;
      ctx.lineWidth = lineWidth;
      ctx.lineCap = 'round';
      ctx.stroke();
    }

    // Center text
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = '700 18px Inter';
    ctx.fillStyle = avgMinutes != null ? (isOverTarget ? '#ef4444' : '#f1f5f9') : '#64748b';
    ctx.fillText(avgMinutes != null ? Math.round(avgMinutes) + 'm' : '—', cx, cy - 4);

    ctx.font = '500 8px Inter';
    ctx.fillStyle = 'rgba(255,255,255,0.35)';
    ctx.fillText(`target ${target}m`, cx, cy + 14);
  }, [avgMinutes, target, pct, isOverTarget, config.color]);

  return (
    <div className="mttr-mini-gauge">
      <canvas ref={canvasRef} style={{ width: 100, height: 100 }} />
      <div className="mttr-gauge-label" style={{ color: config.color }}>
        {config.label}
      </div>
      <div className="mttr-gauge-resolved">
        {resolvedCount ?? 0} resolved
      </div>
    </div>
  );
}

export default function MTTRGauge({ mttrData = null }) {
  const byPriority = mttrData?.by_priority || {};

  return (
    <div className="mttr-gauges">
      {['P1', 'P2', 'P3'].map((prio) => {
        const data = byPriority[prio] || {};
        const config = PRIORITY_CONFIG[prio];
        return (
          <MiniGauge
            key={prio}
            priority={prio}
            avgMinutes={data.avg_minutes}
            resolvedCount={data.resolved_count}
            target={config.target}
          />
        );
      })}
    </div>
  );
}
