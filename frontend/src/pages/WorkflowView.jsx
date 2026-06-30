/**
 * WorkflowView Page — React Flow visualization of the 9-agent linear pipeline.
 * Features:
 *   - Live pipeline progress bar with step counter & timer
 *   - Animated node status transitions (idle → running → completed)
 *   - Real-time node output result cards
 *   - Pipeline summary modal on completion
 */

import { useCallback, useEffect, useState, useRef } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import useAppStore from '../store/useAppStore';
import { getWorkflowState, triggerPipeline } from '../services/api';
import NodeConfigModal from '../components/NodeConfigModal';

// --- 9-agent pipeline steps ---
const PIPELINE_STEPS = [
  'log_collector',
  'preprocessing_engine',
  'classification_agent',
  'rca_agent',
  'priority_agent',
  'context_agent',
  'resolution_agent',
  'orchestrator_agent',
  'notification_agent',
];

const STEP_LABELS = {
  log_collector: 'Collecting Logs',
  preprocessing_engine: 'Preprocessing',
  classification_agent: 'Classifying Incidents',
  rca_agent: 'Root Cause Analysis',
  priority_agent: 'Assigning Priority',
  context_agent: 'Looking Up Context',
  resolution_agent: 'Generating Resolutions',
  orchestrator_agent: 'Orchestrating',
  notification_agent: 'Sending Notifications',
};

// --- Pipeline Progress Banner ---
function PipelineProgressBanner() {
  const { isPipelineRunning, currentNode, nodeData } = useAppStore();
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef(null);
  const startRef = useRef(null);

  const completedSteps = PIPELINE_STEPS.filter(
    (id) => nodeData[id]?.completedAt
  ).length;
  const totalSteps = PIPELINE_STEPS.length;
  const progressPercent = isPipelineRunning
    ? Math.max(((completedSteps) / totalSteps) * 100, 5)
    : completedSteps > 0
    ? 100
    : 0;

  useEffect(() => {
    if (isPipelineRunning) {
      startRef.current = Date.now();
      setElapsed(0);
      timerRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPipelineRunning]);

  if (!isPipelineRunning && completedSteps === 0) return null;

  const formatTime = (s) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
  };

  return (
    <div className={`pipeline-banner ${isPipelineRunning ? 'running' : 'done'}`}>
      <div className="pipeline-banner-content">
        <div className="pipeline-banner-left">
          {isPipelineRunning ? (
            <>
              <span className="pipeline-banner-pulse" />
              <span className="pipeline-banner-label">Pipeline Running</span>
              <span className="pipeline-banner-step">
                {currentNode ? STEP_LABELS[currentNode] || currentNode : 'Starting...'}
              </span>
            </>
          ) : (
            <>
              <span className="pipeline-banner-check">✓</span>
              <span className="pipeline-banner-label">Pipeline Complete</span>
            </>
          )}
        </div>
        <div className="pipeline-banner-right">
          <span className="pipeline-banner-counter">
            {completedSteps}/{totalSteps} steps
          </span>
          <span className="pipeline-banner-timer">
            ⏱ {formatTime(elapsed)}
          </span>
        </div>
      </div>
      <div className="pipeline-banner-bar-track">
        <div
          className="pipeline-banner-bar-fill"
          style={{ width: `${progressPercent}%` }}
        />
      </div>
    </div>
  );
}

// --- Node Output Result Card ---
function NodeResultCard({ nodeId }) {
  const nodeData = useAppStore((s) => s.nodeData[nodeId]);
  if (!nodeData) return null;

  const hasOutput = nodeData.output && nodeData.output.description;
  const hasInput = nodeData.input && nodeData.input.description;
  const isRunning = !nodeData.completedAt && nodeData.startedAt;
  const isCompleted = !!nodeData.completedAt;

  if (!hasInput && !hasOutput && !isRunning) return null;

  return (
    <div className={`node-result-card ${isCompleted ? 'completed' : ''} ${isRunning ? 'running' : ''}`}>
      {isRunning && !isCompleted && (
        <div className="node-result-running">
          <span className="spinner" style={{ width: 12, height: 12, borderWidth: 2 }} />
          <span>{hasInput ? nodeData.input.description : 'Processing...'}</span>
        </div>
      )}
      {isCompleted && hasOutput && (
        <div className="node-result-output">
          <span className="node-result-icon">📤</span>
          <span className="node-result-text">{nodeData.output.description}</span>
          {nodeData.duration != null && (
            <span className="node-result-duration">{nodeData.duration}s</span>
          )}
        </div>
      )}
    </div>
  );
}

// --- Custom Node Component ---
function WorkflowNode({ data }) {
  const statusClass = data.status || 'idle';
  return (
    <div className={`workflow-node ${statusClass}`}>
      <Handle type="target" position={Position.Top} style={{ visibility: 'hidden' }} />
      <div className="workflow-node-header">
        <div
          className="workflow-node-icon"
          style={{ background: data.iconBg, color: data.iconColor }}
        >
          {data.icon}
        </div>
        <span className="workflow-node-title">{data.label}</span>
        {data.status === 'running' && (
          <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2, marginLeft: 'auto' }} />
        )}
        {data.status === 'completed' && (
          <span className="node-done-badge">✓</span>
        )}
      </div>
      <div className="workflow-node-subtitle">{data.subtitle}</div>
      <NodeResultCard nodeId={data.nodeId} />
      <Handle type="source" position={Position.Bottom} style={{ visibility: 'hidden' }} />
    </div>
  );
}

const nodeTypes = {
  workflowNode: WorkflowNode,
};

const initialNodes = [
  {
    id: 'start',
    type: 'workflowNode',
    position: { x: 350, y: 0 },
    data: { label: 'Start', subtitle: 'Pipeline entry point', icon: '⚡', iconBg: 'rgba(245,158,11,0.2)', iconColor: '#f59e0b', status: 'idle', nodeId: 'start' },
  },
  {
    id: 'log_collector',
    type: 'workflowNode',
    position: { x: 350, y: 110 },
    data: { label: 'Log Collector', subtitle: 'Agent 1: Azure Monitor → Raw Logs', icon: '📡', iconBg: 'rgba(16,185,129,0.2)', iconColor: '#10b981', status: 'idle', nodeId: 'log_collector' },
  },
  {
    id: 'preprocessing_engine',
    type: 'workflowNode',
    position: { x: 350, y: 220 },
    data: { label: 'Preprocessing Engine', subtitle: 'Agent 2: Clean, dedup, normalize', icon: '⚙️', iconBg: 'rgba(99,102,241,0.2)', iconColor: '#6366f1', status: 'idle', nodeId: 'preprocessing_engine' },
  },
  {
    id: 'classification_agent',
    type: 'workflowNode',
    position: { x: 350, y: 330 },
    data: { label: 'Classification Agent', subtitle: 'Agent 3: Gemini incident detection', icon: '🔍', iconBg: 'rgba(244,63,94,0.2)', iconColor: '#f43f5e', status: 'idle', nodeId: 'classification_agent' },
  },
  {
    id: 'rca_agent',
    type: 'workflowNode',
    position: { x: 350, y: 440 },
    data: { label: 'RCA Agent', subtitle: 'Agent 3.5: Root Cause Analysis', icon: '🎯', iconBg: 'rgba(167,139,250,0.2)', iconColor: '#a78bfa', status: 'idle', nodeId: 'rca_agent' },
  },
  {
    id: 'priority_agent',
    type: 'workflowNode',
    position: { x: 350, y: 550 },
    data: { label: 'Priority Agent', subtitle: 'Agent 4: Assign P1 / P2 / P3', icon: '⚖️', iconBg: 'rgba(245,158,11,0.2)', iconColor: '#f59e0b', status: 'idle', nodeId: 'priority_agent' },
  },
  {
    id: 'context_agent',
    type: 'workflowNode',
    position: { x: 350, y: 660 },
    data: { label: 'Context Agent', subtitle: 'Agent 5: Historical incident lookup', icon: '📚', iconBg: 'rgba(139,92,246,0.2)', iconColor: '#8b5cf6', status: 'idle', nodeId: 'context_agent' },
  },
  {
    id: 'resolution_agent',
    type: 'workflowNode',
    position: { x: 350, y: 770 },
    data: { label: 'Resolution Agent', subtitle: 'Agent 6: Auto fix + runbook', icon: '💡', iconBg: 'rgba(59,130,246,0.2)', iconColor: '#3b82f6', status: 'idle', nodeId: 'resolution_agent' },
  },
  {
    id: 'orchestrator_agent',
    type: 'workflowNode',
    position: { x: 350, y: 880 },
    data: { label: 'Orchestrator Agent', subtitle: 'Agent 7: Coordinate & summarize', icon: '🎯', iconBg: 'rgba(236,72,153,0.2)', iconColor: '#ec4899', status: 'idle', nodeId: 'orchestrator_agent' },
  },
  {
    id: 'notification_agent',
    type: 'workflowNode',
    position: { x: 350, y: 990 },
    data: { label: 'Notification Agent', subtitle: 'Agent 8: Email alerts', icon: '📧', iconBg: 'rgba(239,68,68,0.2)', iconColor: '#ef4444', status: 'idle', nodeId: 'notification_agent' },
  },
  {
    id: 'end',
    type: 'workflowNode',
    position: { x: 350, y: 1100 },
    data: { label: 'End', subtitle: 'Pipeline complete', icon: '🏁', iconBg: 'rgba(100,116,139,0.2)', iconColor: '#64748b', status: 'idle', nodeId: 'end' },
  },
];

const initialEdges = [
  { id: 'e-start-lc', source: 'start', target: 'log_collector', animated: true, style: { stroke: 'var(--accent-emerald)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--accent-emerald)' } },
  { id: 'e-lc-pp', source: 'log_collector', target: 'preprocessing_engine', animated: true, style: { stroke: 'var(--accent-indigo)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--accent-indigo)' } },
  { id: 'e-pp-ca', source: 'preprocessing_engine', target: 'classification_agent', animated: true, style: { stroke: '#f43f5e' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#f43f5e' } },
  { id: 'e-ca-rca', source: 'classification_agent', target: 'rca_agent', animated: true, style: { stroke: '#a78bfa' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#a78bfa' } },
  { id: 'e-rca-pa', source: 'rca_agent', target: 'priority_agent', animated: true, style: { stroke: '#f59e0b' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#f59e0b' } },
  { id: 'e-pa-ctx', source: 'priority_agent', target: 'context_agent', animated: true, style: { stroke: '#8b5cf6' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' } },
  { id: 'e-ctx-res', source: 'context_agent', target: 'resolution_agent', animated: true, style: { stroke: '#3b82f6' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6' } },
  { id: 'e-res-orch', source: 'resolution_agent', target: 'orchestrator_agent', animated: true, style: { stroke: '#ec4899' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#ec4899' } },
  { id: 'e-orch-notif', source: 'orchestrator_agent', target: 'notification_agent', animated: true, style: { stroke: '#ef4444' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#ef4444' } },
  { id: 'e-notif-end', source: 'notification_agent', target: 'end', style: { stroke: 'var(--border-default)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--text-muted)' } },
];

const NODE_META = {
  log_collector: { label: 'Log Collector', icon: '📡', color: '#10b981' },
  preprocessing_engine: { label: 'Preprocessing Engine', icon: '⚙️', color: '#6366f1' },
  classification_agent: { label: 'Classification Agent', icon: '🔍', color: '#f43f5e' },
  rca_agent: { label: 'RCA Agent', icon: '🎯', color: '#a78bfa' },
  priority_agent: { label: 'Priority Agent', icon: '⚖️', color: '#f59e0b' },
  context_agent: { label: 'Context Agent', icon: '📚', color: '#8b5cf6' },
  resolution_agent: { label: 'Resolution Agent', icon: '💡', color: '#3b82f6' },
  orchestrator_agent: { label: 'Orchestrator Agent', icon: '🎯', color: '#ec4899' },
  notification_agent: { label: 'Notification Agent', icon: '📧', color: '#ef4444' },
};

// --- Pipeline Summary Modal ---
function PipelineSummaryModal() {
  const pipelineSummary = useAppStore((s) => s.pipelineSummary);
  const showSummaryModal = useAppStore((s) => s.showSummaryModal);
  const setShowSummaryModal = useAppStore((s) => s.setShowSummaryModal);
  const nodeData = useAppStore((s) => s.nodeData);

  if (!showSummaryModal || !pipelineSummary) return null;

  const s = pipelineSummary;
  const totalEmails = s.emails_to_send || 0;

  const nodeTimeline = Object.entries(nodeData)
    .filter(([id]) => NODE_META[id])
    .sort((a, b) => (a[1].startedAt || 0) - (b[1].startedAt || 0))
    .map(([id, data]) => ({
      id, meta: NODE_META[id],
      input: data.input?.description || '—',
      output: data.output?.description || '—',
      duration: data.duration,
    }));

  return (
    <div className="psm-overlay" onClick={() => setShowSummaryModal(false)}>
      <div className="psm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="psm-header">
          <div className="psm-header-info">
            <div className="psm-header-row">
              <span className="psm-status-badge">✓ Completed</span>
              <span className="psm-duration-badge">⏱ {s.total_duration || s.duration}s</span>
            </div>
            <h2 className="psm-title">Pipeline Run Summary</h2>
            <p className="psm-run-id">Run ID: {s.runId || '—'}</p>
          </div>
          <button className="psm-close" onClick={() => setShowSummaryModal(false)}>✕</button>
        </div>

        <div className="psm-body">
          <div className="psm-stats-grid">
            <div className="psm-stat"><div className="psm-stat-value">{s.total_collected || 0}</div><div className="psm-stat-label">Logs Collected</div></div>
            <div className="psm-stat"><div className="psm-stat-value">{s.total_preprocessed || 0}</div><div className="psm-stat-label">Preprocessed</div></div>
            <div className="psm-stat"><div className="psm-stat-value">{s.issues_found || 0}</div><div className="psm-stat-label">Issues Found</div></div>
            <div className="psm-stat"><div className="psm-stat-value">{s.total_incidents || 0}</div><div className="psm-stat-label">Incidents</div></div>
            <div className="psm-stat"><div className="psm-stat-value">{s.resolutions_generated || 0}</div><div className="psm-stat-label">Resolutions</div></div>
            <div className="psm-stat"><div className="psm-stat-value">{totalEmails}</div><div className="psm-stat-label">Emails Sent</div></div>
          </div>

          <div className="psm-section">
            <h3 className="psm-section-title">Priority Breakdown</h3>
            <div className="psm-priority-row">
              <div className="psm-priority-card psm-priority-high">
                <span className="psm-priority-label">🔴 P1</span>
                <span className="psm-priority-count">{s.p1_count || 0}</span>
              </div>
              <div className="psm-priority-card psm-priority-medium">
                <span className="psm-priority-label">🟡 P2</span>
                <span className="psm-priority-count">{s.p2_count || 0}</span>
              </div>
              <div className="psm-priority-card psm-priority-low">
                <span className="psm-priority-label">🟢 P3</span>
                <span className="psm-priority-count">{s.p3_count || 0}</span>
              </div>
            </div>
          </div>

          {nodeTimeline.length > 0 && (
            <div className="psm-section">
              <h3 className="psm-section-title">Agent Execution Timeline</h3>
              <div className="psm-timeline">
                {nodeTimeline.map((node, i) => (
                  <div className="psm-timeline-item" key={node.id}>
                    <div className="psm-timeline-connector">
                      <div className="psm-timeline-dot" style={{ background: node.meta.color }}></div>
                      {i < nodeTimeline.length - 1 && <div className="psm-timeline-line"></div>}
                    </div>
                    <div className="psm-timeline-content">
                      <div className="psm-timeline-header">
                        <span className="psm-timeline-icon">{node.meta.icon}</span>
                        <span className="psm-timeline-name">{node.meta.label}</span>
                        {node.duration != null && (
                          <span className="psm-timeline-duration">{node.duration}s</span>
                        )}
                      </div>
                      <div className="psm-timeline-io">
                        <div className="psm-timeline-io-row">
                          <span className="psm-io-badge psm-io-in">IN</span>
                          <span>{node.input}</span>
                        </div>
                        <div className="psm-timeline-io-row">
                          <span className="psm-io-badge psm-io-out">OUT</span>
                          <span>{node.output}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="psm-footer">
          <button className="btn btn-secondary btn-sm" onClick={() => setShowSummaryModal(false)}>
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}


export default function WorkflowView() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const { currentNode, isPipelineRunning, nodeData } = useAppStore();

  const [selectedNode, setSelectedNode] = useState(null);

  // Update node statuses
  useEffect(() => {
    const nodeOrder = ['start', ...PIPELINE_STEPS, 'end'];
    const currentIdx = nodeOrder.indexOf(currentNode);

    setNodes((nds) =>
      nds.map((node) => {
        const idx = nodeOrder.indexOf(node.id);
        let status = 'idle';

        if (isPipelineRunning) {
          if (nodeData[node.id]?.completedAt) {
            status = 'completed';
          } else if (idx === currentIdx) {
            status = 'running';
          } else if (idx < currentIdx) {
            status = 'completed';
          }
        } else if (nodeData[node.id]?.completedAt) {
          status = 'completed';
        }

        return { ...node, data: { ...node.data, status } };
      })
    );

    setEdges((eds) =>
      eds.map((edge) => {
        const nodeOrder2 = ['start', ...PIPELINE_STEPS, 'end'];
        const sourceIdx = nodeOrder2.indexOf(edge.source);
        const targetIdx = nodeOrder2.indexOf(edge.target);
        const isCompleted = sourceIdx >= 0 && targetIdx >= 0 &&
          (nodeData[edge.source]?.completedAt || sourceIdx < currentIdx) &&
          (nodeData[edge.target]?.completedAt || targetIdx <= currentIdx);
        const isCurrent = isPipelineRunning && targetIdx === currentIdx;
        const isPast = sourceIdx >= 0 && sourceIdx < currentIdx;

        // Determine edge color: green for completed, original for current, dim for pending
        let strokeColor = edge.style?.stroke || 'var(--border-default)';
        let strokeWidth = 1.5;
        let opacity = 0.3;
        let animated = true;

        if (isPipelineRunning) {
          if (isCompleted || isPast) {
            strokeColor = '#10b981'; // Green for completed
            strokeWidth = 3;
            opacity = 1;
            animated = false; // Solid line for completed
          } else if (isCurrent) {
            strokeColor = '#10b981'; // Green pulse for current
            strokeWidth = 3;
            opacity = 1;
            animated = true; // Animated for active
          } else {
            opacity = 0.2;
            strokeWidth = 1.5;
          }
        } else if (nodeData[edge.source]?.completedAt && nodeData[edge.target]?.completedAt) {
          // Pipeline finished — all completed edges stay green
          strokeColor = '#10b981';
          strokeWidth = 2.5;
          opacity = 0.9;
          animated = false;
        } else {
          opacity = 0.8;
        }

        return {
          ...edge,
          animated,
          style: {
            stroke: strokeColor,
            strokeWidth,
            opacity,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: strokeColor,
          },
        };
      })
    );
  }, [currentNode, isPipelineRunning, nodeData, setNodes, setEdges]);

  // Polling
  useEffect(() => {
    const pollState = async () => {
      try {
        const res = await getWorkflowState();
        const state = res.data;
        if (state.nodes) {
          setNodes((nds) =>
            nds.map((node) => {
              const stateNode = state.nodes.find((n) => n.node_id === node.id);
              return stateNode
                ? { ...node, data: { ...node.data, status: stateNode.status } }
                : node;
            })
          );
        }
      } catch (e) { }
    };

    pollState();
    const interval = setInterval(pollState, 5000);
    return () => clearInterval(interval);
  }, [setNodes]);

  const onNodeClick = useCallback((_event, node) => {
    setSelectedNode({ id: node.id, name: node.data.label });
  }, []);

  return (
    <div className="page-content" style={{ padding: 0, paddingTop: 'var(--header-height)' }}>
      <PipelineProgressBanner />

      <div style={{ height: 'calc(100vh - var(--header-height))', width: '100%' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          proOptions={{ hideAttribution: true }}
          style={{ background: 'var(--bg-primary)' }}
        >
          <Controls
            style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-md)' }}
          />
          <Background color="rgba(255,255,255,0.03)" gap={20} size={1} />
        </ReactFlow>
      </div>

      {selectedNode && (
        <NodeConfigModal
          nodeId={selectedNode.id}
          nodeName={selectedNode.name}
          onClose={() => setSelectedNode(null)}
        />
      )}

      <PipelineSummaryModal />
    </div>
  );
}
