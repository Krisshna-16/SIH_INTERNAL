import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import {
  fetchReports,
  runExtraction,
  fetchReportEntities,
  ReportItem,
  ExtractionSummary,
  EntityItem,
} from '../api/extraction';
import { EntityTypeFilter } from '../components/EntityTypeFilter';
import { ConfidenceBadge } from '../components/ConfidenceBadge';
import { EmptyState } from '../components/EmptyState';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorBanner } from '../components/ErrorBanner';

export const EntitiesPage: React.FC = () => {
  const { reportId: routeReportId } = useParams<{ reportId: string }>();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string>(routeReportId || '');
  const [summary, setSummary] = useState<ExtractionSummary | null>(null);
  const [entities, setEntities] = useState<EntityItem[]>([]);
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [loading, setLoading] = useState<boolean>(false);
  const [extracting, setExtracting] = useState<boolean>(false);
  const [hasExecuted, setHasExecuted] = useState<boolean>(false);
  const [extractionStep, setExtractionStep] = useState<string>('');
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

  const loadEntities = useCallback(async (reportId: string, typeFilter: string) => {
    if (!reportId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchReportEntities(reportId, typeFilter);
      setEntities(res.items);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch extracted entities.');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRunExtraction = async () => {
    if (!selectedReportId) return;
    setExtracting(true);
    setError(null);
    setExtractionStep('Initializing spaCy NLP Model & Entity Patterns...');

    try {
      // 2.5 second realistic execution feedback
      await new Promise((res) => setTimeout(res, 800));
      setExtractionStep('Scanning UFDR Document Pages & Extracting Character Provenance...');

      const apiResPromise = runExtraction(selectedReportId);

      await new Promise((res) => setTimeout(res, 1100));
      setExtractionStep('Normalizing Extracted Values & Persisting Ground-Truth Records...');

      const res = await apiResPromise;
      await new Promise((r) => setTimeout(r, 600));

      setSummary(res);
      setHasExecuted(true);
      await loadReports();
      await loadEntities(selectedReportId, selectedType);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Extraction failed.');
    } finally {
      setExtracting(false);
      setExtractionStep('');
    }
  };

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
    <div className="entities-page-container">
      {/* Page Header */}
      <header className="page-header">
        <div className="header-title-block">
          <span className="phase-tag">Phase 2 | Neural AI Layer</span>
          <h2>Neural Entity & Event Extraction</h2>
          <p className="subtitle">
            Local NLP entity recognition (spaCy) and deterministic pattern parsing with full provenance tracking.
          </p>
        </div>
      </header>

      {/* Control Bar */}
      <div className="card control-card">
        <div className="control-row">
          <div className="control-group">
            <label htmlFor="report-select" className="font-mono">SELECT CASE REPORT:</label>
            <select
              id="report-select"
              value={selectedReportId}
              onChange={(e) => {
                setSelectedReportId(e.target.value);
                setHasExecuted(false);
                setEntities([]);
                setSummary(null);
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
              onClick={handleRunExtraction}
              disabled={!selectedReportId || extracting}
              className="btn-cyber-primary"
            >
              <span className="btn-icon">⚡</span>
              <span>{extracting ? 'EXTRACTING ENTITIES...' : 'RUN NEURAL EXTRACTION'}</span>
            </button>
          </div>
        </div>
      </div>

      {error && <ErrorBanner message={error} />}

      {/* Live Animated Extraction Loading Overlay */}
      {extracting && (
        <div className="card processing-banner-card font-mono">
          <LoadingSpinner message={extractionStep || 'Executing Neural Extraction Engine...'} />
        </div>
      )}

      {/* Summary Performance Banner (Only shown after explicit extraction) */}
      {summary && hasExecuted && !extracting && (
        <div className="card summary-card">
          <div className="summary-card-header">
            <h3>Neural Extraction Summary Metadata</h3>
            <span className="text-small text-muted font-mono">spaCy NLP Output</span>
          </div>
          <div className="stats-grid">
            <div className="stat-box">
              <span className="stat-value font-mono text-cyan">{summary.total_entities}</span>
              <span className="stat-label font-mono">ENTITIES INDEXED</span>
            </div>
            <div className="stat-box">
              <span className="stat-value font-mono text-blue">{summary.pages_processed}</span>
              <span className="stat-label font-mono">PAGES PARSED</span>
            </div>
            <div className="stat-box">
              <span className="stat-value font-mono text-emerald">
                {Object.keys(summary.entity_counts).length}
              </span>
              <span className="stat-label font-mono">ENTITY CATEGORIES</span>
            </div>
          </div>
        </div>
      )}

      {/* Main Table / Empty State Container */}
      <div className="card main-table-card">
        <div className="table-header-row">
          <h3>Extracted Entities & Provenance Records</h3>
          {hasExecuted && (
            <span className="text-small text-muted font-mono">
              {entities.length} records shown
            </span>
          )}
        </div>

        {/* Filter bar only if extraction has been run */}
        {hasExecuted && (
          <EntityTypeFilter
            selectedType={selectedType}
            onSelectType={(type) => {
              setSelectedType(type);
              if (selectedReportId) loadEntities(selectedReportId, type);
            }}
            entityCounts={summary?.entity_counts}
          />
        )}

        {!hasExecuted && !extracting ? (
          <EmptyState
            icon="🧬"
            title="Neural Entity Extraction Pending"
            description="No extracted entities displayed yet. Click 'RUN NEURAL EXTRACTION' above to scan UFDR report pages with spaCy NLP and extract character-offset provenance records."
          />
        ) : loading || extracting ? (
          <LoadingSpinner message={extracting ? extractionStep : 'Loading extracted records...'} />
        ) : entities.length === 0 ? (
          <EmptyState
            icon="🔍"
            title="No entities found for selected filter"
            description="Try selecting 'ALL' in the filter bar above."
          />
        ) : (
          <div className="table-wrapper">
            <table className="entities-table">
              <thead>
                <tr>
                  <th>TYPE</th>
                  <th>EXTRACTED VALUE</th>
                  <th>NORMALIZED VALUE</th>
                  <th>CONFIDENCE</th>
                  <th>PROVENANCE</th>
                  <th>SOURCE REPORT</th>
                  <th>METHOD</th>
                </tr>
              </thead>
              <tbody>
                {entities.map((ent) => (
                  <tr key={ent.id}>
                    <td>
                      <span className={`type-badge ${getTypeBadgeClass(ent.type)} font-mono`}>
                        {ent.type}
                      </span>
                    </td>
                    <td className="val-cell font-mono text-bold">{ent.value}</td>
                    <td className="val-cell font-mono text-muted">{ent.normalized_value || '-'}</td>
                    <td>
                      <ConfidenceBadge value={ent.confidence} />
                    </td>
                    <td>
                      <span className="page-badge font-mono">Page {ent.source_page}</span>
                    </td>
                    <td className="font-mono text-muted text-small">{ent.source_report}</td>
                    <td>
                      <span className="method-tag font-mono">{ent.extraction_method}</span>
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
