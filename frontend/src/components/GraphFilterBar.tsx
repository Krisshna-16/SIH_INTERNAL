import React from 'react';

interface GraphFilterBarProps {
  minConfidence: number;
  selectedRelType: string;
  expansionDepth: number;
  onFilterChange: (filters: {
    minConfidence?: number;
    selectedRelType?: string;
    expansionDepth?: number;
  }) => void;
  onReset: () => void;
}

export const GraphFilterBar: React.FC<GraphFilterBarProps> = ({
  minConfidence,
  selectedRelType,
  expansionDepth,
  onFilterChange,
  onReset,
}) => {
  return (
    <div className="card control-card graph-filter-card">
      <div className="graph-filter-row">
        <div className="filter-group">
          <label htmlFor="graph-min-conf">
            Min Confidence: <strong>{(minConfidence * 100).toFixed(0)}%</strong>
          </label>
          <input
            id="graph-min-conf"
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={minConfidence}
            onChange={(e) => onFilterChange({ minConfidence: parseFloat(e.target.value) })}
            className="filter-slider"
          />
        </div>

        <div className="filter-group">
          <label>Relationship Type:</label>
          <select
            value={selectedRelType}
            onChange={(e) => onFilterChange({ selectedRelType: e.target.value })}
            className="select-report"
            style={{ minWidth: '160px' }}
          >
            <option value="ALL">All Types</option>
            <option value="USED">USED</option>
            <option value="LOCATED_AT">LOCATED_AT</option>
            <option value="ASSOCIATED_WITH">ASSOCIATED_WITH</option>
            <option value="ACCESSED">ACCESSED</option>
            <option value="CONTACTED">CONTACTED</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Expansion Depth:</label>
          <select
            value={expansionDepth}
            onChange={(e) => onFilterChange({ expansionDepth: parseInt(e.target.value, 10) })}
            className="select-report"
            style={{ minWidth: '100px' }}
          >
            <option value={1}>1 Hop</option>
            <option value={2}>2 Hops</option>
            <option value={3}>3 Hops (Max)</option>
          </select>
        </div>

        <button onClick={onReset} className="btn-secondary btn-sm">
          Reset Graph Filters
        </button>
      </div>
    </div>
  );
};
