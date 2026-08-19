import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { fetchReports, ReportItem } from '../api/extraction';
import {
  fetchReportEvidence,
  consolidateEvidence,
  fetchEvidenceById,
  EvidenceItem,
} from '../api/evidence';
import { EntityTypeFilter } from '../components/EntityTypeFilter';
import { EvidenceDetailModal } from '../components/EvidenceDetailModal';
import { ConfidenceBadge } from '../components/ConfidenceBadge';
import { EmptyState } from '../components/EmptyState';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorBanner } from '../components/ErrorBanner';

export const EvidencePage: React.FC = () => {
  const { reportId: routeReportId } = useParams<{ reportId: string }>();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string>(routeReportId || '');
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalEvidence, setTotalEvidence] = useState<number>(0);
  const [pageSize] = useState<number>(20);
  const [loading, setLoading] = useState<boolean>(false);
  const [consolidating, setConsolidating] = useState<boolean>(false);
  const [hasExecuted, setHasExecuted] = useState<boolean>(false);
  const [consolidateStep, setConsolidateStep] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [selectedEvidenceModal, setSelectedEvidenceModal] = useState<EvidenceItem | null>(null);

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

  const loadEvidence = useCallback(async () => {
    if (!selectedReportId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchReportEvidence(selectedReportId, selectedType, undefined, currentPage, pageSize);
      setEvidenceList(res.items);
      setTotalEvidence(res.total);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch evidence.');
    } finally {
      setLoading(false);
    }
  }, [selectedReportId, selectedType, currentPage, pageSize]);

  const handleConsolidate = async () => {
    if (!selectedReportId) return;
    setConsolidating(true);
    setError(null);
    setConsolidateStep('Loading Extracted Entities & Normalizing Values...');

    try {
      await new Promise((r) => setTimeout(r, 800));
      setConsolidateStep('Consolidating Canonical Ground-Truth Evidence Vault...');

      const apiPromise = consolidateEvidence(selectedReportId);

      await new Promise((r) => setTimeout(r, 1000));
      await apiPromise;
      await new Promise((r) => setTimeout(r, 400));

      setHasExecuted(true);
      setCurrentPage(1);
      await loadEvidence();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Evidence consolidation failed.');
    } finally {
      setConsolidating(false);
      setConsolidateStep('');
    }
  };

  const handleInspectDetail = async (evidenceId: string) => {
    try {
      const detail = await fetchEvidenceById(evidenceId);
      setSelectedEvidenceModal(detail);
    } catch (err: any) {
      setError('Failed to fetch evidence details: ' + err.message);
    }
  };

  const filteredEvidence = evidenceList.filter((item) => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        item.value.toLowerCase().includes(q) ||
        (item.normalized_value && item.normalized_value.toLowerCase().includes(q)) ||
        item.evidence_id.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const totalPages = Math.ceil(totalEvidence / pageSize) || 1;

  const getTypeBadgeClass = (type: string) => {
    switch (type.toUpperCase()) {
      case 'PERSON':
        return 'type-badge-person';
      case 'PHONE':
        return 'type-badge-phone';
      case 'EMAIL':
        return 'type-badge-email';
      case 'LOCATION':
        return 'type-badge-location';
      case 'DATE':
        return 'type-badge-date';
      case 'URL':
      case 'IP_ADDRESS':
        return 'type-badge-network';
      case 'ORG':
        return 'type-badge-org';
      default:
        return 'type-badge-other';
    }
  };

  return (
    <div className="evidence-page-container">
      <header className="page-header">
        <div className="header-title-block">
          <span className="phase-tag">Phase 3 | Evidence Database Layer</span>
          <h2>Canonical Evidence Explorer</h2>
          <p className="subtitle">
            Ground-truth evidence repository with full provenance tracking and immutable audit logging.
          </p>
        </div>
      </header>

      {/* Control Bar */}
      <div className="card control-card">
        <div className="control-row">
          <div className="control-group">
            <label htmlFor="ev-report-select" className="font-mono">SELECT CASE REPORT:</label>
            <select
              id="ev-report-select"
              value={selectedReportId}
              onChange={(e) => {
                setSelectedReportId(e.target.value);
                setHasExecuted(false);
                setEvidenceList([]);
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
              onClick={handleConsolidate}
              disabled={!selectedReportId || consolidating}
              className="btn-cyber-primary"
            >
              <span className="btn-icon">⚡</span>
              <span>{consolidating ? 'CONSOLIDATING...' : 'CONSOLIDATE EVIDENCE'}</span>
            </button>
          </div>
        </div>
      </div>

      {error && <ErrorBanner message={error} />}

      {/* Main Evidence Explorer Card */}
      <div className="card main-table-card">
        <div className="table-header-row">
          <h3>Queryable Evidence Records</h3>
          {hasExecuted && (
            <div className="search-box">
              <input
                type="text"
                placeholder="Search value, ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-input font-mono"
              />
            </div>
          )}
        </div>

        {/* Filter bar only shown if executed */}
        {hasExecuted && (
          <EntityTypeFilter
            selectedType={selectedType}
            onSelectType={(t) => {
              setSelectedType(t);
              setCurrentPage(1);
              if (selectedReportId) loadEvidence();
            }}
          />
        )}

        {!hasExecuted && !consolidating ? (
          <EmptyState
            icon="🔍"
            title="Canonical Evidence Vault Pending"
            description="No evidence records displayed yet. Click 'CONSOLIDATE EVIDENCE' above to index canonical ground-truth evidence records and build immutable audit provenance across report pages."
          />
        ) : loading || consolidating ? (
          <LoadingSpinner message={consolidating ? consolidateStep : 'Loading evidence records...'} />
        ) : filteredEvidence.length === 0 ? (
          <EmptyState
            icon="🔍"
            title="No evidence records found"
            description="Try adjusting your search query or entity type filter."
          />
        ) : (
          <>
            <div className="table-wrapper">
              <table className="entities-table">
                <thead>
                  <tr>
                    <th>EVIDENCE ID</th>
                    <th>TYPE</th>
                    <th>EXTRACTED VALUE</th>
                    <th>NORMALIZED VALUE</th>
                    <th>CONFIDENCE</th>
                    <th>PROVENANCE</th>
                    <th>ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEvidence.map((ev) => (
                    <tr key={ev.evidence_id}>
                      <td className="font-mono text-muted text-small">{ev.evidence_id}</td>
                      <td>
                        <span className={`type-badge ${getTypeBadgeClass(ev.evidence_type)} font-mono`}>
                          {ev.evidence_type}
                        </span>
                      </td>
                      <td className="val-cell font-mono text-bold">{ev.value}</td>
                      <td className="val-cell font-mono text-muted">{ev.normalized_value || '-'}</td>
                      <td>
                        <ConfidenceBadge value={ev.confidence} />
                      </td>
                      <td>
                        <span className="page-badge font-mono">Page {ev.source_page}</span>
                      </td>
                      <td>
                        <button
                          className="btn-inspect-cyber font-mono"
                          onClick={() => handleInspectDetail(ev.evidence_id)}
                        >
                          Inspect Provenance
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div className="pagination-bar" style={{ padding: '1rem 1.25rem' }}>
              <span className="page-info font-mono">
                Showing page {currentPage} of {totalPages} ({totalEvidence} records)
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

      {/* Provenance Detail Modal */}
      <EvidenceDetailModal
        evidence={selectedEvidenceModal}
        onClose={() => setSelectedEvidenceModal(null)}
      />
    </div>
  );
};
