import uuid
import re
import json
import hashlib
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
    Tries proper parsers (json.loads, ET.fromstring) first per detected type,
    falls back to regex heuristics and character chunking as last resort.
    """
    content_str = content_str.strip()
    if not content_str:
        return ["Empty UFDR report file."]

    pages: List[str] = []

    # 1. Try JSON parsing first if content looks like JSON
    if content_str.startswith(("{", "[")):
        try:
            data = json.loads(content_str)
            if isinstance(data, dict):
                # Expect {"pages": [...]} or flatten all string values
                if "pages" in data and isinstance(data["pages"], list):
                    for p in data["pages"]:
                        if isinstance(p, dict):
                            pages.append(p.get("text_content", "") or p.get("content", "") or str(p))
                        elif isinstance(p, str):
                            pages.append(p)
                else:
                    pages.append(json.dumps(data, indent=2))
            elif isinstance(data, list):
                for item in data:
                    pages.append(str(item) if not isinstance(item, str) else item)
            if pages:
                return pages
        except (json.JSONDecodeError, ValueError):
            pass

    # 2. Try proper XML parsing (ElementTree) first for XML-like content
    if content_str.startswith("<") or "<?xml" in content_str:
        try:
            root = ET.fromstring(content_str)
            # Look for page/section/item elements
            for tag in ["page", "report_page", "section", "item"]:
                elems = root.findall(f".//{tag}")
                if not elems:
                    elems = root.findall(f".//{tag.upper()}")
                for elem in elems:
                    text = ET.tostring(elem, encoding="unicode", method="text").strip()
                    if text:
                        pages.append(text)
            # If no structured page elements, extract all text
            if not pages:
                text_pieces = []
                for elem in root.iter():
                    if elem.text and elem.text.strip():
                        text_pieces.append(elem.text.strip())
                full_text = "\n".join(text_pieces)
                if full_text:
                    pages = [full_text[i:i + 2500] for i in range(0, len(full_text), 2500)]
        except ET.ParseError:
            pass

        # 2b. Regex fallback for malformed XML only if ET failed
        if not pages:
            page_blocks = re.findall(r'<(?:page|report_page|section|item)[^>]*>(.*?)</(?:page|report_page|section|item)>', content_str, re.DOTALL | re.IGNORECASE)
            if page_blocks:
                for block in page_blocks:
                    clean_text = re.sub(r'<[^>]+>', ' ', block).strip()
                    if clean_text:
                        pages.append(clean_text)

    # 3. Try Page Delimiters (e.g. --- PAGE 1 --- or Page 1)
    if not pages:
        delim_split = re.split(r'(?:---+|\bPage\s+\d+\b|\bPAGE\s+\d+\b)', content_str, flags=re.IGNORECASE)
        for chunk in delim_split:
            chunk_clean = chunk.strip()
            if len(chunk_clean) > 20:
                pages.append(chunk_clean)

    # 4. Fallback: Chunk long text every 2500 characters
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
    Computes SHA-256 integrity hash for chain-of-custody compliance.
    """
    filename = file.filename or "Uploaded_UFDR_Report.xml"
    try:
        content_bytes = await file.read()
        content_str = content_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {str(e)}")

    # Compute SHA-256 integrity hash over raw uploaded bytes
    content_hash = hashlib.sha256(content_bytes).hexdigest()

    parsed_pages = parse_ufdr_file_content(content_str)

    report_id = f"REP-{uuid.uuid4().hex[:8].upper()}"
    report = Report(
        id=report_id,
        filename=filename,
        status="parsed",
        page_count=len(parsed_pages),
        content_hash=content_hash,
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
        "content_hash": report.content_hash,
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
