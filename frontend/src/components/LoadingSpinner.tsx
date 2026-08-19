import React from 'react';

interface LoadingSpinnerProps {
  message?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ message = 'Loading…' }) => (
  <div className="shared-loading"><span className="spinner" /><span>{message}</span></div>
);
