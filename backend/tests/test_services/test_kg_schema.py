"""Tests for the KG response Pydantic models."""

from app.schemas.knowledge_graph import KGEntity, KGGraphEdge, KGNewsItem, KGResponse


def test_kg_response_empty():
    kg = KGResponse()
    assert kg.news == []
    assert kg.entities == []
    assert kg.graph_nodes == []
    assert kg.graph_edges == []


def test_kg_response_from_raw():
    raw = {
        "news": [
            {"title": "Test Article", "content": "Content", "source": "CNN", "date": "2026-06-01", "url": "https://cnn.com"}
        ],
        "entities": [{"entity": "Apple", "type": "company"}],
        "graph_nodes": [{"id": "1", "label": "Apple", "type": "company"}],
        "graph_edges": [{"source": "Apple", "target": "US", "relationship": "operates_in"}],
    }
    kg = KGResponse.from_raw(raw)
    assert len(kg.news) == 1
    assert isinstance(kg.news[0], KGNewsItem)
    assert kg.news[0].title == "Test Article"
    assert len(kg.entities) == 1
    assert isinstance(kg.entities[0], KGEntity)
    assert kg.entities[0].entity == "Apple"
    assert len(kg.graph_edges) == 1
    assert isinstance(kg.graph_edges[0], KGGraphEdge)
    assert kg.graph_edges[0].relationship == "operates_in"


def test_kg_response_from_raw_none():
    kg = KGResponse.from_raw(None)
    assert kg.news == []
    assert kg.entities == []


def test_kg_response_from_raw_empty():
    kg = KGResponse.from_raw({})
    assert kg.news == []
    assert kg.entities == []
