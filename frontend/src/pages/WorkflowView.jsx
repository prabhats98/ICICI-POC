/**
 * WorkflowView Page - React Flow visualization of the agent pipeline.
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

// Custom node component
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
          <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2, marginLeft: 'auto' }}></span>
        )}
        {data.status === 'completed' && (
          <span style={{ marginLeft: 'auto', color: 'var(--accent-emerald)', fontSize: 14 }}>✓</span>
        )}
      </div>
      <div className="workflow-node-subtitle">{data.subtitle}</div>
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
    },
  },
  {
    id: 'high_priority_handler',
    type: 'workflowNode',
    position: { x: 80, y: 500 },
    data: {
      label: 'Send Alert Email',
      subtitle: 'Agent 4a: Email + Solution',
      icon: '📧',
      iconBg: 'rgba(16,185,129,0.2)',
      iconColor: '#10b981',
      status: 'idle',
    },
  },
  {
    id: 'medium_priority_handler',
    type: 'workflowNode',
    position: { x: 350, y: 500 },
    data: {
      label: 'Auto-Solution Agent',
      subtitle: 'Agent 4b: Find fix on-the-go',
      icon: '🧠',
      iconBg: 'rgba(59,130,246,0.2)',
      iconColor: '#3b82f6',
      status: 'idle',
    },
  },
  {
    id: 'low_priority_handler',
    type: 'workflowNode',
    position: { x: 620, y: 500 },
    data: {
      label: 'Log Data (No Spike)',
      subtitle: 'Agent 4c: Log & Monitor',
      icon: '📝',
      iconBg: 'rgba(100,116,139,0.2)',
      iconColor: '#94a3b8',
      status: 'idle',
    },
  },
  {
    id: 'end_high',
    type: 'workflowNode',
    position: { x: 80, y: 640 },
    data: {
      label: 'End',
      subtitle: 'High priority path complete',
      icon: '🏁',
      iconBg: 'rgba(239,68,68,0.2)',
      iconColor: '#ef4444',
      status: 'idle',
    },
  },
  {
    id: 'end_medium',
    type: 'workflowNode',
    position: { x: 350, y: 640 },
    data: {
      label: 'End',
      subtitle: 'Medium priority path complete',
      icon: '🏁',
      iconBg: 'rgba(239,68,68,0.2)',
      iconColor: '#ef4444',
      status: 'idle',
    },
  },
  {
    id: 'end_low',
    type: 'workflowNode',
    position: { x: 620, y: 640 },
    data: {
      label: 'End',
      subtitle: 'Low priority path complete',
      icon: '🏁',
      iconBg: 'rgba(239,68,68,0.2)',
      iconColor: '#ef4444',
      status: 'idle',
    },
  },
];

const initialEdges = [
  { id: 'e-start-extract', source: 'start', target: 'log_extractor', animated: true, style: { stroke: 'var(--accent-indigo)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--accent-indigo)' } },
  { id: 'e-extract-detect', source: 'log_extractor', target: 'anomaly_detector', animated: true, style: { stroke: 'var(--accent-emerald)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--accent-emerald)' } },
  { id: 'e-detect-classify', source: 'anomaly_detector', target: 'priority_classifier', animated: true, style: { stroke: 'var(--accent-amber)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--accent-amber)' } },
  { id: 'e-classify-high', source: 'priority_classifier', target: 'high_priority_handler', animated: true, label: 'HIGH', style: { stroke: '#ef4444' }, labelStyle: { fill: '#ef4444', fontWeight: 700, fontSize: 11 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#ef4444' } },
  { id: 'e-classify-medium', source: 'priority_classifier', target: 'medium_priority_handler', animated: true, label: 'MEDIUM', style: { stroke: '#f59e0b' }, labelStyle: { fill: '#f59e0b', fontWeight: 700, fontSize: 11 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#f59e0b' } },
  { id: 'e-classify-low', source: 'priority_classifier', target: 'low_priority_handler', animated: true, label: 'LOW', style: { stroke: '#10b981' }, labelStyle: { fill: '#10b981', fontWeight: 700, fontSize: 11 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#10b981' } },
  { id: 'e-high-end', source: 'high_priority_handler', target: 'end_high', style: { stroke: 'var(--border-default)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--text-muted)' } },
  { id: 'e-medium-end', source: 'medium_priority_handler', target: 'end_medium', style: { stroke: 'var(--border-default)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--text-muted)' } },
  { id: 'e-low-end', source: 'low_priority_handler', target: 'end_low', style: { stroke: 'var(--border-default)' }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--text-muted)' } },
];

export default function WorkflowView() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const { currentNode, isPipelineRunning } = useAppStore();

  // Update node statuses when pipeline runs
  useEffect(() => {
    if (!isPipelineRunning && !currentNode) return;

    const nodeOrder = ['start', 'log_extractor', 'anomaly_detector', 'priority_classifier', 'high_priority_handler', 'medium_priority_handler', 'low_priority_handler'];
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

  return (
    <div className="page-content" style={{ padding: 0, paddingTop: 'var(--header-height)' }}>
      <div style={{ height: 'calc(100vh - var(--header-height))', width: '100%' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
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
    </div>
  );
}
