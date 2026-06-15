"""Tests for event CRUD endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_event(client: AsyncClient):
    payload = {
        "title": "Test event",
        "description": "A test event for unit testing",
        "event_type": "other",
        "severity": "low",
        "event_date": "2026-06-01T00:00:00Z",
    }
    response = await client.post("/events", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["event_type"] == "other"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_event_not_found(client: AsyncClient):
    response = await client.get("/events/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_events_empty(client: AsyncClient):
    response = await client.get("/events")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_events_paginated(client: AsyncClient, sample_event: dict):
    response = await client.get("/events?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_filter_events_by_type(client: AsyncClient, sample_event: dict):
    response = await client.get("/events/filter/type/sanction")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_link_entity_to_event(client: AsyncClient, sample_event: dict, sample_entity: dict):
    response = await client.post(
        f"/events/{sample_event['id']}/entities/{sample_entity['id']}"
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_link_entity_twice_returns_409(
    client: AsyncClient, linked_event_entity: dict
):
    response = await client.post(
        f"/events/{linked_event_entity['event_id']}/entities/{linked_event_entity['entity_id']}"
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_unlink_entity(client: AsyncClient, linked_event_entity: dict):
    response = await client.delete(
        f"/events/{linked_event_entity['event_id']}/entities/{linked_event_entity['entity_id']}"
    )
    assert response.status_code == 204
