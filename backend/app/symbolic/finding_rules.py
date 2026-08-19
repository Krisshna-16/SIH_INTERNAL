import json
import logging
from typing import List, Dict, Any
from app.models.evidence import Evidence
from app.symbolic.rules_config import (
    RULE_CLUSTER_PAGE_ID,
    RULE_CLUSTER_PAGE_NAME,
    RULE_CLUSTER_MIN_ENTITIES,
    RULE_LOCATION_FREQ_ID,
    RULE_LOCATION_FREQ_NAME,
    RULE_LOCATION_MIN_COUNT,
)

logger = logging.getLogger(__name__)


def rule_page_cooccurrence_cluster(evidence_list: List[Evidence]) -> List[Dict[str, Any]]:
    """
    Evaluates page evidence clusters. Flags pages containing >= RULE_CLUSTER_MIN_ENTITIES items.
    Classification: INFERENCE.
    """
    if not evidence_list:
        return []

    page_groups: Dict[int, List[Evidence]] = {}
    for ev in evidence_list:
        page_groups.setdefault(ev.source_page, []).append(ev)

    findings = []

    for page_num, items in page_groups.items():
        if len(items) >= RULE_CLUSTER_MIN_ENTITIES:
            vals_str = ", ".join([f"'{e.value}' ({e.evidence_type})" for e in items[:4]])
            if len(items) > 4:
                vals_str += f", and {len(items) - 4} more"

            severity = "HIGH" if len(items) >= 5 else "MEDIUM"
            explanation = (
                f"Flagged because Page {page_num} contains a dense cluster of {len(items)} co-occurring evidence items "
                f"[{vals_str}] in report '{items[0].source_report}' (Rule: {RULE_CLUSTER_PAGE_ID})."
            )

            findings.append({
                "finding_type": "PAGE_COOCCURRENCE_CLUSTER",
                "classification": "INFERENCE",
                "rule_id": RULE_CLUSTER_PAGE_ID,
                "rule_name": RULE_CLUSTER_PAGE_NAME,
                "explanation": explanation,
                "related_evidence_ids": [e.evidence_id for e in items],
                "related_relationship_ids": [],
                "parameters_used": {
                    "min_cluster_size": RULE_CLUSTER_MIN_ENTITIES,
                    "actual_cluster_size": len(items),
                    "page_number": page_num,
                },
                "severity": severity,
            })

    logger.info(f"Rule '{RULE_CLUSTER_PAGE_ID}' flagged {len(findings)} page cluster findings.")
    return findings


def rule_high_frequency_location(evidence_list: List[Evidence]) -> List[Dict[str, Any]]:
    """
    Flags location entities that appear repeatedly across pages.
    Classification: INFERENCE.
    """
    if not evidence_list:
        return []

    loc_groups: Dict[str, List[Evidence]] = {}
    for ev in evidence_list:
        if ev.evidence_type.upper() == "LOCATION":
            norm_key = (ev.normalized_value or ev.value).strip().lower()
            loc_groups.setdefault(norm_key, []).append(ev)

    findings = []

    for loc_key, items in loc_groups.items():
        pages = sorted(list(set([e.source_page for e in items])))
        if len(items) >= RULE_LOCATION_MIN_COUNT:
            loc_name = items[0].value
            pages_str = ", ".join([str(p) for p in pages])
            severity = "HIGH" if len(items) >= 3 else "MEDIUM"

            explanation = (
                f"Flagged high-frequency location '{loc_name}' appearing {len(items)} times across Page(s) {pages_str} "
                f"in report '{items[0].source_report}' (Rule: {RULE_LOCATION_FREQ_ID})."
            )

            findings.append({
                "finding_type": "HIGH_FREQUENCY_LOCATION",
                "classification": "INFERENCE",
                "rule_id": RULE_LOCATION_FREQ_ID,
                "rule_name": RULE_LOCATION_FREQ_NAME,
                "explanation": explanation,
                "related_evidence_ids": [e.evidence_id for e in items],
                "related_relationship_ids": [],
                "parameters_used": {
                    "min_location_occurrences": RULE_LOCATION_MIN_COUNT,
                    "occurrence_count": len(items),
                    "pages": pages,
                },
                "severity": severity,
            })

    logger.info(f"Rule '{RULE_LOCATION_FREQ_ID}' flagged {len(findings)} location frequency findings.")
    return findings
