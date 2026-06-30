/**
 * InfraFlowDiagram — Animated service topology showing real-time request flow.
 * 
 * Visual: User → Front Door → WAF → App Gateway → APIM → App Service → (Blob / SQL)
 * Each node is colored green/red based on live HTTP health checks.
 * Animated dots ("packets") flow along the connections.
 */

import { useEffect, useRef, useState } from 'react';

/* ─── Flow definition: order of services in the request path ─── */
const FLOW_NODES = [
  { id: 'user',              label: 'User Request',       icon: '👤', row: 0, col: 0, type: 'source' },
  { id: 'azure-front-door',  label: 'Front Door',         icon: '🌐', row: 0, col: 1, type: 'service' },
  { id: 'azure-waf',         label: 'WAF',                icon: '🛡️', row: 0, col: 2, type: 'service' },
  { id: 'azure-app-gateway', label: 'App Gateway',        icon: '🔀', row: 0, col: 3, type: 'service' },
  { id: 'azure-apim',        label: 'APIM',               icon: '⚙️', row: 0, col: 4, type: 'service' },
  { id: 'azure-app-service', label: 'App Service',        icon: '🖥️', row: 0, col: 5, type: 'service' },
  { id: 'azure-blob-storage',label: 'Blob Storage',       icon: '📦', row: 1, col: 5, type: 'storage' },
  { id: 'azure-log-analytics',label:'Log Analytics',      icon: '📊', row: 1, col: 3, type: 'platform' },
  { id: 'cloudguard-backend',label: 'CloudGuard API',     icon: '💻', row: 1, col: 1, type: 'platform' },
];

/* ─── Connections: from → to ─── */
const FLOW_EDGES = [
  { from: 'user',              to: 'azure-front-door' },
  { from: 'azure-front-door',  to: 'azure-waf' },
  { from: 'azure-waf',         to: 'azure-app-gateway' },
  { from: 'azure-app-gateway', to: 'azure-apim' },
  { from: 'azure-apim',        to: 'azure-app-service' },
  { from: 'azure-app-service', to: 'azure-blob-storage' },
  { from: 'azure-app-service', to: 'azure-log-analytics' },
  { from: 'azure-log-analytics', to: 'cloudguard-backend' },
];

/* ─── Status helpers ─── */
function getNodeStatus(nodeId, services) {
  if (nodeId === 'user') return { healthy: true, status_code: null, response_time_ms: 0 };
  const svc = services.find((s) => s.id === nodeId);
  if (!svc) return { healthy: null, status_code: null, response_time_ms: 0 };
  return svc;
}

function statusColor(healthy) {
  if (healthy === true) return '#10b981';
  if (healthy === false) return '#ef4444';
  return '#94a3b8';
}

function statusGlow(healthy) {
  if (healthy === true) return '0 0 16px rgba(16,185,129,0.35)';
  if (healthy === false) return '0 0 16px rgba(239,68,68,0.4)';
  return '0 0 8px rgba(148,163,184,0.2)';
}

function statusBg(healthy) {
  if (healthy === true) return '#f0fdf4';
  if (healthy === false) return '#fef2f2';
  return '#f8fafc';
}

function statusBorder(healthy) {
  if (healthy === true) return '#bbf7d0';
  if (healthy === false) return '#fecaca';
  return '#e2e8f0';
}

/* ═══════════════════════════════
   COMPONENT
   ═══════════════════════════════ */
export default function InfraFlowDiagram({ services = [] }) {
  const containerRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [tick, setTick] = useState(0);

  // Animate packets
  useEffect(() => {
    const interval = setInterval(() => setTick((t) => t + 1), 50);
    return () => clearInterval(interval);
  }, []);

  // Measure container
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Layout calculations
  const W = dimensions.width || 900;
  const H = 340;

  // Columns: distribute horizontally
  const colCount = 6; // 0..5
  const rowCount = 2;  // 0..1
  const padX = 70;
  const padY = 50;
  const colW = (W - padX * 2) / (colCount - 1);
  const rowH = (H - padY * 2) / (rowCount || 1);

  const getPos = (node) => ({
    x: padX + node.col * colW,
    y: padY + node.row * rowH,
  });

  const nodeSize = 64;

  return (
    <div ref={containerRef} style={{ width: '100%', minHeight: H, position: 'relative' }}>
      <svg width={W} height={H} style={{ position: 'absolute', top: 0, left: 0 }}>
        <defs>
          {/* Animated gradient for healthy connections */}
          <linearGradient id="flowGradientGreen" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
            <stop offset="50%" stopColor="#10b981" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#10b981" stopOpacity="0.3" />
          </linearGradient>
          <linearGradient id="flowGradientRed" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#ef4444" stopOpacity="0.3" />
            <stop offset="50%" stopColor="#ef4444" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#ef4444" stopOpacity="0.3" />
          </linearGradient>

          {/* Glow filter */}
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* ─── Connection lines ─── */}
        {FLOW_EDGES.map((edge) => {
          const fromNode = FLOW_NODES.find((n) => n.id === edge.from);
          const toNode = FLOW_NODES.find((n) => n.id === edge.to);
          if (!fromNode || !toNode) return null;

          const fromPos = getPos(fromNode);
          const toPos = getPos(toNode);
          const fromStatus = getNodeStatus(edge.from, services);
          const toStatus = getNodeStatus(edge.to, services);

          // Edge is healthy only if both ends are healthy
          const edgeHealthy = fromStatus.healthy !== false && toStatus.healthy !== false;
          const edgeColor = edgeHealthy ? '#10b981' : '#ef4444';
          const edgeOpacity = edgeHealthy ? 0.25 : 0.35;

          // Calculate control points for curved lines (for vertical connections)
          const dx = toPos.x - fromPos.x;
          const dy = toPos.y - fromPos.y;
          const isVertical = Math.abs(dy) > Math.abs(dx) * 0.5;

          let pathD;
          if (isVertical) {
            const midY = (fromPos.y + toPos.y) / 2;
            pathD = `M ${fromPos.x} ${fromPos.y} C ${fromPos.x} ${midY}, ${toPos.x} ${midY}, ${toPos.x} ${toPos.y}`;
          } else {
            const midX = (fromPos.x + toPos.x) / 2;
            pathD = `M ${fromPos.x} ${fromPos.y} C ${midX} ${fromPos.y}, ${midX} ${toPos.y}, ${toPos.x} ${toPos.y}`;
          }

          // Calculate packet position along the path
          const packetPhase = ((tick * 2 + FLOW_EDGES.indexOf(edge) * 30) % 200) / 200;
          const packetX = fromPos.x + (toPos.x - fromPos.x) * packetPhase;
          const packetY = fromPos.y + (toPos.y - fromPos.y) * packetPhase;

          return (
            <g key={`${edge.from}-${edge.to}`}>
              {/* Background line */}
              <path
                d={pathD}
                fill="none"
                stroke={edgeColor}
                strokeWidth={2.5}
                strokeOpacity={edgeOpacity}
                strokeDasharray={edgeHealthy ? 'none' : '6 4'}
              />

              {/* Animated packet dot */}
              {edgeHealthy && (
                <circle
                  cx={packetX}
                  cy={packetY}
                  r={4}
                  fill={edgeColor}
                  opacity={0.9}
                  filter="url(#glow)"
                />
              )}

              {/* Second packet (offset) */}
              {edgeHealthy && (() => {
                const p2 = ((tick * 2 + FLOW_EDGES.indexOf(edge) * 30 + 100) % 200) / 200;
                return (
                  <circle
                    cx={fromPos.x + (toPos.x - fromPos.x) * p2}
                    cy={fromPos.y + (toPos.y - fromPos.y) * p2}
                    r={3}
                    fill={edgeColor}
                    opacity={0.6}
                  />
                );
              })()}

              {/* Pulsing X for broken connections */}
              {!edgeHealthy && (
                <g transform={`translate(${(fromPos.x + toPos.x) / 2}, ${(fromPos.y + toPos.y) / 2})`}>
                  <circle r={10} fill="#fef2f2" stroke="#ef4444" strokeWidth={1.5} />
                  <text textAnchor="middle" dominantBaseline="central" fill="#ef4444" fontSize={12} fontWeight={700}>✕</text>
                </g>
              )}

              {/* Arrow at endpoint */}
              <circle cx={toPos.x} cy={toPos.y} r={0} fill="transparent" />
            </g>
          );
        })}
      </svg>

      {/* ─── Service Nodes (HTML overlays for rich content) ─── */}
      {FLOW_NODES.map((node) => {
        const pos = getPos(node);
        const status = getNodeStatus(node.id, services);
        const color = statusColor(status.healthy);
        const isUser = node.id === 'user';

        return (
          <div
            key={node.id}
            className="flow-node"
            style={{
              position: 'absolute',
              left: pos.x - nodeSize / 2,
              top: pos.y - nodeSize / 2,
              width: nodeSize,
              textAlign: 'center',
              zIndex: 10,
            }}
          >
            {/* Node circle */}
            <div style={{
              width: nodeSize,
              height: nodeSize,
              borderRadius: '50%',
              background: isUser ? '#eff6ff' : statusBg(status.healthy),
              border: `2.5px solid ${isUser ? '#3b82f6' : statusBorder(status.healthy)}`,
              boxShadow: statusGlow(status.healthy),
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 24,
              transition: 'all 0.5s ease',
              cursor: 'default',
              position: 'relative',
            }}>
              {node.icon}

              {/* Pulsing ring for active services */}
              {status.healthy === true && !isUser && (
                <div style={{
                  position: 'absolute', inset: -4, borderRadius: '50%',
                  border: `2px solid ${color}`,
                  opacity: 0.3,
                  animation: 'pulse-ring 2s ease infinite',
                }} />
              )}

              {/* Red pulse for down services */}
              {status.healthy === false && (
                <div style={{
                  position: 'absolute', inset: -4, borderRadius: '50%',
                  border: '2px solid #ef4444',
                  animation: 'pulse-ring 1s ease infinite',
                }} />
              )}
            </div>

            {/* Label */}
            <div style={{
              marginTop: 6,
              fontSize: 11,
              fontWeight: 700,
              color: '#0f172a',
              lineHeight: 1.2,
              whiteSpace: 'nowrap',
            }}>
              {node.label}
            </div>

            {/* Status badge */}
            {!isUser && status.status_code !== null && (
              <div style={{
                marginTop: 2,
                fontSize: 9,
                fontWeight: 800,
                color: color,
                fontFamily: 'monospace',
                letterSpacing: '0.3px',
              }}>
                {status.incident_count > 0
                  ? `⚠️ ${status.incident_count} incident${status.incident_count > 1 ? 's' : ''}`
                  : status.status_code > 0 ? `HTTP ${status.status_code}` : 'N/A'
                }
                {!status.incident_count && status.response_time_ms > 0 && ` · ${status.response_time_ms}ms`}
              </div>
            )}

            {/* Online/Down/Incident text */}
            {!isUser && (
              <div style={{
                fontSize: 9,
                fontWeight: 700,
                color: color,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                marginTop: 1,
              }}>
                {status.incident_count > 0
                  ? `🔴 ${status.incident_severity || 'AFFECTED'}`
                  : status.healthy === true ? '● ONLINE' : status.healthy === false ? '● DOWN' : '○ N/A'
                }
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
