import React from 'react';

interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
}

/** Consistent "no data" placeholder used across all pages. */
export const EmptyState: React.FC<EmptyStateProps> = ({ icon = '📭', title, description }) => (
  <div className="shared-empty-state">
    <span className="empty-icon">{icon}</span>
    <h4>{title}</h4>
    {description && <p>{description}</p>}
  </div>
);
