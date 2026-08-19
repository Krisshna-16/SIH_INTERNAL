from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.timeline.filters import TimelineFilters
from app.timeline.assembler import get_report_timeline, get_timeline_summary, parse_iso_datetime

router = APIRouter(tags=["timeline"])


@router.get("/reports/{report_id}/timeline/summary")
def get_summary(report_id: str, db: Session = Depends(get_db)):
    """
    Returns timeline summary metrics including earliest/latest timestamps and count breakdown.
    Registered BEFORE /timeline/entities/{entity_value} to prevent route collisions.
    """
    try:
        summary = get_timeline_summary(report_id=report_id, db=db)
        res = summary.model_dump()
        res["has_timestamped_evidence"] = summary.total_entries > 0
        return res
    except ValueError as ve:
        if "not found" in str(ve).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assemble timeline summary: {str(e)}"
        )


@router.get("/reports/{report_id}/timeline")
def get_timeline(
    report_id: str,
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format, e.g. 2024-01-01T00:00:00)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format, e.g. 2024-12-31T23:59:59)"),
    evidence_type: Optional[str] = Query(None, description="Filter by evidence type (comma-separated or single)"),
    entity_value: Optional[str] = Query(None, description="Filter timeline entries matching entity value"),
    classification: Optional[str] = Query(None, description="Filter by classification (FACT or INFERENCE)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db),
):
    """
    Retrieves chronologically sorted timeline entries for a report with filtering and pagination.
    """
    if start_date and end_date:
        s_dt = parse_iso_datetime(start_date)
        e_dt = parse_iso_datetime(end_date)
        if s_dt and e_dt and s_dt > e_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date range: start_date cannot be after end_date."
            )

    ev_types = [t.strip() for t in evidence_type.split(",")] if evidence_type else None

    filters = TimelineFilters(
        start_date=start_date,
        end_date=end_date,
        evidence_types=ev_types,
        entity_value=entity_value,
        classification=classification,
        page=page,
        page_size=page_size,
    )

    try:
        items, total_count = get_report_timeline(report_id=report_id, filters=filters, db=db)
        return {
            "report_id": report_id,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "items": [item.model_dump() for item in items],
        }
    except ValueError as ve:
        if "not found" in str(ve).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assemble timeline: {str(e)}"
        )


@router.get("/reports/{report_id}/timeline/entities/{entity_value}")
def get_entity_timeline(
    report_id: str,
    entity_value: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Convenience endpoint returning timeline entries filtered to a specific entity value.
    """
    filters = TimelineFilters(
        entity_value=entity_value,
        page=page,
        page_size=page_size,
    )

    try:
        items, total_count = get_report_timeline(report_id=report_id, filters=filters, db=db)
        return {
            "report_id": report_id,
            "entity_value": entity_value,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "items": [item.model_dump() for item in items],
        }
    except ValueError as ve:
        if "not found" in str(ve).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
