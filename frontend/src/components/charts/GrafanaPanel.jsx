/**
 * GrafanaPanel — Reusable wrapper that provides Grafana-style panel chrome.
 * Dark header bar with title, optional subtitle, time-range selector,
 * loading skeleton, and hover glow.
 */

import { useState } from 'react';

const TIME_RANGES = ['7d', '14d', '30d'];

export default function GrafanaPanel({
  title,
  subtitle,
  children,
  timeRange,
  onTimeRangeChange,
  loading = false,
  className = '',
  fullWidth = false,
}) {
  return (
    <div className={`grafana-panel ${fullWidth ? 'grafana-panel-full' : ''} ${className}`}>
      <div className="grafana-panel-header">
        <div className="grafana-panel-title-group">
          <span className="grafana-panel-title">{title}</span>
          {subtitle && <span className="grafana-panel-subtitle">{subtitle}</span>}
        </div>
        {onTimeRangeChange && (
          <div className="time-range-pills">
            {TIME_RANGES.map((r) => (
              <button
                key={r}
                className={`time-range-pill ${timeRange === r ? 'active' : ''}`}
                onClick={() => onTimeRangeChange(r)}
              >
                {r}
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="grafana-panel-body">
        {loading ? (
          <div className="grafana-panel-skeleton">
            <div className="skeleton-bar" style={{ width: '80%' }} />
            <div className="skeleton-bar" style={{ width: '60%' }} />
            <div className="skeleton-bar" style={{ width: '70%' }} />
            <div className="skeleton-bar" style={{ width: '50%' }} />
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
