import logging
from typing import List, Dict, Any
from app.models.evidence import Evidence
from app.symbolic.rules_config import (
    RULE_COOCCUR_SAME_PAGE_ID,
    RULE_COOCCUR_MIN_CONFIDENCE,
)

logger = logging.getLogger(__name__)


def derive_relationship_type(t1: str, t2: str) -> str:
    """Determines relationship predicate based on entity type pair."""
    types = {t1.upper(), t2.upper()}
    if "PERSON" in types and "PHONE" in types:
        return "USED"
    if "PERSON" in types and "LOCATION" in types:
        return "LOCATED_AT"
    if "PERSON" in types and "EMAIL" in types:
        return "ACCESSED"
    if "PERSON" in types and "URL" in types:
        return "ACCESSED"
    return "ASSOCIATED_WITH"


def rule_same_page_cooccurrence(evidence_list: List[Evidence], max_pairs_per_page: int = 1500) -> List[Dict[str, Any]]:
    """
    Derives direct FACT relationships between evidence items co-occurring on the same source page.
    
    EXPLAINABLE DERIVATION:
    Co-occurrence on the exact same page of a forensic report represents a direct physical observation (FACT).
    """
    if not evidence_list:
        return []

    # Group evidence by source_page
    page_groups: Dict[int, List[Evidence]] = {}
    for ev in evidence_list:
        if ev.confidence < RULE_COOCCUR_MIN_CONFIDENCE:
            continue
        page_groups.setdefault(ev.source_page, []).append(ev)

    relationships = []
    seen_pairs = set()

    for page_num, items in page_groups.items():
        page_rel_count = 0
        # Generate pairwise combinations on the same page
        for i in range(len(items)):
            if page_rel_count >= max_pairs_per_page:
                logger.info(f"Reached max relationship cap ({max_pairs_per_page}) for Page {page_num}.")
                break
            for j in range(i + 1, len(items)):
                e1 = items[i]
                e2 = items[j]

                # Skip identical values (e.g. email co-occurring with exact same email)
                if e1.value.strip().lower() == e2.value.strip().lower():
                    continue

                # Avoid duplicate relationship pairs
                pair_key = tuple(sorted([e1.evidence_id, e2.evidence_id]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                rel_type = derive_relationship_type(e1.evidence_type, e2.evidence_type)
                explanation = (
                    f"Evidence '{e1.value}' ({e1.evidence_type}) and '{e2.value}' ({e2.evidence_type}) "
                    f"co-occur on Page {page_num} of report '{e1.source_report}' (Rule: {RULE_COOCCUR_SAME_PAGE_ID})."
                )

                relationships.append({
                    "source_evidence_id": e1.evidence_id,
                    "target_evidence_id": e2.evidence_id,
                    "relationship_type": rel_type,
                    "classification": "FACT",  # Direct co-occurrence observation
                    "rule_id": RULE_COOCCUR_SAME_PAGE_ID,
                    "explanation": explanation,
                    "confidence": min(e1.confidence, e2.confidence),
                })
                page_rel_count += 1

    logger.info(f"Rule '{RULE_COOCCUR_SAME_PAGE_ID}' derived {len(relationships)} FACT relationships.")
    return relationships
