/**
 * WorkflowView Page - React Flow visualization of the agent pipeline.
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

// --- Node order for progress tracking ---
const PIPELINE_STEPS = [
  'log_extractor',
  'anomaly_detector',
  'priority_classifier',
  'deep_code_analyzer_high',
  'deep_code_analyzer_medium',
  'deep_code_analyzer_low',
  'high_priority_handler',
  'medium_priority_handler',
  'low_priority_handler',
];

const STEP_LABELS = {
  log_extractor: 'Extracting Logs',
  anomaly_detector: 'Detecting Anomalies',
  priority_classifier: 'Classifying Priority',
  deep_code_analyzer_high: 'Deep Analysis (HIGH)',
  deep_code_analyzer_medium: 'Deep Analysis (MEDIUM)',
  deep_code_analyzer_low: 'Deep Analysis (LOW)',
  high_priority_handler: 'Emergency Response',
  medium_priority_handler: 'Solution Architect',
  low_priority_handler: 'Advisory Report',
};

// --- Pipeline Progress Banner ---
function PipelineProgressBanner() {
  const { isPipelineRunning, currentNode, nodeData } = useAppStore();
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef(null);
  const startRef = useRef(null);

  // Count completed steps
  const completedSteps = PIPELINE_STEPS.filter(
    (id) => nodeData[id]?.completedAt
  ).length;
  const currentIdx = PIPELINE_STEPS.indexOf(currentNode);
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

// --- Node Output Result Card (attached to right of node) ---
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

// --- Decision Node (diamond-style) ---
function DecisionNode({ data }) {
  const statusClass = data.status || 'idle';
  return (
    <div className={`workflow-node ${statusClass}`} style={{
      transform: 'rotate(0deg)',
      borderColor: data.status === 'running' ? 'var(--status-running)' :
                   data.status === 'completed' ? 'var(--status-success)' : 'var(--accent-amber)',
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
      subtitle: 'Agent 1: Firestore → PostgreSQL',
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
  // --- Deep Code Analysis Nodes ---
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
  // --- Handler Nodes ---
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
  { id: 'e-start-extract', source: 'start', target: 'log_extractor', animated: true, style: { stroke: 'var(--accent-indigo)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--accent-indigo)' } },
  { id: 'e-extract-detect', source: 'log_extractor', target: 'anomaly_detector', animated: true, style: { stroke: 'var(--accent-emerald)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--accent-emerald)' } },
  { id: 'e-detect-classify', source: 'anomaly_detector', target: 'priority_classifier', animated: true, style: { stroke: 'var(--accent-amber)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--accent-amber)' } },
  { id: 'e-classify-dca-high', source: 'priority_classifier', target: 'deep_code_analyzer_high', animated: true, label: 'HIGH', style: { stroke: '#ef4444' }, labelStyle: { fill: '#ef4444', fontWeight: 700, fontSize: 11 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#ef4444' } },
  { id: 'e-classify-dca-medium', source: 'priority_classifier', target: 'deep_code_analyzer_medium', animated: true, label: 'MEDIUM', style: { stroke: '#f59e0b' }, labelStyle: { fill: '#f59e0b', fontWeight: 700, fontSize: 11 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#f59e0b' } },
  { id: 'e-classify-dca-low', source: 'priority_classifier', target: 'deep_code_analyzer_low', animated: true, label: 'LOW', style: { stroke: '#10b981' }, labelStyle: { fill: '#10b981', fontWeight: 700, fontSize: 11 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#10b981' } },
  { id: 'e-dca-high-handler', source: 'deep_code_analyzer_high', target: 'high_priority_handler', animated: true, style: { stroke: '#8b5cf6' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' } },
  { id: 'e-dca-medium-handler', source: 'deep_code_analyzer_medium', target: 'medium_priority_handler', animated: true, style: { stroke: '#8b5cf6' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' } },
  { id: 'e-dca-low-handler', source: 'deep_code_analyzer_low', target: 'low_priority_handler', animated: true, style: { stroke: '#8b5cf6' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' } },
  { id: 'e-high-end', source: 'high_priority_handler', target: 'end_high', style: { stroke: 'var(--border-default)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--text-muted)' } },
  { id: 'e-medium-end', source: 'medium_priority_handler', target: 'end_medium', style: { stroke: 'var(--border-default)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--text-muted)' } },
  { id: 'e-low-end', source: 'low_priority_handler', target: 'end_low', style: { stroke: 'var(--border-default)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--text-muted)' } },
];

// --- Node metadata for summary ---
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

  // Update node statuses based on WebSocket events
  useEffect(() => {
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
          // Check if this specific node has completed (from nodeData)
          if (nodeData[node.id]?.completedAt) {
            status = 'completed';
          } else if (idx === currentIdx) {
            status = 'running';
          } else if (idx < currentIdx) {
            status = 'completed';
          }
        } else if (nodeData[node.id]?.completedAt) {
          // Pipeline done, but keep completed status
          status = 'completed';
        }

        return { ...node, data: { ...node.data, status } };
      })
    );

    // Highlight active edges
    setEdges((eds) =>
      eds.map((edge) => {
        const sourceIdx = nodeOrder.indexOf(edge.source);
        const targetIdx = nodeOrder.indexOf(edge.target);
        const isActive = isPipelineRunning && sourceIdx >= 0 && sourceIdx < currentIdx;
        const isCurrent = isPipelineRunning && targetIdx === currentIdx;

        return {
          ...edge,
          animated: true,
          style: {
            ...edge.style,
            strokeWidth: isCurrent ? 3 : isActive ? 2.5 : 1.5,
            opacity: isPipelineRunning ? (isActive || isCurrent ? 1 : 0.3) : 0.8,
          },
        };
      })
    );
  }, [currentNode, isPipelineRunning, nodeData, setNodes, setEdges]);

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

  const onNodeClick = useCallback((_event, node) => {
    setSelectedNode({
      id: node.id,
      name: node.data.label,
    });
  }, []);

  return (
    <div className="page-content" style={{ padding: 0, paddingTop: 'var(--header-height)' }}>
      {/* Pipeline Progress Banner */}
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
