import React from 'react';

interface ConfidenceBadgeProps {
  value: number; // 0.0 – 1.0 float
}

/** Standardized confidence badge: high (≥0.8) / medium (≥0.5) / low (<0.5). */
export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ value }) => {
  const pct = (value * 100).toFixed(0);
  let cls = 'conf-badge conf-low';
  if (value >= 0.8) cls = 'conf-badge conf-high';
  else if (value >= 0.5) cls = 'conf-badge conf-med';
  return <span className={cls}>{pct}%</span>;
};
