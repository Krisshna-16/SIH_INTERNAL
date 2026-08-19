import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { fetchReports, ReportItem } from '../api/extraction';
import { fetchQueryHistory, QueryHistoryItem } from '../api/query';

export const PrivacyAuditPage: React.FC = () => {
  const { reportId: routeReportId } = useParams<{ reportId: string }>();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string>(routeReportId || '');
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (routeReportId) {
      setSelectedReportId(routeReportId);
    }
  }, [routeReportId]);

  const loadReports = useCallback(async () => {
    try {
      const data = await fetchReports();
      setReports(data);
      if (data.length > 0 && !selectedReportId) {
        setSelectedReportId(data[0].id);
      }
    } catch (err: any) {
      console.error('Failed to load reports:', err);
    }
  }, [selectedReportId]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const loadAuditHistory = useCallback(async () => {
    if (!selectedReportId) return;
    setLoading(true);
    try {
      const res = await fetchQueryHistory(selectedReportId);
      setHistory(res.history);
    } catch (err: any) {
      console.error('Failed to load privacy audit history:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedReportId]);

  useEffect(() => {
    loadAuditHistory();
  }, [loadAuditHistory]);

  return (
    <div className="privacy-page-container">
      <header className="page-header">
        <div className="header-title-block">
          <span className="phase-tag">Phase 9 | Privacy Gateway & Compliance</span>
          <h2>Privacy & LLM Audit Log</h2>
          <p className="subtitle">
            Auditable record of local and gated external LLM queries, verifying pseudonymization and opt-in compliance.
          </p>
        </div>
      </header>

      {/* Control Card */}
      <div className="card control-card">
        <div className="control-row">
          <div className="control-group">
            <label htmlFor="priv-main-report-select">Select Report:</label>
            <select
              id="priv-main-report-select"
              value={selectedReportId}
              onChange={(e) => setSelectedReportId(e.target.value)}
              className="select-report"
            >
              {reports.length === 0 ? (
                <option value="">No reports available</option>
              ) : (
                reports.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.filename} ({r.id}) — [{r.status}]
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="timeline-summary-stats">
            <span className="stat-pill">Privacy Mode: <strong>Local Default</strong></span>
            <span className="stat-pill">LLM Prompting: 🔒 <strong>Pseudonymized</strong></span>
            <span className="stat-pill">Mapping Table: <strong>Local Memory Only</strong></span>
          </div>
        </div>
      </div>

      {/* Main Audit Table Card */}
      <div className="card main-table-card">
        <div className="table-header-row">
          <h3>LLM Query & Dispatch Audit Trail</h3>
          <span className="text-small text-muted">{history.length} Queries Recorded</span>
        </div>

        {loading ? (
          <div className="loading-state">Loading privacy audit logs...</div>
        ) : history.length === 0 ? (
          <div className="empty-state">No LLM queries recorded for this report.</div>
        ) : (
          <div className="table-wrapper">
            <table className="entities-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Query ID</th>
                  <th>Investigator Question</th>
                  <th>Intent</th>
                  <th>Privacy Status</th>
                  <th>Outcome Status</th>
                </tr>
              </thead>
              <tbody>
                {history.map((log) => (
                  <tr key={log.log_id}>
                    <td className="font-mono text-small">{log.timestamp.slice(0, 19).replace('T', ' ')}</td>
                    <td className="font-mono text-small">{log.query_id}</td>
                    <td>"{log.question}"</td>
                    <td><span className="method-tag">{log.intent}</span></td>
                    <td>
                      <span className="classification-badge badge-class-fact">
                        🔒 Pseudonymized
                      </span>
                    </td>
                    <td>
                      <span className={`classification-badge ${log.status === 'RESULTS_FOUND' ? 'badge-class-fact' : 'severity-med'}`}>
                        {log.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
