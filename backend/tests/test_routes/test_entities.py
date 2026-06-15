"""Tests for entity CRUD endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_entity(client: AsyncClient):
    payload = {
        "name": "Test Corp",
        "entity_type": "company",
        "country_code": "US",
        "ticker_symbols": "TSTC",
    }
    response = await client.post("/entities", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["entity_type"] == "company"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_duplicate_entity_returns_409(client: AsyncClient, sample_entity: dict):
    payload = {
        "name": sample_entity["name"],
        "entity_type": "company",
    }
    response = await client.post("/entities", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_entity_by_id(client: AsyncClient, sample_entity: dict):
    response = await client.get(f"/entities/{sample_entity['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == sample_entity["name"]


@pytest.mark.asyncio
async def test_get_entity_not_found(client: AsyncClient):
    response = await client.get("/entities/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_entities(client: AsyncClient, sample_entity: dict):
    response = await client.get("/entities")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_filter_entities_by_type(client: AsyncClient, sample_entity: dict):
    response = await client.get("/entities/filter/type/company")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_search_entity_by_ticker(client: AsyncClient, sample_entity: dict):
    response = await client.get("/entities/search/ticker/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == sample_entity["name"]
