import { apiClient } from './client';

export interface EvidenceItem {
  evidence_id: string;
  report_id: string;
  evidence_type: string;
  value: string;
  normalized_value: string | null;
  timestamp: string | null;
  confidence: number;
  source_page: number;
  source_report: string;
  provenance_detail: Record<string, any>;
  derived_from_entity_id: string | null;
  created_at: string;
}

export interface EvidenceListResponse {
  report_id: string;
  total: number;
  page: number;
  page_size: number;
  items: EvidenceItem[];
}

export interface EvidenceSummaryResponse {
  report_id: string;
  filename: string;
  page_count: number;
  total_evidence: number;
  type_breakdown: Record<string, number>;
}

export interface ConsolidationResponse {
  report_id: string;
  total_evidence: number;
  evidence_counts: Record<string, number>;
}

export const consolidateEvidence = async (reportId: string): Promise<ConsolidationResponse> => {
  const response = await apiClient.post<ConsolidationResponse>(`/api/v1/reports/${reportId}/evidence/consolidate`);
  return response.data;
};

export const fetchReportEvidence = async (
  reportId: string,
  typeFilter?: string,
  minConfidence?: number,
  page: number = 1,
  pageSize: number = 50
): Promise<EvidenceListResponse> => {
  const params: Record<string, any> = { page, page_size: pageSize };
  if (typeFilter && typeFilter !== 'ALL') {
    params.evidence_type = typeFilter;
  }
  if (minConfidence !== undefined) {
    params.min_confidence = minConfidence;
  }

  const response = await apiClient.get<EvidenceListResponse>(`/api/v1/reports/${reportId}/evidence`, {
    params,
  });
  return response.data;
};

export const fetchEvidenceSummary = async (reportId: string): Promise<EvidenceSummaryResponse> => {
  const response = await apiClient.get<EvidenceSummaryResponse>(`/api/v1/reports/${reportId}/evidence/summary`);
  return response.data;
};

export const fetchEvidenceById = async (evidenceId: string): Promise<EvidenceItem> => {
  const response = await apiClient.get<EvidenceItem>(`/api/v1/evidence/${evidenceId}`);
  return response.data;
};
