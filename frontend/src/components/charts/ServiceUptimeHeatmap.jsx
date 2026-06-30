/**
 * ServiceUptimeHeatmap — Shows service uptime as a colored heatmap grid.
 * Handles API format: heatmapData = [{date, service, count, max_severity, P1, P2, P3}, ...]
 */
export default function ServiceUptimeHeatmap({ heatmapData = [], services = [], days = 30 }) {
  if (!heatmapData || heatmapData.length === 0 || !services || services.length === 0) {
    return (
      <div className="empty-state" style={{ padding: 24 }}>
        <div className="empty-state-icon">🗓️</div>
        <div className="empty-state-title">No uptime data</div>
        <div className="empty-state-text">Service uptime data will appear over time</div>
      </div>
    );
  }

  // Build a lookup: service -> date -> severity level
  const serviceMap = {};
  const allDates = [...new Set(heatmapData.map((d) => d.date))].sort();

  services.forEach((svc) => { serviceMap[svc] = {}; });

  heatmapData.forEach((item) => {
    if (serviceMap[item.service]) {
      const severity = item.P1 > 0 ? 3 : item.P2 > 0 ? 2 : item.P3 > 0 ? 1 : 0;
      serviceMap[item.service][item.date] = severity;
    }
  });

  const getColor = (severity) => {
    if (severity === 0) return '#dcfce7';
    if (severity === 1) return '#fef9c3';
    if (severity === 2) return '#fed7aa';
    return '#fecaca';
  };

  const serviceLabels = {
    'azure-front-door': 'Front Door',
    'azure-app-gateway': 'App Gateway',
    'azure-apim': 'API Mgmt',
    'azure-vm': 'Virtual Machine',
  };

  return (
    <div className="uptime-heatmap">
      {services.map((service) => (
        <div key={service} className="heatmap-row">
          <div className="heatmap-label">{serviceLabels[service] || service}</div>
          <div style={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            {allDates.map((date) => {
              const severity = serviceMap[service]?.[date] ?? 0;
              return (
                <div
                  key={date}
                  className="heatmap-cell"
                  style={{ background: getColor(severity) }}
                  title={`${serviceLabels[service] || service} — ${date}: ${severity === 0 ? 'No issues' : severity === 1 ? 'P3' : severity === 2 ? 'P2' : 'P1'}`}
                />
              );
            })}
          </div>
        </div>
      ))}
      <div style={{ display: 'flex', gap: 12, marginTop: 8, justifyContent: 'flex-end' }}>
        {[
          { label: 'No issues', color: '#dcfce7' },
          { label: 'P3', color: '#fef9c3' },
          { label: 'P2', color: '#fed7aa' },
          { label: 'P1', color: '#fecaca' },
        ].map((l) => (
          <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: '#64748b' }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: l.color }} />
            {l.label}
          </div>
        ))}
      </div>
    </div>
  );
}
