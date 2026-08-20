import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { apiClient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { ErrorBanner } from '../components/ErrorBanner';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [username, setUsername] = useState<string>('investigator');
  const [password, setPassword] = useState<string>('demo123');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const from = (location.state as any)?.from?.pathname || '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError('Please enter both username and password.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await apiClient.post('/api/v1/auth/login', {
        username: username.trim(),
        password: password.trim(),
      });
      const { access_token, user } = res.data;
      login(access_token, user);
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Authentication failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleFillDemoCredentials = () => {
    setUsername('investigator');
    setPassword('demo123');
    setError(null);
  };

  return (
    <div className="login-screen-wrapper">
      <div className="login-box-card">
        {/* Top Header & Branding */}
        <div className="login-brand-header">
          <div className="login-shield-badge">🛡️</div>
          <h1 className="login-title">MHA UFDR Platform</h1>
          <div className="login-mha-sub">MINISTRY OF HOME AFFAIRS // INDIA</div>
          <p className="login-access-notice">
            Authorized Digital Forensics & Investigation Access
          </p>
        </div>

        {error && <ErrorBanner message={error} />}

        {/* Credentials Form */}
        <form onSubmit={handleSubmit} className="login-credentials-form">
          <div className="login-field-group">
            <label htmlFor="login-username" className="login-field-label font-mono">
              INVESTIGATOR USERNAME
            </label>
            <input
              id="login-username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. investigator"
              className="login-text-input font-mono"
              autoFocus
              required
            />
          </div>

          <div className="login-field-group">
            <label htmlFor="login-password" className="login-field-label font-mono">
              PASSWORD
            </label>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="login-text-input font-mono"
              required
            />
          </div>

          <button type="submit" className="login-submit-btn font-mono" disabled={loading}>
            {loading ? 'AUTHENTICATING...' : 'SIGN IN TO FORENSIC PORTAL →'}
          </button>
        </form>

        {/* Demo Auto-fill Footer */}
        <div className="login-demo-footer">
          <span className="demo-footer-label font-mono">HACKATHON DEMO EVALUATION</span>
          <button
            type="button"
            className="demo-autofill-btn font-mono"
            onClick={handleFillDemoCredentials}
          >
            ⚡ Auto-Fill Demo Credentials (investigator / demo123)
          </button>
        </div>
      </div>
    </div>
  );
};
