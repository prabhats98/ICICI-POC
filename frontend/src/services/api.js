/**
 * API Service - Axios wrapper for backend communication.
 */

import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

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
export const getAgentStatus = () => api.get('/api/agents/status');
export const getAgentHistory = (params) => api.get('/api/agents/history', { params });

// --- Workflow ---
export const getWorkflowState = () => api.get('/api/workflow/state');

// --- Export ---
export const exportLogs = (format = 'json') => api.get(`/api/export/logs?format=${format}`, { responseType: 'blob' });
export const exportIncidents = (format = 'json') => api.get(`/api/export/incidents?format=${format}`, { responseType: 'blob' });

// --- WebSocket ---
export const createWebSocket = () => {
  const ws = new WebSocket('ws://localhost:8000/ws/pipeline');
  return ws;
};

export default api;
