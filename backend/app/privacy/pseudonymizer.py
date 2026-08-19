import re
import logging
from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.models.evidence import Evidence
from app.models.pseudonym_mapping import PseudonymMapping
from app.query.retriever import RetrievalResult

logger = logging.getLogger(__name__)


def get_or_create_pseudonym(
    report_id: str,
    real_value: str,
    entity_type: str = "ENTITY",
    evidence_id: Optional[str] = None,
    db: Session = None,
) -> str:
    """
    Retrieves or generates a deterministic pseudonym for a real identity within a report.
    Idempotent check-then-insert pattern.
    """
    if not real_value or not real_value.strip():
        return real_value

    clean_val = real_value.strip()

    # Query existing mapping
    existing = (
        db.query(PseudonymMapping)
        .filter(PseudonymMapping.report_id == report_id, PseudonymMapping.real_value == clean_val)
        .first()
    )
    if existing:
        return existing.pseudonym

    # If entity_type is generic or missing, try lookup via evidence_id or value regex
    resolved_type = entity_type
    if (not resolved_type or resolved_type == "ENTITY") and evidence_id:
        ev_row = db.query(Evidence).filter(Evidence.evidence_id == evidence_id).first()
        if ev_row and ev_row.evidence_type:
            resolved_type = ev_row.evidence_type

    if not resolved_type or resolved_type == "ENTITY":
        if re.search(r"^\+?\d{8,15}$", clean_val.replace(" ", "").replace("-", "")):
            resolved_type = "PHONE"
        elif "@" in clean_val and "." in clean_val:
            resolved_type = "EMAIL"

    clean_type = resolved_type.upper() if resolved_type else "ENTITY"
    count = (
        db.query(PseudonymMapping)
        .filter(PseudonymMapping.report_id == report_id, PseudonymMapping.entity_type == clean_type)
        .count()
    )

    pseudonym = f"{clean_type}_{count + 1:03d}"

    new_mapping = PseudonymMapping(
        report_id=report_id,
        real_value=clean_val,
        pseudonym=pseudonym,
        entity_type=clean_type,
        first_seen_evidence_id=evidence_id,
    )
    db.add(new_mapping)
    db.commit()

    logger.info(f"Created PseudonymMapping for report '{report_id}': '{clean_val}' -> '{pseudonym}'")
    return pseudonym


def pseudonymize_retrieval_result(retrieval_result: RetrievalResult, db: Session) -> RetrievalResult:
    """
    Produces a pseudonymized DEEP COPY of RetrievalResult for LLM inference.
    Replaces all identifying names, phone numbers, emails, and locations with deterministic pseudonyms.
    Original RetrievalResult remains untouched for UI ground-truth references.
    """
    report_id = retrieval_result.report_id
    res_dict = retrieval_result.model_dump()

    # Build lookup map of all real values to pseudonyms for this report
    mapping_lookup: Dict[str, str] = {}

    # 1. Pseudonymize Evidence List
    if "evidence" in res_dict:
        for ev in res_dict["evidence"]:
            etype = ev.get("evidence_type", "ENTITY")
            ev_id = ev.get("evidence_id")

            if ev.get("value"):
                real_val = ev["value"]
                pseudo = get_or_create_pseudonym(report_id, real_val, etype, ev_id, db)
                mapping_lookup[real_val] = pseudo
                ev["value"] = pseudo

            if ev.get("normalized_value"):
                real_norm = ev["normalized_value"]
                pseudo_norm = get_or_create_pseudonym(report_id, real_norm, etype, ev_id, db)
                mapping_lookup[real_norm] = pseudo_norm
                ev["normalized_value"] = pseudo_norm

    # 2. Pseudonymize Relationships List
    if "relationships" in res_dict:
        for rel in res_dict["relationships"]:
            s_ev_id = rel.get("source_evidence_id")
            t_ev_id = rel.get("target_evidence_id")

            if rel.get("source_value"):
                real_val = rel["source_value"]
                pseudo = get_or_create_pseudonym(report_id, real_val, rel.get("source_type", "ENTITY"), s_ev_id, db)
                mapping_lookup[real_val] = pseudo
                rel["source_value"] = pseudo

            if rel.get("target_value"):
                real_val = rel["target_value"]
                pseudo = get_or_create_pseudonym(report_id, real_val, rel.get("target_type", "ENTITY"), t_ev_id, db)
                mapping_lookup[real_val] = pseudo
                rel["target_value"] = pseudo

            if rel.get("explanation"):
                exp_text = rel["explanation"]
                for r_val, p_val in mapping_lookup.items():
                    exp_text = exp_text.replace(r_val, p_val)
                rel["explanation"] = exp_text

    # 3. Pseudonymize Findings List
    if "findings" in res_dict:
        for fnd in res_dict["findings"]:
            if fnd.get("explanation"):
                exp_text = fnd["explanation"]
                for r_val, p_val in mapping_lookup.items():
                    exp_text = exp_text.replace(r_val, p_val)
                fnd["explanation"] = exp_text

    # 4. Pseudonymize Timeline Entries List
    if "timeline_entries" in res_dict:
        for tle in res_dict["timeline_entries"]:
            if tle.get("related_values"):
                new_rel_vals = []
                for rv in tle["related_values"]:
                    pseudo = mapping_lookup.get(rv, get_or_create_pseudonym(report_id, rv, "ENTITY", None, db))
                    new_rel_vals.append(pseudo)
                tle["related_values"] = new_rel_vals

            if tle.get("title"):
                title_text = tle["title"]
                for r_val, p_val in mapping_lookup.items():
                    title_text = title_text.replace(r_val, p_val)
                tle["title"] = title_text

    # 5. Pseudonymize Resolved Entities List
    if "resolved_entities" in res_dict:
        for rent in res_dict["resolved_entities"]:
            if rent.get("mention_text"):
                r_text = rent["mention_text"]
                rent["mention_text"] = mapping_lookup.get(r_text, get_or_create_pseudonym(report_id, r_text, rent.get("entity_type", "ENTITY"), None, db))

            if rent.get("matched_values"):
                rent["matched_values"] = [mapping_lookup.get(mv, get_or_create_pseudonym(report_id, mv, rent.get("entity_type", "ENTITY"), None, db)) for mv in rent["matched_values"]]

    return RetrievalResult(**res_dict)


def resolve_pseudonyms_in_text(text: str, report_id: str, db: Session) -> str:
    """
    Reverses pseudonym tokens back to real ground-truth values.
    Used ONLY when preparing the final answer for display to the authenticated investigator in the UI.
    NEVER sent to any LLM.
    """
    if not text or not text.strip():
        return text

    mappings = db.query(PseudonymMapping).filter(PseudonymMapping.report_id == report_id).all()
    if not mappings:
        return text

    resolved_text = text
    # Sort mappings by pseudonym length descending to prevent partial token replacement
    sorted_mappings = sorted(mappings, key=lambda m: len(m.pseudonym), reverse=True)

    for m in sorted_mappings:
        resolved_text = re.sub(r"\b" + re.escape(m.pseudonym) + r"\b", m.real_value, resolved_text)

    return resolved_text
