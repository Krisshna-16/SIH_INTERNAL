import React, { useEffect, useState, useCallback } from 'react';
import { fetchHealthStatus, HealthResponse } from '../api/client';
import { StatusBadge, ConnectionStatus } from '../components/StatusBadge';

export const HealthCheckPage: React.FC = () => {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('loading');
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string | null>(null);

  const checkHealth = useCallback(async () => {
    setStatus('loading');
    setError(null);
    try {
      const response = await fetchHealthStatus();
      setData(response);
      setStatus('connected');
      setLastChecked(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      setData(null);
      setStatus('disconnected');
      setLastChecked(new Date().toLocaleTimeString());
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to establish connection to backend service.');
      }
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  return (
    <div className="health-page-container">
      <header className="platform-header">
        <div className="header-badge-title">
          <span className="gov-tag">Ministry of Home Affairs | Govt. of India</span>
          <h1>UFDR Forensic Analysis Platform</h1>
          <p className="subtitle">Phase 0 Foundation System & Backend Integration Health Check</p>
        </div>
      </header>

      <main className="health-content">
        <div className="card status-overview-card">
          <div className="card-header">
            <h2>Backend Connectivity Status</h2>
            <StatusBadge status={status} />
          </div>

          <div className="card-body">
            <div className="meta-grid">
              <div className="meta-item">
                <span className="meta-label">Target API URL</span>
                <span className="meta-value code-font">{apiBaseUrl}</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Health Endpoint</span>
                <span className="meta-value code-font">/api/v1/health</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Last Checked</span>
                <span className="meta-value">{lastChecked || 'Checking...'}</span>
              </div>
            </div>

            <div className="action-row">
              <button
                onClick={checkHealth}
                disabled={status === 'loading'}
                className="btn-refresh"
              >
                {status === 'loading' ? 'Checking Connection...' : 'Refresh Health Status'}
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="card error-card">
            <h3>Connection Error</h3>
            <p className="error-text">{error}</p>
            <p className="error-hint">
              Ensure backend server is running: <code>cd backend && uvicorn app.main:app --reload</code>
            </p>
          </div>
        )}

        {data && (
          <div className="card data-card">
            <div className="card-header">
              <h3>Backend Telemetry & Metadata</h3>
              <span className="pill-env">{data.env}</span>
            </div>

            <div className="card-body">
              <div className="data-grid">
                <div className="data-item">
                  <span className="data-label">Application Name</span>
                  <span className="data-value">{data.app}</span>
                </div>
                <div className="data-item">
                  <span className="data-label">Status Flag</span>
                  <span className="data-value status-ok">{data.status}</span>
                </div>
                <div className="data-item">
                  <span className="data-label">Server Timestamp</span>
                  <span className="data-value code-font">{data.timestamp}</span>
                </div>
              </div>

              <div className="json-container">
                <h4>Raw Payload Response</h4>
                <pre className="json-block">{JSON.stringify(data, null, 2)}</pre>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
