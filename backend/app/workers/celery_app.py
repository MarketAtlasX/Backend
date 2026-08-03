"""Celery application configuration for MarketAtlas.

Usage:
    # Start a worker (from project root):
    celery -A app.workers.celery_app worker --loglevel=info

    # Start the beat scheduler (separate terminal):
    celery -A app.workers.celery_app beat --loglevel=info

    # Call a task manually:
    from app.workers.analysis_tasks import analyze_event_task
    analyze_event_task.delay(event_id=42, entity_ids=[1, 2, 3])
"""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "marketatlas",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.analysis_tasks",
        "app.workers.market_data_tasks",
        "app.workers.geo_event_tasks",
        "app.workers.simulation_tasks",
    ],
)

celery_app.conf.beat_schedule = {
    "fetch-market-data-hourly": {
        "task": "app.workers.market_data_tasks.fetch_all_market_data_task",
        "schedule": crontab(minute=0),
        "kwargs": {"period": "1d", "interval": "5m"},
    },
    "fetch-market-data-daily-close": {
        "task": "app.workers.market_data_tasks.fetch_all_market_data_task",
        "schedule": crontab(hour=22, minute=0),
        "kwargs": {"period": "5d", "interval": "1d"},
    },
    "fetch-geo-events": {
        "task": "app.workers.geo_event_tasks.fetch_all_geo_events",
        "schedule": crontab(minute="*/15"),
        "kwargs": {},
    },
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)
