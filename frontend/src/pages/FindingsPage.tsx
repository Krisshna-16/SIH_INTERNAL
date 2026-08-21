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

  useEffect(() => {
    if (selectedReportId) {
      loadFindings();
    }
  }, [selectedReportId, selectedSeverity, currentPage, loadFindings]);

  const handleRunAnalysis = async () => {
    if (!selectedReportId) return;
    setAnalyzing(true);
    setError(null);
    setAnalysisStep('Loading Ground-Truth Evidence & Initializing Symbolic Rules...');

    try {
      await new Promise((r) => setTimeout(r, 600));
      setAnalysisStep('Evaluating Page Co-occurrence & Communication Burst Patterns...');

      const apiPromise = runSymbolicAnalysis(selectedReportId);

      await new Promise((r) => setTimeout(r, 800));
      setAnalysisStep('Deriving Deterministic FACT & INFERENCE Anomaly Triplets...');

      await apiPromise;
      await new Promise((r) => setTimeout(r, 400));

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
        return 'severity-badge-high';
      case 'MEDIUM':
        return 'severity-badge-medium';
      default:
        return 'severity-badge-low';
    }
  };

  const totalPages = Math.ceil(totalFindings / pageSize) || 1;

  return (
    <div className="findings-page-container">
      <header className="page-header">
        <div className="header-title-block">
          <span className="phase-tag">FORENSIC INTELLIGENCE // PHASE 4 ANOMALY FINDINGS</span>
          <h2>Flagged Anomaly Findings</h2>
          <p className="subtitle">
            Explainable investigative flags derived from deterministic correlation rules operating on evidence ground-truth.
          </p>
        </div>
      </header>

      {/* Control Bar */}
      <div className="card control-card" style={{ marginBottom: '1.25rem' }}>
        <div className="control-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div className="control-group" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <label htmlFor="fnd-report-select" className="font-mono text-muted text-small">SELECT CASE REPORT:</label>
            <select
              id="fnd-report-select"
              value={selectedReportId}
              onChange={(e) => {
                setSelectedReportId(e.target.value);
                setCurrentPage(1);
              }}
              className="select-report font-mono"
              style={{ background: '#0f172a', border: '1px solid #334155', color: '#f8fafc', padding: '0.5rem 0.8rem', borderRadius: '6px' }}
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

      {/* Severity Filter */}
      <div className="card filter-card-standalone" style={{ marginBottom: '1.25rem', padding: '0.75rem 1.25rem' }}>
        <div className="filter-container" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span className="filter-label font-mono text-small text-muted">FILTER SEVERITY:</span>
          <div className="filter-chips" style={{ display: 'flex', gap: '0.5rem' }}>
            {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map((s) => (
              <button
                key={s}
                className={`filter-chip ${selectedSeverity === s ? 'active' : ''}`}
                style={{
                  padding: '0.35rem 0.8rem',
                  borderRadius: '4px',
                  border: selectedSeverity === s ? '1px solid #06b6d4' : '1px solid #334155',
                  background: selectedSeverity === s ? 'rgba(6, 182, 212, 0.15)' : 'transparent',
                  color: selectedSeverity === s ? '#38bdf8' : '#94a3b8',
                  cursor: 'pointer',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                }}
                onClick={() => {
                  setSelectedSeverity(s);
                  setCurrentPage(1);
                }}
              >
                <span className="chip-name font-mono">{s}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Findings List Cards / Empty State */}
      {loading || analyzing ? (
        <LoadingSpinner message={analyzing ? analysisStep : 'Evaluating symbolic findings...'} />
      ) : findings.length === 0 ? (
        <EmptyState
          icon="🚩"
          title="No anomaly findings flagged"
          description="No anomalies triggered rule thresholds for this filter. Run Symbolic Analysis above to evaluate deterministic rules."
        />
      ) : (
        <div className="findings-list" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {findings.map((fnd) => {
            const isExpanded = expandedFindingId === fnd.id;
            const detail = findingDetails[fnd.id];

            return (
              <div key={fnd.id} className="finding-item-card card">
                {/* Header Badge Row */}
                <div className="finding-header-row">
                  <div className="finding-badges-left">
                    <span className={`severity-badge ${getSeverityBadgeClass(fnd.severity)}`}>
                      {fnd.severity} SEVERITY
                    </span>
                    <ClassificationBadge classification={fnd.classification} />
                    <span className="finding-id-tag font-mono">[{fnd.id}]</span>
                  </div>
                </div>

                {/* Rule Title & Explanation */}
                <div className="finding-content-block">
                  <h3 className="rule-title">{fnd.rule_name}</h3>
                  <p className="explanation-text">{fnd.explanation}</p>
                </div>

                {/* Structured Parameters Box */}
                <div className="finding-meta-row">
                  <div className="meta-item font-mono">
                    <span className="meta-label">Rule ID:</span>
                    <span className="meta-value">{fnd.rule_id}</span>
                  </div>
                  {fnd.parameters_used && Object.keys(fnd.parameters_used).length > 0 && (
                    <div className="meta-params-group font-mono">
                      <span className="meta-label">Parameters:</span>
                      <div className="params-chips-list">
                        {Object.entries(fnd.parameters_used).map(([key, val]) => (
                          <span key={key} className="param-chip font-mono">
                            <span className="param-key">{key.replace(/_/g, ' ')}:</span>
                            <span className="param-val">
                              {Array.isArray(val) ? `[${val.join(', ')}]` : String(val)}
                            </span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Footer Action Accordion */}
                <div className="finding-footer">
                  <button className="btn-cyber-outline btn-sm font-mono" onClick={() => toggleExpand(fnd.id)}>
                    {isExpanded ? '▲ Hide Linked Evidence' : `▼ View Linked Evidence (${fnd.related_evidence_ids.length} Items)`}
                  </button>
                </div>

                {/* Expanded Linked Evidence Box */}
                {isExpanded && (
                  <div className="expanded-evidence-box">
                    <h4 className="font-mono text-cyan" style={{ fontSize: '0.85rem', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Linked Evidence Ground-Truth Records
                    </h4>
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

          <div className="pagination-bar" style={{ marginTop: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="page-info font-mono text-small text-muted">
              Showing page {currentPage} of {totalPages} ({totalFindings} findings)
            </span>
            <div className="page-buttons" style={{ display: 'flex', gap: '0.5rem' }}>
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
