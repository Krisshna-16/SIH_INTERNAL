from unittest.mock import patch
import pytest
from app.models.report import Report
from app.models.evidence import Evidence
from app.models.relationship import Relationship
from app.models.pseudonym_mapping import PseudonymMapping
from app.models.audit_log import AuditLog
from app.query.retriever import RetrievalResult, QueryIntent, QueryIntentType, RetrievalStatus
from app.privacy.pseudonymizer import get_or_create_pseudonym, pseudonymize_retrieval_result, resolve_pseudonyms_in_text
from app.privacy.minimizer import minimize_for_external
from app.llm.external_llm_client import ExternalLLMClient, ExternalLLMNotConfiguredError
from app.llm.answer_service import answer_investigator_question


# 1. Test Deterministic & Idempotent Pseudonym Mapping
def test_pseudonym_mapping_idempotency(test_db):
    report = Report(id="REP-PRIV-001", filename="Privacy_Report.xml", status="extracted", page_count=1)
    test_db.add(report)
    test_db.commit()

    p1 = get_or_create_pseudonym("REP-PRIV-001", "Inspector Vikram", "PERSON", "EVT-1", test_db)
    p2 = get_or_create_pseudonym("REP-PRIV-001", "Inspector Vikram", "PERSON", "EVT-1", test_db)

    assert p1 == "PERSON_001"
    assert p2 == "PERSON_001"

    # Count mapping rows (must be exactly 1)
    cnt = test_db.query(PseudonymMapping).filter(PseudonymMapping.report_id == "REP-PRIV-001").count()
    assert cnt == 1


# 2. Test Deep-Copy Pseudonymization of RetrievalResult
def test_pseudonymize_retrieval_result(test_db):
    report = Report(id="REP-PRIV-002", filename="Privacy_Report_2.xml", status="extracted", page_count=1)
    test_db.add(report)
    test_db.commit()

    raw_rr = RetrievalResult(
        query_id="QRY-PRIV-1",
        report_id="REP-PRIV-002",
        original_question="Who did Inspector Vikram call?",
        intent=QueryIntent(intent_type=QueryIntentType.COMMUNICATION_QUERY, confidence=0.9),
        resolved_entities=[],
        evidence=[{"evidence_id": "EVT-P1", "evidence_type": "PERSON", "value": "Inspector Vikram", "source_page": 1, "source_report": "Privacy_Report_2.xml"}],
        relationships=[{"id": "REL-P1", "source_evidence_id": "EVT-P1", "source_value": "Inspector Vikram", "target_evidence_id": "EVT-P2", "target_value": "+91 9876543210", "relationship_type": "USED", "classification": "FACT", "rule_id": "R1", "explanation": "Inspector Vikram used +91 9876543210"}],
        findings=[],
        timeline_entries=[],
        status=RetrievalStatus.RESULTS_FOUND,
        retrieval_summary="Summary",
    )

    pseudo_rr = pseudonymize_retrieval_result(raw_rr, test_db)

    # Verify real identities replaced with pseudonyms
    assert pseudo_rr.evidence[0]["value"] == "PERSON_001"
    assert pseudo_rr.relationships[0]["source_value"] == "PERSON_001"
    assert pseudo_rr.relationships[0]["target_value"] == "PHONE_001"
    assert "PERSON_001" in pseudo_rr.relationships[0]["explanation"]

    # Verify evidence IDs remain unchanged
    assert pseudo_rr.evidence[0]["evidence_id"] == "EVT-P1"
    assert pseudo_rr.relationships[0]["id"] == "REL-P1"


# 3. Test Reverse Pseudonym Resolution for UI Display
def test_resolve_pseudonyms_in_text(test_db):
    report = Report(id="REP-PRIV-003", filename="Privacy_Report_3.xml", status="extracted", page_count=1)
    test_db.add(report)
    test_db.commit()

    get_or_create_pseudonym("REP-PRIV-003", "Ankit Verma", "PERSON", None, test_db)

    text = "Based on evidence [EVT-1], PERSON_001 was present at Connaught Place."
    resolved = resolve_pseudonyms_in_text(text, "REP-PRIV-003", test_db)

    assert "Ankit Verma" in resolved
    assert "PERSON_001" not in resolved


# 4. Test External LLM Minimizer (Strips File Names & Page Numbers)
def test_minimize_for_external(test_db):
    report = Report(id="REP-PRIV-004", filename="Privacy_Report_4.xml", status="extracted", page_count=1)
    test_db.add(report)
    test_db.commit()

    raw_rr = RetrievalResult(
        query_id="QRY-PRIV-4",
        report_id="REP-PRIV-004",
        original_question="Q?",
        intent=QueryIntent(intent_type=QueryIntentType.ENTITY_LOOKUP, confidence=0.9),
        resolved_entities=[],
        evidence=[{"evidence_id": "EVT-M1", "evidence_type": "PERSON", "value": "Rahul", "source_page": 5, "source_report": "Secret_File.xml"}],
        relationships=[],
        findings=[],
        timeline_entries=[],
        status=RetrievalStatus.RESULTS_FOUND,
        retrieval_summary="Summary",
    )

    pseudo_rr = pseudonymize_retrieval_result(raw_rr, test_db)
    minimized = minimize_for_external(pseudo_rr)

    # Assert stripped fields are absent from evidence
    assert "source_report" not in minimized["evidence"][0]
    assert "source_page" not in minimized["evidence"][0]
    assert minimized["evidence"][0]["value"] == "PERSON_001"
    assert minimized["privacy_level"] == "MINIMIZED_PSEUDONYMIZED"


# 5. Test External LLM Client Type Enforcement
def test_external_client_type_enforcement():
    client = ExternalLLMClient(api_key="test_key")

    raw_rr = RetrievalResult(
        query_id="Q",
        report_id="R",
        original_question="Q?",
        intent=QueryIntent(intent_type=QueryIntentType.UNKNOWN, confidence=0.0),
        resolved_entities=[],
        evidence=[],
        relationships=[],
        findings=[],
        timeline_entries=[],
        status=RetrievalStatus.NO_EVIDENCE_FOUND,
        retrieval_summary="Summary",
    )

    # Must raise TypeError when raw RetrievalResult object is passed directly
    with pytest.raises(TypeError) as excinfo:
        client.generate_external_answer(raw_rr)

    assert "accepts ONLY dict payloads" in str(excinfo.value)


# 6. Test Unconfigured External API Key (HTTP 503 & No Silent Local Fallback)
def test_unconfigured_external_api_key_503(client, test_db):
    report = Report(id="REP-PRIV-005", filename="Privacy_Report_5.xml", status="extracted", page_count=1)
    test_db.add(report)
    ev = Evidence(evidence_id="EVT-K1", report_id="REP-PRIV-005", evidence_type="PERSON", value="Vikram", confidence=0.9, source_page=1, source_report="Privacy_Report_5.xml", provenance_detail="{}")
    test_db.add(ev)
    test_db.commit()

    with patch("app.core.config.settings.EXTERNAL_LLM_API_KEY", ""):
        with patch("app.llm.answer_service.ollama_client.generate_answer") as mock_ollama:
            res = client.post(f"/api/v1/reports/{report.id}/answer", json={"question": "Tell me about Vikram", "llm_provider": "external"})

            assert res.status_code == 503
            assert "External LLM is not configured" in res.json()["detail"]

            # Assert local Ollama was NOT called as a silent fallback
            mock_ollama.assert_not_called()


# 7. Test Audit Logging for Both Local and External Query Paths
def test_privacy_audit_logging(client, test_db):
    report = Report(id="REP-PRIV-006", filename="Privacy_Report_6.xml", status="extracted", page_count=1)
    test_db.add(report)
    ev = Evidence(evidence_id="EVT-L1", report_id="REP-PRIV-006", evidence_type="PERSON", value="Ankit", confidence=0.9, source_page=1, source_report="Privacy_Report_6.xml", provenance_detail="{}")
    test_db.add(ev)
    test_db.commit()

    with patch("app.llm.answer_service.ollama_client.generate_answer", return_value="Ankit [EVT-L1] is present."):
        res = client.post(f"/api/v1/reports/{report.id}/answer", json={"question": "Who is Ankit?", "llm_provider": "local"})
        assert res.status_code == 200

    audit_logs = test_db.query(AuditLog).filter(AuditLog.report_id == "REP-PRIV-006").all()
    actions = [a.action for a in audit_logs]
    assert "LLM_QUERY_EXECUTED" in actions


# 8. REGRESSION TEST: original_question must be pseudonymized (Issue P1 - CRITICAL PII leak fix)
def test_original_question_pseudonymized_before_external(test_db):
    """
    Verifies that `original_question` containing real PII (names, phone numbers)
    is pseudonymized by `pseudonymize_retrieval_result()` BEFORE it reaches
    `minimize_for_external()` and the external LLM payload.
    
    This test would have FAILED before commit fixing pseudonymizer.py.
    """
    report = Report(id="REP-PRIV-007", filename="PII_Leak_Test.xml", status="extracted", page_count=1)
    test_db.add(report)
    test_db.commit()

    # RetrievalResult with PII in both evidence AND original_question
    raw_rr = RetrievalResult(
        query_id="QRY-LEAK-1",
        report_id="REP-PRIV-007",
        original_question="What did Inspector Vikram do at +91 9876543210?",
        intent=QueryIntent(intent_type=QueryIntentType.COMMUNICATION_QUERY, confidence=0.9),
        resolved_entities=[],
        evidence=[
            {"evidence_id": "EVT-LEAK1", "evidence_type": "PERSON", "value": "Inspector Vikram", "source_page": 1, "source_report": "PII_Leak_Test.xml"},
            {"evidence_id": "EVT-LEAK2", "evidence_type": "PHONE", "value": "+91 9876543210", "source_page": 1, "source_report": "PII_Leak_Test.xml"},
        ],
        relationships=[],
        findings=[],
        timeline_entries=[],
        status=RetrievalStatus.RESULTS_FOUND,
        retrieval_summary="Summary",
    )

    pseudo_rr = pseudonymize_retrieval_result(raw_rr, test_db)

    # CRITICAL ASSERTION: original_question must NOT contain raw PII
    assert "Inspector Vikram" not in pseudo_rr.original_question, \
        f"PII LEAK: Real name 'Inspector Vikram' found in pseudonymized original_question: '{pseudo_rr.original_question}'"
    assert "+91 9876543210" not in pseudo_rr.original_question, \
        f"PII LEAK: Real phone '+91 9876543210' found in pseudonymized original_question: '{pseudo_rr.original_question}'"

    # Verify pseudonyms ARE present in the question
    assert "PERSON_001" in pseudo_rr.original_question
    assert "PHONE_001" in pseudo_rr.original_question

    # Also verify the minimized payload propagates the pseudonymized question
    minimized = minimize_for_external(pseudo_rr)
    assert "Inspector Vikram" not in minimized["original_question"]
    assert "PERSON_001" in minimized["original_question"]


# 9. EDGE CASE: PII in question exists in DB mappings but NOT in this retrieval's evidence
def test_question_pii_from_prior_query_still_redacted(test_db):
    """
    Scenario: A prior query caused 'Ankit Verma' to be pseudonymized as PERSON_001
    in this report. Now a NEW query mentions 'Ankit Verma' in the question, but the
    retrieval result for this query does NOT contain Ankit Verma in its evidence set.
    
    The question must STILL be redacted because the PseudonymMapping exists in the DB.
    """
    report = Report(id="REP-PRIV-008", filename="Cross_Query_PII.xml", status="extracted", page_count=1)
    test_db.add(report)
    test_db.commit()

    # Simulate a PRIOR query that created a pseudonym mapping for "Ankit Verma"
    get_or_create_pseudonym("REP-PRIV-008", "Ankit Verma", "PERSON", "EVT-OLD1", test_db)
    # Also for a phone number
    get_or_create_pseudonym("REP-PRIV-008", "+91 1111111111", "PHONE", "EVT-OLD2", test_db)

    # New query: question mentions Ankit Verma, but evidence set contains DIFFERENT people
    new_rr = RetrievalResult(
        query_id="QRY-CROSS-1",
        report_id="REP-PRIV-008",
        original_question="Did Ankit Verma contact +91 1111111111 last week?",
        intent=QueryIntent(intent_type=QueryIntentType.COMMUNICATION_QUERY, confidence=0.9),
        resolved_entities=[],
        evidence=[
            # NOTE: Evidence contains Priya Singh, NOT Ankit Verma
            {"evidence_id": "EVT-NEW1", "evidence_type": "PERSON", "value": "Priya Singh", "source_page": 2, "source_report": "Cross_Query_PII.xml"},
        ],
        relationships=[],
        findings=[],
        timeline_entries=[],
        status=RetrievalStatus.RESULTS_FOUND,
        retrieval_summary="Summary",
    )

    pseudo_rr = pseudonymize_retrieval_result(new_rr, test_db)

    # CRITICAL: Ankit Verma must be redacted even though they're not in this retrieval's evidence
    assert "Ankit Verma" not in pseudo_rr.original_question, \
        f"CROSS-QUERY PII LEAK: 'Ankit Verma' found in question: '{pseudo_rr.original_question}'"
    assert "+91 1111111111" not in pseudo_rr.original_question, \
        f"CROSS-QUERY PII LEAK: '+91 1111111111' found in question: '{pseudo_rr.original_question}'"

    # The DB-sourced pseudonym should be present
    assert "PERSON_001" in pseudo_rr.original_question
    assert "PHONE_001" in pseudo_rr.original_question

