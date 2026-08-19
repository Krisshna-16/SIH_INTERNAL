import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { fetchReports, ReportItem } from '../api/extraction';
import {
  submitInvestigatorQuery,
  fetchQueryHistory,
  RetrievalResult,
  QueryHistoryItem,
} from '../api/query';
import { QueryHistoryPanel } from '../components/QueryHistoryPanel';

export const QueryPage: React.FC = () => {
  const { reportId: routeReportId } = useParams<{ reportId: string }>();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string>(routeReportId || '');
  const [questionInput, setQuestionInput] = useState<string>('');
  const [retrievalResult, setRetrievalResult] = useState<RetrievalResult | null>(null);
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
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

  const loadHistory = useCallback(async () => {
    if (!selectedReportId) return;
    try {
      const res = await fetchQueryHistory(selectedReportId);
      setHistory(res.history);
    } catch (err: any) {
      console.error('Failed to load query history:', err);
    }
  }, [selectedReportId]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleQuerySubmit = async (qText?: string) => {
    const qToRun = qText || questionInput;
    if (!selectedReportId || !qToRun.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res = await submitInvestigatorQuery(selectedReportId, qToRun.trim());
      setRetrievalResult(res);
      await loadHistory();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Query execution failed.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'RESULTS_FOUND':
        return 'badge-class-fact';
      case 'ENTITY_NOT_RESOLVED':
        return 'severity-med';
      default:
        return 'severity-high';
    }
  };

  return (
    <div className="query-page-container">
      <header className="page-header">
        <div className="header-title-block">
          <span className="phase-tag">Phase 7 | Investigator Query System</span>
          <h2>Ground-Truth Evidence Retriever</h2>
          <p className="subtitle">
            Structured query understanding & verified evidence retrieval — providing provenance-complete inputs for Phase 8 LLM synthesis.
          </p>
        </div>
      </header>

      {/* Control Card */}
      <div className="card control-card">
        <div className="control-row">
          <div className="control-group">
            <label htmlFor="query-main-report-select">Select Report:</label>
            <select
              id="query-main-report-select"
              value={selectedReportId}
              onChange={(e) => {
                setSelectedReportId(e.target.value);
                setRetrievalResult(null);
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
        </div>
      </div>

      {/* Search Bar Input & Sample Questions */}
      <div className="card search-box-card">
        <div className="query-input-row">
          <input
            type="text"
            placeholder="Type your question (e.g. 'Who did Inspector Vikram contact?', 'What happened on 12 March 2024?')..."
            value={questionInput}
            onChange={(e) => setQuestionInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleQuerySubmit(); }}
            className="search-input-large"
          />
          <button
            onClick={() => handleQuerySubmit()}
            disabled={!selectedReportId || !questionInput.trim() || loading}
            className="btn-primary"
          >
            {loading ? 'Searching Ground-Truth...' : 'Search Evidence'}
          </button>
        </div>

        <div className="sample-prompts-row">
          <span className="prompt-label">Sample Prompts:</span>
          <button
            className="prompt-chip"
            onClick={() => { setQuestionInput('Who did Inspector Vikram contact?'); handleQuerySubmit('Who did Inspector Vikram contact?'); }}
          >
            "Who did Inspector Vikram contact?"
          </button>
          <button
            className="prompt-chip"
            onClick={() => { setQuestionInput('What happened on 12 March 2024?'); handleQuerySubmit('What happened on 12 March 2024?'); }}
          >
            "What happened on 12 March 2024?"
          </button>
          <button
            className="prompt-chip"
            onClick={() => { setQuestionInput('What suspicious activity was flagged?'); handleQuerySubmit('What suspicious activity was flagged?'); }}
          >
            "What suspicious activity was flagged?"
          </button>
          <button
            className="prompt-chip"
            onClick={() => { setQuestionInput('Tell me about Agent Zero'); handleQuerySubmit('Tell me about Agent Zero'); }}
          >
            "Tell me about Agent Zero"
          </button>
        </div>
      </div>

      {error && (
        <div className="card error-card">
          <h4>Query Pipeline Notice</h4>
          <p>{error}</p>
        </div>
      )}

      {/* Layout Grid: Result View & Audit History */}
      <div className="query-layout-grid">
        <div className="results-column">
          {retrievalResult && (
            <div className="card result-details-card">
              <div className="result-header-row">
                <div className="intent-badge-group">
                  <span className="method-tag">Intent: <strong>{retrievalResult.intent.intent_type}</strong></span>
                  <span className="confidence-pill conf-high">
                    {(retrievalResult.intent.confidence * 100).toFixed(0)}% Confidence
                  </span>
                  <span className={`classification-badge ${getStatusBadgeClass(retrievalResult.status)}`}>
                    {retrievalResult.status}
                  </span>
                </div>
                <span className="font-mono text-small text-muted">{retrievalResult.query_id}</span>
              </div>

              <div className="summary-banner">
                <p><strong>Retrieval Summary:</strong> {retrievalResult.retrieval_summary}</p>
              </div>

              {/* Resolved Entity Mentions */}
              {retrievalResult.resolved_entities.length > 0 && (
                <div className="resolved-entities-box">
                  <span className="filter-label">Extracted Question Entities:</span>
                  <div className="entity-chips-row">
                    {retrievalResult.resolved_entities.map((rent, i) => (
                      <span
                        key={i}
                        className={`entity-resolution-chip ${rent.matched ? 'chip-matched' : 'chip-unmatched'}`}
                      >
                        {rent.matched ? '✓' : '✗'} {rent.mention_text} ({rent.entity_type})
                        {rent.matched && rent.matched_values.length > 0 && ` → ${rent.matched_values.join(', ')}`}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Explicit No Evidence State */}
              {retrievalResult.status !== 'RESULTS_FOUND' && (
                <div className="no-evidence-alert">
                  <h4>No Verified Evidence Found</h4>
                  <p>
                    The query system checked all verified report ground-truth records but found no matching evidence.
                    No unverified or hallucinated facts were returned.
                  </p>
                </div>
              )}

              {/* Section 1: Retrieved Evidence */}
              {retrievalResult.evidence.length > 0 && (
                <div className="retrieved-section">
                  <h3>Matching Evidence Ground-Truth ({retrievalResult.evidence.length})</h3>
                  <div className="evidence-mini-table">
                    {retrievalResult.evidence.map((ev) => (
                      <div key={ev.evidence_id} className="evidence-mini-row">
                        <span className="mini-type font-mono">{ev.evidence_type}</span>
                        <span className="mini-val font-mono">{ev.value}</span>
                        <span className="page-badge">Page {ev.source_page}</span>
                        <span className="confidence-pill conf-high">
                          {(ev.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Section 2: Retrieved Relationships */}
              {retrievalResult.relationships.length > 0 && (
                <div className="retrieved-section">
                  <h3>Derived Relationships ({retrievalResult.relationships.length})</h3>
                  <div className="table-wrapper">
                    <table className="entities-table">
                      <thead>
                        <tr>
                          <th>Source</th>
                          <th>Predicate</th>
                          <th>Target</th>
                          <th>Classification</th>
                          <th>Rule Explanation</th>
                        </tr>
                      </thead>
                      <tbody>
                        {retrievalResult.relationships.map((rel) => (
                          <tr key={rel.id}>
                            <td className="font-mono">{rel.source_value}</td>
                            <td><span className="predicate-badge">{rel.relationship_type}</span></td>
                            <td className="font-mono">{rel.target_value}</td>
                            <td>
                              <span className={`classification-badge ${rel.classification === 'FACT' ? 'badge-class-fact' : 'badge-class-inference'}`}>
                                {rel.classification}
                              </span>
                            </td>
                            <td className="text-small text-muted">{rel.explanation}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Section 3: Retrieved Findings */}
              {retrievalResult.findings.length > 0 && (
                <div className="retrieved-section">
                  <h3>Flagged Findings ({retrievalResult.findings.length})</h3>
                  <div className="findings-list">
                    {retrievalResult.findings.map((fnd) => (
                      <div key={fnd.id} className="finding-item-card" style={{ padding: '1rem' }}>
                        <div className="finding-title-row">
                          <span className="severity-badge severity-high">{fnd.severity}</span>
                          <h4 className="rule-title">{fnd.rule_name}</h4>
                        </div>
                        <p className="explanation-text">{fnd.explanation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Section 4: Timeline Entries */}
              {retrievalResult.timeline_entries.length > 0 && (
                <div className="retrieved-section">
                  <h3>Timeline Events ({retrievalResult.timeline_entries.length})</h3>
                  <div className="evidence-mini-table">
                    {retrievalResult.timeline_entries.map((tle, i) => (
                      <div key={i} className="evidence-mini-row">
                        <span className="font-mono text-small">{tle.timestamp}</span>
                        <span className="predicate-badge">{tle.event_type}</span>
                        <span className="mini-val">{tle.title}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Audit History Panel */}
        <div className="history-column">
          <QueryHistoryPanel
            history={history}
            onSelectQuestion={(q) => {
              setQuestionInput(q);
              handleQuerySubmit(q);
            }}
          />
        </div>
      </div>
    </div>
  );
};
