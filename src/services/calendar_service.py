import asyncio
import logging
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config import get_settings
from src.db import session as db_session
from src.db.models import CalendarSyncState
from src.services.workspace_service import list_workspace_user_ids, resolve_workspace_for_user
from src.websocket.manager import manager

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    settings = get_settings()
    creds = Credentials.from_authorized_user_file(settings.google_token_path, _SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(settings.google_token_path, "w") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def list_events(time_min_iso: str, time_max_iso: str, max_results: int = 50) -> list[dict]:
    settings = get_settings()
    service = get_calendar_service()
    resp = (
        service.events()
        .list(
            calendarId=settings.google_calendar_id,
            timeMin=time_min_iso,
            timeMax=time_max_iso,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return resp.get("items", [])


def create_event(
    summary: str, start_iso: str, end_iso: str, description: str = "", attendees: list[str] | None = None
) -> dict:
    settings = get_settings()
    service = get_calendar_service()
    body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_iso, "timeZone": settings.calendar_timezone},
        "end": {"dateTime": end_iso, "timeZone": settings.calendar_timezone},
        "attendees": [{"email": a} for a in (attendees or [])],
    }
    return service.events().insert(calendarId=settings.google_calendar_id, body=body).execute()


def update_event(
    event_id: str,
    summary: str | None = None,
    start_iso: str | None = None,
    end_iso: str | None = None,
    description: str | None = None,
) -> dict:
    """Patch an existing Google Calendar event - only the given fields change."""
    settings = get_settings()
    service = get_calendar_service()
    body: dict = {}
    if summary is not None:
        body["summary"] = summary
    if description is not None:
        body["description"] = description
    if start_iso is not None:
        body["start"] = {"dateTime": start_iso, "timeZone": settings.calendar_timezone}
    if end_iso is not None:
        body["end"] = {"dateTime": end_iso, "timeZone": settings.calendar_timezone}
    return service.events().patch(calendarId=settings.google_calendar_id, eventId=event_id, body=body).execute()


def delete_event(event_id: str) -> None:
    settings = get_settings()
    service = get_calendar_service()
    service.events().delete(calendarId=settings.google_calendar_id, eventId=event_id).execute()


async def authorize_calendar_access(user_id: str, workspace_id: str | None) -> tuple[str, list[str]]:
    """Authorize the explicitly configured workspace integration and return its recipients.

    This application currently supports one service-account/token integration. Failing closed
    avoids accidentally exposing that calendar to every tenant until per-workspace OAuth is
    configured in a future integration layer.
    """
    configured_workspace_id = get_settings().google_calendar_workspace_id.strip()
    if not configured_workspace_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Calendar integration is not configured")
    if not workspace_id or workspace_id != configured_workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Calendar is not enabled for this workspace")
    async with db_session.async_session_maker() as db:
        await resolve_workspace_for_user(db, user_id, workspace_id)
        recipients = await list_workspace_user_ids(db, workspace_id)
    return workspace_id, recipients


async def broadcast_change(workspace_id: str, event_type: str, payload: dict) -> None:
    async with db_session.async_session_maker() as db:
        recipients = await list_workspace_user_ids(db, workspace_id)
    await manager.broadcast_to_users(recipients, {"type": event_type, "workspace_id": workspace_id, **payload})


def to_out_dict(event: dict) -> dict:
    """Shared shape for a Google Calendar event, used by both the REST response (CalendarEventOut)
    and the WebSocket push (REST route + agent tool both need to notify the same way)."""
    start = event.get("start", {})
    end = event.get("end", {})
    return {
        "id": event["id"],
        "title": event.get("summary", "(No title)"),
        "start": start.get("dateTime") or start.get("date"),
        "end": end.get("dateTime") or end.get("date"),
        "url": event.get("htmlLink"),
    }


def _fetch_changes(sync_token: str | None) -> tuple[list[dict], str | None]:
    """One full page-through of events().list(). With no sync_token, this is a bootstrap sync
    (events from the last day onward) that just establishes a fresh nextSyncToken; with one, it's
    an incremental diff - Google returns only what changed since that token, deletions included
    (as items with status="cancelled")."""
    settings = get_settings()
    service = get_calendar_service()
    kwargs: dict = {"calendarId": settings.google_calendar_id, "singleEvents": True}
    if sync_token:
        kwargs["syncToken"] = sync_token
    else:
        kwargs["timeMin"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()

    items: list[dict] = []
    next_sync_token = None
    page_token = None
    while True:
        resp = service.events().list(**kwargs, pageToken=page_token).execute()
        items.extend(resp.get("items", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            next_sync_token = resp.get("nextSyncToken")
            break
    return items, next_sync_token


async def poll_calendar_changes() -> None:
    """Periodic APScheduler job: Google Calendar push notifications need a public HTTPS callback
    URL, which this project doesn't have (local dev only, no deployment yet), so this polls with
    an incremental syncToken instead to catch changes made directly in Google Calendar (outside
    the app) and broadcast them to everyone connected - the same WebSocket events the REST routes
    and agent tools already send, so the frontend needs no changes to pick these up. Never raises:
    a failed poll should not crash the scheduler, just retry next interval."""
    workspace_id = get_settings().google_calendar_workspace_id.strip()
    if not workspace_id:
        return
    async with db_session.async_session_maker() as db:
        state = await db.get(CalendarSyncState, workspace_id)
        sync_token = state.sync_token if state else None

    try:
        items, next_sync_token = await asyncio.to_thread(_fetch_changes, sync_token)
    except HttpError as e:
        if sync_token and e.resp.status == 410:
            # Token expired/invalid (e.g. calendar untouched too long) - Google requires starting
            # over with a full sync rather than resuming.
            logger.warning("Calendar sync token expired, resyncing from scratch")
            try:
                items, next_sync_token = await asyncio.to_thread(_fetch_changes, None)
            except Exception:
                logger.exception("Calendar poll full resync failed")
                return
        else:
            logger.exception("Calendar poll failed")
            return
    except Exception:
        logger.exception("Calendar poll failed")
        return

    for event in items:
        if event.get("status") == "cancelled":
            await broadcast_change(workspace_id, "calendar_event_deleted", {"event_id": event["id"]})
        else:
            await broadcast_change(workspace_id, "calendar_event_updated", {"event": to_out_dict(event)})

    async with db_session.async_session_maker() as db:
        state = await db.get(CalendarSyncState, workspace_id)
        if state is None:
            state = CalendarSyncState(workspace_id=workspace_id)
            db.add(state)
        state.sync_token = next_sync_token
        await db.commit()
