import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { fetchReports, ReportItem } from '../api/extraction';
import {
  fetchReportGraph,
  fetchNodeNeighborhood,
  fetchEdgeExplanation,
  fetchGraphSummary,
  GraphData,
  GraphNode,
  GraphEdge,
  GraphSummaryResponse,
  EdgeExplanationResponse,
} from '../api/graph';
import { GraphFilterBar } from '../components/GraphFilterBar';
import { GraphLegend } from '../components/GraphLegend';
import { EmptyState } from '../components/EmptyState';
import { LoadingSpinner } from '../components/LoadingSpinner';

export const GraphPage: React.FC = () => {
  const { reportId: routeReportId } = useParams<{ reportId: string }>();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string>(routeReportId || '');
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [summary, setSummary] = useState<GraphSummaryResponse | null>(null);

  useEffect(() => {
    if (routeReportId) {
      setSelectedReportId(routeReportId);
    }
  }, [routeReportId]);

  // Filter state — Default to 0.80 min confidence for crisp, non-cluttered visualization
  const [minConfidence, setMinConfidence] = useState<number>(0.80);
  const [selectedRelType, setSelectedRelType] = useState<string>('ALL');
  const [expansionDepth, setExpansionDepth] = useState<number>(1);

  // Interaction state
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeExplanation, setSelectedEdgeExplanation] = useState<EdgeExplanationResponse | null>(null);
  const [isNeighborhoodView, setIsNeighborhoodView] = useState<boolean>(false);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

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

  const loadGraph = useCallback(async () => {
    if (!selectedReportId) return;
    setLoading(true);
    setError(null);
    setIsNeighborhoodView(false);
    setSelectedNodeId(null);
    setSelectedEdgeExplanation(null);

    try {
      const [gRes, sumRes] = await Promise.all([
        fetchReportGraph(selectedReportId, minConfidence, selectedRelType),
        fetchGraphSummary(selectedReportId),
      ]);
      setGraphData(gRes);
      setSummary(sumRes);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to build graph.');
    } finally {
      setLoading(false);
    }
  }, [selectedReportId, minConfidence, selectedRelType]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  const handleNodeClick = async (node: GraphNode) => {
    if (!selectedReportId) return;
    setSelectedNodeId(node.id);
    setSelectedEdgeExplanation(null);
    setLoading(true);
    try {
      const subGraph = await fetchNodeNeighborhood(selectedReportId, node.id, expansionDepth);
      setGraphData(subGraph);
      setIsNeighborhoodView(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Neighborhood expansion failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleEdgeClick = async (edge: GraphEdge) => {
    if (!selectedReportId || !edge.relationship_id) return;
    try {
      const exp = await fetchEdgeExplanation(selectedReportId, edge.relationship_id);
      setSelectedEdgeExplanation(exp);
    } catch (err: any) {
      console.error('Failed to load edge explanation:', err);
    }
  };

  const getNodeColor = (type: string) => {
    switch (type.toUpperCase()) {
      case 'PERSON':
        return '#38bdf8';
      case 'PHONE':
        return '#10b981';
      case 'EMAIL':
        return '#c084fc';
      case 'LOCATION':
        return '#f59e0b';
      case 'DATE':
        return '#818cf8';
      default:
        return '#64748b';
    }
  };

  // Compute circular layout coordinates for SVG rendering
  const getLayoutPositions = (nodes: GraphNode[]) => {
    const positions: Record<string, { x: number; y: number }> = {};
    const count = nodes.length;
    const centerX = 360;
    const centerY = 230;
    const radius = Math.min(centerX, centerY) - 50;

    nodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / (count || 1);
      positions[node.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    });

    return positions;
  };

  const nodePositions = graphData ? getLayoutPositions(graphData.nodes) : {};

  return (
    <div className="graph-page-container">
      <header className="page-header">
        <div className="header-title-block">
          <span className="phase-tag">Phase 6 | NetworkX Knowledge Graph</span>
          <h2>Knowledge Graph Explorer</h2>
          <p className="subtitle">
            Visual forensic graph exploration of evidence entities and derived relationships with complete rule provenance.
          </p>
        </div>
      </header>

      {/* Control Card */}
      <div className="card control-card">
        <div className="control-row">
          <div className="control-group">
            <label htmlFor="graph-main-report-select" className="font-mono">SELECT CASE REPORT:</label>
            <select
              id="graph-main-report-select"
              value={selectedReportId}
              onChange={(e) => setSelectedReportId(e.target.value)}
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

          {/* Clean Formatted Metrics Bar with Spaces */}
          {summary && (
            <div className="graph-stats-bar font-mono">
              <span className="graph-stat-pill">NODES: <strong className="text-cyan">{graphData?.nodes.length || 0}</strong></span>
              <span className="graph-stat-pill">EDGES: <strong className="text-blue">{graphData?.edges.length || 0}</strong></span>
              {summary.top_connected_nodes.length > 0 && (
                <span className="graph-stat-pill">
                  TOP HUB: <strong className="text-emerald">{summary.top_connected_nodes[0].value}</strong> ({summary.top_connected_nodes[0].connection_count} links)
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Filter Bar */}
      <GraphFilterBar
        minConfidence={minConfidence}
        selectedRelType={selectedRelType}
        expansionDepth={expansionDepth}
        onFilterChange={(filters) => {
          if (filters.minConfidence !== undefined) setMinConfidence(filters.minConfidence);
          if (filters.selectedRelType !== undefined) setSelectedRelType(filters.selectedRelType);
          if (filters.expansionDepth !== undefined) setExpansionDepth(filters.expansionDepth);
        }}
        onReset={() => {
          setMinConfidence(0.80);
          setSelectedRelType('ALL');
          setExpansionDepth(1);
          loadGraph();
        }}
      />

      <GraphLegend />

      {isNeighborhoodView && (
        <div className="card notice-card font-mono" style={{ padding: '0.75rem 1.25rem', marginBottom: '1.25rem' }}>
          <div className="control-row">
            <span>Viewing Neighborhood Subgraph for node: <strong className="text-cyan">{selectedNodeId}</strong> ({expansionDepth} Hop Expansion)</span>
            <button onClick={loadGraph} className="btn-secondary btn-sm font-mono">
              Reset Full Graph
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="card error-card">
          <h4>Graph Construction Notice</h4>
          <p>{error}</p>
        </div>
      )}

      {/* Main Canvas & Side Panel Container */}
      <div className="graph-layout-container">
        <div className="card graph-canvas-card">
          <div className="table-header-row">
            <h3>Interactive Knowledge Network Canvas</h3>
            <span className="text-small text-muted font-mono">Click node to expand neighborhood • Click edge to inspect explanation</span>
          </div>

          {loading ? (
            <LoadingSpinner message="Building NetworkX graph structure..." />
          ) : !graphData || graphData.nodes.length === 0 ? (
            <EmptyState
              icon="🕸️"
              title="No Network Relationships Found"
              description={selectedReportId ? 'Try adjusting the min confidence slider or select ALL relationship types.' : 'Please select a report.'}
            />
          ) : (
            <div className="svg-canvas-wrapper">
              <svg width="720" height="460" className="graph-svg">
                {/* Draw Edges */}
                {graphData.edges.map((edge) => {
                  const sourcePos = nodePositions[edge.source];
                  const targetPos = nodePositions[edge.target];
                  if (!sourcePos || !targetPos) return null;

                  const isFact = edge.classification === 'FACT';
                  const midX = (sourcePos.x + targetPos.x) / 2;
                  const midY = (sourcePos.y + targetPos.y) / 2;

                  return (
                    <g key={edge.id} className="svg-edge-group" onClick={() => handleEdgeClick(edge)}>
                      <line
                        x1={sourcePos.x}
                        y1={sourcePos.y}
                        x2={targetPos.x}
                        y2={targetPos.y}
                        stroke={isFact ? '#38bdf8' : '#c084fc'}
                        strokeWidth={2}
                        strokeDasharray={isFact ? 'none' : '5,5'}
                        opacity={Math.max(edge.confidence, 0.4)}
                      />
                      <text x={midX} y={midY - 4} className="edge-text-label font-mono">
                        {edge.relationship_type}
                      </text>
                    </g>
                  );
                })}

                {/* Draw Nodes */}
                {graphData.nodes.map((node) => {
                  const pos = nodePositions[node.id];
                  if (!pos) return null;
                  const isSelected = selectedNodeId === node.id;
                  const nodeColor = getNodeColor(node.evidence_type);

                  return (
                    <g
                      key={node.id}
                      className="svg-node-group"
                      onClick={() => handleNodeClick(node)}
                      transform={`translate(${pos.x}, ${pos.y})`}
                    >
                      <circle
                        r={isSelected ? 18 : 14}
                        fill={nodeColor}
                        stroke={isSelected ? '#ffffff' : '#0f172a'}
                        strokeWidth={isSelected ? 3 : 1.5}
                      />
                      <text y={28} className="node-text-label font-mono">
                        {node.value} ({node.evidence_type})
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>
          )}
        </div>

        {/* Edge Explanation Side Panel */}
        {selectedEdgeExplanation && (
          <div className="card edge-side-panel">
            <div className="modal-header">
              <h3>Rule Explanation Drill-Down</h3>
              <button className="btn-close" onClick={() => setSelectedEdgeExplanation(null)}>
                ✕
              </button>
            </div>
            <div className="panel-body">
              <div className="panel-row">
                <span className="panel-label font-mono">Relationship:</span>
                <span className="predicate-badge font-mono">{selectedEdgeExplanation.relationship_type}</span>
              </div>
              <div className="panel-row">
                <span className="panel-label font-mono">Classification:</span>
                <span className={`classification-badge ${selectedEdgeExplanation.classification === 'FACT' ? 'badge-class-fact' : 'badge-class-inference'}`}>
                  {selectedEdgeExplanation.classification}
                </span>
              </div>
              <div className="panel-row">
                <span className="panel-label font-mono">Rule ID:</span>
                <span className="method-tag font-mono">{selectedEdgeExplanation.rule_id}</span>
              </div>

              <div className="panel-section">
                <h4>Human-Readable Explanation</h4>
                <p className="explanation-text">{selectedEdgeExplanation.explanation}</p>
              </div>

              <div className="panel-section">
                <h4>Ground-Truth Entities Involved</h4>
                <div className="mini-entity-box font-mono">
                  <div><strong>Source:</strong> {selectedEdgeExplanation.source_value} ({selectedEdgeExplanation.source_type})</div>
                  <div><strong>Target:</strong> {selectedEdgeExplanation.target_value} ({selectedEdgeExplanation.target_type})</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
