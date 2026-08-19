import React, { useEffect, useState } from 'react';
import { Outlet, useParams, useNavigate } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { fetchReports, ReportItem } from '../api/extraction';
import { useAuth } from '../context/AuthContext';
import { ErrorBanner } from '../components/ErrorBanner';

export const AppShell: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [report, setReport] = useState<ReportItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!reportId) return;
    fetchReports()
      .then((reports) => {
        const match = reports.find((r) => r.id === reportId);
        if (match) {
          setReport(match);
          setError(null);
        } else {
          setReport(null);
          setError(`Report "${reportId}" not found.`);
        }
      })
      .catch(() => setError('Failed to load report details.'));
  }, [reportId]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="app-shell-layout">
      <Sidebar />
      <div className="shell-main-area">
        {/* Clean, Uncluttered Topbar */}
        <header className="topbar">
          <div className="topbar-left">
            <div className="topbar-brand">
              UFDR Analysis Platform <span className="topbar-sub font-mono">// MHA Smart Automation</span>
            </div>
          </div>

          <div className="topbar-right">
            <div className="sys-status-badge" title="Local Forensic Engine Operational">
              <span className="sys-pulse" />
              <span className="sys-text font-mono">SYS.OK</span>
            </div>

            {report && (
              <div className="topbar-report-pill font-mono" title={report.filename}>
                <span>Case: {report.filename}</span>
                <span className={`status-tag status-${report.status}`}>{report.status}</span>
              </div>
            )}

            {user && (
              <div className="topbar-user-control">
                <span className="user-pill font-mono">
                  {user.username}
                </span>
                <button onClick={handleLogout} className="btn-logout" title="Sign out">
                  Logout
                </button>
              </div>
            )}
          </div>
        </header>

        {/* Main Content Area */}
        <main className="shell-content">
          {error ? (
            <ErrorBanner message={error} onRetry={() => navigate('/')} />
          ) : (
            <Outlet />
          )}
        </main>
      </div>
    </div>
  );
};
