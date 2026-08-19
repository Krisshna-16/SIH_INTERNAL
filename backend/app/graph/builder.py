import logging
from typing import Optional, List
import networkx as nx
from sqlalchemy.orm import Session
from app.models.report import Report
from app.models.evidence import Evidence
from app.models.relationship import Relationship

logger = logging.getLogger(__name__)


def build_report_graph(
    report_id: str,
    min_confidence: Optional[float] = None,
    relationship_types: Optional[List[str]] = None,
    db: Session = None,
) -> nx.DiGraph:
    """
    Constructs a NetworkX DiGraph representation of relationships for a report.
    
    ISOLATED NODE EXCLUSION & DETERMINISM:
    Only Evidence entities participating in at least one valid Relationship are added as graph nodes.
    The graph is purely derived from DB state and rebuildable on-demand.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise ValueError(f"Report '{report_id}' not found.")

    query = db.query(Relationship).filter(Relationship.report_id == report_id)

    if min_confidence is not None:
        query = query.filter(Relationship.confidence >= min_confidence)

    if relationship_types and len(relationship_types) > 0:
        cleaned_types = [t.upper() for t in relationship_types if t.upper() != "ALL"]
        if cleaned_types:
            query = query.filter(Relationship.relationship_type.in_(cleaned_types))

    rel_rows = query.all()

    G = nx.DiGraph(report_id=report_id, filename=report.filename)

    if not rel_rows:
        return G

    # Collect participating evidence IDs
    evidence_ids = set()
    for rel in rel_rows:
        evidence_ids.add(rel.source_evidence_id)
        evidence_ids.add(rel.target_evidence_id)

    # Fetch participating Evidence records
    evidence_rows = db.query(Evidence).filter(Evidence.evidence_id.in_(list(evidence_ids))).all()
    ev_map = {ev.evidence_id: ev for ev in evidence_rows}

    # Add Nodes (only participating evidence)
    for ev_id, ev in ev_map.items():
        G.add_node(
            ev_id,
            evidence_id=ev.evidence_id,
            evidence_type=ev.evidence_type,
            value=ev.value,
            normalized_value=ev.normalized_value,
            confidence=ev.confidence,
            source_page=ev.source_page,
            source_report=ev.source_report,
        )

    # Add Edges
    for rel in rel_rows:
        G.add_edge(
            rel.source_evidence_id,
            rel.target_evidence_id,
            relationship_id=rel.id,
            relationship_type=rel.relationship_type,
            classification=rel.classification,
            rule_id=rel.rule_id,
            explanation=rel.explanation,
            confidence=rel.confidence,
        )

    logger.info(f"Built Knowledge Graph for '{report_id}': {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")
    return G
