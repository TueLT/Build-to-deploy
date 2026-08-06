import asyncio
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.auth.dependencies import get_current_user
from src.db.models import User
from src.models.calendar_schemas import CalendarEventCreateRequest, CalendarEventOut, CalendarEventUpdateRequest
from src.services import calendar_service

router = APIRouter()


def _to_out(event: dict) -> CalendarEventOut:
    return CalendarEventOut(**calendar_service.to_out_dict(event))


@router.get("/calendar/events", response_model=list[CalendarEventOut])
async def list_events(
    workspace_id: str = Query(...),
    time_min: str | None = Query(default=None),
    time_max: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
) -> list[CalendarEventOut]:
    await calendar_service.authorize_calendar_access(current_user.id, workspace_id)
    now = datetime.now(UTC)
    time_min = time_min or now.isoformat()
    time_max = time_max or (now + timedelta(days=60)).isoformat()
    try:
        items = await asyncio.to_thread(calendar_service.list_events, time_min, time_max, 100)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Google Calendar error: {e}")
    return [_to_out(e) for e in items]


@router.post("/calendar/events", response_model=CalendarEventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
    request: CalendarEventCreateRequest,
    current_user: User = Depends(get_current_user),
) -> CalendarEventOut:
    workspace_id, _ = await calendar_service.authorize_calendar_access(current_user.id, request.workspace_id)
    try:
        created = await asyncio.to_thread(
            calendar_service.create_event,
            request.summary,
            request.start_iso.isoformat(),
            request.end_iso.isoformat(),
            request.description,
            [str(attendee) for attendee in (request.attendees or [])],
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Google Calendar error: {e}")
    out = _to_out(created)
    await calendar_service.broadcast_change(workspace_id, "calendar_event_created", {"event": out.model_dump()})
    return out


@router.patch("/calendar/events/{event_id}", response_model=CalendarEventOut)
async def update_event(
    event_id: str,
    request: CalendarEventUpdateRequest,
    workspace_id: str = Query(...),
    current_user: User = Depends(get_current_user),
) -> CalendarEventOut:
    workspace_id, _ = await calendar_service.authorize_calendar_access(current_user.id, workspace_id)
    try:
        updated = await asyncio.to_thread(
            calendar_service.update_event,
            event_id,
            request.summary,
            request.start_iso.isoformat() if request.start_iso else None,
            request.end_iso.isoformat() if request.end_iso else None,
            request.description,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Google Calendar error: {e}")
    out = _to_out(updated)
    await calendar_service.broadcast_change(workspace_id, "calendar_event_updated", {"event": out.model_dump()})
    return out


@router.delete("/calendar/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    workspace_id: str = Query(...),
    current_user: User = Depends(get_current_user),
) -> None:
    workspace_id, _ = await calendar_service.authorize_calendar_access(current_user.id, workspace_id)
    try:
        await asyncio.to_thread(calendar_service.delete_event, event_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Google Calendar error: {e}")
    await calendar_service.broadcast_change(workspace_id, "calendar_event_deleted", {"event_id": event_id})
