import React from 'react';

export const GraphLegend: React.FC = () => {
  return (
    <div className="graph-legend-box">
      <div className="legend-section">
        <span className="legend-title">Entity Nodes:</span>
        <div className="legend-items">
          <span className="legend-chip chip-person">● PERSON</span>
          <span className="legend-chip chip-phone">● PHONE</span>
          <span className="legend-chip chip-email">● EMAIL</span>
          <span className="legend-chip chip-location">● LOCATION</span>
          <span className="legend-chip chip-other">● OTHER</span>
        </div>
      </div>

      <div className="legend-section">
        <span className="legend-title">Relationship Edges:</span>
        <div className="legend-items">
          <span className="legend-chip edge-fact">━ FACT (Direct)</span>
          <span className="legend-chip edge-inference">╍╍ INFERENCE (Rule)</span>
        </div>
      </div>
    </div>
  );
};
