import React from 'react';

interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({ message, onRetry }) => (
  <div className="shared-error-banner">
    <span>⚠ {message}</span>
    {onRetry && <button className="btn-sm btn-secondary" onClick={onRetry}>Retry</button>}
  </div>
);
