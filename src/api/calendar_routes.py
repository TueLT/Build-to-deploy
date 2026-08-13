import asyncio
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.db.models import EventCandidate, User
from src.db.session import get_db
from src.models.calendar_schemas import (
    CalendarEventCreateRequest,
    CalendarEventOut,
    CalendarEventUpdateRequest,
    EventBackfillOut,
    EventBackfillRequest,
    EventCandidateOut,
)
from src.services import calendar_service, consent_service, event_extraction_service
from src.services.authorization_service import require_conversation_access

router = APIRouter()


def _to_out(event: dict) -> CalendarEventOut:
    return CalendarEventOut(**calendar_service.to_out_dict(event))


def _candidate_out(candidate: EventCandidate) -> EventCandidateOut:
    return EventCandidateOut.model_validate(candidate, from_attributes=True)


async def _candidate_for_manager(
    db: AsyncSession, candidate_id: str, current_user: User
) -> EventCandidate:
    candidate = await db.get(EventCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event candidate not found")
    await require_conversation_access(db, current_user, candidate.conversation_id, "manager")
    return candidate


@router.get("/calendar/candidates", response_model=list[EventCandidateOut])
async def list_event_candidates(
    conversation_id: str = Query(...),
    include_terminal: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EventCandidateOut]:
    await require_conversation_access(db, current_user, conversation_id, "viewer")
    stmt = select(EventCandidate).where(EventCandidate.conversation_id == conversation_id)
    if not include_terminal:
        stmt = stmt.where(EventCandidate.status == "suggested")
    candidates = list(
        (await db.execute(stmt.order_by(EventCandidate.updated_at.desc()).limit(100))).scalars().all()
    )
    return [_candidate_out(candidate) for candidate in candidates]


@router.post("/calendar/candidates/{candidate_id}/confirm", response_model=EventCandidateOut)
async def confirm_event_candidate(
    candidate_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventCandidateOut:
    candidate = await _candidate_for_manager(db, candidate_id, current_user)
    if candidate.status != "suggested":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Candidate is no longer actionable")
    current_hash = await consent_service.get_consent_scope_hash(db, candidate.conversation_id)
    sources_valid = await consent_service.validate_authorized_source_ids(
        db, candidate.conversation_id, candidate.source_message_ids
    )
    if current_hash != candidate.authorization_scope_hash or not sources_valid:
        candidate.status = "invalidated"
        candidate.invalidated_reason = "group_ai_policy_changed"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="AI policy changed; extract again")

    await calendar_service.authorize_calendar_access(current_user.id, candidate.workspace_id)
    target = await db.get(EventCandidate, candidate.target_candidate_id) if candidate.target_candidate_id else None
    try:
        if candidate.operation == "create":
            if candidate.missing_fields or candidate.start_at is None or candidate.end_at is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Candidate is incomplete: {', '.join(candidate.missing_fields)}",
                )
            created = await asyncio.to_thread(
                calendar_service.create_event,
                candidate.title,
                candidate.start_at.isoformat(),
                candidate.end_at.isoformat(),
                f"Extracted from group conversation {candidate.conversation_id}. Participants mentioned: "
                + ", ".join(candidate.attendees),
                [],
            )
            candidate.calendar_event_id = created.get("id")
            broadcast_type = "calendar_event_created"
            broadcast_payload = {"event": calendar_service.to_out_dict(created)}
        elif candidate.operation == "update":
            if target is None or not target.calendar_event_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Target event is unavailable")
            if candidate.missing_fields or candidate.start_at is None or candidate.end_at is None:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Update is incomplete")
            updated = await asyncio.to_thread(
                calendar_service.update_event,
                target.calendar_event_id,
                candidate.title,
                candidate.start_at.isoformat(),
                candidate.end_at.isoformat(),
                f"Updated from group conversation {candidate.conversation_id}.",
            )
            candidate.calendar_event_id = target.calendar_event_id
            target.title = candidate.title
            target.start_at = candidate.start_at
            target.end_at = candidate.end_at
            target.location = candidate.location
            target.attendees = candidate.attendees
            target.status = "superseded"
            broadcast_type = "calendar_event_updated"
            broadcast_payload = {"event": calendar_service.to_out_dict(updated)}
        else:
            if target is None or not target.calendar_event_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Target event is unavailable")
            await asyncio.to_thread(calendar_service.delete_event, target.calendar_event_id)
            candidate.calendar_event_id = target.calendar_event_id
            target.status = "cancelled"
            broadcast_type = "calendar_event_deleted"
            broadcast_payload = {"event_id": target.calendar_event_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Google Calendar error: {exc}")

    candidate.status = "confirmed"
    await db.commit()
    await db.refresh(candidate)
    await calendar_service.broadcast_change(candidate.workspace_id, broadcast_type, broadcast_payload)
    return _candidate_out(candidate)


@router.post("/calendar/candidates/{candidate_id}/dismiss", response_model=EventCandidateOut)
async def dismiss_event_candidate(
    candidate_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventCandidateOut:
    candidate = await _candidate_for_manager(db, candidate_id, current_user)
    if candidate.status != "suggested":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Candidate is no longer actionable")
    candidate.status = "dismissed"
    await db.commit()
    await db.refresh(candidate)
    return _candidate_out(candidate)


@router.post("/conversations/{conversation_id}/event-backfill", response_model=EventBackfillOut)
async def backfill_event_candidates(
    conversation_id: str,
    request: EventBackfillRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventBackfillOut:
    await require_conversation_access(db, current_user, conversation_id, "manager")
    result = await event_extraction_service.process_event_backfill_batch(
        conversation_id, request.batch_size
    )
    return EventBackfillOut(**result)


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
