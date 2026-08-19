import React, { useEffect, useState, useCallback } from 'react';
import { fetchReports, ReportItem } from '../api/extraction';
import { fetchEvidenceSummary, EvidenceSummaryResponse } from '../api/evidence';

interface DashboardPageProps {
  onNavigateToEvidence: () => void;
  onNavigateToEntities: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onNavigateToEvidence,
  onNavigateToEntities,
}) => {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string>('');
  const [summary, setSummary] = useState<EvidenceSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

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

  const loadSummary = useCallback(async (reportId: string) => {
    if (!reportId) return;
    setLoading(true);
    try {
      const data = await fetchEvidenceSummary(reportId);
      setSummary(data);
    } catch (err: any) {
      console.error('Failed to load summary:', err);
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedReportId) {
      loadSummary(selectedReportId);
    }
  }, [selectedReportId, loadSummary]);

  return (
    <div className="dashboard-page-container">
      <header className="page-header">
        <div className="header-title-block">
          <span className="phase-tag">Phase 3 | Evidence Database Layer</span>
          <h2>Forensic Evidence Dashboard</h2>
          <p className="subtitle">
            Executive overview of consolidated ground-truth evidence records across ingested UFDR extractions.
          </p>
        </div>
      </header>

      {/* Report Selector */}
      <div className="card control-card">
        <div className="control-row">
          <div className="control-group">
            <label htmlFor="dash-report-select">Select Report:</label>
            <select
              id="dash-report-select"
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

          <div className="button-group">
            <button onClick={onNavigateToEntities} className="btn-secondary">
              ⚡ Extract Entities (Phase 2)
            </button>
            <button onClick={onNavigateToEvidence} className="btn-primary">
              🔍 Explore Evidence DB (Phase 3)
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">Loading dashboard analytics...</div>
      ) : !summary ? (
        <div className="card empty-card">
          <p>No consolidated evidence data found for this report. Please process entity extraction and consolidate evidence first.</p>
        </div>
      ) : (
        <div className="dashboard-content">
          {/* Key Metrics */}
          <div className="metrics-grid">
            <div className="metric-card">
              <span className="metric-val">{summary.total_evidence}</span>
              <span className="metric-lbl">Total Evidence Records</span>
            </div>
            <div className="metric-card">
              <span className="metric-val">{summary.page_count}</span>
              <span className="metric-lbl">Source Pages</span>
            </div>
            <div className="metric-card">
              <span className="metric-val">{Object.keys(summary.type_breakdown).length}</span>
              <span className="metric-lbl">Distinct Evidence Categories</span>
            </div>
          </div>

          {/* Category Breakdown Cards */}
          <div className="card breakdown-card">
            <h3>Evidence Breakdown by Category</h3>
            <div className="category-grid">
              {Object.entries(summary.type_breakdown).map(([type, count]) => {
                const percentage = summary.total_evidence > 0 ? ((count / summary.total_evidence) * 100).toFixed(1) : 0;
                return (
                  <div key={type} className="cat-box">
                    <div className="cat-header">
                      <span className="cat-type">{type}</span>
                      <span className="cat-count">{count}</span>
                    </div>
                    <div className="progress-bar-bg">
                      <div className="progress-bar-fill" style={{ width: `${percentage}%` }} />
                    </div>
                    <span className="cat-percent">{percentage}% of total</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
