import React from 'react';
import { QueryHistoryItem } from '../api/query';

interface QueryHistoryPanelProps {
  history: QueryHistoryItem[];
  onSelectQuestion: (question: string) => void;
}

export const QueryHistoryPanel: React.FC<QueryHistoryPanelProps> = ({ history, onSelectQuestion }) => {
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
    <div className="card query-history-card">
      <div className="table-header-row">
        <h3>Investigator Query Audit History</h3>
        <span className="text-small text-muted">{history.length} Queries Logged</span>
      </div>

      {history.length === 0 ? (
        <div className="empty-state">No queries recorded yet for this report.</div>
      ) : (
        <div className="history-list">
          {history.map((item) => (
            <div
              key={item.log_id}
              className="history-item"
              onClick={() => onSelectQuestion(item.question)}
              title="Click to re-run this question"
            >
              <div className="history-item-header">
                <span className={`classification-badge ${getStatusBadgeClass(item.status)}`}>
                  {item.status}
                </span>
                <span className="method-tag">{item.intent}</span>
                <span className="font-mono text-small text-muted">{item.timestamp.slice(0, 19).replace('T', ' ')}</span>
              </div>
              <p className="history-question">"{item.question}"</p>
              <div className="history-footer">
                <span className="text-small text-muted">Retrieved Evidence: {item.evidence_count} items</span>
                <span className="font-mono text-small text-muted">{item.query_id}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
