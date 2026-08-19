import { apiClient } from './client';

export interface GraphNode {
  id: string;
  evidence_id: string;
  evidence_type: string;
  value: string;
  normalized_value: string | null;
  confidence: number;
  source_page: number;
  source_report: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship_id: string;
  relationship_type: string;
  classification: string;
  rule_id: string;
  explanation: string;
  confidence: number;
}

export interface GraphData {
  report_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  target_evidence_id?: string;
  depth?: number;
}

export interface GraphSummaryResponse {
  report_id: string;
  node_count: number;
  edge_count: number;
  relationship_types: Record<string, number>;
  classifications: Record<string, number>;
  top_connected_nodes: Array<{
    evidence_id: string;
    value: string;
    evidence_type: string;
    degree_centrality: number;
    connection_count: number;
  }>;
  metric_type: string;
}

export interface EdgeExplanationResponse {
  relationship_id: string;
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

export const fetchReportGraph = async (
  reportId: string,
  minConfidence?: number,
  relationshipType?: string
): Promise<GraphData> => {
  const params: Record<string, any> = {};
  if (minConfidence !== undefined && minConfidence > 0) {
    params.min_confidence = minConfidence;
  }
  if (relationshipType && relationshipType !== 'ALL') {
    params.relationship_type = relationshipType;
  }

  const response = await apiClient.get<GraphData>(`/api/v1/reports/${reportId}/graph`, {
    params,
  });
  return response.data;
};

export const fetchNodeNeighborhood = async (
  reportId: string,
  evidenceId: string,
  depth: number = 1
): Promise<GraphData> => {
  const response = await apiClient.get<GraphData>(
    `/api/v1/reports/${reportId}/graph/nodes/${encodeURIComponent(evidenceId)}/neighborhood`,
    {
      params: { depth },
    }
  );
  return response.data;
};

export const fetchEdgeExplanation = async (
  reportId: string,
  relationshipId: string
): Promise<EdgeExplanationResponse> => {
  const response = await apiClient.get<EdgeExplanationResponse>(
    `/api/v1/reports/${reportId}/graph/edges/${encodeURIComponent(relationshipId)}/explanation`
  );
  return response.data;
};

export const fetchGraphSummary = async (reportId: string): Promise<GraphSummaryResponse> => {
  const response = await apiClient.get<GraphSummaryResponse>(`/api/v1/reports/${reportId}/graph/summary`);
  return response.data;
};
