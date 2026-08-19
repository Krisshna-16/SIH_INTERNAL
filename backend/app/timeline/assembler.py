import json
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict
from sqlalchemy.orm import Session

from app.models.report import Report
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.timeline.filters import TimelineEntry, TimelineFilters, TimelineSummary

logger = logging.getLogger(__name__)


def parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    """Helper to parse ISO datetime string."""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


def get_report_timeline(
    report_id: str, filters: TimelineFilters, db: Session
) -> Tuple[List[TimelineEntry], int]:
    """
    Dynamically assembles and filters chronological timeline entries from timestamped Evidence and Findings.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        all_reps = [r.id for r in db.query(Report).all()]
        logger.error(f"Report '{report_id}' not found in DB. Available reports: {all_reps}")
        raise ValueError(f"Report '{report_id}' not found.")

    # Query 1: Timestamped Evidence only (strict null timestamp exclusion)
    evidence_rows = (
        db.query(Evidence)
        .filter(Evidence.report_id == report_id, Evidence.timestamp.isnot(None))
        .all()
    )

    all_entries: List[TimelineEntry] = []

    # Map Evidence -> TimelineEntry
    for ev in evidence_rows:
        if ev.timestamp is None:
            continue

        ts_str = ev.timestamp.isoformat()
        rel_vals = [ev.value]
        if ev.normalized_value and ev.normalized_value != ev.value:
            rel_vals.append(ev.normalized_value)

        entry = TimelineEntry(
            entry_id=f"TLE-{ev.evidence_id}",
            timestamp=ts_str,
            event_type=ev.evidence_type,
            evidence_id=ev.evidence_id,
            finding_id=None,
            title=f"{ev.evidence_type} Evidence: {ev.value}",
            related_values=rel_vals,
            source_report=ev.source_report,
            source_page=ev.source_page,
            confidence=ev.confidence,
            classification="FACT",
        )
        all_entries.append(entry)

    # Query 2: Findings as Timeline Markers (positioned at earliest related evidence timestamp)
    finding_rows = db.query(Finding).filter(Finding.report_id == report_id).all()
    for fnd in finding_rows:
        try:
            ev_ids = json.loads(fnd.related_evidence_ids)
        except Exception:
            ev_ids = []

        if ev_ids:
            rel_ev_rows = (
                db.query(Evidence)
                .filter(Evidence.evidence_id.in_(ev_ids), Evidence.timestamp.isnot(None))
                .all()
            )
            if rel_ev_rows:
                # Position marker at earliest timestamp
                earliest_ev = min(rel_ev_rows, key=lambda e: e.timestamp)
                if earliest_ev.timestamp is not None:
                    ts_str = earliest_ev.timestamp.isoformat()
                    fnd_vals = [f.value for f in rel_ev_rows]

                    entry = TimelineEntry(
                        entry_id=f"TLE-{fnd.id}",
                        timestamp=ts_str,
                        event_type=fnd.finding_type,
                        evidence_id=None,
                        finding_id=fnd.id,
                        title=f"Flagged Finding: {fnd.rule_name}",
                        related_values=fnd_vals,
                        source_report=earliest_ev.source_report,
                        source_page=earliest_ev.source_page,
                        confidence=0.9,
                        classification="INFERENCE",
                    )
                    all_entries.append(entry)

    # Apply Filters
    filtered: List[TimelineEntry] = []

    start_dt = parse_iso_datetime(filters.start_date) if filters.start_date else None
    end_dt = parse_iso_datetime(filters.end_date) if filters.end_date else None

    for entry in all_entries:
        entry_dt = parse_iso_datetime(entry.timestamp)

        # Date range filter
        if start_dt and entry_dt and entry_dt < start_dt:
            continue
        if end_dt and entry_dt and entry_dt > end_dt:
            continue

        # Evidence type filter
        if filters.evidence_types and len(filters.evidence_types) > 0:
            if "ALL" not in [t.upper() for t in filters.evidence_types]:
                if entry.event_type.upper() not in [t.upper() for t in filters.evidence_types]:
                    continue

        # Classification filter
        if filters.classification and filters.classification.upper() != "ALL":
            if entry.classification.upper() != filters.classification.upper():
                continue

        # Entity value search filter
        if filters.entity_value and filters.entity_value.strip():
            q = filters.entity_value.strip().lower()
            matches_title = q in entry.title.lower()
            matches_vals = any(q in v.lower() for v in entry.related_values)
            if not (matches_title or matches_vals):
                continue

        filtered.append(entry)

    # Strict ascending sort by timestamp, tiebreaker entry_id
    filtered.sort(key=lambda e: (e.timestamp, e.entry_id))

    total_count = len(filtered)
    offset = (filters.page - 1) * filters.page_size
    paginated = filtered[offset : offset + filters.page_size]

    return paginated, total_count


def get_timeline_summary(report_id: str, db: Session) -> TimelineSummary:
    """
    Computes summary timeline statistics for a report.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        all_reps = [r.id for r in db.query(Report).all()]
        logger.error(f"Report '{report_id}' not found in DB. Available reports: {all_reps}")
        raise ValueError(f"Report '{report_id}' not found.")

    dummy_filters = TimelineFilters(page=1, page_size=10000)
    all_entries, total_count = get_report_timeline(report_id, dummy_filters, db)

    if not all_entries:
        return TimelineSummary(
            report_id=report_id,
            earliest_timestamp=None,
            latest_timestamp=None,
            total_entries=0,
            entries_by_type={},
        )

    earliest = all_entries[0].timestamp
    latest = all_entries[-1].timestamp

    counts: Dict[str, int] = {}
    for entry in all_entries:
        counts[entry.event_type] = counts.get(entry.event_type, 0) + 1

    return TimelineSummary(
        report_id=report_id,
        earliest_timestamp=earliest,
        latest_timestamp=latest,
        total_entries=total_count,
        entries_by_type=counts,
    )
