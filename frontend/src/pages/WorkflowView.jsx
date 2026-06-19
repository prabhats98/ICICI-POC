/**
 * WorkflowView Page - React Flow visualization of the agent pipeline.
 * Includes deep code analysis nodes, Solution Architect naming, node config modal,
 * real-time I/O data panels on nodes, and a pipeline summary modal.
 */

import { useCallback, useEffect, useState } from 'react';
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

// --- Node I/O Panel (rendered inside each node) ---
function NodeIOPanel({ nodeId }) {
  const nodeData = useAppStore((s) => s.nodeData[nodeId]);
  if (!nodeData) return null;

  const hasInput = nodeData.input && nodeData.input.description;
  const hasOutput = nodeData.output && nodeData.output.description;

  if (!hasInput && !hasOutput) return null;

  return (
    <div className="node-io-panel">
      {hasInput && (
        <div className="node-io-item node-io-input">
          <span className="node-io-icon">📥</span>
          <span className="node-io-text">{nodeData.input.description}</span>
        </div>
      )}
      {hasOutput && (
        <div className="node-io-item node-io-output">
          <span className="node-io-icon">📤</span>
          <span className="node-io-text">{nodeData.output.description}</span>
        </div>
      )}
      {nodeData.duration != null && (
        <div className="node-io-duration">
          ⏱ {nodeData.duration}s
        </div>
      )}
    </div>
  );
}

// Custom node component
function WorkflowNode({ data }) {
  const statusClass = data.status || 'idle';
  const extraClass = data.extraClass || '';
  return (
    <div className={`workflow-node ${statusClass} ${extraClass}`}>
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
          <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2, marginLeft: 'auto' }}></span>
        )}
        {data.status === 'completed' && (
          <span style={{ marginLeft: 'auto', color: 'var(--accent-emerald)', fontSize: 14 }}>✓</span>
        )}
      </div>
      <div className="workflow-node-subtitle">{data.subtitle}</div>
      <NodeIOPanel nodeId={data.nodeId} />
      <Handle type="source" position={Position.Bottom} style={{ visibility: 'hidden' }} />
    </div>
  );
}

// Decision node (diamond shape via CSS)
function DecisionNode({ data }) {
  const statusClass = data.status || 'idle';
  return (
    <div className={`workflow-node ${statusClass}`} style={{
      transform: 'rotate(0deg)',
      borderColor: 'var(--accent-amber)',
      borderStyle: 'dashed',
      borderWidth: 2,
    }}>
      <Handle type="target" position={Position.Top} style={{ visibility: 'hidden' }} />
      <div className="workflow-node-header">
        <div className="workflow-node-icon" style={{ background: 'rgba(245,158,11,0.2)', color: '#f59e0b' }}>
          ⚖️
        </div>
        <span className="workflow-node-title">{data.label}</span>
        {data.status === 'running' && (
          <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2, marginLeft: 'auto' }}></span>
        )}
      </div>
      <div className="workflow-node-subtitle">{data.subtitle}</div>
      <NodeIOPanel nodeId={data.nodeId} />
      <Handle type="source" position={Position.Bottom} style={{ visibility: 'hidden' }} />
    </div>
  );
}

const nodeTypes = {
  workflowNode: WorkflowNode,
  decisionNode: DecisionNode,
};

const initialNodes = [
  {
    id: 'start',
    type: 'workflowNode',
    position: { x: 350, y: 0 },
    data: {
      label: 'Start',
      subtitle: 'Workflow entry point',
      icon: '⚡',
      iconBg: 'rgba(245,158,11,0.2)',
      iconColor: '#f59e0b',
      status: 'idle',
      nodeId: 'start',
    },
  },
  {
    id: 'log_extractor',
    type: 'workflowNode',
    position: { x: 350, y: 120 },
    data: {
      label: 'Extract Monitoring Data',
      subtitle: 'Agent 1: Scheduled DB extraction',
      icon: '📊',
      iconBg: 'rgba(16,185,129,0.2)',
      iconColor: '#10b981',
      status: 'idle',
      nodeId: 'log_extractor',
    },
  },
  {
    id: 'anomaly_detector',
    type: 'workflowNode',
    position: { x: 350, y: 240 },
    data: {
      label: 'Detect Spikes & Anomalies',
      subtitle: 'Agent 2: Gemini-powered analysis',
      icon: '🔍',
      iconBg: 'rgba(244,63,94,0.2)',
      iconColor: '#f43f5e',
      status: 'idle',
      nodeId: 'anomaly_detector',
    },
  },
  {
    id: 'priority_classifier',
    type: 'decisionNode',
    position: { x: 350, y: 360 },
    data: {
      label: 'Classify & Prioritize',
      subtitle: 'Agent 3: HIGH / MEDIUM / LOW',
      status: 'idle',
      nodeId: 'priority_classifier',
    },
  },
  // --- Deep Code Analysis Nodes (Purple/Violet) ---
  {
    id: 'deep_code_analyzer_high',
    type: 'workflowNode',
    position: { x: 80, y: 500 },
    data: {
      label: 'Critical Root Cause Analysis',
      subtitle: 'Agent 5: Deep code forensics',
      icon: '🔬',
      iconBg: 'rgba(139,92,246,0.2)',
      iconColor: '#8b5cf6',
      status: 'idle',
      extraClass: 'deep-analysis',
      nodeId: 'deep_code_analyzer_high',
    },
  },
  {
    id: 'deep_code_analyzer_medium',
    type: 'workflowNode',
    position: { x: 350, y: 500 },
    data: {
      label: 'Impact & Code Analysis',
      subtitle: 'Agent 5: Code-level assessment',
      icon: '🧬',
      iconBg: 'rgba(139,92,246,0.2)',
      iconColor: '#8b5cf6',
      status: 'idle',
      extraClass: 'deep-analysis',
      nodeId: 'deep_code_analyzer_medium',
    },
  },
  {
    id: 'deep_code_analyzer_low',
    type: 'workflowNode',
    position: { x: 620, y: 500 },
    data: {
      label: 'Pattern & Trend Analysis',
      subtitle: 'Agent 5: Proactive insights',
      icon: '📊',
      iconBg: 'rgba(139,92,246,0.2)',
      iconColor: '#8b5cf6',
      status: 'idle',
      extraClass: 'deep-analysis',
      nodeId: 'deep_code_analyzer_low',
    },
  },
  // --- Solution Architect + Email Nodes ---
  {
    id: 'high_priority_handler',
    type: 'workflowNode',
    position: { x: 80, y: 640 },
    data: {
      label: 'Emergency Response + Email',
      subtitle: 'Agent 4a: Urgent resolution',
      icon: '🚨',
      iconBg: 'rgba(239,68,68,0.2)',
      iconColor: '#ef4444',
      status: 'idle',
      nodeId: 'high_priority_handler',
    },
  },
  {
    id: 'medium_priority_handler',
    type: 'workflowNode',
    position: { x: 350, y: 640 },
    data: {
      label: 'Solution Architect + Email',
      subtitle: 'Agent 4b: Detailed fix report',
      icon: '🏗️',
      iconBg: 'rgba(59,130,246,0.2)',
      iconColor: '#3b82f6',
      status: 'idle',
      nodeId: 'medium_priority_handler',
    },
  },
  {
    id: 'low_priority_handler',
    type: 'workflowNode',
    position: { x: 620, y: 640 },
    data: {
      label: 'Advisory Report + Email',
      subtitle: 'Agent 4c: Informational digest',
      icon: '📋',
      iconBg: 'rgba(100,116,139,0.2)',
      iconColor: '#94a3b8',
      status: 'idle',
      nodeId: 'low_priority_handler',
    },
  },
  // --- End Nodes ---
  {
    id: 'end_high',
    type: 'workflowNode',
    position: { x: 80, y: 780 },
    data: {
      label: 'End',
      subtitle: 'High priority path complete',
      icon: '🏁',
      iconBg: 'rgba(239,68,68,0.2)',
      iconColor: '#ef4444',
      status: 'idle',
      nodeId: 'end_high',
    },
  },
  {
    id: 'end_medium',
    type: 'workflowNode',
    position: { x: 350, y: 780 },
    data: {
      label: 'End',
      subtitle: 'Medium priority path complete',
      icon: '🏁',
      iconBg: 'rgba(239,68,68,0.2)',
      iconColor: '#ef4444',
      status: 'idle',
      nodeId: 'end_medium',
    },
  },
  {
    id: 'end_low',
    type: 'workflowNode',
    position: { x: 620, y: 780 },
    data: {
      label: 'End',
      subtitle: 'Low priority path complete',
      icon: '🏁',
      iconBg: 'rgba(239,68,68,0.2)',
      iconColor: '#ef4444',
      status: 'idle',
      nodeId: 'end_low',
    },
  },
];

const initialEdges = [
  // Start → Extract → Detect → Classify
  { id: 'e-start-extract', source: 'start', target: 'log_extractor', animated: true, style: { stroke: 'var(--accent-indigo)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--accent-indigo)' } },
  { id: 'e-extract-detect', source: 'log_extractor', target: 'anomaly_detector', animated: true, style: { stroke: 'var(--accent-emerald)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--accent-emerald)' } },
  { id: 'e-detect-classify', source: 'anomaly_detector', target: 'priority_classifier', animated: true, style: { stroke: 'var(--accent-amber)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--accent-amber)' } },

  // Classify → Deep Code Analysis
  { id: 'e-classify-dca-high', source: 'priority_classifier', target: 'deep_code_analyzer_high', animated: true, label: 'HIGH', style: { stroke: '#ef4444' }, labelStyle: { fill: '#ef4444', fontWeight: 700, fontSize: 11 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#ef4444' } },
  { id: 'e-classify-dca-medium', source: 'priority_classifier', target: 'deep_code_analyzer_medium', animated: true, label: 'MEDIUM', style: { stroke: '#f59e0b' }, labelStyle: { fill: '#f59e0b', fontWeight: 700, fontSize: 11 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#f59e0b' } },
  { id: 'e-classify-dca-low', source: 'priority_classifier', target: 'deep_code_analyzer_low', animated: true, label: 'LOW', style: { stroke: '#10b981' }, labelStyle: { fill: '#10b981', fontWeight: 700, fontSize: 11 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#10b981' } },

  // Deep Code Analysis → Solution Architect + Email
  { id: 'e-dca-high-handler', source: 'deep_code_analyzer_high', target: 'high_priority_handler', animated: true, style: { stroke: '#8b5cf6' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' } },
  { id: 'e-dca-medium-handler', source: 'deep_code_analyzer_medium', target: 'medium_priority_handler', animated: true, style: { stroke: '#8b5cf6' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' } },
  { id: 'e-dca-low-handler', source: 'deep_code_analyzer_low', target: 'low_priority_handler', animated: true, style: { stroke: '#8b5cf6' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' } },

  // Solution Architect → End
  { id: 'e-high-end', source: 'high_priority_handler', target: 'end_high', style: { stroke: 'var(--border-default)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--text-muted)' } },
  { id: 'e-medium-end', source: 'medium_priority_handler', target: 'end_medium', style: { stroke: 'var(--border-default)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--text-muted)' } },
  { id: 'e-low-end', source: 'low_priority_handler', target: 'end_low', style: { stroke: 'var(--border-default)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--text-muted)' } },
];

// --- Node metadata for summary display ---
const NODE_META = {
  log_extractor: { label: 'Extract Monitoring Data', icon: '📊', color: '#10b981' },
  anomaly_detector: { label: 'Detect Spikes & Anomalies', icon: '🔍', color: '#f43f5e' },
  priority_classifier: { label: 'Classify & Prioritize', icon: '⚖️', color: '#f59e0b' },
  deep_code_analyzer_high: { label: 'Critical Root Cause Analysis', icon: '🔬', color: '#8b5cf6' },
  deep_code_analyzer_medium: { label: 'Impact & Code Analysis', icon: '🧬', color: '#8b5cf6' },
  deep_code_analyzer_low: { label: 'Pattern & Trend Analysis', icon: '📊', color: '#8b5cf6' },
  high_priority_handler: { label: 'Emergency Response', icon: '🚨', color: '#ef4444' },
  medium_priority_handler: { label: 'Solution Architect', icon: '🏗️', color: '#3b82f6' },
  low_priority_handler: { label: 'Advisory Report', icon: '📋', color: '#94a3b8' },
};

// --- Pipeline Summary Modal ---
function PipelineSummaryModal() {
  const pipelineSummary = useAppStore((s) => s.pipelineSummary);
  const showSummaryModal = useAppStore((s) => s.showSummaryModal);
  const setShowSummaryModal = useAppStore((s) => s.setShowSummaryModal);
  const nodeData = useAppStore((s) => s.nodeData);

  if (!showSummaryModal || !pipelineSummary) return null;

  const s = pipelineSummary;
  const totalEmails = (s.emails_sent?.high || 0) + (s.emails_sent?.medium || 0) + (s.emails_sent?.low || 0);
  const totalSolutions = (s.solutions?.high || 0) + (s.solutions?.medium || 0) + (s.solutions?.low || 0);
  const totalAnalyses = (s.deep_analyses?.high || 0) + (s.deep_analyses?.medium || 0) + (s.deep_analyses?.low || 0);

  // Build per-node timeline from nodeData
  const nodeTimeline = Object.entries(nodeData)
    .filter(([id]) => NODE_META[id])
    .sort((a, b) => (a[1].startedAt || 0) - (b[1].startedAt || 0))
    .map(([id, data]) => ({
      id,
      meta: NODE_META[id],
      input: data.input?.description || '—',
      output: data.output?.description || '—',
      duration: data.duration,
    }));

  return (
    <div className="psm-overlay" onClick={() => setShowSummaryModal(false)}>
      <div className="psm-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
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

        {/* Body */}
        <div className="psm-body">
          {/* Aggregated Stats */}
          <div className="psm-stats-grid">
            <div className="psm-stat">
              <div className="psm-stat-value">{s.logs_processed || 0}</div>
              <div className="psm-stat-label">Logs Processed</div>
            </div>
            <div className="psm-stat">
              <div className="psm-stat-value">{s.issues_found || 0}</div>
              <div className="psm-stat-label">Issues Found</div>
            </div>
            <div className="psm-stat">
              <div className="psm-stat-value">{s.total_incidents || 0}</div>
              <div className="psm-stat-label">Incidents</div>
            </div>
            <div className="psm-stat">
              <div className="psm-stat-value">{totalEmails}</div>
              <div className="psm-stat-label">Emails Sent</div>
            </div>
            <div className="psm-stat">
              <div className="psm-stat-value">{totalSolutions}</div>
              <div className="psm-stat-label">Solutions</div>
            </div>
            <div className="psm-stat">
              <div className="psm-stat-value">{totalAnalyses}</div>
              <div className="psm-stat-label">Deep Analyses</div>
            </div>
          </div>

          {/* Priority Breakdown */}
          <div className="psm-section">
            <h3 className="psm-section-title">Priority Breakdown</h3>
            <div className="psm-priority-row">
              <div className="psm-priority-card psm-priority-high">
                <span className="psm-priority-label">🔴 HIGH</span>
                <span className="psm-priority-count">{s.high_priority || 0}</span>
                <div className="psm-priority-detail">
                  {s.emails_sent?.high || 0} emails · {s.solutions?.high || 0} solutions
                </div>
              </div>
              <div className="psm-priority-card psm-priority-medium">
                <span className="psm-priority-label">🟡 MEDIUM</span>
                <span className="psm-priority-count">{s.medium_priority || 0}</span>
                <div className="psm-priority-detail">
                  {s.emails_sent?.medium || 0} emails · {s.solutions?.medium || 0} solutions
                </div>
              </div>
              <div className="psm-priority-card psm-priority-low">
                <span className="psm-priority-label">🟢 LOW</span>
                <span className="psm-priority-count">{s.low_priority || 0}</span>
                <div className="psm-priority-detail">
                  {s.emails_sent?.low || 0} emails · {s.solutions?.low || 0} solutions
                </div>
              </div>
            </div>
          </div>

          {/* Node Timeline */}
          {nodeTimeline.length > 0 && (
            <div className="psm-section">
              <h3 className="psm-section-title">Node Execution Timeline</h3>
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

          {/* Errors */}
          {s.errors && s.errors.length > 0 && (
            <div className="psm-section">
              <h3 className="psm-section-title" style={{ color: 'var(--priority-high)' }}>⚠ Errors</h3>
              <div className="psm-errors">
                {s.errors.map((err, i) => (
                  <div className="psm-error-item" key={i}>{err}</div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
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
  const { currentNode, isPipelineRunning } = useAppStore();

  // Node config modal state
  const [selectedNode, setSelectedNode] = useState(null);

  // Update node statuses when pipeline runs
  useEffect(() => {
    if (!isPipelineRunning && !currentNode) return;

    const nodeOrder = [
      'start', 'log_extractor', 'anomaly_detector', 'priority_classifier',
      'deep_code_analyzer_high', 'deep_code_analyzer_medium', 'deep_code_analyzer_low',
      'high_priority_handler', 'medium_priority_handler', 'low_priority_handler',
    ];
    const currentIdx = nodeOrder.indexOf(currentNode);

    setNodes((nds) =>
      nds.map((node) => {
        const idx = nodeOrder.indexOf(node.id);
        let status = 'idle';

        if (isPipelineRunning) {
          if (idx < currentIdx) status = 'completed';
          else if (idx === currentIdx) status = 'running';
        } else {
          status = 'idle';
        }

        return { ...node, data: { ...node.data, status } };
      })
    );
  }, [currentNode, isPipelineRunning, setNodes]);

  // Polling workflow state
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
      } catch (e) {
        // API might not be available
      }
    };

    pollState();
    const interval = setInterval(pollState, 5000);
    return () => clearInterval(interval);
  }, [setNodes]);

  // Handle node click → open config modal
  const onNodeClick = useCallback((_event, node) => {
    setSelectedNode({
      id: node.id,
      name: node.data.label,
    });
  }, []);

  return (
    <div className="page-content" style={{ padding: 0, paddingTop: 'var(--header-height)' }}>
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

      {/* Node Config Modal */}
      {selectedNode && (
        <NodeConfigModal
          nodeId={selectedNode.id}
          nodeName={selectedNode.name}
          onClose={() => setSelectedNode(null)}
        />
      )}

      {/* Pipeline Summary Modal */}
      <PipelineSummaryModal />
    </div>
  );
}
