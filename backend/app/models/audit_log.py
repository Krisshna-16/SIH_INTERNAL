from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.db.session import Base


class AuditLog(Base):
    """
    Immutable access and operations audit log for evidence integrity compliance.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor = Column(String, default="system", nullable=False)
    action = Column(String, nullable=False, index=True)
    evidence_id = Column(String, nullable=True, index=True)
    report_id = Column(String, nullable=True, index=True)
    details = Column(Text, nullable=True)  # JSON metadata string
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
