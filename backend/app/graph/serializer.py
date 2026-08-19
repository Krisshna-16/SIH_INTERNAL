from typing import Dict, Any, List
import networkx as nx


def graph_to_frontend_json(G: nx.DiGraph) -> Dict[str, List[Dict[str, Any]]]:
    """
    Serializes a NetworkX DiGraph into standard nodes/edges JSON structure.
    
    PRIVACY / REDACTION HOOK NOTE:
    In Phase 9 (Privacy Gateway), requests returning node `value` or edge `explanation`
    will be intercepted to apply pseudonymization / RBAC redaction prior to display.
    """
    nodes = []
    for node_id, attrs in G.nodes(data=True):
        nodes.append({
            "id": node_id,
            "evidence_id": attrs.get("evidence_id", node_id),
            "evidence_type": attrs.get("evidence_type", "UNKNOWN"),
            "value": attrs.get("value", ""),
            "normalized_value": attrs.get("normalized_value"),
            "confidence": attrs.get("confidence", 1.0),
            "source_page": attrs.get("source_page", 1),
            "source_report": attrs.get("source_report", ""),
        })

    edges = []
    for u, v, attrs in G.edges(data=True):
        edges.append({
            "id": attrs.get("relationship_id", f"{u}->{v}"),
            "source": u,
            "target": v,
            "relationship_id": attrs.get("relationship_id"),
            "relationship_type": attrs.get("relationship_type", "ASSOCIATED_WITH"),
            "classification": attrs.get("classification", "FACT"),
            "rule_id": attrs.get("rule_id", ""),
            "explanation": attrs.get("explanation", ""),
            "confidence": attrs.get("confidence", 1.0),
        })

    return {
        "nodes": nodes,
        "edges": edges,
    }


def get_node_neighborhood(G: nx.DiGraph, evidence_id: str, depth: int = 1) -> Dict[str, List[Dict[str, Any]]]:
    """
    Computes node-centric ego-subgraph within `depth` hops of `evidence_id`.
    Depth is capped at 3 to prevent runaway graph queries.
    """
    if depth > 3:
        raise ValueError("Depth parameter cannot exceed 3.")

    if evidence_id not in G:
        raise ValueError(f"Evidence node '{evidence_id}' not found in report graph.")

    # Convert to undirected for hop distance calculation
    G_undirected = G.to_undirected()
    lengths = nx.single_source_shortest_path_length(G_undirected, evidence_id, cutoff=depth)
    neighborhood_nodes = set(lengths.keys())

    subgraph = G.subgraph(neighborhood_nodes)
    return graph_to_frontend_json(subgraph)
