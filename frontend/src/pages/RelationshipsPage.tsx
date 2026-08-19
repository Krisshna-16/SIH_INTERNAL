import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { fetchReports, ReportItem } from '../api/extraction';
import {
  fetchRelationships,
  runSymbolicAnalysis,
  RelationshipItem,
} from '../api/symbolic';
import { ClassificationBadge } from '../components/ClassificationBadge';
import { EmptyState } from '../components/EmptyState';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorBanner } from '../components/ErrorBanner';

export const RelationshipsPage: React.FC = () => {
  const { reportId: routeReportId } = useParams<{ reportId: string }>();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string>(routeReportId || '');
  const [relationships, setRelationships] = useState<RelationshipItem[]>([]);
  const [selectedRelType, setSelectedRelType] = useState<string>('ALL');
  const [selectedClass, setSelectedClass] = useState<string>('ALL');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalRels, setTotalRels] = useState<number>(0);
  const [pageSize] = useState<number>(25);
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

  const loadRelationships = useCallback(async () => {
    if (!selectedReportId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchRelationships(
        selectedReportId,
        selectedRelType,
        selectedClass,
        currentPage,
        pageSize
      );
      setRelationships(res.items);
      setTotalRels(res.total);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch relationships.');
    } finally {
      setLoading(false);
    }
  }, [selectedReportId, selectedRelType, selectedClass, currentPage, pageSize]);

  const handleRunAnalysis = async () => {
    if (!selectedReportId) return;
    setAnalyzing(true);
    setError(null);
    setAnalysisStep('Loading Ground-Truth Evidence & Initializing Symbolic Rules...');

    try {
      await new Promise((r) => setTimeout(r, 800));
      setAnalysisStep('Evaluating Co-occurrence & Structural Relationships...');

      const apiPromise = runSymbolicAnalysis(selectedReportId);

      await new Promise((r) => setTimeout(r, 1100));
      setAnalysisStep('Deriving Deterministic FACT & INFERENCE Triplets...');

      await apiPromise;
      await new Promise((r) => setTimeout(r, 500));

      setHasExecuted(true);
      setCurrentPage(1);
      await loadRelationships();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Symbolic analysis failed.');
    } finally {
      setAnalyzing(false);
      setAnalysisStep('');
    }
  };

  const totalPages = Math.ceil(totalRels / pageSize) || 1;

  return (
    <div className="relationships-page-container">
      <header className="page-header">
        <div className="header-title-block">
          <span className="phase-tag">Phase 4 | Symbolic AI Rule Engine</span>
          <h2>Derived Relationships</h2>
          <p className="subtitle">
            Deterministic relationship extraction (FACT vs INFERENCE) with complete rule provenance.
          </p>
        </div>
      </header>

      {/* Control Bar */}
      <div className="card control-card">
        <div className="control-row">
          <div className="control-group">
            <label htmlFor="rel-report-select" className="font-mono">SELECT CASE REPORT:</label>
            <select
              id="rel-report-select"
              value={selectedReportId}
              onChange={(e) => {
                setSelectedReportId(e.target.value);
                setHasExecuted(false);
                setRelationships([]);
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

      {/* Main Table Card */}
      <div className="card main-table-card">
        <div className="table-header-row">
          <h3>Derived Relationship Triplets</h3>
          {hasExecuted && (
            <span className="text-small text-muted font-mono">
              {totalRels} triplets derived
            </span>
          )}
        </div>

        {/* Filter Controls (Only shown after explicit analysis) */}
        {hasExecuted && (
          <div className="filter-container">
            <span className="filter-label font-mono">FILTER RELATIONSHIP TYPE:</span>
            <div className="filter-chips">
              {['ALL', 'USED', 'LOCATED_AT', 'ASSOCIATED_WITH', 'ACCESSED', 'CONTACTED'].map((t) => (
                <button
                  key={t}
                  className={`filter-chip ${selectedRelType === t ? 'active' : ''}`}
                  onClick={() => {
                    setSelectedRelType(t);
                    setCurrentPage(1);
                    if (selectedReportId) loadRelationships();
                  }}
                >
                  <span className="chip-name font-mono">{t}</span>
                </button>
              ))}
            </div>

            <span className="filter-label font-mono" style={{ marginTop: '0.75rem' }}>
              CLASSIFICATION:
            </span>
            <div className="filter-chips">
              {['ALL', 'FACT', 'INFERENCE'].map((c) => (
                <button
                  key={c}
                  className={`filter-chip ${selectedClass === c ? 'active' : ''}`}
                  onClick={() => {
                    setSelectedClass(c);
                    setCurrentPage(1);
                    if (selectedReportId) loadRelationships();
                  }}
                >
                  <span className="chip-name font-mono">{c}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {!hasExecuted && !analyzing ? (
          <EmptyState
            icon="🔗"
            title="Symbolic Relationship Engine Pending"
            description="No derived relationships displayed yet. Click 'RUN SYMBOLIC ANALYSIS' above to evaluate deterministic co-occurrence rules and derive FACT vs INFERENCE relationship triplets across report evidence."
          />
        ) : loading || analyzing ? (
          <LoadingSpinner message={analyzing ? analysisStep : 'Loading relationships...'} />
        ) : relationships.length === 0 ? (
          <EmptyState
            icon="🔍"
            title="No relationships derived for selected filter"
            description="Try selecting 'ALL' in the filter bar above."
          />
        ) : (
          <>
            <div className="table-wrapper">
              <table className="entities-table">
                <thead>
                  <tr>
                    <th>SOURCE ENTITY</th>
                    <th>PREDICATE</th>
                    <th>TARGET ENTITY</th>
                    <th>CLASSIFICATION</th>
                    <th>RULE ID</th>
                    <th>RULE EXPLANATION</th>
                  </tr>
                </thead>
                <tbody>
                  {relationships.map((rel) => (
                    <tr key={rel.id}>
                      <td className="val-cell">
                        <span className="font-mono text-bold">{rel.source_value}</span>
                        <span className="type-subtext font-mono text-muted"> ({rel.source_type})</span>
                      </td>
                      <td>
                        <span className="predicate-badge font-mono">{rel.relationship_type}</span>
                      </td>
                      <td className="val-cell">
                        <span className="font-mono text-bold">{rel.target_value}</span>
                        <span className="type-subtext font-mono text-muted"> ({rel.target_type})</span>
                      </td>
                      <td>
                        <ClassificationBadge classification={rel.classification} />
                      </td>
                      <td>
                        <span className="method-tag font-mono">{rel.rule_id}</span>
                      </td>
                      <td className="text-small text-muted">{rel.explanation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="pagination-bar" style={{ padding: '1rem 1.25rem' }}>
              <span className="page-info font-mono">
                Showing page {currentPage} of {totalPages} ({totalRels} relationships)
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
          </>
        )}
      </div>
    </div>
  );
};
