import json
from datetime import datetime, timezone
import pytest
from app.models.report import Report
from app.models.evidence import Evidence
from app.models.relationship import Relationship
from app.models.finding import Finding
from app.models.entity import Entity


def test_data_sensitivity_across_different_reports(client, test_db):
    """
    Data-Sensitivity Verification Test (TASK 3):
    Seeds TWO completely distinct synthetic reports into the database with different
    counts, entities, evidence, relationships, and findings.
    Asserts that API calls to every major endpoint return distinct, report-specific data.
    """
    print("\n" + "="*80)
    print("STARTING DATA-SENSITIVITY VERIFICATION TEST BETWEEN TWO DIFFERENT REPORTS")
    print("="*80)

    # ----------------------------------------------------
    # 1. Seed Report A: Alpha Case (Small Case - 2 entities, 1 evidence, 0 findings)
    # ----------------------------------------------------
    report_a = Report(
        id="REP-ALPHA-101",
        filename="Alpha_Case_Report.xml",
        status="analyzed",
        page_count=2
    )
    test_db.add(report_a)

    ent_a1 = Entity(
        id="ENT-A1", report_id="REP-ALPHA-101", type="PERSON",
        value="Officer Alpha", source_page=1, source_report="Alpha_Case_Report.xml",
        confidence=0.95, extraction_method="regex"
    )
    ent_a2 = Entity(
        id="ENT-A2", report_id="REP-ALPHA-101", type="PHONE",
        value="+91 9999900001", source_page=1, source_report="Alpha_Case_Report.xml",
        confidence=0.98, extraction_method="regex"
    )
    test_db.add_all([ent_a1, ent_a2])

    ev_a1 = Evidence(
        evidence_id="EVT-ALPHA-1", report_id="REP-ALPHA-101", evidence_type="PERSON",
        value="Officer Alpha", confidence=0.95, source_page=1,
        source_report="Alpha_Case_Report.xml", provenance_detail="{}",
        timestamp=datetime(2024, 3, 10, 9, 0, tzinfo=timezone.utc)
    )
    test_db.add(ev_a1)

    # ----------------------------------------------------
    # 2. Seed Report B: Bravo Case (Large Case - 4 entities, 3 evidence, 2 relationships, 1 finding)
    # ----------------------------------------------------
    report_b = Report(
        id="REP-BRAVO-202",
        filename="Bravo_Case_Report.xml",
        status="analyzed",
        page_count=15
    )
    test_db.add(report_b)

    ent_b1 = Entity(id="ENT-B1", report_id="REP-BRAVO-202", type="PERSON", value="Suspect Bravo", source_page=1, source_report="Bravo_Case_Report.xml", confidence=0.9, extraction_method="regex")
    ent_b2 = Entity(id="ENT-B2", report_id="REP-BRAVO-202", type="PHONE", value="+91 8888800002", source_page=1, source_report="Bravo_Case_Report.xml", confidence=0.9, extraction_method="regex")
    ent_b3 = Entity(id="ENT-B3", report_id="REP-BRAVO-202", type="EMAIL", value="bravo@target.com", source_page=2, source_report="Bravo_Case_Report.xml", confidence=0.9, extraction_method="regex")
    ent_b4 = Entity(id="ENT-B4", report_id="REP-BRAVO-202", type="LOCATION", value="Mumbai Port", source_page=3, source_report="Bravo_Case_Report.xml", confidence=0.9, extraction_method="regex")
    test_db.add_all([ent_b1, ent_b2, ent_b3, ent_b4])

    ev_b1 = Evidence(evidence_id="EVT-BRAVO-1", report_id="REP-BRAVO-202", evidence_type="PERSON", value="Suspect Bravo", confidence=0.9, source_page=1, source_report="Bravo_Case_Report.xml", provenance_detail="{}", timestamp=datetime(2024, 3, 12, 10, 30, tzinfo=timezone.utc))
    ev_b2 = Evidence(evidence_id="EVT-BRAVO-2", report_id="REP-BRAVO-202", evidence_type="PHONE", value="+91 8888800002", confidence=0.9, source_page=1, source_report="Bravo_Case_Report.xml", provenance_detail="{}", timestamp=datetime(2024, 3, 12, 10, 35, tzinfo=timezone.utc))
    ev_b3 = Evidence(evidence_id="EVT-BRAVO-3", report_id="REP-BRAVO-202", evidence_type="EMAIL", value="bravo@target.com", confidence=0.9, source_page=2, source_report="Bravo_Case_Report.xml", provenance_detail="{}", timestamp=datetime(2024, 3, 12, 10, 40, tzinfo=timezone.utc))
    test_db.add_all([ev_b1, ev_b2, ev_b3])

    rel_b1 = Relationship(
        id="REL-BRAVO-1", report_id="REP-BRAVO-202",
        source_evidence_id="EVT-BRAVO-1", target_evidence_id="EVT-BRAVO-2",
        relationship_type="USED", classification="FACT", rule_id="RULE-1",
        explanation="Suspect Bravo used +91 8888800002", confidence=0.9
    )
    rel_b2 = Relationship(
        id="REL-BRAVO-2", report_id="REP-BRAVO-202",
        source_evidence_id="EVT-BRAVO-1", target_evidence_id="EVT-BRAVO-3",
        relationship_type="ASSOCIATED_WITH", classification="INFERENCE", rule_id="RULE-2",
        explanation="Associated via email login", confidence=0.85
    )
    test_db.add_all([rel_b1, rel_b2])

    fnd_b1 = Finding(
        id="FND-BRAVO-1", report_id="REP-BRAVO-202", finding_type="SUSPICIOUS_COMMUNICATION",
        classification="INFERENCE", rule_id="RULE-F1", rule_name="High Frequency Contact",
        explanation="Multiple rapid contacts detected", related_evidence_ids=json.dumps(["EVT-BRAVO-1", "EVT-BRAVO-2"]),
        parameters_used="{}", severity="HIGH"
    )
    test_db.add(fnd_b1)

    test_db.commit()

    # ----------------------------------------------------
    # 3. Assert Endpoints Return Report-Specific Data
    # ----------------------------------------------------

    # A. Entities Endpoint
    res_ent_a = client.get(f"/api/v1/reports/{report_a.id}/entities").json()
    res_ent_b = client.get(f"/api/v1/reports/{report_b.id}/entities").json()
    print(f"[ASSERTION A - ENTITIES] Report A Count: {res_ent_a['total']} | Report B Count: {res_ent_b['total']}")
    values_a = [item["value"] for item in res_ent_a["items"]]
    values_b = [item["value"] for item in res_ent_b["items"]]
    print(f"  -> Report A Entity Values: {values_a}")
    print(f"  -> Report B Entity Values: {values_b}")
    assert res_ent_a["total"] == 2
    assert res_ent_b["total"] == 4
    assert "Officer Alpha" in values_a
    assert "Suspect Bravo" in values_b
    assert "Officer Alpha" not in values_b

    # B. Evidence Endpoint & Summary
    res_ev_a = client.get(f"/api/v1/reports/{report_a.id}/evidence").json()
    res_ev_b = client.get(f"/api/v1/reports/{report_b.id}/evidence").json()
    res_sum_a = client.get(f"/api/v1/reports/{report_a.id}/evidence/summary").json()
    res_sum_b = client.get(f"/api/v1/reports/{report_b.id}/evidence/summary").json()
    print(f"[ASSERTION B - EVIDENCE VAULT] Report A Evidence Total: {res_ev_a['total']} (File: {res_sum_a['filename']}) | Report B Evidence Total: {res_ev_b['total']} (File: {res_sum_b['filename']})")
    assert res_ev_a["total"] == 1
    assert res_ev_b["total"] == 3
    assert res_sum_a["filename"] == "Alpha_Case_Report.xml"
    assert res_sum_b["filename"] == "Bravo_Case_Report.xml"

    # C. Relationships Endpoint
    res_rel_a = client.get(f"/api/v1/reports/{report_a.id}/relationships").json()
    res_rel_b = client.get(f"/api/v1/reports/{report_b.id}/relationships").json()
    print(f"[ASSERTION C - RELATIONSHIPS] Report A Relationships: {res_rel_a['total']} | Report B Relationships: {res_rel_b['total']}")
    assert res_rel_a["total"] == 0
    assert res_rel_b["total"] == 2

    # D. Findings Endpoint
    res_fnd_a = client.get(f"/api/v1/reports/{report_a.id}/findings").json()
    res_fnd_b = client.get(f"/api/v1/reports/{report_b.id}/findings").json()
    print(f"[ASSERTION D - ANOMALY FINDINGS] Report A Findings: {res_fnd_a['total']} | Report B Findings: {res_fnd_b['total']}")
    assert res_fnd_a["total"] == 0
    assert res_fnd_b["total"] == 1

    # E. Knowledge Graph Endpoint
    res_grp_a = client.get(f"/api/v1/reports/{report_a.id}/graph").json()
    res_grp_b = client.get(f"/api/v1/reports/{report_b.id}/graph").json()
    print(f"[ASSERTION E - KNOWLEDGE GRAPH] Report A Nodes/Edges: {len(res_grp_a['nodes'])}/{len(res_grp_a['edges'])} | Report B Nodes/Edges: {len(res_grp_b['nodes'])}/{len(res_grp_b['edges'])}")
    assert len(res_grp_a["nodes"]) == 0
    assert len(res_grp_b["nodes"]) == 3
    assert len(res_grp_a["edges"]) == 0
    assert len(res_grp_b["edges"]) == 2

    # F. Timeline Endpoint
    res_tml_a = client.get(f"/api/v1/reports/{report_a.id}/timeline").json()
    res_tml_b = client.get(f"/api/v1/reports/{report_b.id}/timeline").json()
    print(f"[ASSERTION F - TIMELINE STREAM] Report A Timeline Entries: {len(res_tml_a['items'])} | Report B Timeline Entries: {len(res_tml_b['items'])}")
    assert len(res_tml_a["items"]) == 1
    assert len(res_tml_b["items"]) >= 3

    print("="*80)
    print("VERIFICATION COMPLETE: REPORT A AND REPORT B PRODUCED DISTINCT DATA SETS AT EVERY ENDPOINT")
    print("="*80 + "\n")
