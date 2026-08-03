"""Simulation orchestration service.

Coordinates the full simulation lifecycle on behalf of the backend:
  1. Load the user's portfolio allocation.
  2. Fetch the sector snapshot (cached) — injected into the simulator request.
  3. Call the stateless simulator to create + run the scenario.
  4. Persist the result + market snapshot provenance to `simulation_runs`.

The simulator is a pure compute engine and never reaches back into the backend.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Portfolio, SimulationRun
from app.services.sector_data_service import SectorDataService
from app.services.simulator_client import simulator_client

logger = logging.getLogger(__name__)


class SimulationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.sectors = SectorDataService(db)

    async def _get_portfolio(self, portfolio_id: str, user_id: int) -> Portfolio:
        result = await self.db.execute(
            select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        )
        portfolio = result.scalar_one_or_none()
        if portfolio is None:
            raise LookupError(f"Portfolio {portfolio_id} not found for user {user_id}")
        return portfolio

    async def create_run(
        self, portfolio_id: str, user_id: int, payload: dict[str, Any]
    ) -> SimulationRun:
        portfolio = await self._get_portfolio(portfolio_id, user_id)

        run = SimulationRun(
            portfolio_id=portfolio.id,
            scenario=payload.get("scenario") or {},
            status="queued",
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def execute_run(self, run: SimulationRun) -> SimulationRun:
        """Run the simulation synchronously and persist the result."""
        run.status = "running"
        await self.db.commit()

        try:
            allocation = await self._allocation_for(run.portfolio_id)
            sector_snapshot = await self.sectors.get_snapshot()
            scenario = run.scenario or {}

            created = await simulator_client.create_scenario(
                self._build_scenario_payload(scenario)
            )
            scenario_id = created.get("scenario_id", "")
            if not scenario_id:
                raise RuntimeError("Simulator failed to create scenario")

            run_payload = {
                "scenario_id": scenario_id,
                "portfolio_allocation": allocation,
                "sector_data": sector_snapshot.get("sectors", {}),
            }
            sim_result = await simulator_client.run_simulation(run_payload)
            if not sim_result:
                raise RuntimeError("Simulator failed to run simulation")

            run.result = sim_result
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.market_snapshot_time = datetime.utcnow()
            run.sector_data_version = int(sector_snapshot.get("version", 1))
        except Exception as e:
            logger.exception("Simulation run %s failed", run.id)
            run.status = "failed"
            run.error = str(e)
            run.completed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def get_run(self, run_id: str, user_id: int) -> SimulationRun:
        result = await self.db.execute(
            select(SimulationRun)
            .join(Portfolio, SimulationRun.portfolio_id == Portfolio.id)
            .where(SimulationRun.id == run_id, Portfolio.user_id == user_id)
        )
        run = result.scalar_one_or_none()
        if run is None:
            raise LookupError(f"Simulation run {run_id} not found for user {user_id}")
        return run

    async def get_run_by_id(self, run_id: str) -> SimulationRun | None:
        result = await self.db.execute(select(SimulationRun).where(SimulationRun.id == run_id))
        return result.scalar_one_or_none()

    async def list_runs(self, user_id: int, skip: int = 0, limit: int = 50) -> list[SimulationRun]:
        result = await self.db.execute(
            select(SimulationRun)
            .join(Portfolio, SimulationRun.portfolio_id == Portfolio.id)
            .where(Portfolio.user_id == user_id)
            .order_by(SimulationRun.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    def _build_scenario_payload(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Translate a stored scenario dict into the simulator's CreateScenarioRequest shape."""
        assumptions = scenario.get("assumptions", {}) or {}
        if isinstance(assumptions, dict):
            assumptions = assumptions.get("assumptions", assumptions)
            if isinstance(assumptions, dict):
                assumptions = list(assumptions.values())
        return {
            "title": scenario.get("title", "Simulation"),
            "description": scenario.get("description", ""),
            "events": scenario.get("injected_events", scenario.get("events", [])),
            "assumptions": assumptions or [],
            "duration_days": scenario.get("duration_days", 365),
            "uncertainty": scenario.get(
                "expected_uncertainty", scenario.get("uncertainty", 0.3)
            ),
            "tags": scenario.get("tags", []),
        }

    async def _allocation_for(self, portfolio_id: str) -> dict[str, float]:
        result = await self.db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
        portfolio = result.scalar_one_or_none()
        if portfolio is None:
            return {}
        payload = portfolio.allocation or {}
        if isinstance(payload, dict):
            alloc = payload.get("allocation", payload) if "allocation" in payload else payload
        else:
            alloc = {}
        return alloc if isinstance(alloc, dict) else {}


def get_simulation_service(db: AsyncSession = None) -> SimulationService:
    return SimulationService(db)
