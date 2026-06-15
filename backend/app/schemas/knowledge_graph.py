"""Pydantic models for knowledge graph agent responses.

The KG agent (knowledge-graph-agent repo, port 8005) returns raw JSON with
news, entities, graph_nodes, and graph_edges. These models provide type safety
and validation for that response, replacing the previous ad-hoc dict access.
"""

from pydantic import BaseModel, Field


class KGNewsItem(BaseModel):
    title: str = ""
    content: str = ""
    source: str = ""
    date: str = ""
    url: str = ""


class KGEntity(BaseModel):
    entity: str = ""
    type: str = ""


class KGGraphNode(BaseModel):
    id: str = ""
    label: str = ""
    type: str = ""


class KGGraphEdge(BaseModel):
    source: str = ""
    target: str = ""
    relationship: str = ""


class KGResponse(BaseModel):
    """Validated response from the knowledge-graph-agent service."""

    news: list[KGNewsItem] = Field(default_factory=list)
    entities: list[KGEntity] = Field(default_factory=list)
    graph_nodes: list[KGGraphNode] = Field(default_factory=list)
    graph_edges: list[KGGraphEdge] = Field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: dict | None) -> "KGResponse":
        """Construct from the raw dict returned by the KG agent HTTP call.

        Gracefully handles None (service unavailable) and missing keys.
        """
        if raw is None:
            return cls()
        return cls(
            news=[KGNewsItem(**a) for a in (raw.get("news") or [])],
            entities=[KGEntity(**e) for e in (raw.get("entities") or [])],
            graph_nodes=[KGGraphNode(**n) for n in (raw.get("graph_nodes") or [])],
            graph_edges=[KGGraphEdge(**e) for e in (raw.get("graph_edges") or [])],
        )
