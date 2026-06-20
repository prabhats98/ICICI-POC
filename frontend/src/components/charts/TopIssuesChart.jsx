/**
 * TopIssuesChart — User-friendly recurring issues visualization.
 * Redesigned for clarity: each issue card clearly shows what happened,
 * which service is affected, how severe it is, and how often it occurs.
 * Includes a helpful explainer banner and expandable detail cards.
 */

import { useState } from 'react';

const SERVICE_META = {
  'azure-front-door': { label: 'Azure Front Door', short: 'Front Door', icon: '🌐', color: '#6366f1', bg: 'rgba(99,102,241,0.12)', description: 'CDN & global load balancer' },
  'azure-app-gateway': { label: 'Azure App Gateway', short: 'App Gateway', icon: '🔀', color: '#8b5cf6', bg: 'rgba(139,92,246,0.12)', description: 'Web application firewall & L7 load balancer' },
  'azure-apim': { label: 'Azure API Management', short: 'API Mgmt', icon: '⚙️', color: '#06b6d4', bg: 'rgba(6,182,212,0.12)', description: 'API gateway & management platform' },
  'azure-vm': { label: 'Azure Virtual Machine', short: 'VM', icon: '🖥️', color: '#10b981', bg: 'rgba(16,185,129,0.12)', description: 'Virtual machine compute' },
  'Azure Front Door': { label: 'Azure Front Door', short: 'Front Door', icon: '🌐', color: '#6366f1', bg: 'rgba(99,102,241,0.12)', description: 'CDN & global load balancer' },
  'Azure Application Gateway': { label: 'Azure App Gateway', short: 'App Gateway', icon: '🔀', color: '#8b5cf6', bg: 'rgba(139,92,246,0.12)', description: 'Web application firewall & L7 load balancer' },
  'Azure Application Gateway (and Backend Routing/Application)': { label: 'Azure App Gateway', short: 'App Gateway', icon: '🔀', color: '#8b5cf6', bg: 'rgba(139,92,246,0.12)', description: 'Web application firewall & L7 load balancer' },
  'Azure API Management': { label: 'Azure API Management', short: 'API Mgmt', icon: '⚙️', color: '#06b6d4', bg: 'rgba(6,182,212,0.12)', description: 'API gateway & management platform' },
  'Azure Virtual Machine': { label: 'Azure Virtual Machine', short: 'VM', icon: '🖥️', color: '#10b981', bg: 'rgba(16,185,129,0.12)', description: 'Virtual machine compute' },
};

const CATEGORY_INFO = {
  'Security': { color: '#ef4444', bg: 'rgba(239,68,68,0.10)', border: 'rgba(239,68,68,0.25)', icon: '🛡️', tip: 'Unauthorized access attempts, WAF blocks, or auth failures' },
  'Performance': { color: '#f59e0b', bg: 'rgba(245,158,11,0.10)', border: 'rgba(245,158,11,0.25)', icon: '⚡', tip: 'Slow responses, timeouts, or resource bottlenecks' },
  'Availability': { color: '#6366f1', bg: 'rgba(99,102,241,0.10)', border: 'rgba(99,102,241,0.25)', icon: '🔄', tip: 'Service downtime, failed health checks, or connectivity issues' },
  'Configuration': { color: '#06b6d4', bg: 'rgba(6,182,212,0.10)', border: 'rgba(6,182,212,0.25)', icon: '🔧', tip: 'Misconfigured routes, missing backends, or wrong rules' },
  'Network': { color: '#8b5cf6', bg: 'rgba(139,92,246,0.10)', border: 'rgba(139,92,246,0.25)', icon: '🌐', tip: 'DNS issues, SSL errors, or network connectivity problems' },
};

// Map error titles to user-friendly impact descriptions
function getImpactDescription(title, category) {
  const t = (title || '').toLowerCase();
  if (t.includes('404')) return 'Users are hitting broken links or missing pages — this may indicate misconfigured routes or deleted resources.';
  if (t.includes('500')) return 'The server is crashing when processing requests — this could be a code bug, database issue, or resource exhaustion.';
  if (t.includes('502')) return 'The backend server is unreachable — the app gateway cannot forward requests to your application.';
  if (t.includes('503')) return 'The service is temporarily unavailable — the server may be overloaded or under maintenance.';
  if (t.includes('403') || t.includes('forbidden')) return 'Access is being denied — this could be WAF rules blocking legitimate traffic or unauthorized access attempts.';
  if (t.includes('401') || t.includes('unauthorized')) return 'Authentication is failing — users may be unable to log in or API keys may have expired.';
  if (t.includes('402') || t.includes('payment')) return 'Payment or subscription-related errors — this may indicate billing issues with Azure services or API quotas exceeded.';
  if (t.includes('timeout')) return 'Requests are taking too long to complete — the backend may be overloaded or external dependencies are slow.';
  if (t.includes('ssl') || t.includes('certificate')) return 'SSL/TLS certificate issues — this can prevent secure connections and show browser warnings to users.';
  if (t.includes('5xx') || t.includes('backend')) return 'Multiple server-side failures detected — your backend services are experiencing intermittent errors.';
  if (t.includes('rate limit') || t.includes('throttl')) return 'Too many requests are hitting the API — clients may be exceeding rate limits and getting blocked.';
  if (category?.toLowerCase().includes('security')) return 'A security-related pattern was detected — review access controls and firewall rules.';
  if (category?.toLowerCase().includes('performance')) return 'Performance degradation detected — response times may be impacting user experience.';
  return 'A recurring error pattern was identified in your Azure infrastructure logs.';
}

function getRelativeTime(dateStr) {
  if (!dateStr) return 'Unknown';
  const now = new Date();
  const date = new Date(dateStr);
  const diff = Math.floor((now - date) / 1000);

  if (diff < 60) return 'Just now';
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 7200) return '1 hour ago';
  if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
  if (diff < 172800) return 'Yesterday';
  if (diff < 604800) return `${Math.floor(diff / 86400)} days ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function getSeverityInfo(count, maxCount) {
  const ratio = maxCount > 0 ? count / maxCount : 0;
  if (ratio >= 0.8) return { level: 'critical', label: 'Critical Frequency', color: '#ef4444', bg: 'rgba(239,68,68,0.12)', icon: '🔴', barColor: 'linear-gradient(90deg, #dc2626, #ef4444)' };
  if (ratio >= 0.5) return { level: 'high', label: 'High Frequency', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', icon: '🟠', barColor: 'linear-gradient(90deg, #d97706, #f59e0b)' };
  if (ratio >= 0.25) return { level: 'medium', label: 'Medium Frequency', color: '#eab308', bg: 'rgba(234,179,8,0.12)', icon: '🟡', barColor: 'linear-gradient(90deg, #ca8a04, #eab308)' };
  return { level: 'low', label: 'Low Frequency', color: '#10b981', bg: 'rgba(16,185,129,0.12)', icon: '🟢', barColor: 'linear-gradient(90deg, #059669, #10b981)' };
}

function getCategoryStyle(category) {
  if (!category) return { color: '#64748b', bg: 'rgba(100,116,139,0.10)', border: 'rgba(100,116,139,0.25)', icon: '📋', tip: 'Uncategorized issue' };
  for (const [key, style] of Object.entries(CATEGORY_INFO)) {
    if (category.toLowerCase().includes(key.toLowerCase())) return style;
  }
  return { color: '#818cf8', bg: 'rgba(129,140,248,0.10)', border: 'rgba(129,140,248,0.25)', icon: '📋', tip: category };
}

export default function TopIssuesChart({ issues = [] }) {
  const [expandedIdx, setExpandedIdx] = useState(null);
  const [showHelp, setShowHelp] = useState(false);
  const maxCount = Math.max(...issues.map((i) => i.count), 1);
  const totalOccurrences = issues.reduce((sum, i) => sum + i.count, 0);
  const uniqueServices = [...new Set(issues.map((i) => i.source_service))].filter(Boolean);
  const uniqueCategories = [...new Set(issues.map((i) => i.category))].filter(Boolean);

  const handleCardClick = (idx) => {
    setExpandedIdx(expandedIdx === idx ? null : idx);
  };

  return (
    <div className="top-issues-container">
      {/* Helpful Explainer */}
      <div className="top-issues-help-banner">
        <div className="top-issues-help-main">
          <span className="top-issues-help-icon">💡</span>
          <span className="top-issues-help-text">
            These are the <strong>most frequently occurring error patterns</strong> detected across your Azure cloud services.
            Issues appearing more often may indicate systemic problems that need attention.
          </span>
          <button
            className="top-issues-help-toggle"
            onClick={() => setShowHelp(!showHelp)}
            title="Learn more"
          >
            {showHelp ? '▾ Less' : '▸ Learn more'}
          </button>
        </div>
        {showHelp && (
          <div className="top-issues-help-details">
            <div className="top-issues-help-detail-item">
              <span className="top-issues-help-detail-icon">📊</span>
              <span><strong>Occurrence Count</strong> — How many times this exact error pattern was detected. Higher = more urgent.</span>
            </div>
            <div className="top-issues-help-detail-item">
              <span className="top-issues-help-detail-icon">🏷️</span>
              <span><strong>Service Badge</strong> — Which Azure service (e.g., App Gateway, API Management) generated this error.</span>
            </div>
            <div className="top-issues-help-detail-item">
              <span className="top-issues-help-detail-icon">📁</span>
              <span><strong>Category</strong> — The type of issue: Security, Performance, Availability, or Configuration.</span>
            </div>
            <div className="top-issues-help-detail-item">
              <span className="top-issues-help-detail-icon">📏</span>
              <span><strong>Frequency Bar</strong> — Visual comparison showing how this issue's count compares to the most frequent one.</span>
            </div>
          </div>
        )}
      </div>

      {/* Summary Strip */}
      <div className="top-issues-summary-strip">
        <div className="top-issues-summary-item">
          <span className="top-issues-summary-value">{totalOccurrences}</span>
          <span className="top-issues-summary-label">Total Occurrences</span>
        </div>
        <div className="top-issues-summary-divider" />
        <div className="top-issues-summary-item">
          <span className="top-issues-summary-value">{uniqueServices.length}</span>
          <span className="top-issues-summary-label">Services Affected</span>
        </div>
        <div className="top-issues-summary-divider" />
        <div className="top-issues-summary-item">
          <span className="top-issues-summary-value">{uniqueCategories.length}</span>
          <span className="top-issues-summary-label">Categories</span>
        </div>
        <div className="top-issues-summary-divider" />
        <div className="top-issues-summary-item">
          <span className="top-issues-summary-value">{issues.length}</span>
          <span className="top-issues-summary-label">Unique Patterns</span>
        </div>
      </div>

      {/* Issue Cards */}
      <div className="top-issues-list">
        {issues.map((issue, idx) => {
          const svc = SERVICE_META[issue.source_service] || {
            label: issue.source_service || 'Unknown Service',
            short: issue.source_service || 'Unknown',
            icon: '☁️',
            color: '#64748b',
            bg: 'rgba(100,116,139,0.12)',
            description: 'Azure cloud service',
          };
          const catStyle = getCategoryStyle(issue.category);
          const severity = getSeverityInfo(issue.count, maxCount);
          const barPercent = Math.max((issue.count / maxCount) * 100, 3);
          const isExpanded = expandedIdx === idx;
          const impactText = getImpactDescription(issue.title, issue.category);

          return (
            <div
              key={`${issue.title}-${idx}`}
              className={`top-issue-card ${isExpanded ? 'expanded' : ''}`}
              style={{ animationDelay: `${idx * 60}ms` }}
              onClick={() => handleCardClick(idx)}
            >
              {/* Left: Rank + Severity Indicator */}
              <div className="top-issue-left">
                <div className="top-issue-rank-badge" style={{
                  background: idx < 3
                    ? ['linear-gradient(135deg, #fbbf24, #f59e0b)', 'linear-gradient(135deg, #94a3b8, #cbd5e1)', 'linear-gradient(135deg, #cd7f32, #a0522d)'][idx]
                    : 'rgba(255,255,255,0.06)',
                  color: idx < 3 ? (idx === 1 ? '#0f172a' : idx === 0 ? '#000' : '#fff') : 'var(--text-muted)',
                  boxShadow: idx < 3
                    ? ['0 0 12px rgba(251,191,36,0.35)', '0 0 10px rgba(148,163,184,0.25)', '0 0 10px rgba(205,127,50,0.25)'][idx]
                    : 'none',
                  border: idx >= 3 ? '1px solid var(--border-subtle)' : 'none',
                }}>
                  #{idx + 1}
                </div>
              </div>

              {/* Center: Main Content */}
              <div className="top-issue-center">
                {/* Title */}
                <div className="top-issue-title-area">
                  <h4 className="top-issue-title">{issue.title}</h4>
                  <div className="top-issue-severity-pill" style={{
                    background: severity.bg,
                    color: severity.color,
                    border: `1px solid ${severity.color}33`,
                  }}>
                    {severity.icon} {severity.label}
                  </div>
                </div>

                {/* Tags: Service + Category + Last Seen */}
                <div className="top-issue-meta-row">
                  {/* Service */}
                  <div className="top-issue-meta-tag" style={{
                    background: svc.bg,
                    borderColor: `${svc.color}33`,
                    color: svc.color,
                  }} title={`Source: ${svc.label} — ${svc.description}`}>
                    <span className="top-issue-meta-tag-icon">{svc.icon}</span>
                    <span>{svc.short}</span>
                  </div>

                  {/* Category */}
                  {issue.category && (
                    <div className="top-issue-meta-tag" style={{
                      background: catStyle.bg,
                      borderColor: catStyle.border,
                      color: catStyle.color,
                    }} title={`Category: ${catStyle.tip}`}>
                      <span className="top-issue-meta-tag-icon">{catStyle.icon}</span>
                      <span>{issue.category.length > 30 ? issue.category.substring(0, 27) + '...' : issue.category}</span>
                    </div>
                  )}

                  {/* Last Seen */}
                  <div className="top-issue-last-seen-tag" title={`Last seen: ${issue.last_seen ? new Date(issue.last_seen).toLocaleString() : 'Unknown'}`}>
                    🕐 Last seen {getRelativeTime(issue.last_seen)}
                  </div>
                </div>

                {/* Frequency Bar */}
                <div className="top-issue-freq-section">
                  <div className="top-issue-freq-header">
                    <span className="top-issue-freq-label">Frequency</span>
                    <span className="top-issue-freq-pct" style={{ color: severity.color }}>
                      {Math.round(barPercent)}% of max
                    </span>
                  </div>
                  <div className="top-issue-bar-track">
                    <div
                      className="top-issue-bar-fill"
                      style={{
                        width: `${barPercent}%`,
                        background: severity.barColor,
                      }}
                    />
                  </div>
                </div>

                {/* Expanded Detail */}
                {isExpanded && (
                  <div className="top-issue-expanded-detail">
                    <div className="top-issue-impact-box">
                      <div className="top-issue-impact-header">
                        <span className="top-issue-impact-icon">💡</span>
                        <span className="top-issue-impact-title">What does this mean?</span>
                      </div>
                      <p className="top-issue-impact-text">{impactText}</p>
                    </div>
                    <div className="top-issue-detail-grid">
                      <div className="top-issue-detail-item">
                        <span className="top-issue-detail-label">Service</span>
                        <span className="top-issue-detail-value">{svc.label}</span>
                      </div>
                      <div className="top-issue-detail-item">
                        <span className="top-issue-detail-label">Category</span>
                        <span className="top-issue-detail-value">{issue.category || '—'}</span>
                      </div>
                      <div className="top-issue-detail-item">
                        <span className="top-issue-detail-label">Occurrences</span>
                        <span className="top-issue-detail-value" style={{ color: severity.color, fontWeight: 700 }}>
                          {issue.count} time{issue.count !== 1 ? 's' : ''}
                        </span>
                      </div>
                      <div className="top-issue-detail-item">
                        <span className="top-issue-detail-label">Last Detected</span>
                        <span className="top-issue-detail-value">{issue.last_seen ? new Date(issue.last_seen).toLocaleString() : '—'}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Click hint */}
                <div className="top-issue-click-hint">
                  {isExpanded ? '▾ Click to collapse' : '▸ Click for details & impact'}
                </div>
              </div>

              {/* Right: Count Badge */}
              <div className="top-issue-right">
                <div className="top-issue-count-badge" style={{
                  background: severity.bg,
                  color: severity.color,
                  border: `1px solid ${severity.color}33`,
                }}>
                  <span className="top-issue-count-number">{issue.count}</span>
                  <span className="top-issue-count-label">{issue.count === 1 ? 'time' : 'times'}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
