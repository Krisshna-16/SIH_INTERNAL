import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.report import Report
from app.models.evidence import Evidence
from app.models.relationship import Relationship
from app.models.finding import Finding
from app.symbolic.engine import SymbolicEngine

router = APIRouter(tags=["symbolic"])


def parse_json_value(val: Any, default: Any) -> Any:
    """Helper to parse JSON columns whether returned as native Python objects or JSON strings."""
    if isinstance(val, (list, dict)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return default
    return default


@router.post("/reports/{report_id}/analyze")
def run_analysis(report_id: str, db: Session = Depends(get_db)):
    """Triggers Symbolic AI rule engine analysis for a given report."""
    engine = SymbolicEngine()
    try:
        summary = engine.process_report(report_id=report_id, db=db)
        return summary
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Symbolic AI analysis failed: {str(e)}"
        )


@router.get("/reports/{report_id}/relationships")
def list_relationships(
    report_id: str,
    relationship_type: Optional[str] = Query(None, description="Filter by relationship type (e.g. ASSOCIATED_WITH, USED, LOCATED_AT)"),
    classification: Optional[str] = Query(None, description="Filter by classification (FACT or INFERENCE)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db),
):
    """Lists derived relationships for a report with filtering and source/target evidence details."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")

    query = db.query(Relationship).filter(Relationship.report_id == report_id)

    if relationship_type and relationship_type != "ALL":
        query = query.filter(Relationship.relationship_type == relationship_type.upper())
    if classification and classification != "ALL":
        query = query.filter(Relationship.classification == classification.upper())

    total_count = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(Relationship.created_at.desc()).offset(offset).limit(page_size).all()

    # Batch fetch evidence details to eliminate N+1 query overhead
    ev_ids = set()
    for rel in items:
        ev_ids.add(rel.source_evidence_id)
        ev_ids.add(rel.target_evidence_id)

    ev_map: Dict[str, Evidence] = {}
    if ev_ids:
        ev_rows = db.query(Evidence).filter(Evidence.evidence_id.in_(ev_ids)).all()
        ev_map = {e.evidence_id: e for e in ev_rows}

    result = []
    for rel in items:
        source_ev = ev_map.get(rel.source_evidence_id)
        target_ev = ev_map.get(rel.target_evidence_id)

        result.append({
            "id": rel.id,
            "report_id": rel.report_id,
            "source_evidence_id": rel.source_evidence_id,
            "source_value": source_ev.value if source_ev else "Unknown",
            "source_type": source_ev.evidence_type if source_ev else "UNKNOWN",
            "target_evidence_id": rel.target_evidence_id,
            "target_value": target_ev.value if target_ev else "Unknown",
            "target_type": target_ev.evidence_type if target_ev else "UNKNOWN",
            "relationship_type": rel.relationship_type,
            "classification": rel.classification,
            "rule_id": rel.rule_id,
            "explanation": rel.explanation,
            "confidence": rel.confidence,
            "created_at": rel.created_at.isoformat(),
        })

    return {
        "report_id": report_id,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "items": result,
    }


@router.get("/reports/{report_id}/findings")
def list_findings(
    report_id: str,
    finding_type: Optional[str] = Query(None, description="Filter by finding type"),
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MEDIUM, HIGH)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db),
):
    """Lists flagged investigative findings for a report."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")

    query = db.query(Finding).filter(Finding.report_id == report_id)

    if finding_type and finding_type != "ALL":
        query = query.filter(Finding.finding_type == finding_type.upper())
    if severity and severity != "ALL":
        query = query.filter(Finding.severity == severity.upper())

    total_count = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(Finding.severity.desc(), Finding.created_at.desc()).offset(offset).limit(page_size).all()

    result = []
    for fnd in items:
        ev_ids = parse_json_value(fnd.related_evidence_ids, [])
        params = parse_json_value(fnd.parameters_used, {})

        result.append({
            "id": fnd.id,
            "report_id": fnd.report_id,
            "finding_type": fnd.finding_type,
            "classification": fnd.classification,
            "rule_id": fnd.rule_id,
            "rule_name": fnd.rule_name,
            "explanation": fnd.explanation,
            "related_evidence_ids": ev_ids,
            "parameters_used": params,
            "severity": fnd.severity,
            "created_at": fnd.created_at.isoformat(),
        })

    return {
        "report_id": report_id,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "items": result,
    }


@router.get("/findings/{finding_id}")
def get_finding_by_id(finding_id: str, db: Session = Depends(get_db)):
    """
    Retrieves full detail of a finding, resolving related evidence IDs to full Evidence records.
    """
    fnd = db.query(Finding).filter(Finding.id == finding_id).first()
    if not fnd:
        raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found.")

    ev_ids = parse_json_value(fnd.related_evidence_ids, [])
    params = parse_json_value(fnd.parameters_used, {})

    # Resolve related evidence records
    related_evidence = []
    if ev_ids:
        evidence_rows = db.query(Evidence).filter(Evidence.evidence_id.in_(ev_ids)).all()
        for ev in evidence_rows:
            related_evidence.append({
                "evidence_id": ev.evidence_id,
                "evidence_type": ev.evidence_type,
                "value": ev.value,
                "normalized_value": ev.normalized_value,
                "source_page": ev.source_page,
                "source_report": ev.source_report,
                "confidence": ev.confidence,
            })

    return {
        "id": fnd.id,
        "report_id": fnd.report_id,
        "finding_type": fnd.finding_type,
        "classification": fnd.classification,
        "rule_id": fnd.rule_id,
        "rule_name": fnd.rule_name,
        "explanation": fnd.explanation,
        "related_evidence_ids": ev_ids,
        "related_evidence": related_evidence,
        "parameters_used": params,
        "severity": fnd.severity,
        "created_at": fnd.created_at.isoformat(),
    }
