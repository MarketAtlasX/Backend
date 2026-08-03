"""Celery tasks for running simulations asynchronously.

The FastAPI route currently executes simulations inline, but this task is the
mechanism to switch to fully async simulation later (queue -> worker -> save ->
WebSocket notify) without any API contract change.
"""

import logging

from app.workers import _run_async
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_simulation_task(self, run_id: str) -> dict:
    """Execute a persisted SimulationRun via the simulator and store the result."""
    from app.database import AsyncSessionLocal
    from app.services.simulation_service import SimulationService

    async def _run():
        async with AsyncSessionLocal() as db:
            service = SimulationService(db)
            run = await service.get_run_by_id(run_id)
            if run is None:
                return {"run_id": run_id, "status": "not_found"}
            run = await service.execute_run(run)
            return {"run_id": run.id, "status": run.status, "error": run.error}

    try:
        return _run_async(_run())
    except Exception as e:
        logger.exception("Simulation task failed for run %s", run_id)
        raise self.retry(exc=e)
