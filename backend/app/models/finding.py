from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base


class Finding(Base):
    """
    Symbolic AI investigative Finding record flagged by explicit correlation rules.
    """
    __tablename__ = "findings"

    id = Column(String, primary_key=True, index=True)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    finding_type = Column(String, nullable=False, index=True)
    classification = Column(String, default="INFERENCE", nullable=False)
    rule_id = Column(String, nullable=False)
    rule_name = Column(String, nullable=False)
    explanation = Column(Text, nullable=False)
    related_evidence_ids = Column(JSON, nullable=False)
    related_relationship_ids = Column(JSON, nullable=True)
    parameters_used = Column(JSON, nullable=False)
    severity = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    report = relationship("Report")
