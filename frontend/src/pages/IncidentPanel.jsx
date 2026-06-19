/**
 * IncidentPanel Page - View and manage classified incidents.
 */

import { useEffect, useState } from 'react';
import { getIncidents, updateIncident } from '../services/api';

export default function IncidentPanel() {
  const [incidents, setIncidents] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [priorityFilter, setPriorityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    loadIncidents();
  }, [page, priorityFilter, statusFilter]);

  const loadIncidents = async () => {
    setLoading(true);
    try {
      const params = { page, page_size: 10 };
      if (priorityFilter) params.priority = priorityFilter;
      if (statusFilter) params.status = statusFilter;

      const res = await getIncidents(params);
      setIncidents(res.data.items || []);
      setTotal(res.data.total || 0);
      setTotalPages(res.data.total_pages || 0);
    } catch (err) {
      console.error('Load incidents error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleResolve = async (id) => {
    try {
      await updateIncident(id, { status: 'RESOLVED' });
      loadIncidents();
    } catch (err) {
      console.error('Resolve error:', err);
    }
  };

  const formatDate = (d) => d ? new Date(d).toLocaleString() : 'N/A';

  const handleExport = (format) => {
    window.open(`http://localhost:8000/api/export/incidents?format=${format}`, '_blank');
  };

  return (
    <div className="page-content">
      <div className="page-header animate-in">
        <h1>Incident Panel</h1>
        <div className="page-header-actions">
          <button className="btn btn-secondary btn-sm" onClick={() => handleExport('json')}>📥 JSON</button>
          <button className="btn btn-secondary btn-sm" onClick={() => handleExport('csv')}>📥 CSV</button>
          <button className="btn btn-secondary btn-sm" onClick={() => handleExport('xlsx')}>📥 Excel</button>
        </div>
      </div>

      {/* Filters */}
      <div className="filter-bar animate-in animate-in-delay-1">
        <select className="filter-select" value={priorityFilter} onChange={(e) => { setPriorityFilter(e.target.value); setPage(1); }}>
          <option value="">All Priorities</option>
          <option value="HIGH">🔴 High</option>
          <option value="MEDIUM">🟡 Medium</option>
          <option value="LOW">🟢 Low</option>
        </select>
        <select className="filter-select" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
          <option value="">All Statuses</option>
          <option value="OPEN">Open</option>
          <option value="IN_PROGRESS">In Progress</option>
          <option value="ACKNOWLEDGED">Acknowledged</option>
          <option value="RESOLVED">Resolved</option>
          <option value="CLOSED">Closed</option>
        </select>
        <span style={{ marginLeft: 'auto', fontSize: 13, color: 'var(--text-tertiary)' }}>
          {total} incident{total !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Incidents List */}
      <div className="animate-in animate-in-delay-2">
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
            <span className="spinner"></span>
          </div>
        ) : incidents.length === 0 ? (
          <div className="glass-card">
            <div className="empty-state">
              <div className="empty-state-icon">✅</div>
              <div className="empty-state-title">No incidents found</div>
              <div className="empty-state-text">Run the pipeline to detect and classify issues</div>
            </div>
          </div>
        ) : (
          incidents.map((inc) => (
            <div
              key={inc.id}
              className="incident-card"
              onClick={() => setExpandedId(expandedId === inc.id ? null : inc.id)}
            >
              <div className="incident-card-header">
                <span className="incident-card-title">{inc.title}</span>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span className={`priority-badge ${inc.priority.toLowerCase()}`}>{inc.priority}</span>
                  <span className="priority-badge" style={{
                    background: 'var(--bg-glass)',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--border-default)',
                  }}>
                    {inc.status.replace('_', ' ')}
                  </span>
                </div>
              </div>

              <div className="incident-card-body">
                {inc.description?.substring(0, 200)}{inc.description?.length > 200 ? '...' : ''}
              </div>

              <div className="incident-card-meta">
                <span>📁 {inc.category || 'N/A'}</span>
                <span>🕐 {formatDate(inc.created_at)}</span>
                {inc.email_sent && <span>📧 Email sent {formatDate(inc.email_sent_at)}</span>}
              </div>

              {/* Expanded Details */}
              {expandedId === inc.id && (
                <div style={{
                  marginTop: 16,
                  padding: 16,
                  background: 'var(--bg-glass)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                }}>
                  {inc.ai_analysis && (
                    <div style={{ marginBottom: 16 }}>
                      <h4 style={{ fontSize: 13, color: 'var(--accent-indigo-light)', marginBottom: 8 }}>🤖 AI Analysis</h4>
                      <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>{inc.ai_analysis}</p>
                    </div>
                  )}
                  {inc.ai_solution && (
                    <div style={{ marginBottom: 16 }}>
                      <h4 style={{ fontSize: 13, color: 'var(--accent-emerald)', marginBottom: 8 }}>💡 AI Solution</h4>
                      <pre style={{
                        fontSize: 12,
                        color: 'var(--text-secondary)',
                        fontFamily: 'var(--font-mono)',
                        whiteSpace: 'pre-wrap',
                        lineHeight: 1.7,
                        background: 'var(--bg-tertiary)',
                        padding: 12,
                        borderRadius: 'var(--radius-sm)',
                      }}>
                        {inc.ai_solution}
                      </pre>
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: 8 }}>
                    {inc.status !== 'RESOLVED' && (
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={(e) => { e.stopPropagation(); handleResolve(inc.id); }}
                      >
                        ✓ Mark Resolved
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="pagination">
          <button className="pagination-btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>← Prev</button>
          {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
            const p = i + 1;
            return (
              <button key={p} className={`pagination-btn ${page === p ? 'active' : ''}`} onClick={() => setPage(p)}>
                {p}
              </button>
            );
          })}
          <button className="pagination-btn" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next →</button>
        </div>
      )}
    </div>
  );
}
