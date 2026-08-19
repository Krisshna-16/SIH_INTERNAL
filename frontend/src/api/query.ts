import { apiClient } from './client';

export interface QueryIntentItem {
  intent_type: string;
  confidence: number;
  matched_pattern: string | null;
}

export interface ResolvedEntityItem {
  mention_text: string;
  entity_type: string;
  matched: boolean;
  evidence_ids: string[];
  matched_values: string[];
  confidence: number;
}

export interface RetrievalResult {
  query_id: string;
  report_id: string;
  original_question: string;
  intent: QueryIntentItem;
  resolved_entities: ResolvedEntityItem[];
  evidence: any[];
  relationships: any[];
  findings: any[];
  timeline_entries: any[];
  graph_neighborhood: any | null;
  status: 'RESULTS_FOUND' | 'NO_EVIDENCE_FOUND' | 'ENTITY_NOT_RESOLVED';
  retrieval_summary: string;
}

export interface QueryHistoryItem {
  log_id: number;
  query_id: string;
  question: string;
  intent: string;
  status: string;
  evidence_count: number;
  timestamp: string;
}

export interface QueryHistoryResponse {
  report_id: string;
  total_queries: number;
  history: QueryHistoryItem[];
}

export const submitInvestigatorQuery = async (
  reportId: string,
  question: string
): Promise<RetrievalResult> => {
  const response = await apiClient.post<RetrievalResult>(`/api/v1/reports/${reportId}/query`, {
    question,
  });
  return response.data;
};

export const fetchQueryHistory = async (reportId: string): Promise<QueryHistoryResponse> => {
  const response = await apiClient.get<QueryHistoryResponse>(`/api/v1/reports/${reportId}/query/history`);
  return response.data;
};
