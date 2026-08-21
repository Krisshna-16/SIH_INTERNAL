import React from 'react';

export const GraphLegend: React.FC = () => {
  return (
    <div className="graph-legend-box" style={{ background: '#0f172a', border: '1px solid #1e293b', padding: '0.75rem 1.25rem', borderRadius: '6px', marginBottom: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
      <div className="legend-section" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
        <span className="legend-title font-mono text-small text-muted" style={{ fontWeight: 700, textTransform: 'uppercase' }}>Entity Node Types:</span>
        <div className="legend-items" style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
          <span className="legend-chip" style={{ color: '#38bdf8', background: 'rgba(56, 189, 248, 0.12)', border: '1px solid rgba(56, 189, 248, 0.3)', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>● PERSON</span>
          <span className="legend-chip" style={{ color: '#10b981', background: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>● PHONE</span>
          <span className="legend-chip" style={{ color: '#c084fc', background: 'rgba(192, 132, 252, 0.12)', border: '1px solid rgba(192, 132, 252, 0.3)', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>● EMAIL</span>
          <span className="legend-chip" style={{ color: '#f59e0b', background: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.3)', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>● LOCATION</span>
          <span className="legend-chip" style={{ color: '#818cf8', background: 'rgba(129, 140, 248, 0.12)', border: '1px solid rgba(129, 140, 248, 0.3)', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>● DATE</span>
          <span className="legend-chip" style={{ color: '#ec4899', background: 'rgba(236, 72, 153, 0.12)', border: '1px solid rgba(236, 72, 153, 0.3)', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>● URL</span>
          <span className="legend-chip" style={{ color: '#06b6d4', background: 'rgba(6, 182, 212, 0.12)', border: '1px solid rgba(6, 182, 212, 0.3)', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>● IP / OTHER</span>
        </div>
      </div>

      <div className="legend-section" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <span className="legend-title font-mono text-small text-muted" style={{ fontWeight: 700, textTransform: 'uppercase' }}>Edge Classification:</span>
        <div className="legend-items" style={{ display: 'flex', gap: '0.75rem', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
          <span className="legend-chip" style={{ color: '#38bdf8', fontWeight: 700 }}>━━━━ FACT (Direct)</span>
          <span className="legend-chip" style={{ color: '#c084fc', fontWeight: 700 }}>╍╍╍╍ INFERENCE (Rule)</span>
        </div>
      </div>
    </div>
  );
};
