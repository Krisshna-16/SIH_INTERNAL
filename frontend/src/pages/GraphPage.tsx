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
  // Compute concentric alternating circular layout coordinates for SVG rendering
  const getLayoutPositions = (nodes: GraphNode[]) => {
    const positions: Record<string, { x: number; y: number }> = {};
    const count = nodes.length;
    const centerX = 425;
    const centerY = 230;

    nodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / (count || 1);
      // Alternate radius for odd and even nodes to distribute them into two concentric rings
      const radius = i % 2 === 0 ? 190 : 110;
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

          <div className="graph-canvas-relative-container" style={{ position: 'relative', minHeight: '480px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            {loading && !graphData && (
              <LoadingSpinner message="Building NetworkX graph structure..." />
            )}

            {loading && graphData && (
              <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                background: 'rgba(248, 250, 252, 0.85)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 10,
                borderRadius: 'var(--radius)'
              }}>
                <LoadingSpinner message="Updating graph network..." />
              </div>
            )}

            {!loading && (!graphData || graphData.nodes.length === 0) && (
              <EmptyState
                title="No Network Relationships Found"
                description={selectedReportId ? 'Try adjusting the min confidence slider or select ALL relationship types.' : 'Please select a report.'}
              />
            )}

            {graphData && graphData.nodes.length > 0 && (
              <div className="svg-canvas-wrapper" style={{ width: '100%', overflow: 'hidden', backgroundColor: '#f8fafc', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
                <svg width="100%" height="480" viewBox="0 0 850 480" className="graph-svg">
                  {/* Draw Edges */}
                  {graphData.edges.map((edge, i) => {
                    const sourcePos = nodePositions[edge.source];
                    const targetPos = nodePositions[edge.target];
                    if (!sourcePos || !targetPos) return null;

                    const isFact = edge.classification === 'FACT';
                    
                    // Alternate labels along the path (35%, 50%, 65%) to avoid center stacking overlaps
                    const ratio = i % 3 === 0 ? 0.35 : i % 3 === 1 ? 0.5 : 0.65;
                    const midX = sourcePos.x + (targetPos.x - sourcePos.x) * ratio;
                    const midY = sourcePos.y + (targetPos.y - sourcePos.y) * ratio;
                    
                    // Faint background capsule width based on label text length
                    const textWidth = edge.relationship_type.length * 6.5 + 8;

                    return (
                      <g key={edge.id} className="svg-edge-group" onClick={() => handleEdgeClick(edge)} style={{ cursor: 'pointer' }}>
                        <line
                          x1={sourcePos.x}
                          y1={sourcePos.y}
                          x2={targetPos.x}
                          y2={targetPos.y}
                          stroke={isFact ? '#38bdf8' : '#c084fc'}
                          strokeWidth={2}
                          strokeDasharray={isFact ? 'none' : '4,4'}
                          opacity={Math.max(edge.confidence, 0.45)}
                        />
                        {/* Background mask pill so intersecting lines don't clutter the text */}
                        <rect
                          x={midX - textWidth / 2}
                          y={midY - 8}
                          width={textWidth}
                          height={15}
                          fill="#f8fafc"
                          rx="3"
                        />
                        <text
                          x={midX}
                          y={midY + 3}
                          textAnchor="middle"
                          className="edge-text-label font-mono"
                          style={{ fontSize: '0.62rem', fill: '#0f172a', fontWeight: 700 }}
                        >
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
                        style={{ cursor: 'pointer' }}
                      >
                        <circle
                          r={isSelected ? 16 : 12}
                          fill={nodeColor}
                          stroke={isSelected ? '#2563eb' : '#0f172a'}
                          strokeWidth={isSelected ? 2.5 : 1.5}
                        />
                        {/* Center value below node and split type onto second line to save horizontal space */}
                        <text
                          y={24}
                          textAnchor="middle"
                          className="node-text-label font-mono"
                          style={{ fontSize: '0.68rem', fill: '#0f172a', fontWeight: 700 }}
                        >
                          {node.value}
                        </text>
                        <text
                          y={36}
                          textAnchor="middle"
                          className="node-text-label-sub font-mono"
                          style={{ fontSize: '0.58rem', fill: '#475569' }}
                        >
                          {node.evidence_type}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>
            )}
          </div>
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
