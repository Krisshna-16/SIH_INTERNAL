from typing import Dict, Any, List
import networkx as nx


def compute_graph_metrics(G: nx.DiGraph) -> Dict[str, Any]:
    """
    Computes explainable structural graph metrics (degree centrality, node/edge counts).
    
    EXPLAINABLE METRICS NOTE:
    Degree centrality measures structural connection density (number of relationships).
    It is a purely mathematical structural metric, not an AI inference or secret score.
    """
    node_count = G.number_of_nodes()
    edge_count = G.number_of_edges()

    if node_count == 0:
        return {
            "node_count": 0,
            "edge_count": 0,
            "relationship_types": {},
            "classifications": {},
            "top_connected_nodes": [],
            "metric_type": "STRUCTURAL_DEGREE_CENTRALITY",
        }

    # Relationship type breakdown
    rel_counts: Dict[str, int] = {}
    class_counts: Dict[str, int] = {}
    for u, v, attrs in G.edges(data=True):
        rel_type = attrs.get("relationship_type", "ASSOCIATED_WITH")
        rel_cls = attrs.get("classification", "FACT")
        rel_counts[rel_type] = rel_counts.get(rel_type, 0) + 1
        class_counts[rel_cls] = class_counts.get(rel_cls, 0) + 1

    # Degree centrality
    centrality_map = nx.degree_centrality(G)
    sorted_nodes = sorted(centrality_map.items(), key=lambda x: x[1], reverse=True)

    top_nodes: List[Dict[str, Any]] = []
    for node_id, score in sorted_nodes[:5]:
        attrs = G.nodes[node_id]
        top_nodes.append({
            "evidence_id": node_id,
            "value": attrs.get("value", ""),
            "evidence_type": attrs.get("evidence_type", "UNKNOWN"),
            "degree_centrality": round(score, 4),
            "connection_count": G.degree(node_id),
        })

    return {
        "node_count": node_count,
        "edge_count": edge_count,
        "relationship_types": rel_counts,
        "classifications": class_counts,
        "top_connected_nodes": top_nodes,
        "metric_type": "STRUCTURAL_DEGREE_CENTRALITY",
    }
