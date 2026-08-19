import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.query.retriever import retrieve_for_query, RetrievalResult, RetrievalStatus
from app.llm.ollama_client import OllamaClient, OLLAMA_MODEL, OllamaConnectionError, OllamaTimeoutError
from app.llm.external_llm_client import (
    ExternalLLMClient,
    GROQ_MODEL,
    ExternalLLMNotConfiguredError,
    ExternalLLMError,
    ExternalLLMTimeoutError,
)
from app.llm.prompt_builder import build_grounded_prompt
from app.llm.citation_verifier import verify_citations, CitationVerificationResult
from app.privacy.pseudonymizer import pseudonymize_retrieval_result, resolve_pseudonyms_in_text
from app.privacy.minimizer import minimize_for_external

logger = logging.getLogger(__name__)

ollama_client = OllamaClient()
external_client = ExternalLLMClient()


class InvestigatorAnswer(BaseModel):
    """
    Complete Investigator Answer model with post-hoc citation verification,
    ground-truth evidence references, privacy metadata, and fallback indicators.
    """
    query_id: str = Field(..., description="Query ID from Phase 7 retrieval")
    report_id: str = Field(..., description="Target report ID")
    question: str = Field(..., description="Original investigator question")
    answer_text: str = Field(..., description="Resolved natural-language answer or template fallback")
    citations_used: List[str] = Field(default_factory=list, description="List of valid citation IDs used in answer")
    citation_verification: CitationVerificationResult = Field(..., description="Post-hoc citation verification result")
    retrieval_status: str = Field(..., description="Phase 7 retrieval status")
    evidence_references: List[Dict[str, Any]] = Field(default_factory=list, description="Resolved evidence/relationship/finding objects")
    generated_by: str = Field(..., description="'local_llm', 'external_llm', or 'template_fallback'")
    model_name: str = Field(..., description="LLM model identifier")
    external_llm_used: bool = Field(False, description="True if external LLM path (Groq) was used")
    external_llm_provider: Optional[str] = Field(None, description="External LLM provider name if used")
    pseudonymized: bool = Field(True, description="True if Privacy Gateway pseudonymization was applied")
    fallback_used: bool = Field(False, description="True if auto-fallback to local model occurred")
    fallback_reason: Optional[str] = Field(None, description="Explanation for fallback if used")
    created_at: str = Field(..., description="ISO formatted generation timestamp")


def generate_fallback_grounded_answer(rr: RetrievalResult, question: str) -> str:
    """Generates a rich, grounded natural-language answer directly from retrieved ground-truth evidence when LLM calls fail."""
    parts = [f"Based on verified ground-truth evidence in report '{rr.report_id}':\n"]

    if rr.evidence:
        ev_items = [f"• {ev.get('evidence_type')}: **{ev.get('value')}** (Page {ev.get('source_page', 1)}) [{ev.get('evidence_id')}]" for ev in rr.evidence[:6]]
        parts.append("Key Evidence Records:\n" + "\n".join(ev_items) + "\n")

    if rr.relationships:
        rel_items = [f"• {rel.get('source_value')} **{rel.get('relationship_type')}** {rel.get('target_value')} [{rel.get('id')}] ({rel.get('classification')})" for rel in rr.relationships[:5]]
        parts.append("Derived Relationships:\n" + "\n".join(rel_items) + "\n")

    if rr.findings:
        fnd_items = [f"• **{fnd.get('rule_name')}** ({fnd.get('severity')} Severity): {fnd.get('explanation')} [{fnd.get('id')}]" for fnd in rr.findings[:3]]
        parts.append("Flagged Anomaly Findings:\n" + "\n".join(fnd_items) + "\n")

    return "\n".join(parts)


def answer_investigator_question(
    report_id: str,
    question: str,
    db: Session,
    use_external_llm: Optional[bool] = None,
    llm_provider: str = "external",
) -> InvestigatorAnswer:
    """
    Orchestrates the Privacy-Gated Answer Generation Pipeline:
    1. Phase 7 Ground-Truth Retrieval.
    2. Hard Fallback Check: if NO_EVIDENCE_FOUND or ENTITY_NOT_RESOLVED, return template fallback WITHOUT calling LLM.
    3. Mandatory Privacy Gateway Pseudonymization.
    4. Model Dispatch: Groq (default) vs Ollama (local) vs Auto (Groq + local fallback).
    5. Post-Hoc Citation Verification.
    6. UI Resolution: Reverses pseudonyms back to real values for authenticated investigator display.
    7. Audit Logging.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # Handle backward compatibility for use_external_llm boolean flag
    if use_external_llm is not None:
        effective_provider = "external" if use_external_llm else "local"
    else:
        effective_provider = llm_provider.lower().strip() if llm_provider else "external"

    retrieval_result: RetrievalResult = retrieve_for_query(report_id=report_id, question=question, db=db)

    # 1. HARD FALLBACK CHECK: If no evidence or entity not resolved, NEVER call any LLM
    if retrieval_result.status in [RetrievalStatus.NO_EVIDENCE_FOUND, RetrievalStatus.ENTITY_NOT_RESOLVED]:
        logger.info(f"Retrieval status '{retrieval_result.status.value}'. Returning template fallback without LLM call.")
        fallback_text = (
            f"No verified ground-truth evidence was found in report '{report_id}' to answer: \"{question}\".\n\n"
            f"Detail: {retrieval_result.retrieval_summary}"
        )
        empty_verification = CitationVerificationResult(
            all_citations_valid=True,
            cited_ids=[],
            valid_citations=[],
            invalid_citations=[],
            uncited_claim_warning=False,
        )

        return InvestigatorAnswer(
            query_id=retrieval_result.query_id,
            report_id=report_id,
            question=question,
            answer_text=fallback_text,
            citations_used=[],
            citation_verification=empty_verification,
            retrieval_status=retrieval_result.status.value,
            evidence_references=[],
            generated_by="template_fallback",
            model_name="template",
            external_llm_used=False,
            external_llm_provider=None,
            pseudonymized=True,
            fallback_used=False,
            fallback_reason=None,
            created_at=now_iso,
        )

    # 2. MANDATORY PRIVACY GATEWAY PSEUDONYMIZATION
    pseudonymized_rr = pseudonymize_retrieval_result(retrieval_result, db=db)

    raw_pseudo_answer = ""
    gen_by = ""
    model_id = ""
    audit_provider_name = ""
    ext_used = False
    fallback_used = False
    fallback_reason: Optional[str] = None

    # 3. MODEL DISPATCH LOGIC
    if effective_provider == "external":
        ext_used = True
        audit_provider_name = "groq"
        model_id = f"groq/{GROQ_MODEL}"
        gen_by = "external_llm"
        logger.info(f"Explicit external path (Groq) requested for query '{retrieval_result.query_id}'.")
        minimized_payload = minimize_for_external(pseudonymized_rr)
        # Will raise ExternalLLMNotConfiguredError, ExternalLLMError, or ExternalLLMTimeoutError if it fails
        raw_pseudo_answer = external_client.generate_external_answer(minimized_payload)

    elif effective_provider == "auto":
        logger.info(f"Auto path requested for query '{retrieval_result.query_id}'. Attempting Groq first...")
        minimized_payload = minimize_for_external(pseudonymized_rr)
        try:
            raw_pseudo_answer = external_client.generate_external_answer(minimized_payload)
            ext_used = True
            audit_provider_name = "groq"
            model_id = f"groq/{GROQ_MODEL}"
            gen_by = "external_llm"
        except Exception as ge:
            logger.warning(f"Groq call failed in auto mode: {ge}. Executing auto-fallback to local Ollama/Engine.")
            fallback_used = True
            fallback_reason = f"Groq unavailable ({str(ge)})"
            audit_provider_name = "groq_fallback_ollama"
            ext_used = False

            # Try local Ollama, fallback to local synthesis if Ollama offline
            prompt = build_grounded_prompt(pseudonymized_rr)
            try:
                raw_pseudo_answer = ollama_client.generate_answer(prompt)
                model_id = f"ollama/{OLLAMA_MODEL}"
                gen_by = "local_llm"
            except Exception as oe:
                logger.warning(f"Local Ollama also unavailable ({oe}). Generating deterministic grounded synthesis.")
                raw_pseudo_answer = generate_fallback_grounded_answer(pseudonymized_rr, question)
                model_id = "local_grounded_engine"
                gen_by = "template_fallback"

    else:  # effective_provider == "local"
        ext_used = False
        audit_provider_name = f"ollama/{OLLAMA_MODEL}"
        logger.info(f"Explicit local path (Ollama) requested for query '{retrieval_result.query_id}'.")
        prompt = build_grounded_prompt(pseudonymized_rr)
        try:
            raw_pseudo_answer = ollama_client.generate_answer(prompt)
            model_id = f"ollama/{OLLAMA_MODEL}"
            gen_by = "local_llm"
        except Exception as oe:
            logger.warning(f"Local Ollama unavailable ({oe}). Generating deterministic grounded synthesis.")
            raw_pseudo_answer = generate_fallback_grounded_answer(pseudonymized_rr, question)
            model_id = "local_grounded_engine"
            gen_by = "template_fallback"

    # Pre & Post Audit Logging
    db.add(AuditLog(
        actor="investigator",
        action="LLM_QUERY_EXECUTED",
        report_id=report_id,
        details=json.dumps({
            "question": question,
            "provider": audit_provider_name,
            "effective_provider": effective_provider,
            "pseudonymized": True,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
        }),
    ))
    db.commit()

    # 4. Post-Hoc Citation Verification against pseudonymized RetrievalResult
    verification = verify_citations(raw_pseudo_answer, pseudonymized_rr)

    # 5. UI Resolution: Reverse pseudonyms in answer text ONLY for display to investigator
    final_resolved_answer = resolve_pseudonyms_in_text(raw_pseudo_answer, report_id, db=db)

    # Resolve evidence references for valid citations
    evidence_refs: List[Dict[str, Any]] = []
    valid_ids_set = set(verification.valid_citations) if verification.valid_citations else set([e.get("evidence_id") for e in retrieval_result.evidence])

    for ev in retrieval_result.evidence:
        if ev.get("evidence_id") in valid_ids_set or len(evidence_refs) < 5:
            evidence_refs.append({"type": "EVIDENCE", **ev})

    for rel in retrieval_result.relationships:
        if rel.get("id") in valid_ids_set or len(evidence_refs) < 8:
            evidence_refs.append({"type": "RELATIONSHIP", **rel})

    for fnd in retrieval_result.findings:
        if fnd.get("id") in valid_ids_set or len(evidence_refs) < 10:
            evidence_refs.append({"type": "FINDING", **fnd})

    # Post-execution Audit Log Entry
    db.add(AuditLog(
        actor="system_llm",
        action="LLM_ANSWER_GENERATED",
        report_id=report_id,
        details=json.dumps({
            "query_id": retrieval_result.query_id,
            "question": question,
            "provider": audit_provider_name,
            "generated_by": gen_by,
            "model_name": model_id,
            "external_llm_used": ext_used,
            "pseudonymized": True,
            "fallback_used": fallback_used,
            "citations_valid": verification.all_citations_valid,
            "valid_citations_count": len(verification.valid_citations),
        }),
    ))
    db.commit()

    return InvestigatorAnswer(
        query_id=retrieval_result.query_id,
        report_id=report_id,
        question=question,
        answer_text=final_resolved_answer,
        citations_used=verification.valid_citations,
        citation_verification=verification,
        retrieval_status=retrieval_result.status.value,
        evidence_references=evidence_refs[:8],
        generated_by=gen_by,
        model_name=model_id,
        external_llm_used=ext_used,
        external_llm_provider="groq" if ext_used else None,
        pseudonymized=True,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        created_at=now_iso,
    )
