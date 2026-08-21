import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react';
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

  // Filter state — Default to 0.80 min confidence
  const [minConfidence, setMinConfidence] = useState<number>(0.80);
  const [selectedRelType, setSelectedRelType] = useState<string>('ALL');
  const [expansionDepth, setExpansionDepth] = useState<number>(1);

  // Interaction & View state
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeExplanation, setSelectedEdgeExplanation] = useState<EdgeExplanationResponse | null>(null);
  const [isNeighborhoodView, setIsNeighborhoodView] = useState<boolean>(false);

  // Zoom & Pan Canvas State
  const [zoomScale, setZoomScale] = useState<number>(1.0);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

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
    setZoomScale(1.0);
    setPanOffset({ x: 0, y: 0 });

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

  const handleNodeClick = async (node: GraphNode, e: React.MouseEvent) => {
    e.stopPropagation();
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

  const handleEdgeClick = async (edge: GraphEdge, e: React.MouseEvent) => {
    e.stopPropagation();
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
        return '#38bdf8'; // Cyan
      case 'PHONE':
        return '#10b981'; // Emerald
      case 'EMAIL':
        return '#c084fc'; // Purple
      case 'LOCATION':
        return '#f59e0b'; // Amber
      case 'DATE':
        return '#818cf8'; // Indigo
      case 'URL':
        return '#ec4899'; // Pink
      case 'IP_ADDRESS':
        return '#06b6d4'; // Teal
      case 'ORG':
        return '#f97316'; // Orange
      default:
        return '#64748b'; // Slate
    }
  };

  // Iterative Force-Directed Layout Simulation with Collision Avoidance
  const nodePositions = useMemo(() => {
    if (!graphData || graphData.nodes.length === 0) return {};

    const width = 900;
    const height = 550;
    const centerX = width / 2;
    const centerY = height / 2;

    const nodes = graphData.nodes.map((n, i) => {
      // Deterministic initial placement in spiral to avoid single-point overlap
      const angle = i * 0.8;
      const radius = 40 + i * 15;
      return {
        id: n.id,
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
        vx: 0,
        vy: 0,
      };
    });

    const nodeIndexMap: Record<string, number> = {};
    nodes.forEach((n, idx) => {
      nodeIndexMap[n.id] = idx;
    });

    const edges = graphData.edges
      .map((e) => ({
        sourceIdx: nodeIndexMap[e.source],
        targetIdx: nodeIndexMap[e.target],
      }))
      .filter((e) => e.sourceIdx !== undefined && e.targetIdx !== undefined);

    const iterations = 180;
    const k = Math.sqrt((width * height) / (nodes.length || 1));
    const minDistance = 75; // Bounding box collision threshold to prevent label overlaps

    for (let iter = 0; iter < iterations; iter++) {
      // 1. Repulsion between all pairs of nodes
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[j].x - nodes[i].x;
          const dy = nodes[j].y - nodes[i].y;
          let dist = Math.sqrt(dx * dx + dy * dy) || 1;

          // Force repulsion if within collision bounding box
          let repForce = (k * k) / dist;
          if (dist < minDistance) {
            repForce *= 2.5; // Stronger push when overlapping
          }

          const fx = (dx / dist) * repForce;
          const fy = (dy / dist) * repForce;

          nodes[i].vx -= fx * 0.08;
          nodes[i].vy -= fy * 0.08;
          nodes[j].vx += fx * 0.08;
          nodes[j].vy += fy * 0.08;
        }
      }

      // 2. Attraction along edges
      edges.forEach((edge) => {
        const source = nodes[edge.sourceIdx];
        const target = nodes[edge.targetIdx];
        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const attrForce = (dist * dist) / k;

        const fx = (dx / dist) * attrForce;
        const fy = (dy / dist) * attrForce;

        source.vx += fx * 0.04;
        source.vy += fy * 0.04;
        target.vx -= fx * 0.04;
        target.vy -= fy * 0.04;
      });

      // 3. Center Gravity
      nodes.forEach((node) => {
        const dx = centerX - node.x;
        const dy = centerY - node.y;
        node.vx += dx * 0.015;
        node.vy += dy * 0.015;

        // Apply velocity dampening & position updates
        node.x += Math.max(-15, Math.min(15, node.vx));
        node.y += Math.max(-15, Math.min(15, node.vy));
        node.vx *= 0.85;
        node.vy *= 0.85;

        // Clamp to canvas boundary padding
        node.x = Math.max(60, Math.min(width - 60, node.x));
        node.y = Math.max(60, Math.min(height - 60, node.y));
      });
    }

    const posMap: Record<string, { x: number; y: number }> = {};
    nodes.forEach((n) => {
      posMap[n.id] = { x: n.x, y: n.y };
    });

    return posMap;
  }, [graphData]);

  // Mouse Drag Pan Handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // Left click only
    setIsDragging(true);
    dragStartRef.current = { x: e.clientX - panOffset.x, y: e.clientY - panOffset.y };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPanOffset({
      x: e.clientX - dragStartRef.current.x,
      y: e.clientY - dragStartRef.current.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Mouse Wheel Zoom Handler
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoomScale((prev) => Math.min(Math.max(prev * zoomFactor, 0.4), 3.0));
  };

  const resetView = () => {
    setZoomScale(1.0);
    setPanOffset({ x: 0, y: 0 });
  };

  return (
    <div className="graph-page-container">
      <header className="page-header">
        <div className="header-title-block">
          <span className="phase-tag">FORENSIC INTELLIGENCE // PHASE 6 KNOWLEDGE GRAPH</span>
          <h2>Knowledge Graph Explorer</h2>
          <p className="subtitle">
            Visual forensic graph exploration of evidence entities and derived relationships with complete rule provenance.
          </p>
        </div>
      </header>

      {/* Control Card */}
      <div className="card control-card" style={{ marginBottom: '1.25rem' }}>
        <div className="control-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div className="control-group" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <label htmlFor="graph-main-report-select" className="font-mono text-muted text-small">SELECT CASE REPORT:</label>
            <select
              id="graph-main-report-select"
              value={selectedReportId}
              onChange={(e) => setSelectedReportId(e.target.value)}
              className="select-report font-mono"
              style={{ background: '#0f172a', border: '1px solid #334155', color: '#f8fafc', padding: '0.5rem 0.8rem', borderRadius: '6px' }}
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

          {/* Clean Formatted Metrics Bar */}
          {summary && (
            <div className="graph-stats-bar font-mono" style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
              <span className="graph-stat-pill" style={{ background: '#0f172a', border: '1px solid #334155', padding: '0.35rem 0.75rem', borderRadius: '4px', fontSize: '0.75rem' }}>
                NODES: <strong className="text-cyan">{graphData?.nodes.length || 0}</strong>
              </span>
              <span className="graph-stat-pill" style={{ background: '#0f172a', border: '1px solid #334155', padding: '0.35rem 0.75rem', borderRadius: '4px', fontSize: '0.75rem' }}>
                EDGES: <strong style={{ color: '#c084fc' }}>{graphData?.edges.length || 0}</strong>
              </span>
              {summary.top_connected_nodes.length > 0 && (
                <span className="graph-stat-pill" style={{ background: '#0f172a', border: '1px solid #334155', padding: '0.35rem 0.75rem', borderRadius: '4px', fontSize: '0.75rem' }}>
                  MOST CONNECTED: <strong style={{ color: '#10b981' }}>{summary.top_connected_nodes[0].value}</strong> ({summary.top_connected_nodes[0].connection_count} links)
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

      {/* Color-Coded Entity Legend */}
      <GraphLegend />

      {isNeighborhoodView && (
        <div className="card notice-card font-mono" style={{ padding: '0.75rem 1.25rem', marginBottom: '1.25rem' }}>
          <div className="control-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Viewing Neighborhood Subgraph for node: <strong className="text-cyan">{selectedNodeId}</strong> ({expansionDepth} Hop Expansion)</span>
            <button onClick={loadGraph} className="btn-secondary btn-sm font-mono">
              Reset Full Graph
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="card error-card" style={{ marginBottom: '1.25rem' }}>
          <h4>Graph Construction Notice</h4>
          <p>{error}</p>
        </div>
      )}

      {/* Main Canvas & Side Panel Container */}
      <div className="graph-layout-container" style={{ display: 'grid', gridTemplateColumns: selectedEdgeExplanation ? '1fr 340px' : '1fr', gap: '1.25rem' }}>
        <div className="card graph-canvas-card">
          <div className="table-header-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <h3>Interactive Knowledge Network Canvas</h3>
            <span className="text-small text-muted font-mono">
              Click node to expand neighborhood • Click edge to inspect explanation
            </span>
          </div>

          <div
            className="graph-canvas-relative-container"
            style={{ position: 'relative', height: '550px', background: '#090d16', borderRadius: 'var(--radius)', border: '1px solid #1e293b', overflow: 'hidden', cursor: isDragging ? 'grabbing' : 'grab' }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
          >
            {/* Zoom / Pan Interactive Controls Bar */}
            <div style={{ position: 'absolute', top: 12, right: 12, zIndex: 20, display: 'flex', gap: '0.4rem', background: '#0f172a', border: '1px solid #334155', padding: '0.3rem', borderRadius: '6px' }}>
              <button
                className="btn-cyber-outline font-mono"
                style={{ padding: '0.2rem 0.5rem', fontSize: '0.8rem', cursor: 'pointer' }}
                onClick={() => setZoomScale((s) => Math.min(s + 0.2, 3.0))}
                title="Zoom In"
              >
                +
              </button>
              <button
                className="btn-cyber-outline font-mono"
                style={{ padding: '0.2rem 0.5rem', fontSize: '0.8rem', cursor: 'pointer' }}
                onClick={() => setZoomScale((s) => Math.max(s - 0.2, 0.4))}
                title="Zoom Out"
              >
                −
              </button>
              <button
                className="btn-cyber-outline font-mono"
                style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem', cursor: 'pointer' }}
                onClick={resetView}
                title="Reset View / Fit to Bounds"
              >
                ⟲ Reset
              </button>
              <span className="font-mono text-muted text-small" style={{ alignSelf: 'center', marginLeft: '0.3rem', paddingRight: '0.3rem', fontSize: '0.7rem' }}>
                {(zoomScale * 100).toFixed(0)}%
              </span>
            </div>

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
                background: 'rgba(9, 13, 22, 0.85)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 15,
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
              <svg
                width="100%"
                height="100%"
                viewBox="0 0 900 550"
                className="graph-svg"
                style={{ userSelect: 'none' }}
              >
                {/* Transform group for Zoom and Drag-Pan */}
                <g transform={`translate(${panOffset.x}, ${panOffset.y}) scale(${zoomScale})`}>
                  {/* Draw Edges */}
                  {graphData.edges.map((edge, i) => {
                    const sourcePos = nodePositions[edge.source];
                    const targetPos = nodePositions[edge.target];
                    if (!sourcePos || !targetPos) return null;

                    const isFact = edge.classification === 'FACT';

                    // Midpoint for Edge Label with slight perpendicular offset to prevent stacked edge label collisions
                    const baseMidX = (sourcePos.x + targetPos.x) / 2;
                    const baseMidY = (sourcePos.y + targetPos.y) / 2;

                    const dx = targetPos.x - sourcePos.x;
                    const dy = targetPos.y - sourcePos.y;
                    const len = Math.sqrt(dx * dx + dy * dy) || 1;

                    // Perpendicular offset vector for edge label alignment
                    const perpX = -dy / len;
                    const perpY = dx / len;
                    const offsetMag = (i % 2 === 0 ? 1 : -1) * 14;

                    const labelX = baseMidX + perpX * offsetMag;
                    const labelY = baseMidY + perpY * offsetMag;

                    const labelText = edge.relationship_type;
                    const textWidth = labelText.length * 6.8 + 12;

                    return (
                      <g
                        key={edge.id}
                        className="svg-edge-group"
                        onClick={(e) => handleEdgeClick(edge, e)}
                        style={{ cursor: 'pointer' }}
                      >
                        {/* Edge Connecting Line */}
                        <line
                          x1={sourcePos.x}
                          y1={sourcePos.y}
                          x2={targetPos.x}
                          y2={targetPos.y}
                          stroke={isFact ? '#38bdf8' : '#c084fc'}
                          strokeWidth={2.5}
                          strokeDasharray={isFact ? 'none' : '6,6'}
                          opacity={0.85}
                        />

                        {/* Edge Label Background Pill Halo for Collision Legibility */}
                        <rect
                          x={labelX - textWidth / 2}
                          y={labelY - 9}
                          width={textWidth}
                          height={18}
                          fill="#0f172a"
                          stroke={isFact ? '#0284c7' : '#9333ea'}
                          strokeWidth="1"
                          rx="4"
                          opacity="0.95"
                        />

                        {/* Edge Label Text */}
                        <text
                          x={labelX}
                          y={labelY + 4}
                          textAnchor="middle"
                          className="edge-text-label font-mono"
                          style={{
                            fontSize: '0.65rem',
                            fill: isFact ? '#38bdf8' : '#e9d5ff',
                            fontWeight: 700,
                            letterSpacing: '0.02em',
                          }}
                        >
                          {labelText}
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

                    const nodeLabel = node.value;
                    const typeLabel = node.evidence_type;
                    const labelWidth = Math.max(nodeLabel.length, typeLabel.length) * 6.5 + 14;

                    return (
                      <g
                        key={node.id}
                        className="svg-node-group"
                        onClick={(e) => handleNodeClick(node, e)}
                        transform={`translate(${pos.x}, ${pos.y})`}
                        style={{ cursor: 'pointer' }}
                      >
                        {/* Outer Glow Ring if Selected */}
                        {isSelected && (
                          <circle
                            r={20}
                            fill="none"
                            stroke="#06b6d4"
                            strokeWidth={2}
                            strokeDasharray="3,3"
                          />
                        )}

                        {/* Main Node Circle */}
                        <circle
                          r={14}
                          fill={nodeColor}
                          stroke="#0f172a"
                          strokeWidth={2}
                        />

                        {/* Node Label Background Halo Box for 100% Collision-Free Legibility */}
                        <rect
                          x={-labelWidth / 2}
                          y={19}
                          width={labelWidth}
                          height={28}
                          fill="#0f172a"
                          stroke="#1e293b"
                          strokeWidth="1"
                          rx="4"
                          opacity="0.95"
                        />

                        {/* Primary Node Value Text */}
                        <text
                          y={31}
                          textAnchor="middle"
                          className="node-text-label font-mono"
                          style={{
                            fontSize: '0.68rem',
                            fill: '#f8fafc',
                            fontWeight: 700,
                          }}
                        >
                          {nodeLabel}
                        </text>

                        {/* Secondary Entity Type Text */}
                        <text
                          y={43}
                          textAnchor="middle"
                          className="node-text-label-sub font-mono"
                          style={{
                            fontSize: '0.58rem',
                            fill: nodeColor,
                            fontWeight: 700,
                          }}
                        >
                          {typeLabel}
                        </text>
                      </g>
                    );
                  })}
                </g>
              </svg>
            )}
          </div>
        </div>

        {/* Edge Explanation Side Panel */}
        {selectedEdgeExplanation && (
          <div className="card edge-side-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem', background: '#0f172a', border: '1px solid #1e293b' }}>
            <div className="modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #1e293b', paddingBottom: '0.6rem' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>Rule Explanation Drill-Down</h3>
              <button
                className="btn-close"
                onClick={() => setSelectedEdgeExplanation(null)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '1.1rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>
            <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div className="panel-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="panel-label font-mono text-small text-muted">Relationship:</span>
                <span className="predicate-badge font-mono" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 700 }}>
                  {selectedEdgeExplanation.relationship_type}
                </span>
              </div>
              <div className="panel-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="panel-label font-mono text-small text-muted">Classification:</span>
                <span className="classification-badge font-mono" style={{ background: selectedEdgeExplanation.classification === 'FACT' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(192, 132, 252, 0.15)', color: selectedEdgeExplanation.classification === 'FACT' ? '#10b981' : '#c084fc', border: selectedEdgeExplanation.classification === 'FACT' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(192, 132, 252, 0.3)', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 700 }}>
                  {selectedEdgeExplanation.classification}
                </span>
              </div>
              <div className="panel-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="panel-label font-mono text-small text-muted">Rule ID:</span>
                <span className="method-tag font-mono" style={{ color: '#cbd5e1', fontSize: '0.75rem' }}>
                  {selectedEdgeExplanation.rule_id}
                </span>
              </div>

              <div className="panel-section" style={{ borderTop: '1px solid #1e293b', paddingTop: '0.75rem' }}>
                <h4 className="font-mono text-small text-muted" style={{ textTransform: 'uppercase', marginBottom: '0.35rem' }}>Human-Readable Explanation</h4>
                <p className="explanation-text" style={{ fontSize: '0.85rem', color: '#f8fafc', lineHeight: 1.5, margin: 0 }}>
                  {selectedEdgeExplanation.explanation}
                </p>
              </div>

              <div className="panel-section" style={{ borderTop: '1px solid #1e293b', paddingTop: '0.75rem' }}>
                <h4 className="font-mono text-small text-muted" style={{ textTransform: 'uppercase', marginBottom: '0.5rem' }}>Ground-Truth Entities Involved</h4>
                <div className="mini-entity-box font-mono" style={{ background: '#090d16', border: '1px solid #1e293b', padding: '0.75rem', borderRadius: '6px', fontSize: '0.78rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                  <div><strong style={{ color: '#94a3b8' }}>Source:</strong> <span style={{ color: '#38bdf8' }}>{selectedEdgeExplanation.source_value}</span> ({selectedEdgeExplanation.source_type})</div>
                  <div><strong style={{ color: '#94a3b8' }}>Target:</strong> <span style={{ color: '#38bdf8' }}>{selectedEdgeExplanation.target_value}</span> ({selectedEdgeExplanation.target_type})</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
