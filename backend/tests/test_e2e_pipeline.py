from unittest.mock import patch


def test_full_e2e_forensic_pipeline(client, test_db):
    """
    End-to-End Integration Test:
    Executes complete pipeline: Report Ingestion -> Extraction -> Consolidation ->
    Symbolic Analysis -> Timeline -> Graph -> Structured Query -> Grounded Answer.
    """
    # 1. Ingest Synthetic Report
    res_upload = client.post("/api/v1/reports", json={
        "filename": "UFDR_E2E_Case_99.xml",
        "pages": [
            {
                "page_number": 1,
                "text_content": "Suspect Vikram Malhotra (+91 9876543210) called Rahul Sharma (+91 9123456789) on 12 March 2024 at 10:30 AM near Connaught Place.",
            },
            {
                "page_number": 2,
                "text_content": "Follow up email sent to vikram.m@forensics.gov.in from IP 192.168.1.50.",
            },
        ],
    })
    assert res_upload.status_code in (200, 201), f"Upload failed: {res_upload.text}"
    report_id = res_upload.json()["id"]

    # 2. Run Neural Entity Extraction (Phase 2)
    res_extract = client.post(f"/api/v1/reports/{report_id}/extract")
    assert res_extract.status_code == 200, f"Extract failed: {res_extract.text}"
    assert res_extract.json()["total_entities"] > 0

    # 3. Consolidate Evidence Database (Phase 3)
    res_cons = client.post(f"/api/v1/reports/{report_id}/evidence/consolidate")
    assert res_cons.status_code == 200, f"Consolidate failed: {res_cons.text}"
    assert res_cons.json()["total_evidence"] > 0

    # 4. Run Symbolic AI Rule Analysis (Phase 4)
    res_sym = client.post(f"/api/v1/reports/{report_id}/analyze")
    assert res_sym.status_code == 200, f"Analyze failed: {res_sym.text}"
    assert res_sym.json()["total_relationships"] >= 0

    # 5. Fetch Chronological Timeline (Phase 5)
    res_time = client.get(f"/api/v1/reports/{report_id}/timeline")
    assert res_time.status_code == 200, f"Timeline failed: {res_time.text}"
    assert "items" in res_time.json()

    # 6. Fetch Knowledge Graph Network (Phase 6)
    res_graph = client.get(f"/api/v1/reports/{report_id}/graph")
    assert res_graph.status_code == 200, f"Graph failed: {res_graph.text}"
    assert "nodes" in res_graph.json()
    assert "edges" in res_graph.json()

    # 7. Execute Structured Investigator Query (Phase 7)
    res_query = client.post(f"/api/v1/reports/{report_id}/query", json={"question": "Who did Vikram contact?"})
    assert res_query.status_code == 200, f"Query failed: {res_query.text}"
    assert res_query.json()["status"] == "RESULTS_FOUND"

    # 8. Execute Grounded LLM Answer Generation (Phase 8/9 default Groq)
    mock_answer = "Vikram Malhotra [EVT-1] contacted Rahul Sharma on 12 March 2024."
    with patch("app.llm.answer_service.external_client.generate_external_answer", return_value=mock_answer):
        res_answer = client.post(f"/api/v1/reports/{report_id}/answer", json={"question": "Who did Vikram contact?"})
        assert res_answer.status_code == 200, f"Answer failed: {res_answer.text}"
        ans_data = res_answer.json()
        assert ans_data["generated_by"] == "external_llm"
        assert ans_data["external_llm_used"] is True
        assert ans_data["pseudonymized"] is True
