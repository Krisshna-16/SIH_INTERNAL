import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { fetchReports, ReportItem } from '../api/extraction';
import {
  fetchTimeline,
  fetchTimelineSummary,
  TimelineEntryItem,
  TimelineSummaryResponse,
} from '../api/timeline';
import { TimelineFilterBar } from '../components/TimelineFilterBar';
import { TimelineEntityView } from '../components/TimelineEntityView';
import { EvidenceDetailModal } from '../components/EvidenceDetailModal';
import { fetchEvidenceById, EvidenceItem } from '../api/evidence';
import { fetchFindingById, FindingItem } from '../api/symbolic';

export const TimelinePage: React.FC = () => {
  const { reportId: routeReportId } = useParams<{ reportId: string }>();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string>(routeReportId || '');
  const [timelineEntries, setTimelineEntries] = useState<TimelineEntryItem[]>([]);
  const [summary, setSummary] = useState<TimelineSummaryResponse | null>(null);

  useEffect(() => {
    if (routeReportId) {
      setSelectedReportId(routeReportId);
    }
  }, [routeReportId]);
  
  // Filter state
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [entitySearch, setEntitySearch] = useState<string>('');
  const [selectedClass, setSelectedClass] = useState<string>('ALL');
  const [focusedEntity, setFocusedEntity] = useState<string | null>(null);

  // Pagination state
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalEntries, setTotalEntries] = useState<number>(0);
  const [pageSize] = useState<number>(30);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Modal inspection state
  const [selectedEvDetail, setSelectedEvDetail] = useState<EvidenceItem | null>(null);
  const [selectedFndDetail, setSelectedFndDetail] = useState<FindingItem | null>(null);

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

  const loadTimelineData = useCallback(async () => {
    if (!selectedReportId) return;
    setLoading(true);
    setError(null);
    try {
      const [tlRes, sumRes] = await Promise.all([
        fetchTimeline(
          selectedReportId,
          startDate || undefined,
          endDate || undefined,
          selectedType,
          entitySearch,
          selectedClass,
          currentPage,
          pageSize
        ),
        fetchTimelineSummary(selectedReportId),
      ]);

      setTimelineEntries(tlRes.items);
      setTotalEntries(tlRes.total);
      setSummary(sumRes);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch timeline.');
    } finally {
      setLoading(false);
    }
  }, [selectedReportId, startDate, endDate, selectedType, entitySearch, selectedClass, currentPage, pageSize]);

  useEffect(() => {
    loadTimelineData();
  }, [loadTimelineData]);

  const handleFilterChange = (newFilters: {
    startDate?: string;
    endDate?: string;
    selectedType?: string;
    entitySearch?: string;
    selectedClass?: string;
  }) => {
    if (newFilters.startDate !== undefined) setStartDate(newFilters.startDate);
    if (newFilters.endDate !== undefined) setEndDate(newFilters.endDate);
    if (newFilters.selectedType !== undefined) setSelectedType(newFilters.selectedType);
    if (newFilters.entitySearch !== undefined) setEntitySearch(newFilters.entitySearch);
    if (newFilters.selectedClass !== undefined) setSelectedClass(newFilters.selectedClass);
    setCurrentPage(1);
  };

  const handleReset = () => {
    setStartDate('');
    setEndDate('');
    setSelectedType('ALL');
    setEntitySearch('');
    setSelectedClass('ALL');
    setFocusedEntity(null);
    setCurrentPage(1);
  };

  const handleEntryClick = async (entry: TimelineEntryItem) => {
    if (entry.evidence_id) {
      try {
        const ev = await fetchEvidenceById(entry.evidence_id);
        setSelectedEvDetail(ev);
      } catch (err) {
        console.error('Failed to load evidence detail:', err);
      }
    } else if (entry.finding_id) {
      try {
        const fnd = await fetchFindingById(entry.finding_id);
        setSelectedFndDetail(fnd);
      } catch (err) {
        console.error('Failed to load finding detail:', err);
      }
    }
  };

  const totalPages = Math.ceil(totalEntries / pageSize) || 1;

  return (
    <div className="timeline-page-container">
      <header className="page-header">
        <div className="header-title-block">
          <span className="phase-tag">Phase 5 | Timeline Generation</span>
          <h2>Chronological Timeline</h2>
          <p className="subtitle">
            Read-oriented sequence assembling timestamped Evidence ground-truth and Symbolic Findings into an explainable timeline.
          </p>
        </div>
      </header>

      {/* Control & Summary Card */}
      <div className="card control-card">
        <div className="control-row">
          <div className="control-group">
            <label htmlFor="tl-main-report-select">Select Report:</label>
            <select
              id="tl-main-report-select"
              value={selectedReportId}
              onChange={(e) => {
                setSelectedReportId(e.target.value);
                setCurrentPage(1);
                handleReset();
              }}
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

          {summary && (
            <div className="timeline-summary-stats">
              <span className="stat-pill">Total: <strong>{summary.total_entries}</strong></span>
              {summary.earliest_timestamp && (
                <span className="stat-pill">Span: <code>{summary.earliest_timestamp.slice(0, 10)}</code> to <code>{summary.latest_timestamp?.slice(0, 10)}</code></span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Filter Bar */}
      <TimelineFilterBar
        startDate={startDate}
        endDate={endDate}
        selectedType={selectedType}
        entitySearch={entitySearch}
        selectedClass={selectedClass}
        onFilterChange={handleFilterChange}
        onReset={handleReset}
      />

      {/* Focused Entity Mode */}
      {focusedEntity && (
        <TimelineEntityView
          reportId={selectedReportId}
          entityValue={focusedEntity}
          onClearFocus={() => setFocusedEntity(null)}
          onSelectEntry={handleEntryClick}
        />
      )}

      {error && (
        <div className="card error-card">
          <h4>Timeline Assembly Notice</h4>
          <p>{error}</p>
        </div>
      )}

      {/* Timeline Sequence Container */}
      <div className="card main-table-card">
        <div className="table-header-row">
          <h3>Sequence View (Ascending Order)</h3>
          {summary && !summary.has_timestamped_evidence && (
            <span className="text-small text-muted">
              Note: This report currently has 0 timestamped evidence items.
            </span>
          )}
        </div>

        {loading ? (
          <div className="loading-state">Assembling chronological sequence...</div>
        ) : timelineEntries.length === 0 ? (
          <div className="empty-state">
            {selectedReportId
              ? 'No timestamped timeline entries match the selected filters.'
              : 'Please select a report to view the timeline.'}
          </div>
        ) : (
          <div className="timeline-sequence-box">
            {timelineEntries.map((entry) => (
              <div
                key={entry.entry_id}
                className={`timeline-node-card ${entry.classification === 'INFERENCE' ? 'node-finding' : 'node-evidence'}`}
                onClick={() => handleEntryClick(entry)}
              >
                <div className="node-time-col">
                  <span className="node-timestamp font-mono">{entry.timestamp}</span>
                  <span className="node-icon">
                    {entry.classification === 'INFERENCE' ? '⚠️' : '📄'}
                  </span>
                </div>

                <div className="node-content-col">
                  <div className="node-header">
                    <span className="node-title">{entry.title}</span>
                    <div className="node-badges">
                      <span className="predicate-badge">{entry.event_type}</span>
                      <span className={`classification-badge ${entry.classification === 'FACT' ? 'badge-class-fact' : 'badge-class-inference'}`}>
                        {entry.classification}
                      </span>
                    </div>
                  </div>

                  {entry.related_values.length > 0 && (
                    <div className="node-values-row">
                      {entry.related_values.map((val, idx) => (
                        <button
                          key={idx}
                          className="entity-chip-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            setFocusedEntity(val);
                          }}
                          title="Click to focus timeline on this entity"
                        >
                          {val}
                        </button>
                      ))}
                    </div>
                  )}

                  <div className="node-provenance-row">
                    <span className="text-small text-muted">
                      Source: {entry.source_report} (Page {entry.source_page})
                    </span>
                    <span className="text-small text-muted font-mono">
                      {entry.evidence_id || entry.finding_id}
                    </span>
                  </div>
                </div>
              </div>
            ))}

            <div className="pagination-bar" style={{ marginTop: '1rem' }}>
              <span className="page-info">
                Showing page {currentPage} of {totalPages} ({totalEntries} entries)
              </span>
              <div className="page-buttons">
                <button
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage((p) => p - 1)}
                  className="btn-secondary btn-sm"
                >
                  Previous
                </button>
                <button
                  disabled={currentPage >= totalPages}
                  onClick={() => setCurrentPage((p) => p + 1)}
                  className="btn-secondary btn-sm"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Modal Inspection Components */}
      {selectedEvDetail && (
        <EvidenceDetailModal
          evidence={selectedEvDetail}
          onClose={() => setSelectedEvDetail(null)}
        />
      )}

      {selectedFndDetail && (
        <div className="modal-overlay" onClick={() => setSelectedFndDetail(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Flagged Finding Provenance</h3>
              <button className="btn-close" onClick={() => setSelectedFndDetail(null)}>
                ✕
              </button>
            </div>
            <div className="modal-body">
              <p><strong>Rule Name:</strong> {selectedFndDetail.rule_name}</p>
              <p><strong>Rule ID:</strong> {selectedFndDetail.rule_id}</p>
              <p><strong>Severity:</strong> {selectedFndDetail.severity}</p>
              <p><strong>Explanation:</strong> {selectedFndDetail.explanation}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
