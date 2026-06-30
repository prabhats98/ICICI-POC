/**
 * IncidentTimeline — Shows recent incidents in a timeline format.
 */
export default function IncidentTimeline({ incidents = [] }) {
  if (!incidents || incidents.length === 0) {
    return (
      <div className="empty-state" style={{ padding: 24 }}>
        <div className="empty-state-icon">📋</div>
        <div className="empty-state-title">No incidents</div>
        <div className="empty-state-text">Incidents will appear here after pipeline analysis</div>
      </div>
    );
  }

  const priorityColors = { P1: '#ef4444', P2: '#f59e0b', P3: '#10b981' };
  const priorityBg = { P1: '#fef2f2', P2: '#fffbeb', P3: '#ecfdf5' };

  return (
    <div className="incident-timeline">
      {incidents.slice(0, 10).map((inc) => (
        <div key={inc.id} className="timeline-item" style={{ borderLeft: `3px solid ${priorityColors[inc.priority] || '#94a3b8'}` }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <span style={{
                padding: '2px 8px', borderRadius: 12, fontSize: 10, fontWeight: 700,
                background: priorityBg[inc.priority] || '#f1f5f9',
                color: priorityColors[inc.priority] || '#64748b',
              }}>
                {inc.priority}
              </span>
              <span style={{ fontSize: 11, color: '#64748b' }}>
                {inc.source_service || 'Azure'}
              </span>
              <span style={{ fontSize: 11, color: '#94a3b8', marginLeft: 'auto' }}>
                {inc.created_at ? new Date(inc.created_at).toLocaleString() : ''}
              </span>
            </div>
            <div className="timeline-title">{inc.title || 'Incident'}</div>
            {inc.description && (
              <div className="timeline-detail" style={{ marginTop: 4 }}>
                {inc.description.substring(0, 120)}{inc.description.length > 120 ? '…' : ''}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
