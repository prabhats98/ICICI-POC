/**
 * App.jsx - Root application component with routing and authentication.
 * "/" = Landing page (public)
 * "/login" = Login page (public)
 * "/dashboard", "/workflow", etc. = Protected routes
 */

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import ProtectedRoute from "./components/ProtectedRoute";
import Dashboard from "./pages/Dashboard";
import WorkflowView from "./pages/WorkflowView";
import LogExplorer from "./pages/LogExplorer";
import IncidentPanel from "./pages/IncidentPanel";
import Analytics from "./pages/Analytics";
import Settings from "./pages/Settings";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import useWebSocket from "./hooks/useWebSocket";
import useAuthStore from "./store/useAuthStore";

function AuthenticatedLayout() {
  useWebSocket();

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <Header />
        <Routes>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/workflow" element={<WorkflowView />} />
          <Route path="/logs" element={<LogExplorer />} />
          <Route path="/incidents" element={<IncidentPanel />} />
          <Route path="/settings" element={<Settings />} />
          {/* Catch-all: redirect to dashboard */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </div>
    </div>
  );
}

function App() {
  const { checkAuth, isAuthenticated } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<LandingPage />} />
        <Route
          path="/login"
          element={<LoginPage />}
        />

        {/* Protected routes — all dashboard pages */}
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <AuthenticatedLayout />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
