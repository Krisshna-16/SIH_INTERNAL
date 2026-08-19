import re
from typing import List, Dict, Set
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.extraction.pattern_rules import extract_regex_patterns
from app.extraction.spacy_extractor import SpacyExtractor
from app.models.evidence import Evidence


class ResolvedEntity(BaseModel):
    """
    Model representing an entity mention extracted from a question and matched to Evidence ground-truth.
    """
    mention_text: str = Field(..., description="Extracted entity text from question")
    entity_type: str = Field(..., description="Extracted entity type (PERSON, PHONE, EMAIL, LOCATION, etc.)")
    matched: bool = Field(..., description="Whether mention matched evidence in the report")
    evidence_ids: List[str] = Field(default_factory=list, description="Matched Evidence IDs")
    matched_values: List[str] = Field(default_factory=list, description="Matched Evidence ground-truth values")
    confidence: float = Field(..., description="Resolution confidence score")


spacy_extractor = SpacyExtractor()


def extract_question_entities(question: str, report_id: str, db: Session) -> List[ResolvedEntity]:
    """
    Extracts entity mentions from question text using spaCy NER & regex rules,
    then resolves them against existing Evidence ground-truth for the report.
    100% local, deterministic entity resolution.
    """
    if not question or not question.strip():
        return []

    # 1. Run regex extraction on question
    regex_matches = extract_regex_patterns(question)
    candidate_mentions: List[Dict[str, str]] = []
    seen_texts: Set[str] = set()

    for match in regex_matches:
        etype = match[0]
        raw_val = match[1]
        val_clean = raw_val.strip()
        if val_clean and val_clean.lower() not in seen_texts:
            seen_texts.add(val_clean.lower())
            candidate_mentions.append({"mention_text": val_clean, "entity_type": etype})

    # 2. Run spaCy extraction on question
    spacy_dtos = spacy_extractor.extract(page_text=question, page_number=1, report_id="QUESTION")
    for dto in spacy_dtos:
        val_clean = dto.value.strip()
        if val_clean and val_clean.lower() not in seen_texts:
            # Filter out common stop words / question keywords
            if val_clean.lower() not in {"who", "what", "where", "when", "how", "why", "tell", "show", "find", "report", "timeline"}:
                seen_texts.add(val_clean.lower())
                candidate_mentions.append({"mention_text": val_clean, "entity_type": dto.type})

    # Fallback: Capitalized multi-word tokens in question if NER missed them
    words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", question)
    for w in words:
        if w.lower() not in seen_texts and w.lower() not in {"who", "what", "where", "when", "how", "why", "tell", "show", "find", "report", "timeline", "inspector", "suspect"}:
            seen_texts.add(w.lower())
            candidate_mentions.append({"mention_text": w, "entity_type": "PERSON"})

    # Fetch Evidence for report
    evidence_rows = db.query(Evidence).filter(Evidence.report_id == report_id).all()

    resolved_list: List[ResolvedEntity] = []

    for cand in candidate_mentions:
        mtext = cand["mention_text"]
        mtype = cand["entity_type"]
        q_norm = mtext.lower()

        matched_ev_ids = []
        matched_vals = []

        for ev in evidence_rows:
            ev_val_norm = (ev.value or "").lower()
            ev_norm_val_norm = (ev.normalized_value or "").lower()

            if q_norm == ev_val_norm or q_norm == ev_norm_val_norm:
                matched_ev_ids.append(ev.evidence_id)
                matched_vals.append(ev.value)
            elif len(q_norm) >= 3 and (q_norm in ev_val_norm or ev_val_norm in q_norm):
                matched_ev_ids.append(ev.evidence_id)
                matched_vals.append(ev.value)

        # Deduplicate
        matched_ev_ids = list(dict.fromkeys(matched_ev_ids))
        matched_vals = list(dict.fromkeys(matched_vals))

        if matched_ev_ids:
            resolved_list.append(ResolvedEntity(
                mention_text=mtext,
                entity_type=mtype,
                matched=True,
                evidence_ids=matched_ev_ids,
                matched_values=matched_vals,
                confidence=0.95,
            ))
        else:
            resolved_list.append(ResolvedEntity(
                mention_text=mtext,
                entity_type=mtype,
                matched=False,
                evidence_ids=[],
                matched_values=[],
                confidence=0.0,
            ))

    return resolved_list
