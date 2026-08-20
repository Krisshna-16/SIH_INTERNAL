from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base


class Evidence(Base):
    """
    Canonical Ground-Truth Evidence model with complete provenance tracking.
    
    PRIVACY / REDACTION HOOK NOTE:
    In Phase 9 (Privacy Gateway), requests for Evidence `value` and `normalized_value`
    will be intercepted to apply pseudonymization / RBAC redaction rules before
    returning to clients.
    """
    __tablename__ = "evidence"

    evidence_id = Column(String, primary_key=True, index=True)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    evidence_type = Column(String, nullable=False, index=True)
    value = Column(String, nullable=False)
    normalized_value = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=True, index=True)
    confidence = Column(Float, nullable=False)
    source_page = Column(Integer, nullable=False)
    source_report = Column(String, nullable=False)
    provenance_detail = Column(JSON, nullable=False)
    derived_from_entity_id = Column(String, ForeignKey("entities.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    report = relationship("Report")
    derived_entity = relationship("Entity")
