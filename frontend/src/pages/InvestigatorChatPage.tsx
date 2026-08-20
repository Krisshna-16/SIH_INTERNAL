import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { fetchReports, ReportItem } from '../api/extraction';
import { submitInvestigatorAnswer, InvestigatorAnswerResponse } from '../api/answer';
import { EvidenceDetailModal } from '../components/EvidenceDetailModal';
import { fetchEvidenceById, EvidenceItem } from '../api/evidence';
import { LoadingSpinner } from '../components/LoadingSpinner';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  question: string;
  answerResponse?: InvestigatorAnswerResponse;
  timestamp: string;
}

export const InvestigatorChatPage: React.FC = () => {
  const { reportId: routeReportId } = useParams<{ reportId: string }>();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string>(routeReportId || '');
  const [questionInput, setQuestionInput] = useState<string>('');
  const [llmProvider, setLlmProvider] = useState<'external' | 'local' | 'auto'>('external');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (routeReportId) {
      setSelectedReportId(routeReportId);
    }
  }, [routeReportId]);

  // Modal detail inspection
  const [selectedEvDetail, setSelectedEvDetail] = useState<EvidenceItem | null>(null);

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

  // Auto-scroll to bottom of chat thread on new message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, loading]);

  const handleAskQuestion = async (qText?: string) => {
    const qToRun = qText || questionInput;
    if (!selectedReportId || !qToRun.trim()) return;

    const userMsgId = `MSG-U-${Date.now()}`;
    const userMsg: ChatMessage = {
      id: userMsgId,
      sender: 'user',
      question: qToRun.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setChatMessages((prev) => [...prev, userMsg]);
    setQuestionInput('');
    setLoading(true);
    setError(null);

    try {
      const res = await submitInvestigatorAnswer(selectedReportId, qToRun.trim(), llmProvider);
      const aiMsg: ChatMessage = {
        id: `MSG-AI-${Date.now()}`,
        sender: 'assistant',
        question: qToRun.trim(),
        answerResponse: res,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setChatMessages((prev) => [...prev, aiMsg]);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'LLM answer generation failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleCitationClick = async (citationId: string) => {
    if (citationId.startsWith('EVT-')) {
      try {
        const ev = await fetchEvidenceById(citationId);
        setSelectedEvDetail(ev);
      } catch (err) {
        console.error('Failed to load citation evidence:', err);
      }
    }
  };

  // Helper to render inline clickable citation badges
  const renderFormattedAnswer = (text: string) => {
    const parts = text.split(/(\[(?:EVT|REL|FND|TLE)-[A-Za-z0-9-]+\])/g);
    return parts.map((part, idx) => {
      const match = part.match(/^\[((?:EVT|REL|FND|TLE)-[A-Za-z0-9-]+)\]$/);
      if (match) {
        const cid = match[1];
        return (
          <button
            key={idx}
            className="citation-badge-btn font-mono"
            onClick={() => handleCitationClick(cid)}
            title={`Click to view ground-truth evidence source: ${cid}`}
          >
            [{cid}]
          </button>
        );
      }
      return part;
    });
  };

  return (
    <div className="chat-page-container">
      {/* Header */}
      <header className="page-header">
        <div className="header-title-block">
          <span className="phase-tag">Phase 8 / 9 | Grounded LLM & Privacy Gateway</span>
          <h2>TRACE-X Co-Analyst Conversation</h2>
          <p className="subtitle">
            Grounded natural-language answer generation with mandatory pseudonymization & opt-in external AI controls.
          </p>
        </div>
      </header>

      {/* Control Bar */}
      <div className="card control-card">
        <div className="control-row">
          <div className="control-group">
            <label htmlFor="chat-main-report-select" className="font-mono">SELECT CASE REPORT:</label>
            <select
              id="chat-main-report-select"
              value={selectedReportId}
              onChange={(e) => {
                setSelectedReportId(e.target.value);
                setChatMessages([]);
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

          {/* Provider Selection Buttons & Privacy Status */}
          <div className="graph-stats-bar font-mono">
            <span className="graph-stat-pill">Privacy: 🔒 <strong className="text-cyan">Pseudonymized</strong></span>
            
            <div className="provider-selector-group">
              <label className="font-mono text-small text-muted" style={{ marginRight: '0.4rem' }}>MODEL:</label>
              <select
                value={llmProvider}
                onChange={(e) => setLlmProvider(e.target.value as any)}
                className="select-report font-mono"
                style={{ minWidth: '220px', padding: '0.35rem 0.6rem', fontSize: '0.78rem' }}
              >
                <option value="external">⚡ External AI (Groq, Fast Default)</option>
                <option value="auto">🔄 Auto (Groq + Local Fallback)</option>
                <option value="local">💻 Local AI (Ollama, Air-Gapped)</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="card error-card">
          <h4>AI Assistant Notice</h4>
          <p>{error}</p>
        </div>
      )}

      {/* Main Conversational Thread Window */}
      <div className="card chat-thread-card">
        <div className="table-header-row">
          <h3>Interactive Conversational Thread</h3>
          <span className="text-small text-muted font-mono">{chatMessages.length} Messages</span>
        </div>

        <div className="chat-messages-container">
          {chatMessages.length === 0 ? (
            <div className="chat-welcome-placeholder font-mono">
              <h4>Investigator TRACE-X Co-Analyst Ready</h4>
              <p>Ask any question below or click a quick prompt to analyze grounded evidence records with zero-trust privacy protection.</p>
            </div>
          ) : (
            <div className="chat-thread-list">
              {chatMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`chat-bubble-wrapper ${msg.sender === 'user' ? 'bubble-user-row' : 'bubble-ai-row'}`}
                >
                  {msg.sender === 'user' ? (
                    <div className="chat-bubble-user">
                      <div className="bubble-header-bar font-mono">
                        <span className="user-sender-label">👤 Investigator</span>
                        <span className="bubble-time-tag">{msg.timestamp}</span>
                      </div>
                      <p className="bubble-message-text">{msg.question}</p>
                    </div>
                  ) : (
                    <div className="chat-card-ai">
                      <div className="ai-card-header">
                        <div className="ai-header-meta font-mono">
                          <span className="ai-avatar-icon">
                            {msg.answerResponse?.external_llm_used ? '⚡' : '🤖'}
                          </span>
                          <span className="ai-sender-label">
                            {msg.answerResponse?.external_llm_used ? 'Groq AI Model' : 'Local AI Assistant'}
                          </span>
                          <span className="ai-model-tag">{msg.answerResponse?.model_name || 'local_grounded_engine'}</span>
                          <span className="privacy-badge-pill">🔒 Identity Pseudonymized</span>
                        </div>
                        <span className="bubble-time-tag font-mono">{msg.timestamp}</span>
                      </div>

                      {/* Visible Fallback Warning if fallback occurred */}
                      {msg.answerResponse?.fallback_used && (
                        <div className="fallback-notice-banner font-mono">
                          ⚠️ <strong>Groq was unavailable</strong> — this answer was generated locally instead.
                          {msg.answerResponse.fallback_reason && <span className="text-small"> ({msg.answerResponse.fallback_reason})</span>}
                        </div>
                      )}

                      <div className="ai-card-body">
                        <div className="ai-response-text">
                          {renderFormattedAnswer(msg.answerResponse?.answer_text || '')}
                        </div>

                        {/* Verified Ground-Truth Evidence Sources */}
                        {msg.answerResponse?.evidence_references && msg.answerResponse.evidence_references.length > 0 && (
                          <div className="evidence-sources-box">
                            <span className="sources-title font-mono">VERIFIED GROUND-TRUTH CITATIONS:</span>
                            <div className="sources-chips-grid font-mono">
                              {msg.answerResponse.evidence_references.map((ref, idx) => (
                                <button
                                  key={idx}
                                  className="source-citation-chip"
                                  onClick={() => handleCitationClick(ref.evidence_id || ref.id)}
                                >
                                  <span className="src-id">[{ref.evidence_id || ref.id}]</span>
                                  <span className="src-val">{ref.value || ref.relationship_type || ref.rule_name}</span>
                                  {ref.source_page && <span className="src-page">Page {ref.source_page}</span>}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="chat-bubble-wrapper bubble-ai-row">
                  <div className="chat-card-ai ai-loading-box font-mono">
                    <LoadingSpinner message={llmProvider === 'local' ? 'Local LLM generating grounded answer (may take up to a minute)...' : 'Thinking...'} />
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
          )}
        </div>

        {/* Input Box Section */}
        <div className="chat-input-box-container">
          <div className="chat-textarea-wrapper">
            <textarea
              rows={3}
              placeholder="Type your question for the AI Assistant (e.g. 'Who did Inspector Vikram contact on 12 March 2024?')..."
              value={questionInput}
              onChange={(e) => setQuestionInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleAskQuestion();
                }
              }}
              className="chat-input-textarea font-mono"
            />
            <div className="chat-submit-row">
              <span className="chat-hint-text font-mono">Press Enter to send • Shift+Enter for new line</span>
              <button
                onClick={() => handleAskQuestion()}
                disabled={!selectedReportId || !questionInput.trim() || loading}
                className="btn-cyber-primary"
              >
                <span>{loading ? 'ANALYZING...' : 'ASK TRACE-X'}</span>
              </button>
            </div>
          </div>

          {/* Quick Sample Prompts */}
          <div className="chat-quick-prompts-bar">
            <span className="prompt-bar-label font-mono">QUICK PROMPTS:</span>
            <div className="prompt-chips-wrapper">
              <button
                className="quick-prompt-btn font-mono"
                onClick={() => handleAskQuestion('Who did Inspector Vikram contact?')}
              >
                "Who did Inspector Vikram contact?"
              </button>
              <button
                className="quick-prompt-btn font-mono"
                onClick={() => handleAskQuestion('What happened on 12 March 2024?')}
              >
                "What happened on 12 March 2024?"
              </button>
              <button
                className="quick-prompt-btn font-mono"
                onClick={() => handleAskQuestion('What suspicious activity was flagged?')}
              >
                "What suspicious activity was flagged?"
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Evidence Detail Modal */}
      {selectedEvDetail && (
        <EvidenceDetailModal
          evidence={selectedEvDetail}
          onClose={() => setSelectedEvDetail(null)}
        />
      )}
    </div>
  );
};
