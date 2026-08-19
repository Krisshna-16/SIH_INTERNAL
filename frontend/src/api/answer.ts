import { apiClient } from './client';

export interface CitationVerificationResultItem {
  all_citations_valid: boolean;
  cited_ids: string[];
  valid_citations: string[];
  invalid_citations: string[];
  uncited_claim_warning: boolean;
}

export interface InvestigatorAnswerResponse {
  query_id: string;
  report_id: string;
  question: string;
  answer_text: string;
  citations_used: string[];
  citation_verification: CitationVerificationResultItem;
  retrieval_status: string;
  evidence_references: any[];
  generated_by: 'local_llm' | 'external_llm' | 'template_fallback';
  model_name: string;
  external_llm_used: boolean;
  external_llm_provider: string | null;
  pseudonymized: boolean;
  fallback_used?: boolean;
  fallback_reason?: string | null;
  created_at: string;
}

export const submitInvestigatorAnswer = async (
  reportId: string,
  question: string,
  llmProvider: 'external' | 'local' | 'auto' = 'external'
): Promise<InvestigatorAnswerResponse> => {
  const response = await apiClient.post<InvestigatorAnswerResponse>(`/api/v1/reports/${reportId}/answer`, {
    question,
    llm_provider: llmProvider,
  });
  return response.data;
};
