from unittest.mock import patch
import pytest
from app.models.report import Report
from app.models.evidence import Evidence
from app.models.relationship import Relationship
from app.models.finding import Finding
from app.query.intent_classifier import classify_intent, QueryIntentType
from app.query.entity_resolver import extract_question_entities
from app.query.retriever import retrieve_for_query, RetrievalStatus


# 1. Test Intent Classifier
def test_intent_classification_patterns():
    q_comm = classify_intent("Who did Vikram talk to on 12 March 2024?")
    assert q_comm.intent_type == QueryIntentType.COMMUNICATION_QUERY

    q_rel = classify_intent("How are Inspector Vikram and Connaught Place connected?")
    assert q_rel.intent_type == QueryIntentType.RELATIONSHIP_QUERY

    q_tl = classify_intent("Show me the timeline for 15 January 2024.")
    assert q_tl.intent_type == QueryIntentType.TIMELINE_QUERY

    q_fnd = classify_intent("What suspicious activity was flagged by rules?")
    assert q_fnd.intent_type == QueryIntentType.FINDING_QUERY

    q_lookup = classify_intent("Tell me about Suspect Ankit")
    assert q_lookup.intent_type == QueryIntentType.ENTITY_LOOKUP

    q_unk = classify_intent("asdfghjkl 12345")
    assert q_unk.intent_type == QueryIntentType.UNKNOWN


# 2. Test Question Entity Resolution
def test_question_entity_resolution(test_db):
    report = Report(id="REP-QRY-001", filename="Query_Test_Report.xml", status="extracted", page_count=1)
    test_db.add(report)

    ev1 = Evidence(evidence_id="EVT-Q1", report_id="REP-QRY-001", evidence_type="PERSON", value="Inspector Vikram", confidence=0.9, source_page=1, source_report="Query_Test_Report.xml", provenance_detail="{}")
    ev2 = Evidence(evidence_id="EVT-Q2", report_id="REP-QRY-001", evidence_type="PHONE", value="+91 9876543210", confidence=0.9, source_page=1, source_report="Query_Test_Report.xml", provenance_detail="{}")
    test_db.add_all([ev1, ev2])
    test_db.commit()

    # Known entity question
    resolved = extract_question_entities("Did Inspector Vikram call +91 9876543210?", "REP-QRY-001", test_db)
    matched = [r for r in resolved if r.matched]
    assert len(matched) >= 1
    assert "EVT-Q1" in matched[0].evidence_ids or "EVT-Q2" in matched[0].evidence_ids

    # Unknown entity question
    resolved_unknown = extract_question_entities("Tell me about Agent Zero", "REP-QRY-001", test_db)
    unmatched = [r for r in resolved_unknown if not r.matched]
    assert len(unmatched) >= 1
    assert unmatched[0].mention_text == "Agent Zero"


# 3. Test End-to-End Retrieval & Audit History
def test_query_retrieval_and_audit_history(client, test_db):
    report = Report(id="REP-QRY-API", filename="API_Query_Report.xml", status="extracted", page_count=1)
    test_db.add(report)

    ev1 = Evidence(evidence_id="EVT-M1", report_id="REP-QRY-API", evidence_type="PERSON", value="Ankit Verma", confidence=0.95, source_page=1, source_report="API_Query_Report.xml", provenance_detail="{}")
    ev2 = Evidence(evidence_id="EVT-M2", report_id="REP-QRY-API", evidence_type="LOCATION", value="Connaught Place", confidence=0.95, source_page=1, source_report="API_Query_Report.xml", provenance_detail="{}")
    test_db.add_all([ev1, ev2])

    rel = Relationship(id="REL-M1", report_id="REP-QRY-API", source_evidence_id="EVT-M1", target_evidence_id="EVT-M2", relationship_type="LOCATED_AT", classification="FACT", rule_id="RULE-PAGE-01", explanation="Ankit visited Connaught Place", confidence=0.95)
    test_db.add(rel)
    test_db.commit()

    # 1. Known Query Submission
    res1 = client.post(f"/api/v1/reports/{report.id}/query", json={"question": "Where was Ankit Verma located?"})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "RESULTS_FOUND"
    assert len(data1["evidence"]) > 0
    assert len(data1["relationships"]) > 0

    # 2. Unknown Entity Query Submission (ENTITY_NOT_RESOLVED)
    res2 = client.post(f"/api/v1/reports/{report.id}/query", json={"question": "Who is Agent Zero?"})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "ENTITY_NOT_RESOLVED"
    assert "no matching ground-truth evidence" in data2["retrieval_summary"]

    # 3. GET Query History
    res_hist = client.get(f"/api/v1/reports/{report.id}/query/history")
    assert res_hist.status_code == 200
    data_hist = res_hist.json()
    assert data_hist["total_queries"] == 2
    questions = [h["question"] for h in data_hist["history"]]
    assert "Where was Ankit Verma located?" in questions
    assert "Who is Agent Zero?" in questions


# 4. Test Graceful Degradation on Sub-service Failure
def test_query_graceful_degradation(client, test_db):
    report = Report(id="REP-DEG-001", filename="Degradation_Report.xml", status="extracted", page_count=1)
    test_db.add(report)
    ev = Evidence(evidence_id="EVT-D1", report_id="REP-DEG-001", evidence_type="PERSON", value="Rahul", confidence=0.9, source_page=1, source_report="Degradation_Report.xml", provenance_detail="{}")
    test_db.add(ev)
    test_db.commit()

    # Mock graph builder to raise an exception
    with patch("app.query.retriever.build_report_graph", side_effect=RuntimeError("Graph service temporary unavailable")):
        res = client.post(f"/api/v1/reports/{report.id}/query", json={"question": "How are Rahul and others connected?"})
        assert res.status_code == 200  # Must return 200, not 500
        data = res.json()
        assert data["status"] in ["RESULTS_FOUND", "NO_EVIDENCE_FOUND"]
        assert "Graph sub-retrieval notice" in data["retrieval_summary"]
