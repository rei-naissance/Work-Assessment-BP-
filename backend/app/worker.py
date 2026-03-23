"""ARQ worker entrypoint.

Run with:
    arq app.worker.WorkerSettings

Or via docker-compose (see the `worker` service).
"""

import logging
import os

from arq.connections import RedisSettings
from arq.cron import cron
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.tasks.generate_binder import generate_binder_job  # noqa: F401 — registered below
from app.tasks.reconcile_payments import reconcile_payments_job  # noqa: F401

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    ctx["mongo"] = AsyncIOMotorClient(settings.mongo_uri)
    ctx["db"] = ctx["mongo"].get_default_database()
    os.makedirs(settings.data_dir, exist_ok=True)
    logger.info("ARQ worker started (mongo=%s, data_dir=%s)", settings.mongo_uri, settings.data_dir)


async def shutdown(ctx: dict) -> None:
    ctx["mongo"].close()
    logger.info("ARQ worker shut down")


class WorkerSettings:
    functions = [generate_binder_job]
    cron_jobs = [
        # Run payment reconciliation every 6 hours
        cron(reconcile_payments_job, hour={0, 6, 12, 18}, minute=15, run_at_startup=False),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    # Allow up to 4 concurrent binder jobs per worker instance
    max_jobs = 4
    # PDF generation + AI calls can take a while; cap at 10 minutes
    job_timeout = 600
