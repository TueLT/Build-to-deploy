from pathlib import Path

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import get_settings

settings = get_settings()

if settings.database_url.startswith("sqlite:///"):
    db_path = settings.database_url.removeprefix("sqlite:///")
    if db_path not in (":memory:", ""):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

# SQLAlchemyJobStore persists scheduled jobs (e.g. reminders) so they survive a server restart -
# without it, a job's row in the DB could say "scheduled" while the actual APScheduler job that
# would fire it is gone, and it would just never fire.
scheduler = AsyncIOScheduler(jobstores={"default": SQLAlchemyJobStore(url=settings.database_url)})
