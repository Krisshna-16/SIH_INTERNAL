import re
from typing import List, Set
from pydantic import BaseModel, Field
from app.query.retriever import RetrievalResult


class CitationVerificationResult(BaseModel):
    """
    Post-hoc Citation Verification Result model validating LLM citations against ground-truth.
    """
    all_citations_valid: bool = Field(..., description="True if all cited IDs exist in pre-retrieved evidence")
    cited_ids: List[str] = Field(default_factory=list, description="All citation IDs extracted from answer text")
    valid_citations: List[str] = Field(default_factory=list, description="Validated citation IDs")
    invalid_citations: List[str] = Field(default_factory=list, description="Hallucinated/unmatched citation IDs")
    uncited_claim_warning: bool = Field(..., description="True if answer has content but zero citations")


def verify_citations(answer_text: str, retrieval_result: RetrievalResult) -> CitationVerificationResult:
    """
    Verifies that every inline citation in the LLM answer matches an ID present in RetrievalResult.
    Safety feature: flags hallucinated or out-of-context citation IDs.
    """
    if not answer_text or not answer_text.strip():
        return CitationVerificationResult(
            all_citations_valid=True,
            cited_ids=[],
            valid_citations=[],
            invalid_citations=[],
            uncited_claim_warning=False,
        )

    # Regex to extract bracketed IDs: [EVT-XXXX], [REL-XXXX], [FND-XXXX], [TLE-XXXX]
    raw_matches = re.findall(r"\[((?:EVT|REL|FND|TLE)-[A-Za-z0-9-]+)\]", answer_text)
    cited_ids = list(dict.fromkeys(raw_matches))  # deduplicate preserving order

    # Build set of allowable valid IDs from RetrievalResult
    allowable_ids: Set[str] = set()

    for ev in retrieval_result.evidence:
        if ev.get("evidence_id"):
            allowable_ids.add(ev["evidence_id"])

    for rel in retrieval_result.relationships:
        if rel.get("id"):
            allowable_ids.add(rel["id"])

    for fnd in retrieval_result.findings:
        if fnd.get("id"):
            allowable_ids.add(fnd["id"])

    for tle in retrieval_result.timeline_entries:
        if tle.get("entry_id"):
            allowable_ids.add(tle["entry_id"])
        if tle.get("evidence_id"):
            allowable_ids.add(tle["evidence_id"])
        if tle.get("finding_id"):
            allowable_ids.add(tle["finding_id"])

    valid_citations = []
    invalid_citations = []

    for cid in cited_ids:
        if cid in allowable_ids:
            valid_citations.append(cid)
        else:
            invalid_citations.append(cid)

    all_valid = len(invalid_citations) == 0
    has_uncited_warning = len(answer_text.strip()) > 50 and len(cited_ids) == 0

    return CitationVerificationResult(
        all_citations_valid=all_valid,
        cited_ids=cited_ids,
        valid_citations=valid_citations,
        invalid_citations=invalid_citations,
        uncited_claim_warning=has_uncited_warning,
    )
