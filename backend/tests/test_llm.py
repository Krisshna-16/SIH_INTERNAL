from unittest.mock import patch, MagicMock
import pytest
from app.models.report import Report
from app.models.evidence import Evidence
from app.models.relationship import Relationship
from app.models.audit_log import AuditLog
from app.query.retriever import RetrievalResult, QueryIntent, QueryIntentType, RetrievalStatus
from app.llm.prompt_builder import build_grounded_prompt
from app.llm.citation_verifier import verify_citations
from app.llm.answer_service import answer_investigator_question
from app.llm.ollama_client import OllamaConnectionError
from app.llm.external_llm_client import ExternalLLMError, ExternalLLMNotConfiguredError


# 1. Test Prompt Builder Contains Citation Mandates & Evidence IDs
def test_build_grounded_prompt():
    dummy_rr = RetrievalResult(
        query_id="QRY-DUMMY",
        report_id="REP-DUMMY",
        original_question="Who did Vikram contact?",
        intent=QueryIntent(intent_type=QueryIntentType.COMMUNICATION_QUERY, confidence=0.95),
        resolved_entities=[],
        evidence=[{"evidence_id": "EVT-V1", "evidence_type": "PERSON", "value": "Vikram", "source_page": 1, "source_report": "R.xml", "confidence": 0.9}],
        relationships=[{"id": "REL-V1", "source_value": "Vikram", "relationship_type": "CONTACTED", "target_value": "Rahul", "classification": "FACT", "rule_id": "R1", "explanation": "Call log"}],
        findings=[],
        timeline_entries=[],
        status=RetrievalStatus.RESULTS_FOUND,
        retrieval_summary="Retrieved 1 evidence and 1 relationship",
    )

    prompt = build_grounded_prompt(dummy_rr)
    assert "[EVT-V1]" in prompt
    assert "[REL-V1]" in prompt
    assert "CITATIONS" in prompt or "CITATION MANDATE" in prompt
    assert "Who did Vikram contact?" in prompt


# 2. Test Citation Verifier Valid vs Invalid Citation IDs
def test_verify_citations():
    dummy_rr = RetrievalResult(
        query_id="QRY-DUMMY",
        report_id="REP-DUMMY",
        original_question="Test Q",
        intent=QueryIntent(intent_type=QueryIntentType.ENTITY_LOOKUP, confidence=0.9),
        resolved_entities=[],
        evidence=[{"evidence_id": "EVT-100", "evidence_type": "PERSON", "value": "Test", "source_page": 1, "source_report": "R.xml"}],
        relationships=[],
        findings=[],
        timeline_entries=[],
        status=RetrievalStatus.RESULTS_FOUND,
        retrieval_summary="Summary",
    )

    # Valid Citation
    ans_valid = "Inspector Vikram was identified in evidence [EVT-100]."
    res_valid = verify_citations(ans_valid, dummy_rr)
    assert res_valid.all_citations_valid is True
    assert res_valid.valid_citations == ["EVT-100"]
    assert len(res_valid.invalid_citations) == 0

    # Invalid / Hallucinated Citation
    ans_fake = "Agent Zero was mentioned in [EVT-FAKE-999]."
    res_fake = verify_citations(ans_fake, dummy_rr)
    assert res_fake.all_citations_valid is False
    assert "EVT-FAKE-999" in res_fake.invalid_citations


# 3. Test Hard Fallback: NO LLM Call on NO_EVIDENCE_FOUND
def test_hard_fallback_no_llm_call(test_db):
    report = Report(id="REP-FALL-001", filename="Fallback_Report.xml", status="extracted", page_count=1)
    test_db.add(report)
    test_db.commit()

    with patch("app.llm.answer_service.external_client.generate_external_answer") as mock_ext:
        with patch("app.llm.answer_service.ollama_client.generate_answer") as mock_ollama:
            answer = answer_investigator_question("REP-FALL-001", "Who is Agent Zero?", test_db)

            # Assert neither Groq nor Ollama were called
            mock_ext.assert_not_called()
            mock_ollama.assert_not_called()

            assert answer.generated_by == "template_fallback"
            assert answer.model_name == "template"
            assert "No verified ground-truth evidence was found" in answer.answer_text


# 4. Test Default Provider is External (Groq) When Omitted
def test_default_provider_is_external(client, test_db):
    report = Report(id="REP-DEF-001", filename="Default_Report.xml", status="extracted", page_count=1)
    test_db.add(report)
    ev = Evidence(evidence_id="EVT-D1", report_id="REP-DEF-001", evidence_type="PERSON", value="Vikram", confidence=0.9, source_page=1, source_report="Default_Report.xml", provenance_detail="{}")
    test_db.add(ev)
    test_db.commit()

    mock_groq_answer = "Inspector Vikram [EVT-D1] is present."

    with patch("app.llm.answer_service.external_client.generate_external_answer", return_value=mock_groq_answer) as mock_ext:
        res = client.post(f"/api/v1/reports/{report.id}/answer", json={"question": "Who is Vikram?"})
        assert res.status_code == 200
        data = res.json()

        mock_ext.assert_called_once()
        assert data["external_llm_used"] is True
        assert data["external_llm_provider"] == "groq"
        assert data["generated_by"] == "external_llm"


# 5. Test Auto Mode Fallback to Local on Simulated Groq Failure
def test_auto_mode_fallback(client, test_db):
    report = Report(id="REP-AUTO-001", filename="Auto_Report.xml", status="extracted", page_count=1)
    test_db.add(report)
    ev = Evidence(evidence_id="EVT-A1", report_id="REP-AUTO-001", evidence_type="PERSON", value="Rahul", confidence=0.9, source_page=1, source_report="Auto_Report.xml", provenance_detail="{}")
    test_db.add(ev)
    test_db.commit()

    mock_ollama_response = "Rahul [EVT-A1] was identified locally."

    with patch("app.llm.answer_service.external_client.generate_external_answer", side_effect=ExternalLLMError("Groq 500 error")):
        with patch("app.llm.answer_service.ollama_client.generate_answer", return_value=mock_ollama_response):
            res = client.post(f"/api/v1/reports/{report.id}/answer", json={"question": "Who is Rahul?", "llm_provider": "auto"})
            assert res.status_code == 200
            data = res.json()

            assert data["fallback_used"] is True
            assert "Groq unavailable" in data["fallback_reason"]
            assert data["external_llm_used"] is False
            assert data["generated_by"] == "local_llm"


# 6. Test Explicit External Mode Does NOT Fall Back Silently
def test_explicit_external_no_silent_fallback(client, test_db):
    report = Report(id="REP-EXP-001", filename="Exp_Report.xml", status="extracted", page_count=1)
    test_db.add(report)
    ev = Evidence(evidence_id="EVT-X1", report_id="REP-EXP-001", evidence_type="PERSON", value="Priya", confidence=0.9, source_page=1, source_report="Exp_Report.xml", provenance_detail="{}")
    test_db.add(ev)
    test_db.commit()

    with patch("app.llm.answer_service.external_client.generate_external_answer", side_effect=ExternalLLMNotConfiguredError("External LLM is not configured. API key missing")):
        with patch("app.llm.answer_service.ollama_client.generate_answer") as mock_ollama:
            res = client.post(f"/api/v1/reports/{report.id}/answer", json={"question": "Who is Priya?", "llm_provider": "external"})

            assert res.status_code == 503
            assert "External LLM is not configured" in res.json()["detail"]
            mock_ollama.assert_not_called()


# 7. Test Audit Log Records 'groq' Provider
def test_audit_log_records_groq_provider(client, test_db):
    report = Report(id="REP-AUD-001", filename="Audit_Report.xml", status="extracted", page_count=1)
    test_db.add(report)
    ev = Evidence(evidence_id="EVT-AU1", report_id="REP-AUD-001", evidence_type="PERSON", value="Ankit", confidence=0.9, source_page=1, source_report="Audit_Report.xml", provenance_detail="{}")
    test_db.add(ev)
    test_db.commit()

    mock_groq_answer = "Ankit [EVT-AU1] is documented."

    with patch("app.llm.answer_service.external_client.generate_external_answer", return_value=mock_groq_answer):
        res = client.post(f"/api/v1/reports/{report.id}/answer", json={"question": "Who is Ankit?", "llm_provider": "external"})
        assert res.status_code == 200

    audit_logs = test_db.query(AuditLog).filter(AuditLog.report_id == "REP-AUD-001").all()
    groq_entries = [a for a in audit_logs if "groq" in a.details.lower()]
    assert len(groq_entries) > 0
