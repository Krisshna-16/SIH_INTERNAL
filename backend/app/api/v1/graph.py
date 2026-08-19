from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.relationship import Relationship
from app.models.evidence import Evidence
from app.graph.builder import build_report_graph
from app.graph.serializer import graph_to_frontend_json, get_node_neighborhood
from app.graph.metrics import compute_graph_metrics

router = APIRouter(tags=["graph"])


@router.get("/reports/{report_id}/graph/summary")
def get_graph_summary(report_id: str, db: Session = Depends(get_db)):
    """
    Returns knowledge graph summary metrics (node count, edge count, top degree centrality nodes).
    Registered BEFORE /graph/nodes/... and /graph/edges/... to avoid route collisions.
    """
    try:
        G = build_report_graph(report_id=report_id, db=db)
        metrics = compute_graph_metrics(G)
        return {
            "report_id": report_id,
            **metrics,
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.get("/reports/{report_id}/graph")
def get_report_graph(
    report_id: str,
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Filter edges by min confidence"),
    relationship_type: Optional[str] = Query(None, description="Filter edges by relationship type (e.g. USED, LOCATED_AT)"),
    db: Session = Depends(get_db),
):
    """
    Retrieves knowledge graph nodes and edges for visual forensic exploration.
    """
    rel_types = [t.strip() for t in relationship_type.split(",")] if relationship_type else None

    try:
        G = build_report_graph(
            report_id=report_id,
            min_confidence=min_confidence,
            relationship_types=rel_types,
            db=db,
        )
        return {
            "report_id": report_id,
            **graph_to_frontend_json(G),
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build graph: {str(e)}"
        )


@router.get("/reports/{report_id}/graph/nodes/{evidence_id}/neighborhood")
def get_neighborhood(
    report_id: str,
    evidence_id: str,
    depth: int = Query(1, ge=1, description="Hop depth (1 to 3)"),
    db: Session = Depends(get_db),
):
    """
    Node-centric graph expansion endpoint. Returns subgraph within `depth` hops of target node.
    """
    if depth > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Depth parameter cannot exceed 3."
        )

    try:
        G = build_report_graph(report_id=report_id, db=db)
        subgraph_data = get_node_neighborhood(G, evidence_id=evidence_id, depth=depth)
        return {
            "report_id": report_id,
            "target_evidence_id": evidence_id,
            "depth": depth,
            **subgraph_data,
        }
    except ValueError as ve:
        err_msg = str(ve)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)


@router.get("/reports/{report_id}/graph/edges/{relationship_id}/explanation")
def get_edge_explanation(
    report_id: str,
    relationship_id: str,
    db: Session = Depends(get_db),
):
    """
    Drill-down endpoint returning full rule explanation and source/target evidence details for a specific graph edge.
    """
    rel = (
        db.query(Relationship)
        .filter(Relationship.report_id == report_id, Relationship.id == relationship_id)
        .first()
    )
    if not rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship '{relationship_id}' not found for report '{report_id}'."
        )

    source_ev = db.query(Evidence).filter(Evidence.evidence_id == rel.source_evidence_id).first()
    target_ev = db.query(Evidence).filter(Evidence.evidence_id == rel.target_evidence_id).first()

    return {
        "relationship_id": rel.id,
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
    }
