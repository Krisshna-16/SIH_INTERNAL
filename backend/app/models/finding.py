from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base


class Finding(Base):
    """
    Symbolic AI investigative Finding record flagged by explicit correlation rules.
    """
    __tablename__ = "findings"

    id = Column(String, primary_key=True, index=True)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    finding_type = Column(String, nullable=False, index=True)  # PAGE_COOCCURRENCE_CLUSTER, HIGH_FREQUENCY_LOCATION, etc.
    classification = Column(String, default="INFERENCE", nullable=False) # Always INFERENCE for derived rule findings
    rule_id = Column(String, nullable=False)
    rule_name = Column(String, nullable=False)
    explanation = Column(Text, nullable=False)
    related_evidence_ids = Column(Text, nullable=False)        # JSON string list of evidence_ids
    related_relationship_ids = Column(Text, nullable=True)    # JSON string list of relationship_ids
    parameters_used = Column(Text, nullable=False)             # JSON string dict of rule parameters
    severity = Column(String, nullable=False, index=True)      # LOW, MEDIUM, HIGH
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    report = relationship("Report")
