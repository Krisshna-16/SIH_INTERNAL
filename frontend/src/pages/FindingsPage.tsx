import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { fetchReports, ReportItem } from '../api/extraction';
import {
  fetchFindings,
  fetchFindingById,
  runSymbolicAnalysis,
  FindingItem,
} from '../api/symbolic';
import { ClassificationBadge } from '../components/ClassificationBadge';
import { EmptyState } from '../components/EmptyState';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorBanner } from '../components/ErrorBanner';

export const FindingsPage: React.FC = () => {
  const { reportId: routeReportId } = useParams<{ reportId: string }>();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string>(routeReportId || '');
  const [findings, setFindings] = useState<FindingItem[]>([]);
  const [selectedSeverity, setSelectedSeverity] = useState<string>('ALL');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalFindings, setTotalFindings] = useState<number>(0);
  const [pageSize] = useState<number>(15);
  const [expandedFindingId, setExpandedFindingId] = useState<string | null>(null);
  const [findingDetails, setFindingDetails] = useState<Record<string, FindingItem>>({});
  const [loading, setLoading] = useState<boolean>(false);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [hasExecuted, setHasExecuted] = useState<boolean>(false);
  const [analysisStep, setAnalysisStep] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

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

  const loadFindings = useCallback(async () => {
    if (!selectedReportId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchFindings(selectedReportId, undefined, selectedSeverity, currentPage, pageSize);
      setFindings(res.items);
      setTotalFindings(res.total);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch findings.');
    } finally {
      setLoading(false);
    }
  }, [selectedReportId, selectedSeverity, currentPage, pageSize]);

  const handleRunAnalysis = async () => {
    if (!selectedReportId) return;
    setAnalyzing(true);
    setError(null);
    setAnalysisStep('Loading Ground-Truth Evidence & Initializing Symbolic Rules...');

    try {
      await new Promise((r) => setTimeout(r, 800));
      setAnalysisStep('Evaluating Page Co-occurrence & Communication Burst Patterns...');

      const apiPromise = runSymbolicAnalysis(selectedReportId);

      await new Promise((r) => setTimeout(r, 1100));
      setAnalysisStep('Deriving Deterministic FACT & INFERENCE Anomaly Triplets...');

      await apiPromise;
      await new Promise((r) => setTimeout(r, 500));

      setHasExecuted(true);
      setCurrentPage(1);
      await loadFindings();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Symbolic analysis failed.');
    } finally {
      setAnalyzing(false);
      setAnalysisStep('');
    }
  };

  const toggleExpand = async (findingId: string) => {
    if (expandedFindingId === findingId) {
      setExpandedFindingId(null);
      return;
    }

    setExpandedFindingId(findingId);
    if (!findingDetails[findingId]) {
      try {
        const fullDetail = await fetchFindingById(findingId);
        setFindingDetails((prev) => ({ ...prev, [findingId]: fullDetail }));
      } catch (err: any) {
        console.error('Failed to load finding details:', err);
      }
    }
  };

  const getSeverityBadgeClass = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'HIGH':
        return 'severity-high';
      case 'MEDIUM':
        return 'severity-med';
      default:
        return 'severity-low';
    }
  };

  const totalPages = Math.ceil(totalFindings / pageSize) || 1;

  return (
    <div className="findings-page-container">
      <header className="page-header">
        <div className="header-title-block">
          <span className="phase-tag">Phase 4 | Symbolic AI Rule Engine</span>
          <h2>Flagged Anomaly Findings</h2>
          <p className="subtitle">
            Explainable investigative flags derived from deterministic correlation rules operating on evidence ground-truth.
          </p>
        </div>
      </header>

      {/* Control Bar */}
      <div className="card control-card">
        <div className="control-row">
          <div className="control-group">
            <label htmlFor="fnd-report-select" className="font-mono">SELECT CASE REPORT:</label>
            <select
              id="fnd-report-select"
              value={selectedReportId}
              onChange={(e) => {
                setSelectedReportId(e.target.value);
                setHasExecuted(false);
                setFindings([]);
                setCurrentPage(1);
              }}
              className="select-report font-mono"
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
            <button
              onClick={handleRunAnalysis}
              disabled={!selectedReportId || analyzing}
              className="btn-cyber-primary"
            >
              <span className="btn-icon">⚡</span>
              <span>{analyzing ? 'EVALUATING RULES...' : 'RUN SYMBOLIC ANALYSIS'}</span>
            </button>
          </div>
        </div>
      </div>

      {error && <ErrorBanner message={error} />}

      {/* Severity Filter (Only shown if executed) */}
      {hasExecuted && (
        <div className="card filter-card-standalone">
          <div className="filter-container">
            <span className="filter-label font-mono">FILTER SEVERITY:</span>
            <div className="filter-chips">
              {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map((s) => (
                <button
                  key={s}
                  className={`filter-chip ${selectedSeverity === s ? 'active' : ''}`}
                  onClick={() => {
                    setSelectedSeverity(s);
                    setCurrentPage(1);
                    if (selectedReportId) loadFindings();
                  }}
                >
                  <span className="chip-name font-mono">{s}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Findings List Cards / Empty State */}
      {!hasExecuted && !analyzing ? (
        <EmptyState
          icon="🚩"
          title="Symbolic Rule Engine Pending"
          description="No anomaly findings displayed yet. Click 'RUN SYMBOLIC ANALYSIS' above to evaluate deterministic co-occurrence and communication burst rules against report evidence."
        />
      ) : loading || analyzing ? (
        <LoadingSpinner message={analyzing ? analysisStep : 'Evaluating symbolic findings...'} />
      ) : findings.length === 0 ? (
        <EmptyState
          icon="✓"
          title="No rule findings flagged"
          description="No anomalies triggered rule thresholds for this filter."
        />
      ) : (
        <div className="findings-list">
          {findings.map((fnd) => {
            const isExpanded = expandedFindingId === fnd.id;
            const detail = findingDetails[fnd.id];

            return (
              <div key={fnd.id} className="finding-item-card">
                <div className="finding-header">
                  <div className="finding-title-row">
                    <span className={`severity-badge ${getSeverityBadgeClass(fnd.severity)}`}>
                      {fnd.severity} SEVERITY
                    </span>
                    <ClassificationBadge classification={fnd.classification} />
                    <span className="finding-id-tag font-mono">{fnd.id}</span>
                  </div>
                  <h3 className="rule-title">{fnd.rule_name}</h3>
                </div>

                <div className="finding-body">
                  <p className="explanation-text">{fnd.explanation}</p>

                  <div className="finding-meta-row">
                    <span className="meta-tag font-mono">Rule ID: <strong>{fnd.rule_id}</strong></span>
                    <span className="meta-tag font-mono">
                      Parameters: <code>{JSON.stringify(fnd.parameters_used)}</code>
                    </span>
                  </div>
                </div>

                <div className="finding-footer">
                  <button className="btn-expand font-mono" onClick={() => toggleExpand(fnd.id)}>
                    {isExpanded ? '▲ Hide Linked Evidence' : `▼ View Linked Evidence (${fnd.related_evidence_ids.length} Items)`}
                  </button>
                </div>

                {isExpanded && (
                  <div className="expanded-evidence-box">
                    <h4>Linked Evidence Ground-Truth Records</h4>
                    {!detail ? (
                      <div className="text-muted text-small font-mono">Loading evidence details...</div>
                    ) : detail.related_evidence && detail.related_evidence.length > 0 ? (
                      <div className="evidence-mini-table">
                        {detail.related_evidence.map((ev) => (
                          <div key={ev.evidence_id} className="evidence-mini-row">
                            <span className="mini-type font-mono">{ev.evidence_type}</span>
                            <span className="mini-val font-mono">{ev.value}</span>
                            <span className="page-badge font-mono">Page {ev.source_page}</span>
                            <span className="confidence-pill conf-high font-mono">
                              {(ev.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-muted text-small font-mono">
                        Evidence IDs: {fnd.related_evidence_ids.join(', ')}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          <div className="pagination-bar" style={{ marginTop: '1rem' }}>
            <span className="page-info font-mono">
              Showing page {currentPage} of {totalPages} ({totalFindings} findings)
            </span>
            <div className="page-buttons">
              <button
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => p - 1)}
                className="btn-secondary btn-sm font-mono"
              >
                Previous
              </button>
              <button
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((p) => p + 1)}
                className="btn-secondary btn-sm font-mono"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
