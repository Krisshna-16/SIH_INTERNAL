import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchReports, runExtraction, ReportItem } from '../api/extraction';
import { consolidateEvidence, fetchEvidenceSummary, EvidenceSummaryResponse } from '../api/evidence';
import { runSymbolicAnalysis, SymbolicAnalysisSummary } from '../api/symbolic';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { EmptyState } from '../components/EmptyState';

type PipelineStep = 'idle' | 'running' | 'done' | 'error';

interface StepState {
  extract: PipelineStep;
  consolidate: PipelineStep;
  analyze: PipelineStep;
  extractMsg: string;
  consolidateMsg: string;
  analyzeMsg: string;
}

export const ReportDashboardPage: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<ReportItem | null>(null);
  const [summary, setSummary] = useState<EvidenceSummaryResponse | null>(null);
  const [symbolicSummary, setSymbolicSummary] = useState<SymbolicAnalysisSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [pipeline, setPipeline] = useState<StepState>({
    extract: 'idle',
    consolidate: 'idle',
    analyze: 'idle',
    extractMsg: '',
    consolidateMsg: '',
    analyzeMsg: '',
  });

  const loadData = useCallback(async () => {
    if (!reportId) return;
    setLoading(true);
    try {
      const reports = await fetchReports();
      const match = reports.find((r) => r.id === reportId);
      setReport(match || null);

      try {
        setSummary(await fetchEvidenceSummary(reportId));
      } catch {
        setSummary(null);
      }

      try {
        const { fetchRelationships, fetchFindings } = await import('../api/symbolic');
        const [rels, fnds] = await Promise.all([
          fetchRelationships(reportId, undefined, undefined, 1, 1),
          fetchFindings(reportId, undefined, undefined, 1, 1),
        ]);
        setSymbolicSummary({
          report_id: reportId,
          total_relationships: rels.total,
          total_findings: fnds.total,
          relationship_types: {},
          finding_types: {},
          severities: {},
        });
      } catch {
        setSymbolicSummary(null);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [reportId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const runFullPipeline = async () => {
    if (!reportId) return;

    // Confirmation dialog safeguard if pipeline has already been run
    if (pipeline.analyze === 'done' || report?.status === 'analyzed') {
      const confirmReRun = window.confirm("Pipeline has already been executed for this report. Are you sure you want to re-run?");
      if (!confirmReRun) return;
    }

    setPipeline({
      extract: 'running',
      consolidate: 'idle',
      analyze: 'idle',
      extractMsg: 'Initializing spaCy NER NLP Models...',
      consolidateMsg: '',
      analyzeMsg: '',
    });

    try {
      const extPromise = runExtraction(reportId);
      await new Promise((r) => setTimeout(r, 1200));
      setPipeline((p) => ({ ...p, extractMsg: 'Parsing UFDR Pages & Character Offsets...' }));
      await new Promise((r) => setTimeout(r, 1300));
      const ext = await extPromise;

      setPipeline((p) => ({
        ...p,
        extract: 'done',
        extractMsg: `✓ ${ext.total_entities} entities indexed`,
        consolidate: 'running',
        consolidateMsg: 'Building Ground-Truth Canonical Vault...',
      }));
    } catch (e: any) {
      setPipeline((p) => ({ ...p, extract: 'error', extractMsg: e?.response?.data?.detail || 'Extraction failed' }));
      return;
    }

    try {
      const consPromise = consolidateEvidence(reportId);
      await new Promise((r) => setTimeout(r, 1500));
      const cons = await consPromise;

      setPipeline((p) => ({
        ...p,
        consolidate: 'done',
        consolidateMsg: `✓ ${cons.total_evidence} evidence records`,
        analyze: 'running',
        analyzeMsg: 'Evaluating Symbolic Correlation Rules...',
      }));
    } catch (e: any) {
      setPipeline((p) => ({ ...p, consolidate: 'error', consolidateMsg: e?.response?.data?.detail || 'Consolidation failed' }));
      return;
    }

    try {
      const symPromise = runSymbolicAnalysis(reportId);
      await new Promise((r) => setTimeout(r, 1200));
      setPipeline((p) => ({ ...p, analyzeMsg: 'Detecting Anomaly Bursts & Fact Triplets...' }));
      await new Promise((r) => setTimeout(r, 1300));
      const sym = await symPromise;

      setPipeline((p) => ({
        ...p,
        analyze: 'done',
        analyzeMsg: `✓ ${sym.total_relationships} relations, ${sym.total_findings} findings`,
      }));
      await loadData();
    } catch (e: any) {
      setPipeline((p) => ({ ...p, analyze: 'error', analyzeMsg: e?.response?.data?.detail || 'Analysis failed' }));
      await loadData();
    }
  };

  const getCategoryIcon = (cat: string) => {
    switch (cat.toUpperCase()) {
      case 'PERSON': return '👤';
      case 'PHONE': return '📱';
      case 'EMAIL': return '✉️';
      case 'LOCATION': return '📍';
      case 'DATE': return '📅';
      case 'URL': return '🌐';
      case 'IP_ADDRESS': return '💻';
      case 'ORG': return '🏢';
      default: return '📄';
    }
  };

  const stepIcon = (s: PipelineStep) => (s === 'done' ? '✓' : s === 'error' ? '✗' : s === 'running' ? '⏳' : '○');

  if (loading) return <LoadingSpinner message="Initializing Mission Control metrics..." />;
  if (!report) return <EmptyState icon="❌" title="Report not found" description={`No case report with ID "${reportId}" exists.`} />;

  const isRunning = pipeline.extract === 'running' || pipeline.consolidate === 'running' || pipeline.analyze === 'running';

  return (
    <div className="dashboard-page">
      {/* Page Title & Mission Control Header */}
      <div className="dash-header-row">
        <div>
          <span className="phase-tag">FORENSIC INTELLIGENCE // PHASE 10 DASHBOARD</span>
          <h1 className="dash-title">Mission Control Dashboard</h1>
          <p className="subtitle">
            Unified forensic summary and active pipeline orchestrator for <strong className="text-cyan">{report.filename}</strong>
          </p>
        </div>

        <div className="dash-action-group">
          <button
            className="btn-cyber-primary"
            onClick={runFullPipeline}
            disabled={isRunning}
          >
            <span className="btn-icon">⚡</span>
            <span>{isRunning ? 'EXECUTING PIPELINE (6s)...' : 'EXECUTE FULL PIPELINE'}</span>
          </button>
        </div>
      </div>

      {/* Animated Pipeline Stage Tracker */}
      <div className="card pipeline-card">
        <div className="pipeline-header">
          <div className="pipeline-title-block">
            <span className="pipeline-badge font-mono">AUTOMATED PIPELINE</span>
            <h3>Forensic Processing Engine</h3>
          </div>
          <span className="text-small text-muted font-mono">STATUS: {report.status.toUpperCase()}</span>
        </div>

        <div className="pipeline-steps-grid">
          <div className={`pipeline-step-box step-${pipeline.extract}`}>
            <div className="step-header">
              <span className="step-num font-mono">01</span>
              <span className="step-name">NER Extraction</span>
              <span className="step-status-icon">{stepIcon(pipeline.extract)}</span>
            </div>
            <p className="step-desc">{pipeline.extractMsg || 'spaCy NLP entity recognition'}</p>
          </div>

          <div className={`pipeline-step-box step-${pipeline.consolidate}`}>
            <div className="step-header">
              <span className="step-num font-mono">02</span>
              <span className="step-name">Evidence Consolidation</span>
              <span className="step-status-icon">{stepIcon(pipeline.consolidate)}</span>
            </div>
            <p className="step-desc">{pipeline.consolidateMsg || 'Ground-truth evidence indexing'}</p>
          </div>

          <div className={`pipeline-step-box step-${pipeline.analyze}`}>
            <div className="step-header">
              <span className="step-num font-mono">03</span>
              <span className="step-name">Symbolic Analysis</span>
              <span className="step-status-icon">{stepIcon(pipeline.analyze)}</span>
            </div>
            <p className="step-desc">{pipeline.analyzeMsg || 'Anomaly & correlation rule evaluation'}</p>
          </div>
        </div>
      </div>

      {/* Key Metric Cards Bar */}
      <div className="metrics-grid">
        <div className="metric-card card-cyan" onClick={() => navigate(`/reports/${reportId}/evidence`)}>
          <div className="metric-header">
            <span className="metric-lbl">EVIDENCE RECORDS</span>
            <span className="metric-icon">🔍</span>
          </div>
          <span className="metric-val font-mono">{summary?.total_evidence ?? 0}</span>
          <span className="metric-sub font-mono">Indexed Ground-Truth</span>
        </div>

        <div className="metric-card card-blue">
          <div className="metric-header">
            <span className="metric-lbl">SOURCE PAGES</span>
            <span className="metric-icon">📄</span>
          </div>
          <span className="metric-val font-mono">{summary?.page_count ?? report.page_count}</span>
          <span className="metric-sub font-mono">UFDR Parsed Pages</span>
        </div>

        <div className="metric-card card-purple">
          <div className="metric-header">
            <span className="metric-lbl">EVIDENCE CATEGORIES</span>
            <span className="metric-icon">🧬</span>
          </div>
          <span className="metric-val font-mono">{summary ? Object.keys(summary.type_breakdown).length : 0}</span>
          <span className="metric-sub font-mono">Entity Types</span>
        </div>

        <div className="metric-card card-emerald" onClick={() => navigate(`/reports/${reportId}/relationships`)}>
          <div className="metric-header">
            <span className="metric-lbl">RELATIONSHIPS</span>
            <span className="metric-icon">🔗</span>
          </div>
          <span className="metric-val font-mono">{symbolicSummary?.total_relationships ?? 0}</span>
          <span className="metric-sub font-mono">Derived Triplets</span>
        </div>

        <div className="metric-card card-rose" onClick={() => navigate(`/reports/${reportId}/findings`)}>
          <div className="metric-header">
            <span className="metric-lbl">FLAGGED FINDINGS</span>
            <span className="metric-icon">🚩</span>
          </div>
          <span className="metric-val font-mono">{symbolicSummary?.total_findings ?? 0}</span>
          <span className="metric-sub font-mono">Rule Anomalies</span>
        </div>
      </div>

      {/* Two Column Main Content Grid */}
      <div className="dashboard-main-grid">
        {/* Left Main Column (2/3 width) */}
        <div className="dash-left-col">
          {/* Evidence Category Distribution Breakdown */}
          <div className="card category-breakdown-card">
            <div className="card-header-bar">
              <div className="ch-title">
                <h3>Evidence Category Distribution</h3>
                <span className="text-small text-muted font-mono">Ground-Truth Breakdown</span>
              </div>
              <button className="btn-text-action" onClick={() => navigate(`/reports/${reportId}/evidence`)}>
                Explore Vault →
              </button>
            </div>

            {summary && Object.keys(summary.type_breakdown).length > 0 ? (
              <div className="category-items-grid">
                {Object.entries(summary.type_breakdown).map(([type, count]) => {
                  const percentage = summary.total_evidence > 0 ? ((count / summary.total_evidence) * 100).toFixed(1) : '0';
                  return (
                    <div key={type} className="cat-item-card">
                      <div className="cat-item-header">
                        <span className="cat-icon">{getCategoryIcon(type)}</span>
                        <span className="cat-name font-mono">{type}</span>
                        <span className="cat-count-badge font-mono">{count}</span>
                      </div>

                      <div className="cat-progress-track">
                        <div className="cat-progress-bar" style={{ width: `${percentage}%` }} />
                      </div>

                      <div className="cat-item-footer font-mono">
                        <span>{percentage}% of total</span>
                        <span className="text-muted">EVT-{type}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="empty-state-padding">
                <p className="text-muted">No evidence records indexed yet. Execute full pipeline above to process.</p>
              </div>
            )}
          </div>

          {/* Quick Access Intelligence Modules */}
          <div className="quick-modules-grid">
            <div className="quick-module-card" onClick={() => navigate(`/reports/${reportId}/entities`)}>
              <div className="qm-header">
                <span className="qm-icon">🧬</span>
                <span className="qm-phase font-mono">PHASE 2</span>
              </div>
              <h4>Neural Entity Index</h4>
              <p>spaCy NLP entity recognition with character-offset provenance.</p>
              <span className="qm-link font-mono">View Entities →</span>
            </div>

            <div className="quick-module-card" onClick={() => navigate(`/reports/${reportId}/timeline`)}>
              <div className="qm-header">
                <span className="qm-icon">📅</span>
                <span className="qm-phase font-mono">PHASE 5</span>
              </div>
              <h4>Timeline Stream</h4>
              <p>Chronological event progression with time-window filtering.</p>
              <span className="qm-link font-mono">View Timeline →</span>
            </div>

            <div className="quick-module-card" onClick={() => navigate(`/reports/${reportId}/graph`)}>
              <div className="qm-header">
                <span className="qm-icon">🕸️</span>
                <span className="qm-phase font-mono">PHASE 6</span>
              </div>
              <h4>Knowledge Graph</h4>
              <p>Interactive entity node-edge network with neighborhood expansion.</p>
              <span className="qm-link font-mono">View Graph →</span>
            </div>

            <div className="quick-module-card" onClick={() => navigate(`/reports/${reportId}/chat`)}>
              <div className="qm-header">
                <span className="qm-icon">💬</span>
                <span className="qm-phase font-mono">PHASE 8/9</span>
              </div>
              <h4>AI Co-Analyst</h4>
              <p>Grounded Q&A assistant with mandatory identity pseudonymization.</p>
              <span className="qm-link font-mono">Launch Assistant →</span>
            </div>
          </div>
        </div>

        {/* Right Column - Intelligence Dock (1/3 width) */}
        <div className="dash-right-col">
          {/* Executive Case Info Panel */}
          <div className="card intel-panel-card">
            <div className="intel-panel-header">
              <span className="intel-icon">⚡</span>
              <h3>Executive Insights</h3>
            </div>
            <div className="intel-body">
              <div className="intel-row">
                <span className="intel-lbl font-mono">CASE ID</span>
                <span className="intel-val font-mono">{report.id}</span>
              </div>
              <div className="intel-row">
                <span className="intel-lbl font-mono">FILE SOURCE</span>
                <span className="intel-val font-mono">{report.filename}</span>
              </div>
              <div className="intel-row">
                <span className="intel-lbl font-mono">TOTAL PAGES</span>
                <span className="intel-val font-mono">{report.page_count} Pages</span>
              </div>
              <div className="intel-row">
                <span className="intel-lbl font-mono">PIPELINE STATE</span>
                <span className={`status-pill status-${report.status}`}>{report.status}</span>
              </div>
            </div>
          </div>

          {/* Privacy & Security Status Stream */}
          <div className="card intel-panel-card">
            <div className="intel-panel-header">
              <span className="intel-icon">🔒</span>
              <h3>Privacy & Compliance Stream</h3>
            </div>
            <div className="privacy-stream-list">
              <div className="stream-item">
                <span className="stream-dot dot-green" />
                <div className="stream-content">
                  <span className="stream-title">Ground-Truth Storage Locked</span>
                  <span className="stream-sub font-mono">Local SQLite Database</span>
                </div>
              </div>

              <div className="stream-item">
                <span className="stream-dot dot-cyan" />
                <div className="stream-content">
                  <span className="stream-title">Identity Pseudonymization Active</span>
                  <span className="stream-sub font-mono">Deterministic Token Mapping</span>
                </div>
              </div>

              <div className="stream-item">
                <span className="stream-dot dot-purple" />
                <div className="stream-content">
                  <span className="stream-title">Grounded LLM Prompting</span>
                  <span className="stream-sub font-mono">Ollama local-by-default</span>
                </div>
              </div>
            </div>

            <div className="panel-footer">
              <button className="btn-secondary btn-block btn-sm font-mono" onClick={() => navigate(`/reports/${reportId}/privacy`)}>
                View Audit Trail →
              </button>
            </div>
          </div>

          {/* Prepared AI Assistant Quick Prompts */}
          <div className="card intel-panel-card">
            <div className="intel-panel-header">
              <span className="intel-icon">💬</span>
              <h3>Quick AI Prompts</h3>
            </div>
            <div className="quick-prompts-list">
              <button
                className="prompt-launch-btn"
                onClick={() => navigate(`/reports/${reportId}/chat`)}
              >
                <span>"Who did Inspector Vikram contact?"</span>
                <span className="prompt-arrow">→</span>
              </button>
              <button
                className="prompt-launch-btn"
                onClick={() => navigate(`/reports/${reportId}/chat`)}
              >
                <span>"What happened on 12 March 2024?"</span>
                <span className="prompt-arrow">→</span>
              </button>
              <button
                className="prompt-launch-btn"
                onClick={() => navigate(`/reports/${reportId}/chat`)}
              >
                <span>"Summarize suspicious communication patterns"</span>
                <span className="prompt-arrow">→</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
