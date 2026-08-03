"""Tests for portfolio CRUD endpoints (auth-guarded, user-isolated)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth_service import create_access_token


async def _make_user(db_session: AsyncSession, email: str) -> str:
    """Create a user directly in the DB and return a JWT for them."""
    user = User(
        email=email,
        hashed_password="unused-in-tests",
        display_name=email.split("@")[0],
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return create_access_token(user.id)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _portfolio_payload(name: str = "Balanced") -> dict:
    return {
        "name": name,
        "allocation": {"technology": 0.2, "energy": 0.1, "healthcare": 0.15},
    }


@pytest.mark.asyncio
async def test_create_portfolio_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/portfolios", json=_portfolio_payload())
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_and_get_portfolio(client: AsyncClient, db_session: AsyncSession):
    token = await _make_user(db_session, "alice@test.com")
    resp = await client.post("/api/v1/portfolios", json=_portfolio_payload(), headers=_auth(token))
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Balanced"
    assert data["allocation"]["version"] == 1
    assert data["allocation"]["allocation"]["technology"] == 0.2

    get_resp = await client.get(f"/api/v1/portfolios/{data['id']}", headers=_auth(token))
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == data["id"]


@pytest.mark.asyncio
async def test_list_portfolios_scoped_to_user(client: AsyncClient, db_session: AsyncSession):
    token = await _make_user(db_session, "bob@test.com")
    await client.post("/api/v1/portfolios", json=_portfolio_payload("A"), headers=_auth(token))
    await client.post("/api/v1/portfolios", json=_portfolio_payload("B"), headers=_auth(token))
    resp = await client.get("/api/v1/portfolios", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_user_isolation(client: AsyncClient, db_session: AsyncSession):
    alice = await _make_user(db_session, "carol@test.com")
    bob = await _make_user(db_session, "dave@test.com")

    created = await client.post(
        "/api/v1/portfolios", json=_portfolio_payload(), headers=_auth(alice)
    )
    pid = created.json()["id"]

    # Bob cannot read Alice's portfolio
    resp = await client.get(f"/api/v1/portfolios/{pid}", headers=_auth(bob))
    assert resp.status_code == 404

    # Bob cannot delete Alice's portfolio
    resp = await client.delete(f"/api/v1/portfolios/{pid}", headers=_auth(bob))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_portfolio(client: AsyncClient, db_session: AsyncSession):
    token = await _make_user(db_session, "erin@test.com")
    created = await client.post(
        "/api/v1/portfolios", json=_portfolio_payload(), headers=_auth(token)
    )
    pid = created.json()["id"]

    resp = await client.patch(
        f"/api/v1/portfolios/{pid}",
        json={"allocation": {"bonds": 0.4, "cash": 0.1}},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["allocation"]["allocation"]["bonds"] == 0.4


@pytest.mark.asyncio
async def test_delete_portfolio(client: AsyncClient, db_session: AsyncSession):
    token = await _make_user(db_session, "frank@test.com")
    created = await client.post(
        "/api/v1/portfolios", json=_portfolio_payload(), headers=_auth(token)
    )
    pid = created.json()["id"]

    resp = await client.delete(f"/api/v1/portfolios/{pid}", headers=_auth(token))
    assert resp.status_code == 204

    get_resp = await client.get(f"/api/v1/portfolios/{pid}", headers=_auth(token))
    assert get_resp.status_code == 404
