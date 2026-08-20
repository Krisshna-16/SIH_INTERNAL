import pytest
from app.models.report import Report
from app.models.entity import Entity
from app.models.evidence import Evidence
from app.models.audit_log import AuditLog
from app.evidence.consolidator import consolidate_report_evidence


# 1. Test Consolidation Mapping and Idempotency
def test_consolidate_report_evidence_idempotency(test_db):
    report = Report(id="REP-TEST-PROV", filename="Forensic_Test_Case.xml", status="extracted", page_count=2)
    test_db.add(report)

    ent1 = Entity(
        id="ENT-001",
        report_id="REP-TEST-PROV",
        type="PERSON",
        value="Rahul Sharma",
        normalized_value="Rahul Sharma",
        confidence=0.75,
        source_page=1,
        source_report="Forensic_Test_Case.xml",
        extraction_method="spacy_ner",
    )
    ent2 = Entity(
        id="ENT-002",
        report_id="REP-TEST-PROV",
        type="PHONE",
        value="+91 9876543210",
        normalized_value="+919876543210",
        confidence=0.95,
        source_page=1,
        source_report="Forensic_Test_Case.xml",
        extraction_method="regex_phone",
    )
    test_db.add_all([ent1, ent2])
    test_db.commit()

    # First Consolidation
    summary1 = consolidate_report_evidence("REP-TEST-PROV", test_db)
    assert summary1["total_evidence"] == 2
    assert summary1["evidence_counts"]["PERSON"] == 1
    assert summary1["evidence_counts"]["PHONE"] == 1

    ev_count_1 = test_db.query(Evidence).filter(Evidence.report_id == "REP-TEST-PROV").count()
    assert ev_count_1 == 2

    # Second Consolidation (Idempotency Check)
    summary2 = consolidate_report_evidence("REP-TEST-PROV", test_db)
    assert summary2["total_evidence"] == 2

    ev_count_2 = test_db.query(Evidence).filter(Evidence.report_id == "REP-TEST-PROV").count()
    assert ev_count_2 == 2  # Must not duplicate rows


# 1B. Test Three Runs Equality
def test_consolidate_report_evidence_three_runs_equality(test_db):
    report = Report(id="REP-TRIPLE-RUN", filename="Triple_Run_Case.xml", status="extracted", page_count=1)
    test_db.add(report)

    ent1 = Entity(id="ENT-T1", report_id="REP-TRIPLE-RUN", type="PERSON", value="Vikram", confidence=0.9, source_page=1, source_report="Triple_Run_Case.xml", extraction_method="spacy_ner")
    ent2 = Entity(id="ENT-T2", report_id="REP-TRIPLE-RUN", type="PHONE", value="+91 9876543210", confidence=0.9, source_page=1, source_report="Triple_Run_Case.xml", extraction_method="regex")
    test_db.add_all([ent1, ent2])
    test_db.commit()

    run1 = consolidate_report_evidence("REP-TRIPLE-RUN", test_db)
    count1 = test_db.query(Evidence).filter(Evidence.report_id == "REP-TRIPLE-RUN").count()

    run2 = consolidate_report_evidence("REP-TRIPLE-RUN", test_db)
    count2 = test_db.query(Evidence).filter(Evidence.report_id == "REP-TRIPLE-RUN").count()

    run3 = consolidate_report_evidence("REP-TRIPLE-RUN", test_db)
    count3 = test_db.query(Evidence).filter(Evidence.report_id == "REP-TRIPLE-RUN").count()

    assert count1 == count2 == count3 == 2
    assert run1["total_evidence"] == run2["total_evidence"] == run3["total_evidence"] == 2


# 2. Strict Provenance Completeness Check
def test_evidence_provenance_completeness(test_db):
    report = Report(id="REP-PROV-CHECK", filename="Provenance_Verification.xml", status="extracted", page_count=1)
    test_db.add(report)

    ent = Entity(
        id="ENT-999",
        report_id="REP-PROV-CHECK",
        type="LOCATION",
        value="Connaught Place",
        normalized_value="Connaught Place",
        confidence=0.75,
        source_page=3,
        source_report="Provenance_Verification.xml",
        extraction_method="spacy_ner",
    )
    test_db.add(ent)
    test_db.commit()

    consolidate_report_evidence("REP-PROV-CHECK", test_db)

    evidence_items = test_db.query(Evidence).filter(Evidence.report_id == "REP-PROV-CHECK").all()
    assert len(evidence_items) == 1

    ev = evidence_items[0]
    assert ev.source_report == "Provenance_Verification.xml"
    assert ev.source_page == 3
    assert ev.confidence == 0.75
    assert ev.derived_from_entity_id == "ENT-999"
    assert ev.provenance_detail is not None
    assert "spacy_ner" in str(ev.provenance_detail)


# 3. API Integration Test for Consolidation, Search, Summary, and Detail View Logging
def test_api_evidence_endpoints_and_audit(client, test_db):
    seed_payload = {
        "filename": "API_Evidence_Test_Report.xml",
        "pages": [
            {"page_number": 1, "text_content": "Contact Inspector Vikram at vikram@gov.in or call 9876543210."}
        ],
    }

    create_resp = client.post("/api/v1/reports", json=seed_payload)
    assert create_resp.status_code == 201
    report_id = create_resp.json()["id"]

    # Run extraction first
    ext_resp = client.post(f"/api/v1/reports/{report_id}/extract")
    assert ext_resp.status_code == 200

    # POST consolidate
    cons_resp = client.post(f"/api/v1/reports/{report_id}/evidence/consolidate")
    assert cons_resp.status_code == 200
    summary_data = cons_resp.json()
    assert summary_data["total_evidence"] > 0

    # GET summary
    sum_resp = client.get(f"/api/v1/reports/{report_id}/evidence/summary")
    assert sum_resp.status_code == 200
    sum_json = sum_resp.json()
    assert sum_json["total_evidence"] == summary_data["total_evidence"]
    assert "type_breakdown" in sum_json

    # GET list evidence with filter
    list_resp = client.get(f"/api/v1/reports/{report_id}/evidence?evidence_type=EMAIL")
    assert list_resp.status_code == 200
    list_json = list_resp.json()
    assert len(list_json["items"]) > 0

    target_ev_id = list_json["items"][0]["evidence_id"]

    # GET detail by ID & verify AuditLog
    detail_resp = client.get(f"/api/v1/evidence/{target_ev_id}")
    assert detail_resp.status_code == 200
    detail_json = detail_resp.json()
    assert detail_json["evidence_id"] == target_ev_id
    assert "provenance_detail" in detail_json

    # Verify audit log recorded EVIDENCE_VIEWED
    audit_entry = (
        test_db.query(AuditLog)
        .filter(AuditLog.evidence_id == target_ev_id, AuditLog.action == "EVIDENCE_VIEWED")
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.actor == "system"


# 4. Test 404 handling
def test_evidence_not_found(client):
    response = client.get("/api/v1/evidence/EVT-NON-EXISTENT")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


# 5. Test 0 entities consolidation (empty report)
def test_empty_report_consolidation(test_db):
    empty_report = Report(id="REP-EMPTY", filename="Empty_Report.xml", status="parsed", page_count=1)
    test_db.add(empty_report)
    test_db.commit()

    summary = consolidate_report_evidence("REP-EMPTY", test_db)
    assert summary["total_evidence"] == 0
    assert summary["evidence_counts"] == {}
