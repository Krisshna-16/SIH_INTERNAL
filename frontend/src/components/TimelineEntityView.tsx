import React, { useEffect, useState } from 'react';
import { fetchEntityTimeline, TimelineEntryItem } from '../api/timeline';

interface TimelineEntityViewProps {
  reportId: string;
  entityValue: string;
  onClearFocus: () => void;
  onSelectEntry: (entry: TimelineEntryItem) => void;
}

export const TimelineEntityView: React.FC<TimelineEntityViewProps> = ({
  reportId,
  entityValue,
  onClearFocus,
  onSelectEntry,
}) => {
  const [entries, setEntries] = useState<TimelineEntryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    const loadFocusedTimeline = async () => {
      if (!reportId || !entityValue) return;
      setLoading(true);
      try {
        const res = await fetchEntityTimeline(reportId, entityValue, 1, 100);
        setEntries(res.items);
      } catch (err) {
        console.error('Failed to load entity focus timeline:', err);
      } finally {
        setLoading(false);
      }
    };
    loadFocusedTimeline();
  }, [reportId, entityValue]);

  return (
    <div className="card entity-focus-card">
      <div className="entity-focus-header">
        <div className="focus-title-block">
          <span className="focus-label">Entity Focus View Mode</span>
          <h3>{entityValue}</h3>
        </div>
        <button onClick={onClearFocus} className="btn-secondary btn-sm">
          ✕ Exit Focus Mode
        </button>
      </div>

      {loading ? (
        <div className="loading-state">Loading focused entity timeline...</div>
      ) : entries.length === 0 ? (
        <div className="empty-state">No timestamped events found for '{entityValue}'.</div>
      ) : (
        <div className="focus-timeline-list">
          {entries.map((entry) => (
            <div
              key={entry.entry_id}
              className="focus-timeline-item"
              onClick={() => onSelectEntry(entry)}
            >
              <span className="font-mono text-small text-muted">{entry.timestamp}</span>
              <span className="predicate-badge">{entry.event_type}</span>
              <span className="focus-item-title">{entry.title}</span>
              <span className={`classification-badge ${entry.classification === 'FACT' ? 'badge-class-fact' : 'badge-class-inference'}`}>
                {entry.classification}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
