/**
 * Global App Store - Zustand state management.
 */

import { create } from 'zustand';

const useAppStore = create((set) => ({
  // Dashboard data
  dashboard: null,
  isDashboardLoading: true,

  // Pipeline status
  isPipelineRunning: false,
  pipelineEnabled: true,
  currentNode: null,
  
  // WebSocket connection
  wsConnected: false,

  // Active page
  activePage: 'dashboard',

  // Notifications
  notifications: [],

  // Node I/O data — map of nodeId → { input, output, startedAt, completedAt }
  nodeData: {},

  // Pipeline summary (populated on pipeline_complete)
  pipelineSummary: null,

  // Summary modal visibility
  showSummaryModal: false,

  // Actions
  setDashboard: (data) => set({ dashboard: data, isDashboardLoading: false }),
  setDashboardLoading: (loading) => set({ isDashboardLoading: loading }),
  setPipelineRunning: (running) => set({ isPipelineRunning: running }),
  setPipelineEnabled: (enabled) => set({ pipelineEnabled: enabled }),
  setCurrentNode: (node) => set({ currentNode: node }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
  setActivePage: (page) => set({ activePage: page }),

  setNodeData: (nodeId, data) =>
    set((state) => ({
      nodeData: {
        ...state.nodeData,
        [nodeId]: { ...(state.nodeData[nodeId] || {}), ...data },
      },
    })),

  setPipelineSummary: (summary) => set({ pipelineSummary: summary }),
  setShowSummaryModal: (show) => set({ showSummaryModal: show }),

  clearPipelineData: () => set({ nodeData: {}, pipelineSummary: null, showSummaryModal: false }),
  
  addNotification: (notification) =>
    set((state) => ({
      notifications: [
        { id: Date.now(), timestamp: new Date(), ...notification },
        ...state.notifications.slice(0, 19),
      ],
    })),
  
  clearNotifications: () => set({ notifications: [] }),
}));

export default useAppStore;
