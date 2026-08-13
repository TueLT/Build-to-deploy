import logging
from datetime import UTC, datetime, timedelta

from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from starlette.concurrency import run_in_threadpool

from src.config import get_settings
from src.services import google_credentials
from src.websocket.manager import manager

logger = logging.getLogger(__name__)
_PRIMARY = "primary"


def get_calendar_service():
    """Legacy test seam retained while runtime credentials are now resolved per user."""
    raise RuntimeError("A user-specific Google Calendar service is required")


_DEFAULT_SERVICE_FACTORY = get_calendar_service


async def _service(user_id: str) -> Resource:
    if get_calendar_service is not _DEFAULT_SERVICE_FACTORY:
        return get_calendar_service()
    credentials = await google_credentials.get_credentials(user_id)
    return await run_in_threadpool(build, "calendar", "v3", credentials=credentials)


async def authorize_calendar_access(user_id: str, workspace_id: str | None = None) -> tuple[str, list[str]]:
    """Compatibility seam; access is now established by the user's encrypted OAuth credential."""
    await google_credentials.get_credentials(user_id)
    return workspace_id or "", [user_id]


async def list_events(user_id: str, time_min_iso: str, time_max_iso: str, max_results: int = 50) -> list[dict]:
    service = await _service(user_id)

    def call():
        return (
            service.events()
            .list(
                calendarId=_PRIMARY,
                timeMin=time_min_iso,
                timeMax=time_max_iso,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

    return (await run_in_threadpool(call)).get("items", [])


async def create_event(
    user_id: str,
    summary: str,
    start_iso: str,
    end_iso: str,
    description: str = "",
    attendees: list[str] | None = None,
    timezone: str | None = None,
) -> dict:
    service = await _service(user_id)
    tz = timezone or get_settings().calendar_timezone
    body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_iso, "timeZone": tz},
        "end": {"dateTime": end_iso, "timeZone": tz},
        "attendees": [{"email": value} for value in (attendees or [])],
    }
    return await run_in_threadpool(lambda: service.events().insert(calendarId=_PRIMARY, body=body).execute())


async def update_event(
    user_id: str,
    event_id: str,
    summary: str | None = None,
    start_iso: str | None = None,
    end_iso: str | None = None,
    description: str | None = None,
    timezone: str | None = None,
) -> dict:
    service = await _service(user_id)
    tz = timezone or get_settings().calendar_timezone
    body: dict = {}
    if summary is not None:
        body["summary"] = summary
    if description is not None:
        body["description"] = description
    if start_iso is not None:
        body["start"] = {"dateTime": start_iso, "timeZone": tz}
    if end_iso is not None:
        body["end"] = {"dateTime": end_iso, "timeZone": tz}
    return await run_in_threadpool(
        lambda: service.events().patch(calendarId=_PRIMARY, eventId=event_id, body=body).execute()
    )


async def delete_event(user_id: str, event_id: str) -> None:
    service = await _service(user_id)
    await run_in_threadpool(lambda: service.events().delete(calendarId=_PRIMARY, eventId=event_id).execute())


async def broadcast_change(user_id: str, event_type: str, payload: dict) -> None:
    await manager.broadcast_to_users([user_id], {"type": event_type, **payload})


def to_out_dict(event: dict) -> dict:
    start = event.get("start", {})
    end = event.get("end", {})
    return {
        "id": event["id"],
        "title": event.get("summary", "(No title)"),
        "start": start.get("dateTime") or start.get("date"),
        "end": end.get("dateTime") or end.get("date"),
        "url": event.get("htmlLink"),
    }


async def _fetch_changes(user_id: str, sync_token: str | None) -> tuple[list[dict], str | None]:
    service = await _service(user_id)
    kwargs: dict = {"calendarId": _PRIMARY, "singleEvents": True}
    if sync_token:
        kwargs["syncToken"] = sync_token
    else:
        kwargs["timeMin"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    items: list[dict] = []
    page_token = None
    next_sync_token = None
    while True:
        response = await run_in_threadpool(lambda: service.events().list(**kwargs, pageToken=page_token).execute())
        items.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            next_sync_token = response.get("nextSyncToken")
            break
    return items, next_sync_token


async def _poll_one_user(user_id: str) -> None:
    sync_token = await google_credentials.get_sync_token(user_id)
    try:
        items, next_sync_token = await _fetch_changes(user_id, sync_token)
    except google_credentials.CalendarNotConnectedError:
        return
    except HttpError as exc:
        if sync_token and exc.resp.status == 410:
            try:
                items, next_sync_token = await _fetch_changes(user_id, None)
            except Exception:  # noqa: BLE001 - one poll must not stop the scheduler
                logger.exception("Calendar full resync failed for user %s", user_id)
                return
        else:
            logger.exception("Calendar poll failed for user %s", user_id)
            return
    except Exception:  # noqa: BLE001 - one poll must not stop the scheduler
        logger.exception("Calendar poll failed for user %s", user_id)
        return

    for event in items:
        if event.get("status") == "cancelled":
            await broadcast_change(user_id, "calendar_event_deleted", {"event_id": event["id"]})
        else:
            await broadcast_change(user_id, "calendar_event_updated", {"event": to_out_dict(event)})
    await google_credentials.set_sync_token(user_id, next_sync_token)


async def poll_calendar_changes() -> None:
    connected = set(await google_credentials.list_connected_user_ids())
    for user_id in [value for value in list(manager.active) if value in connected]:
        try:
            await _poll_one_user(user_id)
        except Exception:  # noqa: BLE001 - isolate users within a polling tick
            logger.exception("Calendar poll failed for user %s", user_id)
