import uuid
import re
import xml.etree.ElementTree as ET
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, status
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


def parse_ufdr_file_content(content_str: str) -> List[str]:
    """
    Parses uploaded XML, JSON, or TXT content into a list of page text strings.
    Handles standard UFDR XML tags (<page>, <report_page>, <item>), page delimiter comments,
    or falls back to logical character chunking.
    """
    content_str = content_str.strip()
    if not content_str:
        return ["Empty UFDR report file."]

    pages: List[str] = []

    # 1. Try XML parsing
    if content_str.startswith("<") or "<?xml" in content_str:
        try:
            # Look for explicit <page> or <report_page> or <section> tags using regex to avoid malformed XML errors
            page_blocks = re.findall(r'<(?:page|report_page|section|item)[^>]*>(.*?)</(?:page|report_page|section|item)>', content_str, re.DOTALL | re.IGNORECASE)
            if page_blocks:
                for block in page_blocks:
                    # Strip inner XML tags
                    clean_text = re.sub(r'<[^>]+>', ' ', block).strip()
                    if clean_text:
                        pages.append(clean_text)

            if not pages:
                # Try parsing as standard ElementTree
                root = ET.fromstring(content_str)
                text_pieces = []
                for elem in root.iter():
                    if elem.text and elem.text.strip():
                        text_pieces.append(elem.text.strip())
                full_text = "\n".join(text_pieces)
                if full_text:
                    pages = [full_text[i:i + 2500] for i in range(0, len(full_text), 2500)]
        except Exception:
            pass

    # 2. Try Page Delimiters (e.g. --- PAGE 1 --- or Page 1)
    if not pages:
        delim_split = re.split(r'(?:---+|\bPage\s+\d+\b|\bPAGE\s+\d+\b)', content_str, flags=re.IGNORECASE)
        for chunk in delim_split:
            chunk_clean = chunk.strip()
            if len(chunk_clean) > 20:
                pages.append(chunk_clean)

    # 3. Fallback: Chunk long text every 2500 characters
    if not pages:
        chunk_size = 2500
        for i in range(0, len(content_str), chunk_size):
            pages.append(content_str[i:i + chunk_size])

    return pages if pages else [content_str]


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_report_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Accepts real UFDR XML, TXT, or JSON file upload, parses pages, and stores in database.
    """
    filename = file.filename or "Uploaded_UFDR_Report.xml"
    try:
        content_bytes = await file.read()
        content_str = content_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {str(e)}")

    parsed_pages = parse_ufdr_file_content(content_str)

    report_id = f"REP-{uuid.uuid4().hex[:8].upper()}"
    report = Report(
        id=report_id,
        filename=filename,
        status="parsed",
        page_count=len(parsed_pages),
    )
    db.add(report)

    for p_num, p_text in enumerate(parsed_pages, start=1):
        page = ReportPage(
            report_id=report_id,
            page_number=p_num,
            text_content=p_text,
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
