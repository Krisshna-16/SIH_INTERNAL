import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.db.session import Base


class EntityType(str, enum.Enum):
    PERSON = "PERSON"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    LOCATION = "LOCATION"
    DATE = "DATE"
    URL = "URL"
    USERNAME = "USERNAME"
    ORG = "ORG"
    IP_ADDRESS = "IP_ADDRESS"
    OTHER = "OTHER"


class Entity(Base):
    """
    Extracted forensic entity with full provenance tracking.
    
    PRIVACY / REDACTION HOOK NOTE:
    In Phase 9 (Privacy Gateway), raw entity values (e.g. real names, phone numbers)
    will be intercepted here or via view-layer filters to apply pseudonymization / 
    role-based redaction prior to investigator presentation or export.
    """
    __tablename__ = "entities"

    id = Column(String, primary_key=True, index=True)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    type = Column(String, nullable=False, index=True)
    value = Column(String, nullable=False)
    normalized_value = Column(String, nullable=True)
    confidence = Column(Float, nullable=False)
    source_page = Column(Integer, nullable=False)
    source_report = Column(String, nullable=False)
    extraction_method = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    report = relationship("Report", back_populates="entities")
