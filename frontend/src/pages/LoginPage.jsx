/**
 * LoginPage - Enterprise login page with Azure branding.
 * All icons are inline SVGs — no emojis.
 */

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import useAuthStore from '../store/useAuthStore';
import {
  BrainIcon, BroadcastIcon, AlertIcon, ChartIcon,
  EnvelopeIcon, LockIcon, EyeIcon, EyeOffIcon,
  WarningIcon, KeyIcon, ArrowLeftIcon,
} from '../components/Icons';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, isLoading, error, clearError } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const success = await login(email, password);
    if (success) {
      navigate('/dashboard');
    }
  };

  return (
    <div className="login-page" id="login-page">
      {/* Left panel - branding */}
      <div className="login-left">
        <div className="login-left-glow" />
        <div className="login-left-content">
          <img src="/image.png" alt="KR Elixir" className="login-logo" />
          <h2 className="login-left-title">CloudGuard</h2>
          <p className="login-left-tagline">
            Azure Cloud Log Intelligence Platform
          </p>
          <div className="login-left-features">
            {[
              { Icon: BrainIcon, text: 'AI-Powered Log Analysis' },
              { Icon: BroadcastIcon, text: 'Real-Time Monitoring' },
              { Icon: AlertIcon, text: 'Automated Incident Response' },
              { Icon: ChartIcon, text: 'Compliance Reporting' },
            ].map((item, i) => (
              <div key={i} className="login-left-feature">
                <item.Icon size={18} />
                <span>{item.text}</span>
              </div>
            ))}
          </div>
          <div className="login-left-footer">
            <span>© {new Date().getFullYear()} KR Elixir Technology</span>
          </div>
        </div>
      </div>

      {/* Right panel - form */}
      <div className="login-right">
        <div className="login-form-container">
          <div className="login-form-header">
            <div className="login-azure-badge" id="azure-badge">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M7.47 1.027L2.877 5.79l3.167 5.98L1 12.973h11.17L7.47 1.027z" fill="#0078D4"/>
                <path d="M9.193 2.308L6.2 6.282l1.78 3.127-4.08.798 8.27.017-3-7.916z" fill="url(#azure-grad)"/>
                <defs><linearGradient id="azure-grad" x1="6.2" y1="3" x2="10.17" y2="10.2" gradientUnits="userSpaceOnUse"><stop stopColor="#1490DF"/><stop offset="1" stopColor="#1F56A3"/></linearGradient></defs>
              </svg>
              Connected to Azure
            </div>
            <h1 className="login-form-title">Sign in to CloudGuard</h1>
            <p className="login-form-subtitle">
              Access the Azure Cloud Log Intelligence Platform
            </p>
          </div>

          {error && (
            <div className="login-error" id="login-error">
              <WarningIcon size={16} />
              <span>{error}</span>
              <button className="login-error-close" onClick={clearError}>×</button>
            </div>
          )}

          <form onSubmit={handleSubmit} className="login-form" id="login-form">
            <div className="login-field">
              <label className="login-label" htmlFor="email">Email Address</label>
              <div className="login-input-wrapper">
                <span className="login-input-icon"><EnvelopeIcon size={16} /></span>
                <input
                  id="email"
                  type="email"
                  className="login-input"
                  placeholder="admin@krelixir.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  autoFocus
                />
              </div>
            </div>

            <div className="login-field">
              <label className="login-label" htmlFor="password">Password</label>
              <div className="login-input-wrapper">
                <span className="login-input-icon"><LockIcon size={16} /></span>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  className="login-input"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="login-toggle-password"
                  id="toggle-password"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOffIcon size={18} /> : <EyeIcon size={18} />}
                </button>
              </div>
            </div>

            <div className="login-options">
              <label className="login-remember" htmlFor="remember">
                <input
                  id="remember"
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                <span className="login-checkbox-custom" />
                Remember me
              </label>
            </div>

            <button
              type="submit"
              className="btn btn-primary login-submit"
              id="login-submit"
              disabled={isLoading || !email || !password}
            >
              {isLoading ? (
                <>
                  <span className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} />
                  Signing in...
                </>
              ) : (
                <><KeyIcon size={16} /> Sign In</>
              )}
            </button>
          </form>

          <div className="login-back">
            <Link to="/" className="login-back-link" id="back-to-landing">
              <ArrowLeftIcon size={14} /> Back to Home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
