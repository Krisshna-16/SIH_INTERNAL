import pytest
from app.models.report import Report
from app.models.evidence import Evidence
from app.models.relationship import Relationship
from app.models.finding import Finding
from app.symbolic.relationship_rules import rule_same_page_cooccurrence
from app.symbolic.finding_rules import rule_page_cooccurrence_cluster
from app.symbolic.engine import SymbolicEngine


# 1. Test Relationship Derivation Rules (FACT classification & explanation)
def test_same_page_relationship_rule(test_db):
    report = Report(id="REP-SYM-001", filename="Symbolic_Test_Case.xml", status="extracted", page_count=1)
    test_db.add(report)

    ev1 = Evidence(
        evidence_id="EVT-001",
        report_id="REP-SYM-001",
        evidence_type="PERSON",
        value="Inspector Vikram",
        confidence=0.9,
        source_page=1,
        source_report="Symbolic_Test_Case.xml",
        provenance_detail="{}",
    )
    ev2 = Evidence(
        evidence_id="EVT-002",
        report_id="REP-SYM-001",
        evidence_type="PHONE",
        value="+91 9876543210",
        confidence=0.95,
        source_page=1,
        source_report="Symbolic_Test_Case.xml",
        provenance_detail="{}",
    )
    test_db.add_all([ev1, ev2])
    test_db.commit()

    derived_rels = rule_same_page_cooccurrence([ev1, ev2])
    assert len(derived_rels) == 1
    rel = derived_rels[0]

    assert rel["relationship_type"] == "USED"
    assert rel["classification"] == "FACT"
    assert rel["rule_id"] == "RULE-COOCCUR-PAGE-001"
    assert "Inspector Vikram" in rel["explanation"]
    assert "+91 9876543210" in rel["explanation"]


# 2. Test Threshold-based Finding Rules (Threshold Met vs Below Threshold)
def test_finding_rules_thresholds(test_db):
    ev_below = [
        Evidence(evidence_id="EVT-A1", report_id="R1", evidence_type="PERSON", value="A", confidence=0.9, source_page=1, source_report="R1", provenance_detail="{}"),
        Evidence(evidence_id="EVT-A2", report_id="R1", evidence_type="PHONE", value="B", confidence=0.9, source_page=1, source_report="R1", provenance_detail="{}"),
    ]
    findings_below = rule_page_cooccurrence_cluster(ev_below)
    assert len(findings_below) == 0  # 2 entities < threshold 3

    ev_above = [
        Evidence(evidence_id="EVT-B1", report_id="R1", evidence_type="PERSON", value="A", confidence=0.9, source_page=2, source_report="R1", provenance_detail="{}"),
        Evidence(evidence_id="EVT-B2", report_id="R1", evidence_type="PHONE", value="B", confidence=0.9, source_page=2, source_report="R1", provenance_detail="{}"),
        Evidence(evidence_id="EVT-B3", report_id="R1", evidence_type="LOCATION", value="C", confidence=0.9, source_page=2, source_report="R1", provenance_detail="{}"),
    ]
    findings_above = rule_page_cooccurrence_cluster(ev_above)
    assert len(findings_above) == 1  # 3 entities >= threshold 3
    assert findings_above[0]["finding_type"] == "PAGE_COOCCURRENCE_CLUSTER"
    assert findings_above[0]["classification"] == "INFERENCE"
    assert len(findings_above[0]["related_evidence_ids"]) == 3


# 3. Test Symbolic Engine Idempotency
def test_symbolic_engine_idempotency(test_db):
    report = Report(id="REP-IDEM-001", filename="Idempotency_Report.xml", status="extracted", page_count=1)
    test_db.add(report)

    for i in range(1, 4):
        test_db.add(Evidence(
            evidence_id=f"EVT-IDEM-{i}",
            report_id="REP-IDEM-001",
            evidence_type="PERSON" if i == 1 else ("PHONE" if i == 2 else "LOCATION"),
            value=f"Entity_{i}",
            confidence=0.9,
            source_page=1,
            source_report="Idempotency_Report.xml",
            provenance_detail="{}",
        ))
    test_db.commit()

    engine = SymbolicEngine()

    # First run
    summary1 = engine.process_report("REP-IDEM-001", test_db)
    assert summary1["total_relationships"] > 0
    assert summary1["total_findings"] > 0

    rel_count_1 = test_db.query(Relationship).filter(Relationship.report_id == "REP-IDEM-001").count()
    fnd_count_1 = test_db.query(Finding).filter(Finding.report_id == "REP-IDEM-001").count()

    # Second run
    summary2 = engine.process_report("REP-IDEM-001", test_db)
    rel_count_2 = test_db.query(Relationship).filter(Relationship.report_id == "REP-IDEM-001").count()
    fnd_count_2 = test_db.query(Finding).filter(Finding.report_id == "REP-IDEM-001").count()

    assert rel_count_1 == rel_count_2
    assert fnd_count_1 == fnd_count_2


# 4. API Integration Test for /analyze, /relationships, /findings, and GET /findings/{id}
def test_api_symbolic_endpoints(client):
    seed_payload = {
        "filename": "API_Symbolic_Test_Report.xml",
        "pages": [
            {
                "page_number": 1,
                "text_content": "Suspect Vikram (+91 9876543210) visited Connaught Place and New Delhi. Contact vikram@test.org.",
            }
        ],
    }

    # 1. Create Report
    create_resp = client.post("/api/v1/reports", json=seed_payload)
    assert create_resp.status_code == 201
    report_id = create_resp.json()["id"]

    # 2. Extract Entities & Consolidate Evidence
    client.post(f"/api/v1/reports/{report_id}/extract")
    client.post(f"/api/v1/reports/{report_id}/evidence/consolidate")

    # 3. Trigger Symbolic Analysis
    analyze_resp = client.post(f"/api/v1/reports/{report_id}/analyze")
    assert analyze_resp.status_code == 200
    summary = analyze_resp.json()

    assert summary["total_relationships"] > 0
    assert summary["total_findings"] > 0

    # 4. List Relationships
    rels_resp = client.get(f"/api/v1/reports/{report_id}/relationships")
    assert rels_resp.status_code == 200
    rels_data = rels_resp.json()
    assert len(rels_data["items"]) > 0

    first_rel = rels_data["items"][0]
    assert first_rel["classification"] == "FACT"
    assert len(first_rel["explanation"]) > 0
    assert len(first_rel["rule_id"]) > 0

    # 5. List Findings
    fnds_resp = client.get(f"/api/v1/reports/{report_id}/findings")
    assert fnds_resp.status_code == 200
    fnds_data = fnds_resp.json()
    assert len(fnds_data["items"]) > 0

    first_fnd = fnds_data["items"][0]
    target_fnd_id = first_fnd["id"]
    assert first_fnd["classification"] == "INFERENCE"
    assert len(first_fnd["rule_id"]) > 0
    assert len(first_fnd["explanation"]) > 0
    assert len(first_fnd["related_evidence_ids"]) > 0

    # 6. GET Finding Detail by ID & verify evidence resolution
    detail_resp = client.get(f"/api/v1/findings/{target_fnd_id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()

    assert detail_data["id"] == target_fnd_id
    assert "related_evidence" in detail_data
    assert len(detail_data["related_evidence"]) > 0
    assert "evidence_id" in detail_data["related_evidence"][0]
