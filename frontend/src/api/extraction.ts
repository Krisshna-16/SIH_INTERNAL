import { apiClient } from './client';

export interface ReportItem {
  id: string;
  filename: string;
  status: string;
  page_count: number;
  created_at: string;
}

export interface ExtractionSummary {
  report_id: string;
  filename: string;
  total_entities: number;
  entity_counts: Record<string, number>;
  pages_processed: number;
  page_errors: number;
}

export interface EntityItem {
  id: string;
  report_id: string;
  type: string;
  value: string;
  normalized_value: string | null;
  confidence: number;
  source_page: number;
  source_report: string;
  extraction_method: string;
  created_at: string;
}

export interface EntityListResponse {
  report_id: string;
  total: number;
  page: number;
  limit: number;
  items: EntityItem[];
}

export const fetchReports = async (): Promise<ReportItem[]> => {
  const response = await apiClient.get<ReportItem[]>('/api/v1/reports');
  return response.data;
};

export const uploadReportFile = async (file: File): Promise<ReportItem> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.post<ReportItem>('/api/v1/reports/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const createSyntheticReport = async (
  filename: string,
  pages: { page_number: number; text_content: string }[]
): Promise<ReportItem> => {
  const response = await apiClient.post<ReportItem>('/api/v1/reports', {
    filename,
    pages,
  });
  return response.data;
};

export const runExtraction = async (reportId: string): Promise<ExtractionSummary> => {
  const response = await apiClient.post<ExtractionSummary>(`/api/v1/reports/${reportId}/extract`);
  return response.data;
};

export const fetchReportEntities = async (
  reportId: string,
  typeFilter?: string,
  minConfidence?: number
): Promise<EntityListResponse> => {
  const params: Record<string, any> = { limit: 100 };
  if (typeFilter && typeFilter !== 'ALL') {
    params.type = typeFilter;
  }
  if (minConfidence !== undefined) {
    params.min_confidence = minConfidence;
  }

  const response = await apiClient.get<EntityListResponse>(`/api/v1/reports/${reportId}/entities`, {
    params,
  });
  return response.data;
};
