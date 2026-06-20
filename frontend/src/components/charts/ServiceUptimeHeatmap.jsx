/**
 * ServiceUptimeHeatmap — 30-day grid heatmap per service.
 * Each cell = 1 day, colored by max incident severity that day.
 */

import { useState } from 'react';

const SERVICE_DISPLAY = {
  'azure-front-door': { label: 'Front Door', icon: '🌐' },
  'azure-app-gateway': { label: 'App Gateway', icon: '🔀' },
  'azure-apim': { label: 'API Mgmt', icon: '⚙️' },
  'azure-vm': { label: 'VM', icon: '🖥️' },
};

const SEVERITY_COLORS = {
  P1: { bg: 'rgba(239,68,68,0.7)', border: '#ef4444', label: 'P1 Critical' },
  P2: { bg: 'rgba(245,158,11,0.5)', border: '#f59e0b', label: 'P2 Warning' },
  P3: { bg: 'rgba(99,102,241,0.35)', border: '#6366f1', label: 'P3 Info' },
  null: { bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.3)', label: 'No incidents' },
};

export default function ServiceUptimeHeatmap({ heatmapData = [], services = [], days = 30 }) {
  const [tooltip, setTooltip] = useState(null);

  // Group by service
  const byService = {};
  services.forEach((svc) => { byService[svc] = []; });
  heatmapData.forEach((cell) => {
    if (byService[cell.service]) {
      byService[cell.service].push(cell);
    }
  });

  return (
    <div className="uptime-heatmap">
      <div className="uptime-heatmap-grid">
        {services.map((svc) => {
          const display = SERVICE_DISPLAY[svc] || { label: svc, icon: '☁️' };
          const cells = byService[svc] || [];

          return (
            <div key={svc} className="uptime-heatmap-row">
              <div className="uptime-heatmap-label" title={display.label}>
                <span className="uptime-heatmap-icon">{display.icon}</span>
                <span className="uptime-heatmap-name">{display.label}</span>
              </div>
              <div className="uptime-heatmap-cells">
                {cells.map((cell, i) => {
                  const severity = cell.count > 0 ? cell.max_severity : null;
                  const colors = SEVERITY_COLORS[severity] || SEVERITY_COLORS[null];
                  const dateLabel = new Date(cell.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

                  return (
                    <div
                      key={`${svc}-${i}`}
                      className="uptime-heatmap-cell"
                      style={{
                        background: colors.bg,
                        borderColor: cell.count > 0 ? colors.border : 'transparent',
                      }}
                      onMouseEnter={(e) => setTooltip({
                        x: e.clientX,
                        y: e.clientY,
                        date: dateLabel,
                        service: display.label,
                        count: cell.count,
                        severity: colors.label,
                        p1: cell.P1,
                        p2: cell.P2,
                        p3: cell.P3,
                      })}
                      onMouseLeave={() => setTooltip(null)}
                    />
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="uptime-heatmap-legend">
        <span className="uptime-heatmap-legend-label">Less</span>
        {[null, 'P3', 'P2', 'P1'].map((sev) => {
          const colors = SEVERITY_COLORS[sev];
          return (
            <div
              key={sev || 'none'}
              className="uptime-heatmap-legend-cell"
              style={{ background: colors.bg }}
              title={colors.label}
            />
          );
        })}
        <span className="uptime-heatmap-legend-label">More</span>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div className="uptime-heatmap-tooltip" style={{
          left: tooltip.x + 12,
          top: tooltip.y - 80,
        }}>
          <div className="uptime-tooltip-date">{tooltip.date}</div>
          <div className="uptime-tooltip-service">{tooltip.service}</div>
          <div className="uptime-tooltip-severity">{tooltip.severity}</div>
          {tooltip.count > 0 && (
            <div className="uptime-tooltip-breakdown">
              P1: {tooltip.p1} · P2: {tooltip.p2} · P3: {tooltip.p3}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
