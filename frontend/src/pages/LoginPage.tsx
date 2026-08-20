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
      {/* Subtle background telemetry details */}
      <div className="bg-telemetry-overlay font-mono">
        <div className="telemetry-item top-left">TRACE-X // UFDR CORRELATION ENGINE</div>
        <div className="telemetry-item top-right">SYS_NODE: IN-DL-SRV-04 // [SECURE]</div>
        <div className="telemetry-item bottom-left">LAT/LONG: 28.6139° N, 77.2090° E</div>
        <div className="telemetry-item bottom-right">CIPHER: TLS_AES_256_GCM_SHA384</div>
      </div>

      <div className="login-box-card dossier-container">
        {/* Top metal clip simulating a clipboard/folder */}
        <div className="dossier-clip"></div>

        {/* Top Header & Branding */}
        <div className="dossier-header">
          <div className="dossier-header-left">
            <div className="dossier-seal-badge">
              <svg viewBox="0 0 100 100" className="mha-seal-svg">
                <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" strokeWidth="2" />
                <circle cx="50" cy="50" r="38" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="4 2" />
                <path d="M50,20 L60,40 L80,45 L65,60 L70,80 L50,70 L30,80 L35,60 L20,45 L40,40 Z" fill="currentColor" opacity="0.8" />
              </svg>
            </div>
            <div className="dossier-org-title">
              <span className="dossier-org-main brand-tracex">
                TR
                <span className="brand-fingerprint-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="brand-fingerprint-svg">
                    <path strokeLinecap="round" d="M12 2a10 10 0 0 0-10 10c0 2 .5 3.9 1.4 5.6" />
                    <path strokeLinecap="round" d="M12 5a7 7 0 0 0-7 7c0 1.2.3 2.4.9 3.4" />
                    <path strokeLinecap="round" d="M12 8a4 4 0 0 0-4 4v.5" />
                    <path strokeLinecap="round" d="M12 11a1 1 0 0 0-1 1v2c0 2 1.6 3.6 3.6 3.6m-1.2-5.6V12a1 1 0 0 1 1-1h1a1 1 0 0 1 1 1v1.5c0 2-1.6 3.6-3.6 3.6m3.6-5.1v1.5M7.6 19.3A10 10 0 0 0 12 22a10 10 0 0 0 8.8-5.3" />
                    <path strokeLinecap="round" d="M4.6 15.6A10 10 0 0 0 12 22m4.8-13.4V7a7 7 0 0 0-11.9-5" />
                  </svg>
                </span>
                CE-X
              </span>
              <span className="dossier-org-sub">HYBRID AI INVESTIGATOR THAT NEVER MISSES</span>
            </div>
          </div>

        </div>

        <div className="dossier-divider"></div>

        {/* Content Section: Split into 2 columns */}
        <div className="dossier-content">
          {/* Left Column: Form & Info */}
          <div className="dossier-form-column">
            <div className="dossier-classification font-mono">
              CLASSIFICATION: RESTRICTED // FORENSIC SYSTEM ACCESS ONLY
            </div>

            {error && <ErrorBanner message={error} />}

            {/* Credentials Form */}
            <form onSubmit={handleSubmit} className="dossier-form">
              <div className="dossier-field">
                <label htmlFor="login-username" className="dossier-field-label font-mono">
                  NAME:
                </label>
                <input
                  id="login-username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="ENTER ASSIGNED INVESTIGATOR NAME"
                  className="dossier-text-input font-mono"
                  autoFocus
                  required
                />
              </div>

              <div className="dossier-field">
                <label htmlFor="login-password" className="dossier-field-label font-mono">
                  RECORD ACCESS PASSCODE:
                </label>
                <input
                  id="login-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="dossier-text-input font-mono"
                  required
                />
              </div>

              <button type="submit" className="dossier-submit-btn font-mono" disabled={loading}>
                {loading ? 'AUTHENTICATING SYSTEM...' : 'SIGN IN TO FORENSIC PORTAL'}
              </button>
            </form>

            {/* Demo Auto-fill */}
            <div className="dossier-demo-box font-mono">
              <div className="demo-label">HACKATHON DEMO EVALUATION SYSTEM</div>
              <button
                type="button"
                className="dossier-autofill-btn"
                onClick={handleFillDemoCredentials}
              >
                Auto-Fill Demo Credentials (investigator / demo123)
              </button>
            </div>


          </div>

          {/* Right Column: Visual dossier assets */}
          <div className="dossier-visual-column">
            {/* Agent ID Card */}
            <div className="agent-id-card">
              <div className="agent-card-strap-hole"></div>
              <div className="agent-card-header">
                <div className="agent-card-logo">
                  <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor" style={{ display: 'block' }}>
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  </svg>
                </div>
                <div className="agent-card-title">INVESTIGATOR</div>
              </div>
              <div className="agent-photo-container">
                <svg viewBox="0 0 100 100" className="agent-silhouette-svg">
                  <circle cx="50" cy="40" r="22" fill="#334155" />
                  <path d="M50,65 C30,65 20,80 20,100 L80,100 C80,80 70,65 50,65 Z" fill="#334155" />
                </svg>
              </div>
              <div className="barcode-container">
                <div className="barcode-bars">
                  <div className="bar thick"></div>
                  <div className="bar thin"></div>
                  <div className="bar medium"></div>
                  <div className="bar thick"></div>
                  <div className="bar thin"></div>
                  <div className="bar thick"></div>
                  <div className="bar thin"></div>
                  <div className="bar medium"></div>
                  <div className="bar thick"></div>
                  <div className="bar thin"></div>
                </div>
                <div className="barcode-text font-mono">INVESTIGATOR ID CARD</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
