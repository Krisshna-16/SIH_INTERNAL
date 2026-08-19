import json
from app.query.retriever import RetrievalResult

SYSTEM_INSTRUCTIONS = """You are an official AI Forensic Assistant for the Ministry of Home Affairs (India) analyzing UFDR extraction reports.

STRICT GROUNDEDNESS & CITATION INSTRUCTIONS:
1. Answer the investigator's question ONLY using the verified ground-truth evidence provided in the EVIDENCE BLOCK below.
2. CITATION MANDATE: Every factual claim, sentence, or assertion MUST include an inline evidence citation in exact bracketed format: [EVT-XXXX], [REL-XXXX], or [FND-XXXX].
3. TAXONOMY DISCIPLINE: Clearly distinguish direct facts (FACT) from rule-based inferences (INFERENCE). Phrase inferences as "may be associated based on rule X" rather than certainties.
4. ZERO HALLUCINATION: Never invent names, phone numbers, locations, dates, or relationships not present in the evidence block.
5. If the provided evidence is insufficient to fully answer part of the question, state explicitly what is missing. Do not guess.
"""


def build_grounded_prompt(retrieval_result: RetrievalResult) -> str:
    """
    Constructs a grounded, citation-enforced prompt for the local LLM using Phase 7 RetrievalResult.
    
    PRIVACY / REDACTION HOOK NOTE:
    In Phase 9 (Privacy Gateway), `retrieval_result` entity values and evidence text
    will be intercepted and pseudonymized here before prompt string construction.
    """
    evidence_block_lines = []

    # 1. Evidence Items
    if retrieval_result.evidence:
        evidence_block_lines.append("--- GROUND-TRUTH EVIDENCE ITEMS ---")
        for ev in retrieval_result.evidence:
            ev_id = ev.get("evidence_id")
            ev_type = ev.get("evidence_type")
            ev_val = ev.get("value")
            ev_page = ev.get("source_page")
            ev_report = ev.get("source_report")
            ev_conf = ev.get("confidence", 1.0)
            evidence_block_lines.append(
                f"- ID: [{ev_id}] | Type: {ev_type} | Value: '{ev_val}' | Source: Page {ev_page} of {ev_report} | Confidence: {ev_conf}"
            )

    # 2. Relationship Triplets
    if retrieval_result.relationships:
        evidence_block_lines.append("\n--- DERIVED RELATIONSHIP TRIPLETS ---")
        for rel in retrieval_result.relationships:
            rel_id = rel.get("id")
            s_val = rel.get("source_value")
            rel_type = rel.get("relationship_type")
            t_val = rel.get("target_value")
            cls = rel.get("classification")
            rule = rel.get("rule_id")
            exp = rel.get("explanation")
            evidence_block_lines.append(
                f"- ID: [{rel_id}] | Triplet: ({s_val}) --[{rel_type}]--> ({t_val}) | Class: {cls} | Rule: {rule} | Explanation: {exp}"
            )

    # 3. Flagged Findings
    if retrieval_result.findings:
        evidence_block_lines.append("\n--- FLAGGED ANOMALY FINDINGS ---")
        for fnd in retrieval_result.findings:
            fnd_id = fnd.get("id")
            name = fnd.get("rule_name")
            sev = fnd.get("severity")
            exp = fnd.get("explanation")
            rel_ids = fnd.get("related_evidence_ids", [])
            evidence_block_lines.append(
                f"- ID: [{fnd_id}] | Finding: {name} ({sev} Severity) | Explanation: {exp} | Evidence Linked: {rel_ids}"
            )

    # 4. Timeline Entries
    if retrieval_result.timeline_entries:
        evidence_block_lines.append("\n--- CHRONOLOGICAL TIMELINE EVENTS ---")
        for tle in retrieval_result.timeline_entries:
            tle_id = tle.get("entry_id")
            ts = tle.get("timestamp")
            title = tle.get("title")
            cls = tle.get("classification")
            evidence_block_lines.append(
                f"- Timestamp: {ts} | Title: {title} | Class: {cls} | Entry ID: {tle_id}"
            )

    evidence_text = "\n".join(evidence_block_lines) if evidence_block_lines else "NO EVIDENCE RECORDED."

    prompt = f"""{SYSTEM_INSTRUCTIONS}

--- EVIDENCE BLOCK ---
Report ID: {retrieval_result.report_id}
{evidence_text}

--- INVESTIGATOR QUESTION ---
"{retrieval_result.original_question}"

--- ASSISTANT GROUNDED RESPONSE ---
"""

    return prompt
