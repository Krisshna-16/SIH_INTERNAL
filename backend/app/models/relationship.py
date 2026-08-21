from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base


class Relationship(Base):
    """
    Symbolic AI Relationship record derived from Evidence co-occurrence and explicit rules.
    """
    __tablename__ = "relationships"

    id = Column(String, primary_key=True, index=True)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    source_evidence_id = Column(String, ForeignKey("evidence.evidence_id"), nullable=False, index=True)
    target_evidence_id = Column(String, ForeignKey("evidence.evidence_id"), nullable=False, index=True)
    relationship_type = Column(String, nullable=False, index=True)
    classification = Column(String, nullable=False, index=True)
    rule_id = Column(String, nullable=False)
    explanation = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    report = relationship("Report")
    source_evidence = relationship("Evidence", foreign_keys=[source_evidence_id])
    target_evidence = relationship("Evidence", foreign_keys=[target_evidence_id])
