"""Tests for sector market-data and simulation orchestration endpoints.

The simulator client is mocked so tests run without a live simulator.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth_service import create_access_token
from app.services.simulator_client import simulator_client


async def _make_user(db_session: AsyncSession, email: str) -> str:
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


async def _make_portfolio(db_session: AsyncSession, token: str, client: AsyncClient) -> str:
    resp = await client.post(
        "/api/v1/portfolios",
        json={"name": "Test", "allocation": {"technology": 0.5, "energy": 0.5}},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _fake_result() -> dict:
    return {
        "run_id": "run-1",
        "simulation_id": "sim-1",
        "status": "completed",
        "summary": {"outlook": "Cautious", "total_paths": 100},
    }


@pytest.mark.asyncio
async def test_sector_snapshot_is_public(client: AsyncClient):
    resp = await client.get("/api/v1/market-data/sectors")
    assert resp.status_code == 200
    assert "sectors" in resp.json()


@pytest.mark.asyncio
async def test_sector_snapshot_returns_sectors(client: AsyncClient, db_session: AsyncSession):
    token = await _make_user(db_session, "sector@test.com")

    async def _fake_create(*args, **kwargs):
        return {"scenario_id": "scen-1", "simulation_id": "sim-1"}

    async def _fake_run(*args, **kwargs):
        return _fake_result()

    original_create = simulator_client.create_scenario
    original_run = simulator_client.run_simulation
    simulator_client.create_scenario = _fake_create
    simulator_client.run_simulation = _fake_run
    try:
        pid = await _make_portfolio(db_session, token, client)
        resp = await client.post(
            "/api/v1/simulations",
            json={"portfolio_id": pid, "scenario": {"title": "Hike"}},
            headers=_auth(token),
        )
    finally:
        simulator_client.create_scenario = original_create
        simulator_client.run_simulation = original_run

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "completed"
    assert data["result"]["run_id"] == "run-1"
    assert data["market_snapshot_time"] is not None
    assert data["sector_data_version"] == 1


@pytest.mark.asyncio
async def test_simulation_requires_auth(client: AsyncClient):
    resp = await client.post(
        "/api/v1/simulations",
        json={"portfolio_id": "some-id", "scenario": {}},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_simulation_unknown_portfolio_404(client: AsyncClient, db_session: AsyncSession):
    token = await _make_user(db_session, "noport@test.com")
    resp = await client.post(
        "/api/v1/simulations",
        json={"portfolio_id": "00000000-0000-0000-0000-000000000000", "scenario": {}},
        headers=_auth(token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_simulation_marks_failed_on_simulator_error(
    client: AsyncClient, db_session: AsyncSession
):
    token = await _make_user(db_session, "fail@test.com")

    async def _fake_create(*args, **kwargs):
        return {}

    original_create = simulator_client.create_scenario
    simulator_client.create_scenario = _fake_create
    try:
        pid = await _make_portfolio(db_session, token, client)
        resp = await client.post(
            "/api/v1/simulations",
            json={"portfolio_id": pid, "scenario": {"title": "X"}},
            headers=_auth(token),
        )
    finally:
        simulator_client.create_scenario = original_create

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "failed"
    assert "failed to create scenario" in data["error"]


@pytest.mark.asyncio
async def test_list_runs_user_scoped(client: AsyncClient, db_session: AsyncSession):
    alice = await _make_user(db_session, "runsalice@test.com")
    bob = await _make_user(db_session, "runsbob@test.com")

    async def _fake_create(*args, **kwargs):
        return {"scenario_id": "scen-1", "simulation_id": "sim-1"}

    async def _fake_run(*args, **kwargs):
        return _fake_result()

    original_create = simulator_client.create_scenario
    original_run = simulator_client.run_simulation
    simulator_client.create_scenario = _fake_create
    simulator_client.run_simulation = _fake_run
    try:
        pid = await _make_portfolio(db_session, alice, client)
        await client.post(
            "/api/v1/simulations",
            json={"portfolio_id": pid, "scenario": {"title": "A"}},
            headers=_auth(alice),
        )
    finally:
        simulator_client.create_scenario = original_create
        simulator_client.run_simulation = original_run

    # Alice sees her run; Bob sees none
    alice_resp = await client.get("/api/v1/simulations", headers=_auth(alice))
    assert alice_resp.status_code == 200
    assert len(alice_resp.json()) == 1

    bob_resp = await client.get("/api/v1/simulations", headers=_auth(bob))
    assert bob_resp.status_code == 200
    assert len(bob_resp.json()) == 0
