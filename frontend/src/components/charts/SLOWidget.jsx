/**
 * SLOWidget — SLO compliance gauge with error budget bar.
 * Shows target vs actual compliance %, error budget remaining, and burn rate.
 */

import { useRef, useEffect, useState } from 'react';

export default function SLOWidget({ sloData = null }) {
  const canvasRef = useRef(null);
  const [animPct, setAnimPct] = useState(0);

  const data = sloData || {
    target_pct: 99.5,
    compliance_pct: 100,
    error_budget_total_pct: 0.5,
    error_budget_remaining_pct: 0.5,
    error_budget_used_pct: 0,
    burn_rate: 0,
    total_incidents: 0,
    within_sla: 0,
  };

  useEffect(() => {
    let start = null;
    const from = animPct;
    const to = data.compliance_pct;
    const duration = 1200;

    function animate(ts) {
      if (!start) start = ts;
      const progress = Math.min((ts - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimPct(from + (to - from) * eased);
      if (progress < 1) requestAnimationFrame(animate);
    }
    requestAnimationFrame(animate);
  }, [data.compliance_pct]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = 280;
    const h = 150;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h - 10;
    const radius = 100;
    const lineWidth = 12;
    const startAngle = Math.PI;
    const endAngle = Math.PI * 2;
    const totalArc = endAngle - startAngle;
    const valueAngle = startAngle + (Math.min(animPct, 100) / 100) * totalArc;

    // Determine color
    let color = '#10b981';
    if (animPct < data.target_pct) color = '#f59e0b';
    if (animPct < data.target_pct - 1) color = '#ef4444';

    // Background track
    ctx.beginPath();
    ctx.arc(cx, cy, radius, startAngle, endAngle);
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Target line
    const targetAngle = startAngle + (data.target_pct / 100) * totalArc;
    const tX = cx + Math.cos(targetAngle) * (radius - lineWidth);
    const tY = cy + Math.sin(targetAngle) * (radius - lineWidth);
    const tX2 = cx + Math.cos(targetAngle) * (radius + lineWidth);
    const tY2 = cy + Math.sin(targetAngle) * (radius + lineWidth);
    ctx.beginPath();
    ctx.moveTo(tX, tY);
    ctx.lineTo(tX2, tY2);
    ctx.strokeStyle = 'rgba(255,255,255,0.3)';
    ctx.lineWidth = 2;
    ctx.setLineDash([3, 3]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Value arc
    if (animPct > 0) {
      const grad = ctx.createLinearGradient(cx - radius, cy, cx + radius, cy);
      grad.addColorStop(0, color + '88');
      grad.addColorStop(1, color);
      ctx.beginPath();
      ctx.arc(cx, cy, radius, startAngle, valueAngle);
      ctx.strokeStyle = grad;
      ctx.lineWidth = lineWidth;
      ctx.lineCap = 'round';
      ctx.stroke();
    }

    // Center text
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = '800 32px Inter';
    ctx.fillStyle = color;
    ctx.fillText(animPct.toFixed(1) + '%', cx, cy - 30);

    ctx.font = '500 11px Inter';
    ctx.fillStyle = 'rgba(255,255,255,0.4)';
    ctx.fillText('SLO COMPLIANCE', cx, cy - 8);
  }, [animPct, data.target_pct]);

  const budgetPct = data.error_budget_total_pct > 0
    ? Math.min((data.error_budget_remaining_pct / data.error_budget_total_pct) * 100, 100)
    : 100;
  const budgetColor = budgetPct > 60 ? '#10b981' : budgetPct > 30 ? '#f59e0b' : '#ef4444';

  return (
    <div className="slo-widget">
      <canvas ref={canvasRef} style={{ width: 280, height: 150 }} />
      <div className="slo-details">
        <div className="slo-detail-row">
          <span className="slo-detail-label">Target SLO</span>
          <span className="slo-detail-value">{data.target_pct}%</span>
        </div>
        <div className="slo-detail-row">
          <span className="slo-detail-label">Total Incidents</span>
          <span className="slo-detail-value">{data.total_incidents}</span>
        </div>
        <div className="slo-detail-row">
          <span className="slo-detail-label">SLA Violations</span>
          <span className="slo-detail-value" style={{ color: (data.sla_violations || 0) > 0 ? '#ef4444' : '#10b981' }}>
            {data.sla_violations || 0}
          </span>
        </div>
        <div className="slo-budget-section">
          <div className="slo-budget-header">
            <span className="slo-budget-label">Error Budget</span>
            <span className="slo-budget-value" style={{ color: budgetColor }}>
              {data.error_budget_remaining_pct}% remaining
            </span>
          </div>
          <div className="slo-budget-bar-track">
            <div className="slo-budget-bar-fill" style={{
              width: `${budgetPct}%`,
              background: `linear-gradient(90deg, ${budgetColor}88, ${budgetColor})`,
            }} />
          </div>
          <div className="slo-burn-rate">
            Burn Rate: <span style={{ color: data.burn_rate > 1 ? '#ef4444' : '#64748b', fontWeight: 700 }}>
              {data.burn_rate}x
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
