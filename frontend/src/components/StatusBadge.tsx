import React from 'react';

export type ConnectionStatus = 'connected' | 'disconnected' | 'loading';

interface StatusBadgeProps {
  status: ConnectionStatus;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'connected':
        return {
          label: 'Connected',
          className: 'badge-connected',
          indicatorColor: '#10b981',
        };
      case 'disconnected':
        return {
          label: 'Disconnected',
          className: 'badge-disconnected',
          indicatorColor: '#ef4444',
        };
      case 'loading':
      default:
        return {
          label: 'Checking status...',
          className: 'badge-loading',
          indicatorColor: '#f59e0b',
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div className={`status-badge ${config.className}`}>
      <span
        className="status-indicator-dot"
        style={{ backgroundColor: config.indicatorColor }}
      />
      <span className="status-label">{config.label}</span>
    </div>
  );
};
