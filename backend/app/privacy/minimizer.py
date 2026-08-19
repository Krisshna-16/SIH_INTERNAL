from typing import Dict, Any
from app.query.retriever import RetrievalResult


def minimize_for_external(pseudonymized_result: RetrievalResult) -> Dict[str, Any]:
    """
    Strips raw file paths, source report filenames, page numbers, and free-text provenance details
    from a pseudonymized RetrievalResult prior to external LLM dispatch.
    
    PRIVACY MINIMIZATION GUARANTEE:
    Retains only pseudonyms, relationship predicates, classification taxonomy, and evidence IDs.
    Raw source provenance strings are completely stripped.
    """
    if not isinstance(pseudonymized_result, RetrievalResult):
        raise TypeError("minimize_for_external strictly expects a RetrievalResult object.")

    minimized_evidence = []
    for ev in pseudonymized_result.evidence:
        minimized_evidence.append({
            "evidence_id": ev.get("evidence_id"),
            "evidence_type": ev.get("evidence_type"),
            "value": ev.get("value"),  # Already pseudonymized
            "confidence": ev.get("confidence", 1.0),
        })

    minimized_relationships = []
    for rel in pseudonymized_result.relationships:
        minimized_relationships.append({
            "id": rel.get("id"),
            "source_evidence_id": rel.get("source_evidence_id"),
            "source_value": rel.get("source_value"),  # Pseudonymized
            "target_evidence_id": rel.get("target_evidence_id"),
            "target_value": rel.get("target_value"),  # Pseudonymized
            "relationship_type": rel.get("relationship_type"),
            "classification": rel.get("classification"),
            "rule_id": rel.get("rule_id"),
            "explanation": rel.get("explanation"),  # Pseudonymized
            "confidence": rel.get("confidence", 1.0),
        })

    minimized_findings = []
    for fnd in pseudonymized_result.findings:
        minimized_findings.append({
            "id": fnd.get("id"),
            "finding_type": fnd.get("finding_type"),
            "classification": fnd.get("classification"),
            "rule_id": fnd.get("rule_id"),
            "rule_name": fnd.get("rule_name"),
            "explanation": fnd.get("explanation"),  # Pseudonymized
            "severity": fnd.get("severity"),
            "related_evidence_ids": fnd.get("related_evidence_ids", []),
        })

    minimized_timeline = []
    for tle in pseudonymized_result.timeline_entries:
        minimized_timeline.append({
            "entry_id": tle.get("entry_id"),
            "timestamp": tle.get("timestamp"),
            "event_type": tle.get("event_type"),
            "title": tle.get("title"),  # Pseudonymized
            "related_values": tle.get("related_values", []),  # Pseudonymized
            "classification": tle.get("classification"),
        })

    return {
        "query_id": pseudonymized_result.query_id,
        "report_id": pseudonymized_result.report_id,
        "original_question": pseudonymized_result.original_question,
        "intent": pseudonymized_result.intent.model_dump(),
        "resolved_entities": [rent.model_dump() for rent in pseudonymized_result.resolved_entities],
        "evidence": minimized_evidence,
        "relationships": minimized_relationships,
        "findings": minimized_findings,
        "timeline_entries": minimized_timeline,
        "status": pseudonymized_result.status.value,
        "retrieval_summary": pseudonymized_result.retrieval_summary,
        "privacy_level": "MINIMIZED_PSEUDONYMIZED",
    }
