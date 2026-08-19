from datetime import datetime, timezone
import pytest
from app.models.report import Report
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.timeline.assembler import get_report_timeline, get_timeline_summary
from app.timeline.filters import TimelineFilters


# 1. Test Ascending Order and Null Timestamp Exclusion
def test_timeline_ascending_and_null_exclusion(test_db):
    report = Report(id="REP-TL-001", filename="Timeline_Test_Report.xml", status="extracted", page_count=2)
    test_db.add(report)

    dt1 = datetime(2024, 3, 12, 10, 30, 0, tzinfo=timezone.utc)
    dt2 = datetime(2024, 3, 12, 14, 5, 0, tzinfo=timezone.utc)
    dt3 = datetime(2024, 3, 11, 9, 15, 0, tzinfo=timezone.utc)

    # 3 timestamped evidence rows + 1 null timestamp evidence row
    ev1 = Evidence(evidence_id="EVT-TL-01", report_id="REP-TL-001", evidence_type="DATE", value="12 March 2024", timestamp=dt1, confidence=0.9, source_page=1, source_report="Timeline_Test_Report.xml", provenance_detail="{}")
    ev2 = Evidence(evidence_id="EVT-TL-02", report_id="REP-TL-001", evidence_type="PHONE", value="+91 9876543210", timestamp=dt2, confidence=0.9, source_page=1, source_report="Timeline_Test_Report.xml", provenance_detail="{}")
    ev3 = Evidence(evidence_id="EVT-TL-03", report_id="REP-TL-001", evidence_type="LOCATION", value="Connaught Place", timestamp=dt3, confidence=0.9, source_page=2, source_report="Timeline_Test_Report.xml", provenance_detail="{}")
    ev_null = Evidence(evidence_id="EVT-TL-NULL", report_id="REP-TL-001", evidence_type="PERSON", value="Rahul", timestamp=None, confidence=0.9, source_page=1, source_report="Timeline_Test_Report.xml", provenance_detail="{}")

    test_db.add_all([ev1, ev2, ev3, ev_null])
    test_db.commit()

    filters = TimelineFilters(page=1, page_size=50)
    entries, total = get_report_timeline("REP-TL-001", filters, test_db)

    assert total == 3
    assert len(entries) == 3

    # Verify NULL timestamp evidence is excluded
    entry_ev_ids = [e.evidence_id for e in entries if e.evidence_id]
    assert "EVT-TL-NULL" not in entry_ev_ids

    # Verify strict ascending order (dt3 -> dt1 -> dt2)
    assert entries[0].evidence_id == "EVT-TL-03"
    assert entries[1].evidence_id == "EVT-TL-01"
    assert entries[2].evidence_id == "EVT-TL-02"


# 2. Test Timeline API Integration with Filters & Findings
def test_api_timeline_filtering(client, test_db):
    report = Report(id="REP-TL-API", filename="API_Timeline_Report.xml", status="extracted", page_count=2)
    test_db.add(report)

    dt1 = datetime(2024, 1, 10, 8, 0, 0, tzinfo=timezone.utc)
    dt2 = datetime(2024, 5, 20, 15, 30, 0, tzinfo=timezone.utc)

    ev1 = Evidence(evidence_id="EVT-A1", report_id="REP-TL-API", evidence_type="EMAIL", value="vikram@gov.in", timestamp=dt1, confidence=0.95, source_page=1, source_report="API_Timeline_Report.xml", provenance_detail="{}")
    ev2 = Evidence(evidence_id="EVT-A2", report_id="REP-TL-API", evidence_type="PHONE", value="+91 9112233445", timestamp=dt2, confidence=0.95, source_page=2, source_report="API_Timeline_Report.xml", provenance_detail="{}")
    test_db.add_all([ev1, ev2])

    fnd = Finding(
        id="FND-TL-01",
        report_id="REP-TL-API",
        finding_type="COMMUNICATION_CLUSTER",
        classification="INFERENCE",
        rule_id="RULE-COMM-CLUSTER-001",
        rule_name="Communication Window Cluster",
        explanation="Flagged communication cluster",
        related_evidence_ids='["EVT-A1", "EVT-A2"]',
        parameters_used='{}',
        severity="HIGH",
    )
    test_db.add(fnd)
    test_db.commit()

    # 1. GET Full Timeline
    res1 = client.get(f"/api/v1/reports/{report.id}/timeline")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total"] == 3  # 2 Evidence + 1 Finding marker

    # 2. Date Range Filter
    res_date = client.get(f"/api/v1/reports/{report.id}/timeline?start_date=2024-05-01T00:00:00")
    assert res_date.status_code == 200
    data_date = res_date.json()
    assert data_date["total"] == 1
    assert data_date["items"][0]["evidence_id"] == "EVT-A2"

    # 3. Entity Search Filter (Matches both Evidence EVT-A1 and Finding FND-TL-01 referencing vikram@gov.in)
    res_entity = client.get(f"/api/v1/reports/{report.id}/timeline/entities/vikram@gov.in")
    assert res_entity.status_code == 200
    data_entity = res_entity.json()
    assert data_entity["total"] == 2
    assert data_entity["items"][0]["evidence_id"] == "EVT-A1"

    # 4. Classification Filter
    res_fact = client.get(f"/api/v1/reports/{report.id}/timeline?classification=FACT")
    assert res_fact.status_code == 200
    assert res_fact.json()["total"] == 2

    res_inf = client.get(f"/api/v1/reports/{report.id}/timeline?classification=INFERENCE")
    assert res_inf.status_code == 200
    assert res_inf.json()["total"] == 1


# 3. Test Summary Endpoint
def test_timeline_summary_endpoint(client, test_db):
    report = Report(id="REP-TL-SUM", filename="Summary_Report.xml", status="extracted", page_count=1)
    test_db.add(report)

    dt1 = datetime(2024, 2, 1, 10, 0, 0, tzinfo=timezone.utc)
    dt2 = datetime(2024, 2, 10, 18, 0, 0, tzinfo=timezone.utc)

    ev1 = Evidence(evidence_id="EVT-S1", report_id="REP-TL-SUM", evidence_type="LOCATION", value="Delhi", timestamp=dt1, confidence=0.9, source_page=1, source_report="Summary_Report.xml", provenance_detail="{}")
    ev2 = Evidence(evidence_id="EVT-S2", report_id="REP-TL-SUM", evidence_type="LOCATION", value="Mumbai", timestamp=dt2, confidence=0.9, source_page=1, source_report="Summary_Report.xml", provenance_detail="{}")
    test_db.add_all([ev1, ev2])
    test_db.commit()

    res = client.get(f"/api/v1/reports/{report.id}/timeline/summary")
    assert res.status_code == 200
    data = res.json()

    assert data["total_entries"] == 2
    assert data["has_timestamped_evidence"] is True
    assert data["earliest_timestamp"].startswith("2024-02-01T10:00:00")
    assert data["latest_timestamp"].startswith("2024-02-10T18:00:00")
    assert data["entries_by_type"]["LOCATION"] == 2


# 4. Test Error Handling (Invalid Date Range & 404)
def test_timeline_invalid_date_range(client, test_db):
    report = Report(id="REP-TL-ERR", filename="Err_Report.xml", status="extracted", page_count=1)
    test_db.add(report)
    test_db.commit()

    res = client.get(f"/api/v1/reports/{report.id}/timeline?start_date=2024-12-31T00:00:00&end_date=2024-01-01T00:00:00")
    assert res.status_code == 400
    assert "start_date cannot be after end_date" in res.json()["detail"]

    res_404 = client.get("/api/v1/reports/NON-EXISTENT/timeline")
    assert res_404.status_code == 404
