from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint
from app.db.session import Base


class PseudonymMapping(Base):
    """
    Persistent mapping table associating real evidence identities with deterministic pseudonym tokens.
    
    SECURITY & PRIVACY REQUIREMENT:
    This table exists exclusively in the local database and is NEVER serialized into any LLM prompt
    or exposed via public API endpoints.
    """
    __tablename__ = "pseudonym_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(64), ForeignKey("reports.id"), nullable=False, index=True)
    real_value = Column(String(512), nullable=False)
    pseudonym = Column(String(128), nullable=False)
    entity_type = Column(String(64), nullable=False)
    first_seen_evidence_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("report_id", "real_value", name="uix_report_real_value"),
        UniqueConstraint("report_id", "pseudonym", name="uix_report_pseudonym"),
    )

    def __repr__(self):
        return f"<PseudonymMapping(report_id='{self.report_id}', pseudonym='{self.pseudonym}', type='{self.entity_type}')>"
