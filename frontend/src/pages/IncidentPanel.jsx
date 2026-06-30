/**
 * IncidentPanel Page — View and manage classified incidents with P1/P2/P3.
 * Includes service filter, detailed expansion with full incident info.
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
  const [serviceFilter, setServiceFilter] = useState('');
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    loadIncidents();
  }, [page, priorityFilter, statusFilter, serviceFilter]);

  const loadIncidents = async () => {
    setLoading(true);
    try {
      const params = { page, page_size: 10 };
      if (priorityFilter) params.priority = priorityFilter;
      if (statusFilter) params.status = statusFilter;
      if (serviceFilter) params.source_service = serviceFilter;

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
      await updateIncident(id, { status: 'RESOLVED', resolved_by: 'manual' });
      loadIncidents();
    } catch (err) {
      console.error('Resolve error:', err);
    }
  };

  const formatDate = (d) => d && d !== 'None' ? new Date(d).toLocaleString() : 'N/A';

  const handleExport = (format) => {
    window.open(`http://localhost:8001/api/export/incidents?format=${format}`, '_blank');
  };

  const priorityBadge = (p) => {
    const map = { P1: 'high', P2: 'medium', P3: 'low' };
    return map[p] || 'low';
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
          <option value="P1">🔴 P1 Critical</option>
          <option value="P2">🟡 P2 Warning</option>
          <option value="P3">🟢 P3 Info</option>
        </select>
        <select className="filter-select" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
          <option value="">All Statuses</option>
          <option value="OPEN">Open</option>
          <option value="IN_PROGRESS">In Progress</option>
          <option value="ACKNOWLEDGED">Acknowledged</option>
          <option value="RESOLVED">Resolved</option>
          <option value="CLOSED">Closed</option>
        </select>
        <select className="filter-select" value={serviceFilter} onChange={(e) => { setServiceFilter(e.target.value); setPage(1); }}>
          <option value="">All Services</option>
          <option value="Azure Front Door">Azure Front Door</option>
          <option value="Azure Application Gateway">App Gateway</option>
          <option value="Azure API Management">API Management</option>
          <option value="Azure Virtual Machine">VM</option>
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
                  <span className={`priority-badge ${priorityBadge(inc.priority)}`}>{inc.priority}</span>
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
                <span>🏢 {inc.source_service || 'N/A'}</span>
                <span>📁 {inc.category || 'N/A'}</span>
                <span>🕐 {formatDate(inc.created_at)}</span>
                {inc.email_sent && <span>📧 Email sent</span>}
                {inc.historical_match_count > 0 && <span>📚 {inc.historical_match_count} past matches</span>}
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
                      <h4 style={{ fontSize: 13, color: 'var(--accent-indigo-light)', marginBottom: 8 }}>🔍 Incident Classification</h4>
                      <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>{inc.ai_analysis}</p>
                    </div>
                  )}

                  {/* Root Cause Analysis Panel */}
                  {inc.root_cause && (
                    <div style={{
                      marginBottom: 16,
                      padding: 14,
                      background: 'linear-gradient(135deg, rgba(99,102,241,0.08), rgba(139,92,246,0.05))',
                      borderRadius: 10,
                      border: '1px solid rgba(99,102,241,0.2)',
                    }}>
                      <h4 style={{ fontSize: 13, color: '#a78bfa', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                        🎯 Root Cause Analysis
                        {inc.confidence_score && (
                          <span style={{
                            fontSize: 11,
                            background: inc.confidence_score > 0.8 ? 'rgba(16,185,129,0.15)' : inc.confidence_score > 0.6 ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
                            color: inc.confidence_score > 0.8 ? '#10b981' : inc.confidence_score > 0.6 ? '#f59e0b' : '#ef4444',
                            padding: '2px 8px',
                            borderRadius: 12,
                            fontWeight: 600,
                          }}>
                            {(inc.confidence_score * 100).toFixed(0)}% confidence
                          </span>
                        )}
                      </h4>
                      <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 8 }}>{inc.root_cause}</p>
                      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 12, color: 'var(--text-tertiary)' }}>
                        {inc.root_cause_category && <span>📂 <strong>{inc.root_cause_category}</strong></span>}
                        {inc.affected_component && <span>🔧 <strong>{inc.affected_component}</strong></span>}
                        {inc.owner_team && <span>👥 <strong>{inc.owner_team}</strong></span>}
                      </div>
                    </div>
                  )}

                  {/* Structured Recommendation Panel */}
                  {(inc.immediate_resolution || inc.preventive_action) && (
                    <div style={{
                      marginBottom: 16,
                      padding: 14,
                      background: 'linear-gradient(135deg, rgba(16,185,129,0.08), rgba(6,182,212,0.05))',
                      borderRadius: 10,
                      border: '1px solid rgba(16,185,129,0.2)',
                    }}>
                      <h4 style={{ fontSize: 13, color: '#34d399', marginBottom: 10 }}>💡 Recommendations</h4>
                      {inc.immediate_resolution && (
                        <div style={{ marginBottom: 10 }}>
                          <div style={{ fontSize: 11, color: '#ef4444', fontWeight: 600, marginBottom: 4 }}>⚡ Immediate Resolution</div>
                          <pre style={{
                            fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)',
                            whiteSpace: 'pre-wrap', lineHeight: 1.6, background: 'var(--bg-tertiary)',
                            padding: 10, borderRadius: 8, margin: 0,
                          }}>{inc.immediate_resolution}</pre>
                        </div>
                      )}
                      {inc.preventive_action && (
                        <div style={{ marginBottom: 10 }}>
                          <div style={{ fontSize: 11, color: '#06b6d4', fontWeight: 600, marginBottom: 4 }}>🛡️ Preventive Action</div>
                          <pre style={{
                            fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)',
                            whiteSpace: 'pre-wrap', lineHeight: 1.6, background: 'var(--bg-tertiary)',
                            padding: 10, borderRadius: 8, margin: 0,
                          }}>{inc.preventive_action}</pre>
                        </div>
                      )}
                      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 12, color: 'var(--text-tertiary)', marginTop: 6 }}>
                        {inc.business_impact && <span>📈 {inc.business_impact}</span>}
                        {inc.estimated_resolution_minutes && <span>⏱️ Est. {inc.estimated_resolution_minutes}m</span>}
                      </div>
                    </div>
                  )}

                  {inc.ai_solution && (
                    <div style={{ marginBottom: 16 }}>
                      <h4 style={{ fontSize: 13, color: 'var(--accent-emerald)', marginBottom: 8 }}>💡 Recommended Resolution</h4>
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
                  {inc.resolution_runbook && inc.resolution_runbook !== inc.ai_solution && (
                    <div style={{ marginBottom: 16 }}>
                      <h4 style={{ fontSize: 13, color: 'var(--accent-amber)', marginBottom: 8 }}>📖 Runbook</h4>
                      <pre style={{
                        fontSize: 12, color: 'var(--text-secondary)',
                        fontFamily: 'var(--font-mono)', whiteSpace: 'pre-wrap', lineHeight: 1.7,
                        background: 'var(--bg-tertiary)', padding: 12, borderRadius: 'var(--radius-sm)',
                      }}>
                        {inc.resolution_runbook}
                      </pre>
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: 8 }}>
                    {inc.status !== 'RESOLVED' && inc.status !== 'CLOSED' && (
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
