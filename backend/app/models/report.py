from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    status = Column(String, default="parsed", nullable=False)
    page_count = Column(Integer, default=0, nullable=False)
    content_hash = Column(String, nullable=True)  # SHA-256 hash of raw uploaded bytes
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    pages = relationship("ReportPage", back_populates="report", cascade="all, delete-orphan")
    entities = relationship("Entity", back_populates="report", cascade="all, delete-orphan")


class ReportPage(Base):
    __tablename__ = "report_pages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)
    tables_json = Column(JSON, nullable=True)

    report = relationship("Report", back_populates="pages")
