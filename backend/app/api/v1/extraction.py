from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.report import Report, ReportPage
from app.models.entity import Entity
from app.extraction.pipeline import ExtractionPipeline

router = APIRouter(tags=["extraction"])


@router.post("/reports/{report_id}/extract")
def run_extraction(report_id: str, db: Session = Depends(get_db)):
    """
    Triggers neural and pattern extraction pipeline for a given report ID.
    Performs spaCy NER and pattern-matching across all parsed pages.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot run extraction: Report '{report_id}' does not exist."
        )

    page_count = db.query(ReportPage).filter(ReportPage.report_id == report_id).count()
    if page_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot run extraction: Report '{report_id}' has no parsed pages."
        )

    pipeline = ExtractionPipeline()
    try:
        summary = pipeline.process_report(report_id=report_id, db=db)
        return summary
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during entity extraction: {str(e)}"
        )


@router.get("/reports/{report_id}/entities")
def get_report_entities(
    report_id: str,
    type: Optional[str] = Query(None, description="Filter by entity type (e.g. PERSON, PHONE, EMAIL, LOCATION)"),
    min_confidence: Optional[float] = Query(None, description="Filter entities with confidence >= min_confidence"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db),
):
    """
    Retrieves extracted entities for a report with optional type and confidence filtering.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")

    query = db.query(Entity).filter(Entity.report_id == report_id)

    if type:
        query = query.filter(Entity.type == type.upper())
    if min_confidence is not None:
        query = query.filter(Entity.confidence >= min_confidence)

    total_count = query.count()
    offset = (page - 1) * limit
    entities = query.order_by(Entity.source_page.asc(), Entity.confidence.desc()).offset(offset).limit(limit).all()

    items = [
        {
            "id": ent.id,
            "report_id": ent.report_id,
            "type": ent.type,
            "value": ent.value,
            "normalized_value": ent.normalized_value,
            "confidence": ent.confidence,
            "source_page": ent.source_page,
            "source_report": ent.source_report,
            "extraction_method": ent.extraction_method,
            "created_at": ent.created_at.isoformat(),
        }
        for ent in entities
    ]

    return {
        "report_id": report_id,
        "total": total_count,
        "page": page,
        "limit": limit,
        "items": items,
    }


@router.get("/entities/{entity_id}")
def get_entity_by_id(entity_id: str, db: Session = Depends(get_db)):
    """Fetch single extracted entity with complete provenance information."""
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found.")

    return {
        "id": entity.id,
        "report_id": entity.report_id,
        "type": entity.type,
        "value": entity.value,
        "normalized_value": entity.normalized_value,
        "confidence": entity.confidence,
        "source_page": entity.source_page,
        "source_report": entity.source_report,
        "extraction_method": entity.extraction_method,
        "created_at": entity.created_at.isoformat(),
    }
