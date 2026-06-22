/**
 * Auth Store - Zustand store for authentication state management.
 */

import { create } from 'zustand';
import api from '../services/api';

const useAuthStore = create((set, get) => ({
  // State
  user: null,
  token: localStorage.getItem('cloudguard_token') || null,
  isAuthenticated: false,
  isLoading: true,
  error: null,

  // Login
  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await api.post('/api/auth/login', { email, password });
      const { access_token, user } = data;
      localStorage.setItem('cloudguard_token', access_token);
      set({
        token: access_token,
        user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
      return true;
    } catch (err) {
      const message =
        err.response?.data?.detail || 'Invalid email or password';
      set({ error: message, isLoading: false });
      return false;
    }
  },

  // Logout
  logout: () => {
    localStorage.removeItem('cloudguard_token');
    set({
      token: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
  },

  // Check existing token validity
  checkAuth: async () => {
    const token = get().token;
    if (!token) {
      set({ isLoading: false, isAuthenticated: false });
      return;
    }
    try {
      const { data } = await api.get('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      set({
        user: data,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      localStorage.removeItem('cloudguard_token');
      set({
        token: null,
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },

  clearError: () => set({ error: null }),
}));

export default useAuthStore;
