import json
import logging
import uuid
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.report import Report
from app.models.evidence import Evidence
from app.models.relationship import Relationship
from app.models.finding import Finding
from app.models.audit_log import AuditLog

from app.query.intent_classifier import classify_intent, QueryIntent, QueryIntentType
from app.query.entity_resolver import extract_question_entities, ResolvedEntity
from app.timeline.assembler import get_report_timeline
from app.timeline.filters import TimelineFilters
from app.graph.builder import build_report_graph
from app.graph.serializer import get_node_neighborhood

logger = logging.getLogger(__name__)


class RetrievalStatus(str, Enum):
    RESULTS_FOUND = "RESULTS_FOUND"
    NO_EVIDENCE_FOUND = "NO_EVIDENCE_FOUND"
    ENTITY_NOT_RESOLVED = "ENTITY_NOT_RESOLVED"


class RetrievalResult(BaseModel):
    """
    Self-contained, provenance-complete Retrieval Result passed to Phase 8 LLM synthesis.
    
    PRIVACY / REDACTION HOOK NOTE:
    In Phase 9 (Privacy Gateway), requests passing RetrievalResult to Phase 8 LLM
    will be intercepted to apply pseudonymization / RBAC redaction prior to LLM context construction.
    """
    query_id: str = Field(..., description="Unique query execution ID")
    report_id: str = Field(..., description="Target report ID")
    original_question: str = Field(..., description="Investigator's natural language question")
    intent: QueryIntent = Field(..., description="Classified intent with confidence score")
    resolved_entities: List[ResolvedEntity] = Field(default_factory=list, description="Resolved entity mentions")
    evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Retrieved ground-truth Evidence records")
    relationships: List[Dict[str, Any]] = Field(default_factory=list, description="Retrieved Relationship records")
    findings: List[Dict[str, Any]] = Field(default_factory=list, description="Retrieved Finding records")
    timeline_entries: List[Dict[str, Any]] = Field(default_factory=list, description="Retrieved Timeline entries")
    graph_neighborhood: Optional[Dict[str, Any]] = Field(None, description="Retrieved Graph neighborhood")
    status: RetrievalStatus = Field(..., description="Structured retrieval outcome status")
    retrieval_summary: str = Field(..., description="Human and machine readable retrieval summary for audit")


def serialize_evidence(ev: Evidence) -> Dict[str, Any]:
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
    }


def serialize_relationship(rel: Relationship, db: Session) -> Dict[str, Any]:
    source_ev = db.query(Evidence).filter(Evidence.evidence_id == rel.source_evidence_id).first()
    target_ev = db.query(Evidence).filter(Evidence.evidence_id == rel.target_evidence_id).first()
    return {
        "id": rel.id,
        "source_evidence_id": rel.source_evidence_id,
        "source_value": source_ev.value if source_ev else "Unknown",
        "target_evidence_id": rel.target_evidence_id,
        "target_value": target_ev.value if target_ev else "Unknown",
        "relationship_type": rel.relationship_type,
        "classification": rel.classification,
        "rule_id": rel.rule_id,
        "explanation": rel.explanation,
        "confidence": rel.confidence,
    }


def serialize_finding(fnd: Finding) -> Dict[str, Any]:
    try:
        ev_ids = json.loads(fnd.related_evidence_ids)
    except Exception:
        ev_ids = []
    return {
        "id": fnd.id,
        "finding_type": fnd.finding_type,
        "classification": fnd.classification,
        "rule_id": fnd.rule_id,
        "rule_name": fnd.rule_name,
        "explanation": fnd.explanation,
        "related_evidence_ids": ev_ids,
        "severity": fnd.severity,
    }


def retrieve_for_query(report_id: str, question: str, db: Session) -> RetrievalResult:
    """
    Executes the structured Query Pipeline: Question -> Intent -> Entity Resolution -> Ground-Truth Retrieval.
    100% deterministic, explainable, and zero LLM calls.
    """
    if not question or not question.strip():
        raise ValueError("Question string cannot be empty.")

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise ValueError(f"Report '{report_id}' not found.")

    query_id = f"QRY-{uuid.uuid4().hex[:8].upper()}"
    q_clean = question.strip()

    # 1. Classify Intent
    intent = classify_intent(q_clean)

    # 2. Resolve Question Entities
    resolved_entities = extract_question_entities(q_clean, report_id, db)

    # Collect matched evidence IDs
    matched_ev_ids: List[str] = []
    unmatched_mentions: List[str] = []
    for rent in resolved_entities:
        if rent.matched:
            matched_ev_ids.extend(rent.evidence_ids)
        else:
            unmatched_mentions.append(rent.mention_text)

    matched_ev_ids = list(dict.fromkeys(matched_ev_ids))

    retrieved_ev: List[Evidence] = []
    retrieved_rels: List[Relationship] = []
    retrieved_fnds: List[Finding] = []
    retrieved_tl: List[Any] = []
    retrieved_graph: Optional[Dict[str, Any]] = None
    partial_notes: List[str] = []

    # 3. Handle ENTITY_NOT_RESOLVED path if entity was mentioned but unverified in report
    if resolved_entities and not matched_ev_ids:
        mentions_str = ", ".join([f"'{m}'" for m in unmatched_mentions])
        summary_text = (
            f"Extracted entity mention(s) [{mentions_str}] from question, but no matching ground-truth evidence "
            f"was found in report '{report.filename}' ({report_id})."
        )

        db.add(AuditLog(
            actor="investigator",
            action="INVESTIGATOR_QUERY",
            report_id=report_id,
            details=json.dumps({
                "query_id": query_id,
                "question": q_clean,
                "intent": intent.intent_type.value,
                "status": RetrievalStatus.ENTITY_NOT_RESOLVED.value,
                "evidence_count": 0,
            }),
        ))
        db.commit()

        return RetrievalResult(
            query_id=query_id,
            report_id=report_id,
            original_question=q_clean,
            intent=intent,
            resolved_entities=resolved_entities,
            evidence=[],
            relationships=[],
            findings=[],
            timeline_entries=[],
            graph_neighborhood=None,
            status=RetrievalStatus.ENTITY_NOT_RESOLVED,
            retrieval_summary=summary_text,
        )

    # 4. Dispatch Intent Retrieval Logic
    if intent.intent_type == QueryIntentType.COMMUNICATION_QUERY:
        if matched_ev_ids:
            retrieved_ev = db.query(Evidence).filter(Evidence.evidence_id.in_(matched_ev_ids)).all()
            retrieved_rels = (
                db.query(Relationship)
                .filter(
                    Relationship.report_id == report_id,
                    (Relationship.source_evidence_id.in_(matched_ev_ids)) | (Relationship.target_evidence_id.in_(matched_ev_ids)),
                )
                .all()
            )
        else:
            retrieved_rels = (
                db.query(Relationship)
                .filter(
                    Relationship.report_id == report_id,
                    Relationship.relationship_type.in_(["CONTACTED", "USED", "ASSOCIATED_WITH"]),
                )
                .limit(20)
                .all()
            )
            rel_ev_ids = [r.source_evidence_id for r in retrieved_rels] + [r.target_evidence_id for r in retrieved_rels]
            if rel_ev_ids:
                retrieved_ev = db.query(Evidence).filter(Evidence.evidence_id.in_(list(set(rel_ev_ids)))).all()

    elif intent.intent_type == QueryIntentType.RELATIONSHIP_QUERY:
        if matched_ev_ids:
            retrieved_ev = db.query(Evidence).filter(Evidence.evidence_id.in_(matched_ev_ids)).all()
            retrieved_rels = (
                db.query(Relationship)
                .filter(
                    Relationship.report_id == report_id,
                    (Relationship.source_evidence_id.in_(matched_ev_ids)) | (Relationship.target_evidence_id.in_(matched_ev_ids)),
                )
                .all()
            )
            # Try graph neighborhood retrieval
            try:
                G = build_report_graph(report_id, db=db)
                if matched_ev_ids[0] in G:
                    retrieved_graph = get_node_neighborhood(G, matched_ev_ids[0], depth=1)
            except Exception as ge:
                logger.warning(f"Graph neighborhood sub-retrieval notice: {ge}")
                partial_notes.append(f"Graph sub-retrieval notice: {str(ge)}")
        else:
            retrieved_rels = db.query(Relationship).filter(Relationship.report_id == report_id).limit(20).all()

    elif intent.intent_type == QueryIntentType.TIMELINE_QUERY:
        try:
            t_filters = TimelineFilters(
                entity_value=resolved_entities[0].mention_text if resolved_entities else None,
                page=1,
                page_size=50,
            )
            t_entries, _ = get_report_timeline(report_id, t_filters, db)
            retrieved_tl = [e.model_dump() for e in t_entries]
        except Exception as te:
            logger.warning(f"Timeline sub-retrieval notice: {te}")
            partial_notes.append(f"Timeline sub-retrieval notice: {str(te)}")

        if matched_ev_ids:
            retrieved_ev = db.query(Evidence).filter(Evidence.evidence_id.in_(matched_ev_ids)).all()

    elif intent.intent_type == QueryIntentType.FINDING_QUERY:
        retrieved_fnds = db.query(Finding).filter(Finding.report_id == report_id).all()
        if matched_ev_ids:
            retrieved_ev = db.query(Evidence).filter(Evidence.evidence_id.in_(matched_ev_ids)).all()

    else:  # ENTITY_LOOKUP or UNKNOWN fallback
        if matched_ev_ids:
            retrieved_ev = db.query(Evidence).filter(Evidence.evidence_id.in_(matched_ev_ids)).all()
            retrieved_rels = (
                db.query(Relationship)
                .filter(
                    Relationship.report_id == report_id,
                    (Relationship.source_evidence_id.in_(matched_ev_ids)) | (Relationship.target_evidence_id.in_(matched_ev_ids)),
                )
                .all()
            )
            # Find referencing findings
            fnd_candidates = db.query(Finding).filter(Finding.report_id == report_id).all()
            for f in fnd_candidates:
                try:
                    f_ids = json.loads(f.related_evidence_ids)
                    if any(ev_id in f_ids for ev_id in matched_ev_ids):
                        retrieved_fnds.append(f)
                except Exception:
                    pass
        else:
            # General report search fallback
            retrieved_ev = db.query(Evidence).filter(Evidence.report_id == report_id).limit(10).all()

    # Serialize objects
    ser_ev = [serialize_evidence(e) for e in retrieved_ev]
    ser_rel = [serialize_relationship(r, db) for r in retrieved_rels]
    ser_fnd = [serialize_finding(f) for f in retrieved_fnds]

    # Evaluate Status
    total_found = len(ser_ev) + len(ser_rel) + len(ser_fnd) + len(retrieved_tl)
    if total_found > 0:
        status = RetrievalStatus.RESULTS_FOUND
        summary_text = (
            f"Retrieved {len(ser_ev)} evidence items, {len(ser_rel)} relationships, "
            f"{len(ser_fnd)} findings, and {len(retrieved_tl)} timeline events for intent '{intent.intent_type}'."
        )
    else:
        status = RetrievalStatus.NO_EVIDENCE_FOUND
        summary_text = f"No verified evidence found matching question '{q_clean}' in report '{report.filename}'."

    if partial_notes:
        summary_text += " (" + "; ".join(partial_notes) + ")"

    # Write Audit Log
    db.add(AuditLog(
        actor="investigator",
        action="INVESTIGATOR_QUERY",
        report_id=report_id,
        details=json.dumps({
            "query_id": query_id,
            "question": q_clean,
            "intent": intent.intent_type.value,
            "status": status.value,
            "evidence_count": len(ser_ev),
            "relationship_count": len(ser_rel),
            "finding_count": len(ser_fnd),
        }),
    ))
    db.commit()

    return RetrievalResult(
        query_id=query_id,
        report_id=report_id,
        original_question=q_clean,
        intent=intent,
        resolved_entities=resolved_entities,
        evidence=ser_ev,
        relationships=ser_rel,
        findings=ser_fnd,
        timeline_entries=retrieved_tl,
        graph_neighborhood=retrieved_graph,
        status=status,
        retrieval_summary=summary_text,
    )
