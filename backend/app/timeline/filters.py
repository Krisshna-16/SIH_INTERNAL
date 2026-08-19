from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class TimelineEntry(BaseModel):
    """
    Chronological Timeline Entry model exposing ground-truth provenance and classification.
    
    PRIVACY / REDACTION HOOK NOTE:
    In Phase 9 (Privacy Gateway), requests returning `title` or `related_values`
    will be intercepted to apply pseudonymization / RBAC redaction prior to display.
    """
    entry_id: str = Field(..., description="Unique entry ID (e.g., TLE-EVT-XXXX or TLE-FND-XXXX)")
    timestamp: str = Field(..., description="ISO formatted timestamp")
    event_type: str = Field(..., description="Evidence type or finding category")
    evidence_id: Optional[str] = Field(None, description="Linked Evidence ID if derived from Evidence")
    finding_id: Optional[str] = Field(None, description="Linked Finding ID if derived from Finding")
    title: str = Field(..., description="Human-readable timeline event title")
    related_values: List[str] = Field(default_factory=list, description="Associated entity values")
    source_report: str = Field(..., description="Originating UFDR report filename")
    source_page: int = Field(..., description="Originating page number")
    confidence: float = Field(..., description="Confidence score")
    classification: str = Field(..., description="Classification taxonomy (FACT vs INFERENCE)")


class TimelineFilters(BaseModel):
    """
    Query parameters for filtering chronological timeline views.
    """
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    evidence_types: Optional[List[str]] = None
    entity_value: Optional[str] = None
    classification: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=100000)


class TimelineSummary(BaseModel):
    """
    Chronological timeline summary metrics.
    """
    report_id: str
    earliest_timestamp: Optional[str] = None
    latest_timestamp: Optional[str] = None
    total_entries: int
    entries_by_type: Dict[str, int] = Field(default_factory=dict)
