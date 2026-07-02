"""Build and analyze knowledge graphs from extracted entities."""

import logging

import networkx as nx

from app.geopolitical.models import ExtractedEntity, GraphEdge, GraphNode

logger = logging.getLogger(__name__)

RELATION_MAP = {
    "COUNTRY": ("affects", "affected_by"),
    "ORGANIZATION": ("interacts_with", "interacted_by"),
    "PERSON": ("involves", "involved_by"),
    "PRODUCT": ("produces", "produced_by"),
    "EVENT": ("impacts", "impacted_by"),
    "FACILITY": ("located_in", "located_in_by"),
    "LOCATION": ("located_in", "located_in_by"),
    "GROUP": ("related_to", "related_by"),
    "LAW": ("regulates", "regulated_by"),
}


def build_knowledge_graph(
    company_name: str,
    entities: list[ExtractedEntity],
) -> tuple[list[GraphNode], list[GraphEdge]]:
    g = nx.DiGraph()

    company_id = company_name.lower().replace(" ", "_")
    g.add_node(company_id, label=company_name, type="Company")

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    for entity in entities:
        entity_id = entity.name.lower().replace(" ", "_")
        g.add_node(entity_id, label=entity.name, type=entity.entity_type)

        fwd_rel, rev_rel = RELATION_MAP.get(entity.entity_type, ("related_to", "related_by"))
        g.add_edge(entity_id, company_id, relation=fwd_rel, weight=1.0)
        g.add_edge(company_id, entity_id, relation=rev_rel, weight=1.0)

    for node_id, data in g.nodes(data=True):
        nodes.append(GraphNode(
            id=node_id,
            label=data.get("label", node_id),
            node_type=data.get("type", "unknown"),
        ))

    for u, v, data in g.edges(data=True):
        edges.append(GraphEdge(
            source=u,
            target=v,
            relation=data.get("relation", "related_to"),
            weight=data.get("weight", 1.0),
        ))

    logger.info(f"build_knowledge_graph: {len(nodes)} nodes, {len(edges)} edges for '{company_name}'")
    return nodes, edges


def analyze_graph_impact(
    company_name: str,
    nodes: list[GraphNode],
    edges: list[GraphEdge],
) -> tuple[float, list[str]]:
    g = nx.DiGraph()
    company_id = company_name.lower().replace(" ", "_")

    for node in nodes:
        g.add_node(node.id, label=node.label, type=node.node_type)
    for edge in edges:
        g.add_edge(edge.source, edge.target, relation=edge.relation, weight=edge.weight)

    messages: list[str] = []

    if company_id not in g:
        return 0.0, ["Company node not found in graph"]

    impact_scores: list[float] = []
    for node in g.nodes():
        if node == company_id:
            continue
        try:
            paths = list(nx.all_simple_paths(g, source=node, target=company_id, cutoff=4))
            if paths:
                avg_weight = sum(
                    g.edges[path[i], path[i+1]].get("weight", 1.0)
                    for path in paths
                    for i in range(len(path) - 1)
                ) / max(len(paths), 1)
                impact = 1.0 / max(len(paths[0]) - 1, 1) * avg_weight
                impact_scores.append(min(impact, 1.0))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue

    composite_risk = max(impact_scores) if impact_scores else 0.0
    total_paths = sum(1 for _ in nx.all_simple_paths(g, source=company_id, target=company_id, cutoff=4)) if company_id in g else 0
    messages.append(f"Identified impact pathways to {company_name}")
    messages.append(f"Composite risk score: {composite_risk:.2f}")

    logger.info(f"analyze_graph_impact: risk={composite_risk:.2f}, paths={total_paths}")
    return composite_risk, messages
