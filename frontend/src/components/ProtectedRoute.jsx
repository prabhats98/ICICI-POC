/**
 * ProtectedRoute - Route guard that redirects unauthenticated users to /login.
 */

import { Navigate } from 'react-router-dom';
import useAuthStore from '../store/useAuthStore';

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="auth-loading">
        <div className="auth-loading-inner">
          <div className="spinner" style={{ width: 40, height: 40, borderWidth: 3 }} />
          <p>Verifying authentication...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
