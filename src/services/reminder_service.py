import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from src.db import session as db_session
from src.db.models import Reminder
from src.services.scheduler import scheduler
from src.websocket.manager import manager

logger = logging.getLogger(__name__)


async def schedule_reminder(
    *,
    owner_id: str | None,
    title: str,
    due_at_iso: str,
    lead_minutes: int = 30,
    message: str = "",
    source: str = "manual",
) -> Reminder:
    due_at = datetime.fromisoformat(due_at_iso)
    fire_at = due_at - timedelta(minutes=lead_minutes)

    async with db_session.async_session_maker() as db:
        reminder = Reminder(
            owner_id=owner_id, title=title, message=message, due_at=due_at, fire_at=fire_at, source=source
        )
        db.add(reminder)
        await db.commit()
        await db.refresh(reminder)

    scheduler.add_job(_fire_reminder_job, "date", run_date=fire_at, args=[reminder.id], id=reminder.id)
    return reminder


async def _fire_reminder_job(reminder_id: str) -> None:
    """APScheduler job callback executed when a reminder's lead time elapses."""
    async with db_session.async_session_maker() as db:
        reminder = await db.get(Reminder, reminder_id)
        if reminder is None or reminder.status != "scheduled":
            return
        reminder.status = "fired"
        await db.commit()
        owner_id, title, message = reminder.owner_id, reminder.title, reminder.message

    logger.info("Reminder fired: %s (%s)", title, reminder_id)
    if owner_id:
        await manager.broadcast_to_users(
            [owner_id],
            {"type": "reminder_fired", "reminder": {"id": reminder_id, "title": title, "message": message}},
        )


async def list_reminders(owner_id: str | None) -> list[Reminder]:
    async with db_session.async_session_maker() as db:
        result = await db.execute(
            select(Reminder).where(Reminder.owner_id == owner_id).order_by(Reminder.fire_at)
        )
        return list(result.scalars().all())


async def cancel_reminder(reminder_id: str, owner_id: str) -> bool:
    async with db_session.async_session_maker() as db:
        reminder = (
            await db.execute(
                select(Reminder).where(Reminder.id == reminder_id, Reminder.owner_id == owner_id)
            )
        ).scalar_one_or_none()
        if reminder is None:
            return False
        if reminder.status == "scheduled":
            try:
                scheduler.remove_job(reminder_id)
            except Exception:  # noqa: BLE001 - job may already have fired/been removed
                pass
        reminder.status = "cancelled"
        await db.commit()
    return True
