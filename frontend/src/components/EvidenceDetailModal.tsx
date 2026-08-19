import React from 'react';
import { EvidenceItem } from '../api/evidence';

interface EvidenceDetailModalProps {
  evidence: EvidenceItem | null;
  onClose: () => void;
}

export const EvidenceDetailModal: React.FC<EvidenceDetailModalProps> = ({ evidence, onClose }) => {
  if (!evidence) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-block">
            <span className="modal-badge-id">{evidence.evidence_id}</span>
            <h3>Evidence Record & Provenance</h3>
          </div>
          <button className="btn-close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="modal-body">
          <div className="audit-notice">
            <span>🔒 Audit Notice: Viewing this evidence record generates an immutable access entry in the audit log.</span>
          </div>

          <div className="provenance-grid">
            <div className="prov-item">
              <span className="prov-label">Evidence Type</span>
              <span className="prov-val font-mono">{evidence.evidence_type}</span>
            </div>
            <div className="prov-item">
              <span className="prov-label">Confidence Score</span>
              <span className="prov-val">{(evidence.confidence * 100).toFixed(0)}%</span>
            </div>
            <div className="prov-item">
              <span className="prov-label">Extracted Value</span>
              <span className="prov-val font-mono highlight-val">{evidence.value}</span>
            </div>
            <div className="prov-item">
              <span className="prov-label">Normalized Value</span>
              <span className="prov-val font-mono">{evidence.normalized_value || '-'}</span>
            </div>
            <div className="prov-item">
              <span className="prov-label">Source Report</span>
              <span className="prov-val font-mono">{evidence.source_report}</span>
            </div>
            <div className="prov-item">
              <span className="prov-label">Source Page</span>
              <span className="prov-val">Page {evidence.source_page}</span>
            </div>
            <div className="prov-item">
              <span className="prov-label">Derived Entity ID</span>
              <span className="prov-val font-mono">{evidence.derived_from_entity_id || '-'}</span>
            </div>
            <div className="prov-item">
              <span className="prov-label">Created Timestamp</span>
              <span className="prov-val font-mono">{evidence.created_at}</span>
            </div>
          </div>

          <div className="json-container">
            <h4>Raw Provenance Details (JSON)</h4>
            <pre className="json-block">{JSON.stringify(evidence.provenance_detail, null, 2)}</pre>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            Close Inspection
          </button>
        </div>
      </div>
    </div>
  );
};
