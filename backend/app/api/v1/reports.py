import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.report import Report, ReportPage

router = APIRouter(prefix="/reports", tags=["reports"])


class PageCreateSchema(BaseModel):
    page_number: int
    text_content: str
    tables_json: Optional[str] = None


class ReportCreateSchema(BaseModel):
    filename: str = Field(..., example="UFDR_Report_Case_2024_08.xml")
    pages: List[PageCreateSchema]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_report(payload: ReportCreateSchema, db: Session = Depends(get_db)):
    """Creates/seeds a new UFDR report with parsed pages for testing & extraction."""
    report_id = f"REP-{uuid.uuid4().hex[:8].upper()}"
    report = Report(
        id=report_id,
        filename=payload.filename,
        status="parsed",
        page_count=len(payload.pages),
    )
    db.add(report)

    for p in payload.pages:
        page = ReportPage(
            report_id=report_id,
            page_number=p.page_number,
            text_content=p.text_content,
            tables_json=p.tables_json,
        )
        db.add(page)

    db.commit()
    db.refresh(report)
    return {
        "id": report.id,
        "filename": report.filename,
        "status": report.status,
        "page_count": report.page_count,
        "created_at": report.created_at.isoformat(),
    }


@router.get("")
def list_reports(db: Session = Depends(get_db)):
    """List all ingested UFDR reports."""
    reports = db.query(Report).order_by(Report.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "status": r.status,
            "page_count": r.page_count,
            "created_at": r.created_at.isoformat(),
        }
        for r in reports
    ]


@router.get("/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db)):
    """Fetch report details and page counts."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")
    return {
        "id": report.id,
        "filename": report.filename,
        "status": report.status,
        "page_count": report.page_count,
        "created_at": report.created_at.isoformat(),
    }
