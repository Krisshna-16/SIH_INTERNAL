import React from 'react';

interface EntityTypeFilterProps {
  selectedType: string;
  onSelectType: (type: string) => void;
  entityCounts?: Record<string, number>;
}

const ALL_TYPES = [
  'ALL',
  'PERSON',
  'PHONE',
  'EMAIL',
  'LOCATION',
  'DATE',
  'URL',
  'IP_ADDRESS',
  'ORG',
];

export const EntityTypeFilter: React.FC<EntityTypeFilterProps> = ({
  selectedType,
  onSelectType,
  entityCounts,
}) => {
  return (
    <div className="filter-container">
      <span className="filter-label font-mono">FILTER BY ENTITY TYPE:</span>
      <div className="filter-chips">
        {ALL_TYPES.map((type) => {
          const isSelected = selectedType === type;
          const count = entityCounts
            ? type === 'ALL'
              ? Object.values(entityCounts).reduce((a, b) => a + b, 0)
              : entityCounts[type] || 0
            : null;

          return (
            <button
              key={type}
              type="button"
              className={`filter-chip ${isSelected ? 'active' : ''}`}
              onClick={() => onSelectType(type)}
            >
              <span className="chip-name font-mono">{type}</span>
              {count !== null && <span className="chip-count font-mono">{count}</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
};
