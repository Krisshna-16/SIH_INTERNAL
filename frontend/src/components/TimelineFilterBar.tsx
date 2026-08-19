import React from 'react';

interface TimelineFilterBarProps {
  startDate: string;
  endDate: string;
  selectedType: string;
  entitySearch: string;
  selectedClass: string;
  onFilterChange: (filters: {
    startDate?: string;
    endDate?: string;
    selectedType?: string;
    entitySearch?: string;
    selectedClass?: string;
  }) => void;
  onReset: () => void;
}

export const TimelineFilterBar: React.FC<TimelineFilterBarProps> = ({
  startDate,
  endDate,
  selectedType,
  entitySearch,
  selectedClass,
  onFilterChange,
  onReset,
}) => {
  return (
    <div className="card control-card timeline-filter-card">
      <div className="timeline-filter-row">
        <div className="filter-group">
          <label htmlFor="tl-start-date" className="font-mono">FROM:</label>
          <input
            id="tl-start-date"
            type="datetime-local"
            value={startDate}
            onChange={(e) => onFilterChange({ startDate: e.target.value })}
            className="filter-input-date font-mono"
          />
        </div>

        <div className="filter-group">
          <label htmlFor="tl-end-date" className="font-mono">TO:</label>
          <input
            id="tl-end-date"
            type="datetime-local"
            value={endDate}
            onChange={(e) => onFilterChange({ endDate: e.target.value })}
            className="filter-input-date font-mono"
          />
        </div>

        <div className="filter-group">
          <label htmlFor="tl-entity-search" className="font-mono">SEARCH ENTITY:</label>
          <input
            id="tl-entity-search"
            type="text"
            placeholder="e.g. Vikram, Gurgaon..."
            value={entitySearch}
            onChange={(e) => onFilterChange({ entitySearch: e.target.value })}
            className="search-input font-mono"
          />
        </div>

        <div className="filter-group">
          <label className="font-mono">TYPE:</label>
          <select
            value={selectedType}
            onChange={(e) => onFilterChange({ selectedType: e.target.value })}
            className="select-report font-mono"
            style={{ minWidth: '140px' }}
          >
            <option value="ALL">All Types</option>
            <option value="PERSON">PERSON</option>
            <option value="PHONE">PHONE</option>
            <option value="EMAIL">EMAIL</option>
            <option value="LOCATION">LOCATION</option>
            <option value="DATE">DATE</option>
            <option value="COMMUNICATION_CLUSTER">COMMUNICATION CLUSTER</option>
            <option value="PAGE_COOCCURRENCE_CLUSTER">PAGE CLUSTER</option>
          </select>
        </div>

        <div className="filter-group">
          <label className="font-mono">CLASS:</label>
          <select
            value={selectedClass}
            onChange={(e) => onFilterChange({ selectedClass: e.target.value })}
            className="select-report font-mono"
            style={{ minWidth: '130px' }}
          >
            <option value="ALL">All Classes</option>
            <option value="FACT">FACT</option>
            <option value="INFERENCE">INFERENCE</option>
          </select>
        </div>

        <button onClick={onReset} className="btn-secondary btn-sm font-mono">
          Reset Filters
        </button>
      </div>
    </div>
  );
};
