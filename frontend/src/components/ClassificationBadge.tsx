import React from 'react';

interface ClassificationBadgeProps {
  classification: string; // FACT | INFERENCE | RULE | UNKNOWN
}

/** Standardized FACT / INFERENCE classification badge. */
export const ClassificationBadge: React.FC<ClassificationBadgeProps> = ({ classification }) => {
  const upper = (classification || 'UNKNOWN').toUpperCase();
  const cls = upper === 'FACT' ? 'cls-badge cls-fact' : upper === 'INFERENCE' ? 'cls-badge cls-inference' : 'cls-badge cls-other';
  return <span className={cls}>{upper}</span>;
};
