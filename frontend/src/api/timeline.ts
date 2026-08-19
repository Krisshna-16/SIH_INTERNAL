import { apiClient } from './client';

export interface TimelineEntryItem {
  entry_id: string;
  timestamp: string;
  event_type: string;
  evidence_id: string | null;
  finding_id: string | null;
  title: string;
  related_values: string[];
  source_report: string;
  source_page: number;
  confidence: number;
  classification: string;
}

export interface TimelineResponse {
  report_id: string;
  total: number;
  page: number;
  page_size: number;
  items: TimelineEntryItem[];
}

export interface TimelineSummaryResponse {
  report_id: string;
  earliest_timestamp: string | null;
  latest_timestamp: string | null;
  total_entries: number;
  entries_by_type: Record<string, number>;
  has_timestamped_evidence: boolean;
}

export const fetchTimeline = async (
  reportId: string,
  startDate?: string,
  endDate?: string,
  evidenceType?: string,
  entityValue?: string,
  classification?: string,
  page: number = 1,
  pageSize: number = 50
): Promise<TimelineResponse> => {
  const params: Record<string, any> = { page, page_size: pageSize };
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  if (evidenceType && evidenceType !== 'ALL') params.evidence_type = evidenceType;
  if (entityValue && entityValue.trim()) params.entity_value = entityValue.trim();
  if (classification && classification !== 'ALL') params.classification = classification;

  const response = await apiClient.get<TimelineResponse>(`/api/v1/reports/${reportId}/timeline`, {
    params,
  });
  return response.data;
};

export const fetchEntityTimeline = async (
  reportId: string,
  entityValue: string,
  page: number = 1,
  pageSize: number = 50
): Promise<TimelineResponse> => {
  const response = await apiClient.get<TimelineResponse>(
    `/api/v1/reports/${reportId}/timeline/entities/${encodeURIComponent(entityValue)}`,
    {
      params: { page, page_size: pageSize },
    }
  );
  return response.data;
};

export const fetchTimelineSummary = async (reportId: string): Promise<TimelineSummaryResponse> => {
  const response = await apiClient.get<TimelineSummaryResponse>(`/api/v1/reports/${reportId}/timeline/summary`);
  return response.data;
};
