/**
 * LogExplorer Page - Searchable, filterable log table with export.
 */

import { useEffect, useState } from 'react';
import { getLogs } from '../services/api';

export default function LogExplorer() {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ level: '', source: '', search: '' });

  useEffect(() => {
    loadLogs();
  }, [page, filters]);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const params = { page, page_size: 20 };
      if (filters.level) params.level = filters.level;
      if (filters.source) params.source = filters.source;
      if (filters.search) params.search = filters.search;

      const res = await getLogs(params);
      setLogs(res.data.items || []);
      setTotal(res.data.total || 0);
      setTotalPages(res.data.total_pages || 0);
    } catch (err) {
      console.error('Load logs error:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (d) => d ? new Date(d).toLocaleString() : 'N/A';

  const handleExport = (format) => {
    const apiBase = window.location.hostname === 'localhost' ? 'http://localhost:8001' : `http://${window.location.hostname}`;
    window.open(`${apiBase}/api/export/logs?format=${format}`, '_blank');
  };

  return (
    <div className="page-content">
      <div className="page-header animate-in">
        <h1>Log Explorer</h1>
        <div className="page-header-actions">
          <button className="btn btn-secondary btn-sm" onClick={() => handleExport('json')}>📥 JSON</button>
          <button className="btn btn-secondary btn-sm" onClick={() => handleExport('csv')}>📥 CSV</button>
          <button className="btn btn-secondary btn-sm" onClick={() => handleExport('xlsx')}>📥 Excel</button>
        </div>
      </div>

      {/* Filters */}
      <div className="filter-bar animate-in animate-in-delay-1">
        <input
          className="header-search"
          type="text"
          placeholder="Search log messages..."
          value={filters.search}
          onChange={(e) => { setFilters({ ...filters, search: e.target.value }); setPage(1); }}
          style={{ width: 300 }}
        />
        <select
          className="filter-select"
          value={filters.level}
          onChange={(e) => { setFilters({ ...filters, level: e.target.value }); setPage(1); }}
        >
          <option value="">All Levels</option>
          <option value="CRITICAL">🔴 Critical</option>
          <option value="ERROR">🟠 Error</option>
          <option value="WARNING">🟡 Warning</option>
          <option value="INFO">🔵 Info</option>
        </select>
        <input
          className="header-search"
          type="text"
          placeholder="Filter by source..."
          value={filters.source}
          onChange={(e) => { setFilters({ ...filters, source: e.target.value }); setPage(1); }}
          style={{ width: 200 }}
        />
        <span style={{ marginLeft: 'auto', fontSize: 13, color: 'var(--text-tertiary)' }}>
          {total.toLocaleString()} logs
        </span>
      </div>

      {/* Table */}
      <div className="glass-card animate-in animate-in-delay-2" style={{ padding: 0, overflow: 'auto' }}>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
            <span className="spinner"></span>
          </div>
        ) : logs.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📝</div>
            <div className="empty-state-title">No logs found</div>
            <div className="empty-state-text">Try adjusting your filters or seed some test data</div>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Level</th>
                <th>Source</th>
                <th>Message</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td style={{ whiteSpace: 'nowrap', fontSize: 12, fontFamily: 'var(--font-mono)' }}>
                    {formatDate(log.timestamp)}
                  </td>
                  <td>
                    <span className={`log-level ${log.level.toLowerCase()}`}>
                      {log.level}
                    </span>
                  </td>
                  <td style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
                    {log.source}
                  </td>
                  <td>
                    <span className="log-message">{log.message}</span>
                  </td>
                  <td>
                    <span className={`status-dot ${log.is_processed ? 'success' : 'idle'}`}></span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
          {totalPages > 7 && <span style={{ color: 'var(--text-muted)' }}>...</span>}
          <button className="pagination-btn" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next →</button>
        </div>
      )}
    </div>
  );
}
