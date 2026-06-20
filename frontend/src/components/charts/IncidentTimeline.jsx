/**
 * IncidentTimeline — Vertical PagerDuty-style timeline with live events.
 * Color-coded by priority with relative timestamps and pulse animation.
 */

const PRIORITY_STYLES = {
  P1: { color: '#ef4444', bg: 'rgba(239,68,68,0.12)', border: '#ef444433', icon: '🔴', label: 'Critical' },
  P2: { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', border: '#f59e0b33', icon: '🟡', label: 'Warning' },
  P3: { color: '#10b981', bg: 'rgba(16,185,129,0.12)', border: '#10b98133', icon: '🟢', label: 'Info' },
};

const STATUS_ICONS = {
  OPEN: '🔓',
  IN_PROGRESS: '⚡',
  ACKNOWLEDGED: '👁️',
  RESOLVED: '✅',
  CLOSED: '🔒',
};

function getRelativeTime(dateStr) {
  if (!dateStr || dateStr === 'None') return 'Unknown';
  const now = new Date();
  const date = new Date(dateStr);
  const diff = Math.floor((now - date) / 1000);
  if (diff < 60) return 'Just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 7200) return '1h ago';
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 172800) return 'Yesterday';
  return `${Math.floor(diff / 86400)}d ago`;
}

const SERVICE_LABELS = {
  'azure-front-door': 'Front Door',
  'azure-app-gateway': 'App Gateway',
  'azure-apim': 'API Mgmt',
  'azure-vm': 'VM',
};

export default function IncidentTimeline({ incidents = [] }) {
  if (incidents.length === 0) {
    return (
      <div className="empty-state" style={{ padding: '24px' }}>
        <div className="empty-state-icon">📋</div>
        <div className="empty-state-title">No recent events</div>
        <div className="empty-state-text">Incidents will appear here in real-time</div>
      </div>
    );
  }

  return (
    <div className="incident-timeline">
      {incidents.slice(0, 12).map((inc, idx) => {
        const pStyle = PRIORITY_STYLES[inc.priority] || PRIORITY_STYLES.P3;
        const isFirst = idx === 0;
        const statusIcon = STATUS_ICONS[inc.status] || '📋';
        const serviceName = SERVICE_LABELS[inc.source_service] || inc.source_service || '—';

        return (
          <div
            key={inc.id}
            className={`timeline-event ${isFirst ? 'timeline-event-latest' : ''}`}
            style={{ animationDelay: `${idx * 60}ms` }}
          >
            {/* Timeline connector */}
            <div className="timeline-connector">
              <div
                className={`timeline-dot ${isFirst ? 'timeline-dot-pulse' : ''}`}
                style={{
                  background: pStyle.color,
                  boxShadow: isFirst ? `0 0 12px ${pStyle.color}66` : 'none',
                }}
              />
              {idx < incidents.length - 1 && <div className="timeline-line" />}
            </div>

            {/* Event content */}
            <div className="timeline-content" style={{
              borderColor: pStyle.border,
            }}>
              <div className="timeline-header">
                <span className="timeline-priority-badge" style={{
                  background: pStyle.bg,
                  color: pStyle.color,
                  border: `1px solid ${pStyle.border}`,
                }}>
                  {inc.priority}
                </span>
                <span className="timeline-status">
                  {statusIcon} {inc.status?.replace('_', ' ')}
                </span>
                <span className="timeline-time">{getRelativeTime(inc.created_at)}</span>
              </div>
              <div className="timeline-title">{inc.title}</div>
              <div className="timeline-meta">
                <span className="timeline-service">{serviceName}</span>
                {inc.category && (
                  <>
                    <span className="timeline-sep">·</span>
                    <span className="timeline-category">{inc.category}</span>
                  </>
                )}
                {inc.email_sent && (
                  <span className="timeline-email-badge">📧</span>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
