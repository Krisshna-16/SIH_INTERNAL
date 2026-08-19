import pytest
from app.extraction.pattern_rules import extract_regex_patterns, normalize_phone
from app.extraction.spacy_extractor import SpacyExtractor
from app.models.entity import Entity


# 1. Regex Extractor Unit Tests
def test_regex_pattern_extraction():
    sample_text = (
        "Contact investigator Vikram Malhotra at vikram.m@forensics.gov.in or call +91 9876543210. "
        "Case logs updated at https://evidence.internal/case/101 from IP 192.168.1.45."
    )
    matches = extract_regex_patterns(sample_text)

    types = [m[0] for m in matches]
    raw_vals = [m[1] for m in matches]
    confidences = [m[3] for m in matches]

    assert "EMAIL" in types
    assert "PHONE" in types
    assert "URL" in types
    assert "IP_ADDRESS" in types

    assert "vikram.m@forensics.gov.in" in raw_vals
    assert "+91 9876543210" in raw_vals
    assert "https://evidence.internal/case/101" in raw_vals
    assert "192.168.1.45" in raw_vals

    for c in confidences:
        assert 0.9 <= c <= 1.0


def test_phone_normalization():
    assert normalize_phone("9876543210") == "+919876543210"
    assert normalize_phone("+91 98765 43210") == "+919876543210"
    assert normalize_phone("09876543210") == "+919876543210"


# 2. Pipeline Unit Test
def test_extraction_pipeline_synthetic_page():
    extractor = SpacyExtractor()
    sample_page = (
        "Rahul Sharma called 9876543210 regarding a meeting near Connaught Place "
        "on 12 March 2024. Email confirmation sent to rahul.sharma@example.com."
    )
    dtos = extractor.extract(page_text=sample_page, page_number=1, report_id="REP-TEST-001")

    assert len(dtos) >= 4

    types = [d.type for d in dtos]
    assert "PHONE" in types
    assert "EMAIL" in types
    assert "PERSON" in types or "LOCATION" in types

    for d in dtos:
        assert d.source_page == 1
        assert d.source_report == "REP-TEST-001"
        assert 0.0 <= d.confidence <= 1.0
        assert d.extraction_method in ["spacy_ner", "regex_phone", "regex_email", "regex_url", "regex_ip"]


# 3. API Integration Test for POST /extract & GET /entities
def test_api_extract_and_get_entities(client):
    seed_payload = {
        "filename": "Synthetic_UFDR_Report.xml",
        "pages": [
            {
                "page_number": 1,
                "text_content": "Suspect Ankit Verma visited Connaught Place on 15 January 2024. Contact: ankit.v@test.org or +91 9123456789.",
            },
            {
                "page_number": 2,
                "text_content": "Follow up meeting scheduled with Priya Singh at New Delhi. Evidence server: http://secure-portal.gov.in.",
            },
        ],
    }

    create_resp = client.post("/api/v1/reports", json=seed_payload)
    assert create_resp.status_code == 201
    report_data = create_resp.json()
    report_id = report_data["id"]

    # Trigger extraction
    extract_resp = client.post(f"/api/v1/reports/{report_id}/extract")
    assert extract_resp.status_code == 200
    extract_data = extract_resp.json()

    assert extract_data["report_id"] == report_id
    assert extract_data["total_entities"] > 0
    assert extract_data["pages_processed"] == 2
    assert extract_data["page_errors"] == 0
    assert "entity_counts" in extract_data

    # Fetch entities via GET /reports/{report_id}/entities
    entities_resp = client.get(f"/api/v1/reports/{report_id}/entities")
    assert entities_resp.status_code == 200
    entities_data = entities_resp.json()

    assert entities_data["total"] == extract_data["total_entities"]
    assert len(entities_data["items"]) > 0

    first_item = entities_data["items"][0]
    assert "id" in first_item
    assert first_item["source_page"] in [1, 2]
    assert first_item["source_report"] == "Synthetic_UFDR_Report.xml"
    assert 0.0 <= first_item["confidence"] <= 1.0


# 4. Strict Provenance Enforcement Test
def test_no_entity_without_traceable_provenance(client, test_db):
    seed_payload = {
        "filename": "Provenance_Check_Report.xml",
        "pages": [{"page_number": 1, "text_content": "Call log entry from 9998887776 on 10 February 2024."}],
    }

    create_resp = client.post("/api/v1/reports", json=seed_payload)
    report_id = create_resp.json()["id"]

    client.post(f"/api/v1/reports/{report_id}/extract")

    entities = test_db.query(Entity).filter(Entity.report_id == report_id).all()
    assert len(entities) > 0

    for ent in entities:
        assert ent.source_page is not None
        assert ent.source_page > 0
        assert ent.source_report is not None
        assert len(ent.source_report.strip()) > 0
        assert ent.confidence is not None


# 5. Error Handling Test for Missing/Empty Reports
def test_extract_invalid_report(client):
    response = client.post("/api/v1/reports/NON-EXISTENT-ID/extract")
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]
