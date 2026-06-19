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
  currentNode: null,
  
  // WebSocket connection
  wsConnected: false,

  // Active page
  activePage: 'dashboard',

  // Notifications
  notifications: [],

  // Actions
  setDashboard: (data) => set({ dashboard: data, isDashboardLoading: false }),
  setDashboardLoading: (loading) => set({ isDashboardLoading: loading }),
  setPipelineRunning: (running) => set({ isPipelineRunning: running }),
  setCurrentNode: (node) => set({ currentNode: node }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
  setActivePage: (page) => set({ activePage: page }),
  
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
