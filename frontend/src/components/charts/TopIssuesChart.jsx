/**
 * TopIssuesChart — Shows top recurring issues as a ranked list.
 */
export default function TopIssuesChart({ issues = [] }) {
  if (!issues || issues.length === 0) return null;

  return (
    <div className="top-issues-list">
      {issues.map((issue, i) => (
        <div key={i} className="top-issue-item">
          <div className={`top-issue-rank ${i < 3 ? `rank-${i + 1}` : 'rank-default'}`}>
            {i + 1}
          </div>
          <div className="top-issue-info">
            <div className="top-issue-title">
              {issue.title || issue.category || issue.error_signature || 'Unknown Issue'}
            </div>
            <div className="top-issue-meta">
              {issue.source_service && <span>{issue.source_service}</span>}
              {issue.first_seen && <span> · First seen: {new Date(issue.first_seen).toLocaleDateString()}</span>}
              {issue.last_seen && <span> · Last: {new Date(issue.last_seen).toLocaleDateString()}</span>}
            </div>
          </div>
          <div className="top-issue-count">
            {issue.count || issue.total_occurrences || 0}
            <div style={{ fontSize: 10, color: '#94a3b8', fontWeight: 500 }}>events</div>
          </div>
        </div>
      ))}
    </div>
  );
}
