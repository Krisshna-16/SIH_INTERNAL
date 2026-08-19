import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.report import Report
from app.models.evidence import Evidence
from app.models.audit_log import AuditLog
from app.evidence.consolidator import consolidate_report_evidence

router = APIRouter(tags=["evidence"])


@router.post("/reports/{report_id}/evidence/consolidate")
def consolidate_evidence(report_id: str, db: Session = Depends(get_db)):
    """Triggers canonical evidence consolidation for a given report."""
    try:
        summary = consolidate_report_evidence(report_id=report_id, db=db)
        return summary
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evidence consolidation failed: {str(e)}"
        )


@router.get("/reports/{report_id}/evidence")
def list_report_evidence(
    report_id: str,
    evidence_type: Optional[str] = Query(None, description="Filter by evidence type (e.g. PERSON, PHONE, EMAIL, LOCATION)"),
    min_confidence: Optional[float] = Query(None, description="Filter evidence with confidence >= min_confidence"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db),
):
    """Lists consolidated evidence for a report with filtering and pagination."""
    print("[DEBUG list_report_evidence] db.bind:", db.bind)
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")

    query = db.query(Evidence).filter(Evidence.report_id == report_id)

    if evidence_type and evidence_type != "ALL":
        query = query.filter(Evidence.evidence_type == evidence_type.upper())
    if min_confidence is not None:
        query = query.filter(Evidence.confidence >= min_confidence)

    total_count = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(Evidence.source_page.asc(), Evidence.confidence.desc()).offset(offset).limit(page_size).all()

    result_items = []
    for ev in items:
        try:
            prov = json.loads(ev.provenance_detail)
        except Exception:
            prov = {"raw": ev.provenance_detail}

        result_items.append({
            "evidence_id": ev.evidence_id,
            "report_id": ev.report_id,
            "evidence_type": ev.evidence_type,
            "value": ev.value,
            "normalized_value": ev.normalized_value,
            "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
            "confidence": ev.confidence,
            "source_page": ev.source_page,
            "source_report": ev.source_report,
            "provenance_detail": prov,
            "derived_from_entity_id": ev.derived_from_entity_id,
            "created_at": ev.created_at.isoformat(),
        })

    return {
        "report_id": report_id,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "items": result_items,
    }


@router.get("/reports/{report_id}/evidence/summary")
def get_evidence_summary(report_id: str, db: Session = Depends(get_db)):
    """Returns evidence type breakdown counts for executive dashboarding."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")

    counts_query = (
        db.query(Evidence.evidence_type, func.count(Evidence.evidence_id))
        .filter(Evidence.report_id == report_id)
        .group_by(Evidence.evidence_type)
        .all()
    )

    counts = {t: cnt for t, cnt in counts_query}
    total = sum(counts.values())

    return {
        "report_id": report_id,
        "filename": report.filename,
        "page_count": report.page_count,
        "total_evidence": total,
        "type_breakdown": counts,
    }


@router.get("/evidence/{evidence_id}")
def get_evidence_by_id(evidence_id: str, db: Session = Depends(get_db)):
    """
    Retrieves full evidence record with complete provenance details.
    Logs an EVIDENCE_VIEWED entry in AuditLog.
    """
    print("[DEBUG get_evidence_by_id] db.bind:", db.bind)
    ev = db.query(Evidence).filter(Evidence.evidence_id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found.")

    # Log audit entry
    audit_entry = AuditLog(
        actor="system",
        action="EVIDENCE_VIEWED",
        evidence_id=evidence_id,
        report_id=ev.report_id,
        details=json.dumps({"accessed_at": ev.created_at.isoformat()}),
    )
    db.add(audit_entry)
    db.commit()

    try:
        prov = json.loads(ev.provenance_detail)
    except Exception:
        prov = {"raw": ev.provenance_detail}

    return {
        "evidence_id": ev.evidence_id,
        "report_id": ev.report_id,
        "evidence_type": ev.evidence_type,
        "value": ev.value,
        "normalized_value": ev.normalized_value,
        "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
        "confidence": ev.confidence,
        "source_page": ev.source_page,
        "source_report": ev.source_report,
        "provenance_detail": prov,
        "derived_from_entity_id": ev.derived_from_entity_id,
        "created_at": ev.created_at.isoformat(),
    }
