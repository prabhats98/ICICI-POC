/**
 * API Service - Axios wrapper for backend communication.
 * Includes JWT auth interceptors for automatic token attachment and 401 handling.
 */

import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// --- Request Interceptor: attach JWT token ---
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('cloudguard_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// --- Response Interceptor: handle 401 → redirect to login ---
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Don't redirect if we're already on auth routes
      const isAuthRoute = error.config?.url?.includes('/api/auth/');
      if (!isAuthRoute) {
        localStorage.removeItem('cloudguard_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// --- Auth ---
export const authLogin = (email, password) => api.post('/api/auth/login', { email, password });
export const authMe = () => api.get('/api/auth/me');
export const authLogout = () => api.post('/api/auth/logout');

// --- Dashboard ---
export const getDashboardSummary = () => api.get('/api/dashboard');

// --- Logs ---
export const getLogs = (params) => api.get('/api/logs/', { params });
export const getLogStats = () => api.get('/api/logs/stats');
export const getLog = (id) => api.get(`/api/logs/${id}`);

// --- Incidents ---
export const getIncidents = (params) => api.get('/api/incidents/', { params });
export const getIncidentStats = () => api.get('/api/incidents/stats');
export const getIncident = (id) => api.get(`/api/incidents/${id}`);
export const updateIncident = (id, data) => api.patch(`/api/incidents/${id}`, data);

// --- Agents ---
export const triggerPipeline = (data = {}) => api.post('/api/agents/run', { trigger_type: 'manual', ...data });
export const resetAndRunPipeline = () => api.post('/api/agents/reset-and-run');
export const getAgentStatus = () => api.get('/api/agents/status');
export const getAgentHistory = (params) => api.get('/api/agents/history', { params });

// --- Pipeline Control ---
export const getPipelineStatus = () => api.get('/api/pipeline/status');
export const togglePipeline = (enabled) => api.post('/api/pipeline/toggle', { enabled });
export const triggerManualRun = (data = {}) => api.post('/api/pipeline/run', data);
export const getPipelineThresholds = () => api.get('/api/pipeline/thresholds');
export const updatePipelineThresholds = (data) => api.put('/api/pipeline/thresholds', data);

// --- Workflow ---
export const getWorkflowState = () => api.get('/api/workflow/state');

// --- Node Config ---
export const getNodeConfig = (nodeId) => api.get(`/api/workflow/nodes/${nodeId}/config`);
export const updateNodeConfig = (nodeId, params) => api.put(`/api/workflow/nodes/${nodeId}/config`, { params });

// --- Export ---
export const exportLogs = (format = 'json') => api.get(`/api/export/logs?format=${format}`, { responseType: 'blob' });
export const exportIncidents = (format = 'json') => api.get(`/api/export/incidents?format=${format}`, { responseType: 'blob' });

// --- Ingest / Simulate ---
export const simulateLogs = (data = {}) => api.post('/api/ingest/simulate', {
  count: 60,
  spread_minutes: 30,
  trigger_pipeline: true,
  ...data,
});
export const ingestStats = () => api.get('/api/ingest/stats');

// --- Analytics ---
export const getIncidentTrend = (days = 7) => api.get(`/api/analytics/incident-trend?days=${days}`);
export const getServiceBreakdown = () => api.get('/api/analytics/service-breakdown');
export const getErrorDistribution = () => api.get('/api/analytics/error-distribution');
export const getNotificationHistory = (limit = 50) => api.get(`/api/analytics/notification-history?limit=${limit}`);
export const getTopIssues = (limit = 10) => api.get(`/api/analytics/top-issues?limit=${limit}`);
export const getLogVolume = (days = 7) => api.get(`/api/analytics/log-volume?days=${days}`);
export const getPipelineRuns = (limit = 20) => api.get(`/api/analytics/pipeline-runs?limit=${limit}`);
export const getMTTR = () => api.get('/api/analytics/mttr');
export const getGoldenSignals = () => api.get('/api/analytics/golden-signals');
export const getSystemHealth = () => api.get('/api/analytics/system-health');
export const getSLOStatus = () => api.get('/api/analytics/slo-status');
export const getServiceUptime = (days = 30) => api.get(`/api/analytics/service-uptime?days=${days}`);
export const getKPITrends = (days = 7) => api.get(`/api/analytics/kpi-trends?days=${days}`);

// --- WebSocket ---
export const createWebSocket = () => {
  const ws = new WebSocket('ws://localhost:8000/ws/pipeline');
  return ws;
};

export default api;
