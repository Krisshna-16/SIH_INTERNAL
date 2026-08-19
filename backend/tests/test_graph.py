import pytest
from app.models.report import Report
from app.models.evidence import Evidence
from app.models.relationship import Relationship
from app.graph.builder import build_report_graph
from app.graph.serializer import graph_to_frontend_json, get_node_neighborhood
from app.graph.metrics import compute_graph_metrics


# 1. Test Graph Building, Determinism, and Isolated Node Exclusion
def test_graph_building_and_isolated_exclusion(test_db):
    report = Report(id="REP-GR-001", filename="Graph_Test_Report.xml", status="extracted", page_count=1)
    test_db.add(report)

    # 3 evidence rows forming a triangle relationship + 1 isolated evidence row
    evA = Evidence(evidence_id="EVT-A", report_id="REP-GR-001", evidence_type="PERSON", value="Inspector Vikram", confidence=0.9, source_page=1, source_report="Graph_Test_Report.xml", provenance_detail="{}")
    evB = Evidence(evidence_id="EVT-B", report_id="REP-GR-001", evidence_type="PHONE", value="+91 9876543210", confidence=0.95, source_page=1, source_report="Graph_Test_Report.xml", provenance_detail="{}")
    evC = Evidence(evidence_id="EVT-C", report_id="REP-GR-001", evidence_type="LOCATION", value="Connaught Place", confidence=0.85, source_page=1, source_report="Graph_Test_Report.xml", provenance_detail="{}")
    ev_isolated = Evidence(evidence_id="EVT-ISO", report_id="REP-GR-001", evidence_type="EMAIL", value="isolated@gov.in", confidence=0.9, source_page=2, source_report="Graph_Test_Report.xml", provenance_detail="{}")

    test_db.add_all([evA, evB, evC, ev_isolated])

    rel1 = Relationship(id="REL-01", report_id="REP-GR-001", source_evidence_id="EVT-A", target_evidence_id="EVT-B", relationship_type="USED", classification="FACT", rule_id="RULE-PAGE-01", explanation="Co-occur on page 1", confidence=0.9)
    rel2 = Relationship(id="REL-02", report_id="REP-GR-001", source_evidence_id="EVT-A", target_evidence_id="EVT-C", relationship_type="LOCATED_AT", classification="FACT", rule_id="RULE-PAGE-01", explanation="Co-occur on page 1", confidence=0.85)
    rel3 = Relationship(id="REL-03", report_id="REP-GR-001", source_evidence_id="EVT-B", target_evidence_id="EVT-C", relationship_type="ASSOCIATED_WITH", classification="FACT", rule_id="RULE-PAGE-01", explanation="Co-occur on page 1", confidence=0.85)

    test_db.add_all([rel1, rel2, rel3])
    test_db.commit()

    # Build Graph 1
    G1 = build_report_graph("REP-GR-001", db=test_db)

    # Verify node count (3 participating entities; isolated EVT-ISO excluded)
    assert G1.number_of_nodes() == 3
    assert "EVT-ISO" not in G1.nodes
    assert "EVT-A" in G1.nodes
    assert "EVT-B" in G1.nodes
    assert "EVT-C" in G1.nodes

    # Verify edge count
    assert G1.number_of_edges() == 3

    # Build Graph 2 for determinism check
    G2 = build_report_graph("REP-GR-001", db=test_db)
    assert G1.number_of_nodes() == G2.number_of_nodes()
    assert G1.number_of_edges() == G2.number_of_edges()
    assert set(G1.nodes) == set(G2.nodes)


# 2. Test Serialization & Neighborhood Expansion
def test_neighborhood_expansion(test_db):
    report = Report(id="REP-GR-002", filename="Chain_Report.xml", status="extracted", page_count=1)
    test_db.add(report)

    # Chain: A -> B -> C -> D
    nodes = [Evidence(evidence_id=f"EVT-CHAIN-{i}", report_id="REP-GR-002", evidence_type="PERSON", value=f"Person_{i}", confidence=0.9, source_page=1, source_report="Chain_Report.xml", provenance_detail="{}") for i in range(1, 5)]
    test_db.add_all(nodes)

    rels = [
        Relationship(id="REL-C-1", report_id="REP-GR-002", source_evidence_id="EVT-CHAIN-1", target_evidence_id="EVT-CHAIN-2", relationship_type="ASSOCIATED_WITH", classification="FACT", rule_id="RULE-1", explanation="E1", confidence=0.9),
        Relationship(id="REL-C-2", report_id="REP-GR-002", source_evidence_id="EVT-CHAIN-2", target_evidence_id="EVT-CHAIN-3", relationship_type="ASSOCIATED_WITH", classification="FACT", rule_id="RULE-1", explanation="E2", confidence=0.9),
        Relationship(id="REL-C-3", report_id="REP-GR-002", source_evidence_id="EVT-CHAIN-3", target_evidence_id="EVT-CHAIN-4", relationship_type="ASSOCIATED_WITH", classification="FACT", rule_id="RULE-1", explanation="E3", confidence=0.9),
    ]
    test_db.add_all(rels)
    test_db.commit()

    G = build_report_graph("REP-GR-002", db=test_db)

    # Depth 1 from Node 1: should contain Node 1 & Node 2
    n_depth1 = get_node_neighborhood(G, "EVT-CHAIN-1", depth=1)
    node_ids_d1 = [n["id"] for n in n_depth1["nodes"]]
    assert len(node_ids_d1) == 2
    assert "EVT-CHAIN-1" in node_ids_d1
    assert "EVT-CHAIN-2" in node_ids_d1

    # Depth 2 from Node 1: should contain Node 1, Node 2 & Node 3
    n_depth2 = get_node_neighborhood(G, "EVT-CHAIN-1", depth=2)
    node_ids_d2 = [n["id"] for n in n_depth2["nodes"]]
    assert len(node_ids_d2) == 3
    assert "EVT-CHAIN-3" in node_ids_d2


# 3. Test API Endpoints, Filters, Edge Explanation, Depth Cap
def test_api_graph_endpoints(client, test_db):
    report = Report(id="REP-GR-API", filename="API_Graph_Report.xml", status="extracted", page_count=1)
    test_db.add(report)

    ev1 = Evidence(evidence_id="EVT-X1", report_id="REP-GR-API", evidence_type="PERSON", value="Suspect A", confidence=0.95, source_page=1, source_report="API_Graph_Report.xml", provenance_detail="{}")
    ev2 = Evidence(evidence_id="EVT-X2", report_id="REP-GR-API", evidence_type="PHONE", value="+91 9990001112", confidence=0.60, source_page=1, source_report="API_Graph_Report.xml", provenance_detail="{}")
    test_db.add_all([ev1, ev2])

    rel = Relationship(
        id="REL-X-1",
        report_id="REP-GR-API",
        source_evidence_id="EVT-X1",
        target_evidence_id="EVT-X2",
        relationship_type="USED",
        classification="FACT",
        rule_id="RULE-COOCCUR-PAGE-001",
        explanation="Suspect A used +91 9990001112 on page 1",
        confidence=0.60,
    )
    test_db.add(rel)
    test_db.commit()

    # 1. GET Full Graph
    res_full = client.get(f"/api/v1/reports/{report.id}/graph")
    assert res_full.status_code == 200
    data_full = res_full.json()
    assert len(data_full["nodes"]) == 2
    assert len(data_full["edges"]) == 1

    # 2. Min Confidence Filter (0.8 filter excludes confidence 0.60 edge)
    res_conf = client.get(f"/api/v1/reports/{report.id}/graph?min_confidence=0.80")
    assert res_conf.status_code == 200
    assert len(res_conf.json()["edges"]) == 0

    # 3. Graph Summary Endpoint
    res_sum = client.get(f"/api/v1/reports/{report.id}/graph/summary")
    assert res_sum.status_code == 200
    data_sum = res_sum.json()
    assert data_sum["node_count"] == 2
    assert data_sum["edge_count"] == 1
    assert len(data_sum["top_connected_nodes"]) > 0

    # 4. Edge Explanation Endpoint
    res_exp = client.get(f"/api/v1/reports/{report.id}/graph/edges/REL-X-1/explanation")
    assert res_exp.status_code == 200
    data_exp = res_exp.json()
    assert data_exp["relationship_id"] == "REL-X-1"
    assert data_exp["rule_id"] == "RULE-COOCCUR-PAGE-001"
    assert "Suspect A used" in data_exp["explanation"]

    # 5. Depth Cap Validation (depth=4 returns 400)
    res_depth_err = client.get(f"/api/v1/reports/{report.id}/graph/nodes/EVT-X1/neighborhood?depth=4")
    assert res_depth_err.status_code == 400
    assert "cannot exceed 3" in res_depth_err.json()["detail"]
