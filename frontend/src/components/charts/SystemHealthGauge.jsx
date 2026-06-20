/**
 * SystemHealthGauge — Animated radial gauge showing overall system health (0-100).
 * Uses canvas for rendering a smooth arc with color transitions.
 */

import { useRef, useEffect, useState } from 'react';

function getHealthColor(score) {
  if (score >= 80) return { main: '#10b981', glow: 'rgba(16,185,129,0.3)', label: 'Healthy', bg: 'rgba(16,185,129,0.08)' };
  if (score >= 50) return { main: '#f59e0b', glow: 'rgba(245,158,11,0.3)', label: 'Degraded', bg: 'rgba(245,158,11,0.08)' };
  return { main: '#ef4444', glow: 'rgba(239,68,68,0.3)', label: 'Critical', bg: 'rgba(239,68,68,0.08)' };
}

export default function SystemHealthGauge({ score = 0, status = 'HEALTHY', factors = {} }) {
  const canvasRef = useRef(null);
  const [animScore, setAnimScore] = useState(0);

  useEffect(() => {
    let start = null;
    const from = animScore;
    const to = score;
    const duration = 1500;

    function animate(ts) {
      if (!start) start = ts;
      const progress = Math.min((ts - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimScore(from + (to - from) * eased);
      if (progress < 1) requestAnimationFrame(animate);
    }
    requestAnimationFrame(animate);
  }, [score]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const size = 200;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, size, size);

    const cx = size / 2;
    const cy = size / 2 + 10;
    const radius = 78;
    const lineWidth = 10;
    const startAngle = Math.PI * 0.8;
    const endAngle = Math.PI * 2.2;
    const totalArc = endAngle - startAngle;
    const valueAngle = startAngle + (animScore / 100) * totalArc;
    const colors = getHealthColor(animScore);

    // Background track
    ctx.beginPath();
    ctx.arc(cx, cy, radius, startAngle, endAngle);
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Value arc
    if (animScore > 0) {
      const grad = ctx.createLinearGradient(cx - radius, cy, cx + radius, cy);
      grad.addColorStop(0, colors.main + 'aa');
      grad.addColorStop(1, colors.main);
      ctx.beginPath();
      ctx.arc(cx, cy, radius, startAngle, valueAngle);
      ctx.strokeStyle = grad;
      ctx.lineWidth = lineWidth;
      ctx.lineCap = 'round';
      ctx.stroke();

      // Glow
      ctx.shadowColor = colors.glow;
      ctx.shadowBlur = 15;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, valueAngle - 0.1, valueAngle);
      ctx.strokeStyle = colors.main;
      ctx.lineWidth = lineWidth;
      ctx.lineCap = 'round';
      ctx.stroke();
      ctx.shadowBlur = 0;
    }

    // Center score
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = '800 42px Inter';
    ctx.fillStyle = colors.main;
    ctx.fillText(Math.round(animScore).toString(), cx, cy - 8);

    // Status label
    ctx.font = '600 12px Inter';
    ctx.fillStyle = 'rgba(255,255,255,0.5)';
    ctx.fillText('SYSTEM HEALTH', cx, cy + 22);
  }, [animScore]);

  const colors = getHealthColor(animScore);

  return (
    <div className="system-health-gauge">
      <canvas
        ref={canvasRef}
        style={{ width: 200, height: 200 }}
      />
      <div className="health-status-badge" style={{
        background: colors.bg,
        color: colors.main,
        border: `1px solid ${colors.main}33`,
      }}>
        <span className="health-status-dot" style={{
          background: colors.main,
          boxShadow: `0 0 8px ${colors.glow}`,
        }} />
        {colors.label}
      </div>
      {factors && (
        <div className="health-factors">
          <div className="health-factor-item">
            <span className="health-factor-label">Open P1</span>
            <span className="health-factor-value" style={{ color: factors.open_p1 > 0 ? '#ef4444' : '#64748b' }}>
              {factors.open_p1 ?? 0}
            </span>
          </div>
          <div className="health-factor-item">
            <span className="health-factor-label">Error Rate</span>
            <span className="health-factor-value">{factors.error_rate ?? 0}%</span>
          </div>
          <div className="health-factor-item">
            <span className="health-factor-label">Pipeline</span>
            <span className="health-factor-value" style={{ color: '#10b981' }}>
              {factors.pipeline_success_rate ?? 100}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
