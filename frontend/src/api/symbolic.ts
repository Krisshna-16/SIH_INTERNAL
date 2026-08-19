import { apiClient } from './client';

export interface RelationshipItem {
  id: string;
  report_id: string;
  source_evidence_id: string;
  source_value: string;
  source_type: string;
  target_evidence_id: string;
  target_value: string;
  target_type: string;
  relationship_type: string;
  classification: string;
  rule_id: string;
  explanation: string;
  confidence: number;
  created_at: string;
}

export interface RelationshipListResponse {
  report_id: string;
  total: number;
  page: number;
  page_size: number;
  items: RelationshipItem[];
}

export interface FindingItem {
  id: string;
  report_id: string;
  finding_type: string;
  classification: string;
  rule_id: string;
  rule_name: string;
  explanation: string;
  related_evidence_ids: string[];
  related_evidence?: Array<{
    evidence_id: string;
    evidence_type: string;
    value: string;
    normalized_value: string | null;
    source_page: number;
    source_report: string;
    confidence: number;
  }>;
  parameters_used: Record<string, any>;
  severity: string;
  created_at: string;
}

export interface FindingListResponse {
  report_id: string;
  total: number;
  page: number;
  page_size: number;
  items: FindingItem[];
}

export interface SymbolicAnalysisSummary {
  report_id: string;
  total_relationships: number;
  total_findings: number;
  relationship_types: Record<string, number>;
  finding_types: Record<string, number>;
  severities: Record<string, number>;
}

export const runSymbolicAnalysis = async (reportId: string): Promise<SymbolicAnalysisSummary> => {
  const response = await apiClient.post<SymbolicAnalysisSummary>(`/api/v1/reports/${reportId}/analyze`);
  return response.data;
};

export const fetchRelationships = async (
  reportId: string,
  relType?: string,
  classification?: string,
  page: number = 1,
  pageSize: number = 50
): Promise<RelationshipListResponse> => {
  const params: Record<string, any> = { page, page_size: pageSize };
  if (relType && relType !== 'ALL') {
    params.relationship_type = relType;
  }
  if (classification && classification !== 'ALL') {
    params.classification = classification;
  }

  const response = await apiClient.get<RelationshipListResponse>(`/api/v1/reports/${reportId}/relationships`, {
    params,
  });
  return response.data;
};

export const fetchFindings = async (
  reportId: string,
  findingType?: string,
  severity?: string,
  page: number = 1,
  pageSize: number = 50
): Promise<FindingListResponse> => {
  const params: Record<string, any> = { page, page_size: pageSize };
  if (findingType && findingType !== 'ALL') {
    params.finding_type = findingType;
  }
  if (severity && severity !== 'ALL') {
    params.severity = severity;
  }

  const response = await apiClient.get<FindingListResponse>(`/api/v1/reports/${reportId}/findings`, {
    params,
  });
  return response.data;
};

export const fetchFindingById = async (findingId: string): Promise<FindingItem> => {
  const response = await apiClient.get<FindingItem>(`/api/v1/findings/${findingId}`);
  return response.data;
};
