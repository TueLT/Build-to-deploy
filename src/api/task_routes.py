import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.config import get_settings
from src.db.models import Conversation, Task, User
from src.db.session import get_db
from src.models.task_schemas import TaskCreateRequest, TaskOut, UpdateTaskStatusRequest
from src.services import calendar_service, reminder_service
from src.services.authorization_service import require_conversation_access
from src.services.workspace_service import resolve_workspace_for_user
from src.websocket.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()

_PRIORITY_RANK = {"High": 0, "Medium": 1, "Low": 2}

def _to_out(task: Task, *, due_at_override=None) -> TaskOut:
    due_at = due_at_override if due_at_override is not None else task.due_at
    if due_at is not None and due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=ZoneInfo(get_settings().calendar_timezone))
    return TaskOut(
        id=task.id,
        workspace_id=task.workspace_id,
        conversation_id=task.conversation_id,
        title=task.title,
        due_at=due_at,
        priority=task.priority,
        status=task.status,
        source=task.source,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


async def _get_own_task_or_404(task_id: str, current_user: User, db: AsyncSession) -> Task:
    task = (
        await db.execute(select(Task).where(Task.id == task_id, Task.owner_id == current_user.id))
    ).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    await resolve_workspace_for_user(db, current_user.id, task.workspace_id)
    return task


@router.get("/tasks", response_model=list[TaskOut])
async def list_tasks(
    workspace_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[TaskOut]:
    workspace = await resolve_workspace_for_user(db, current_user.id, workspace_id)
    tasks = (
        await db.execute(
            select(Task)
            .where(Task.owner_id == current_user.id, Task.workspace_id == workspace.id)
            .order_by(
                Task.due_at.is_(None),
                Task.due_at.asc(),
                case((Task.priority == "High", 0), (Task.priority == "Medium", 1), else_=2),
                Task.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
    ).scalars().all()
    return [_to_out(t) for t in tasks]


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: TaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskOut:
    workspace = await resolve_workspace_for_user(db, current_user.id, request.workspace_id)
    if request.conversation_id is not None:
        await require_conversation_access(db, current_user, request.conversation_id, "viewer")
        conversation = await db.get(Conversation, request.conversation_id)
        if conversation is None or conversation.workspace_id != workspace.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="conversation_id does not belong to the selected workspace",
            )
    due_at = request.due_at
    if due_at is not None and due_at.tzinfo is None:
        # Same ambiguity reminder_service/proactive_service already guard against: a naive due_at
        # (no UTC offset - e.g. AIPanel's "Extract tasks" posting the LLM's raw due_at straight
        # here) would otherwise let Postgres/asyncpg interpret it using the DB server's own session
        # timezone, which only happens to match calendar_timezone by coincidence on a given machine
        # (verified: local Postgres here defaults to Asia/Bangkok, not something this app controls) -
        # explicit is correct everywhere, not just on this machine.
        due_at = due_at.replace(tzinfo=ZoneInfo(get_settings().calendar_timezone))
    task = Task(
        workspace_id=workspace.id,
        owner_id=current_user.id,
        conversation_id=request.conversation_id,
        title=request.title,
        due_at=due_at,
        priority=request.priority,
        status="pending" if request.source == "manual" else "suggested",
        source=request.source,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    out = _to_out(task, due_at_override=due_at)
    await manager.broadcast_to_users([current_user.id], {"type": "task_created", "task": out.model_dump(mode="json")})
    return out


async def _add_to_calendar_and_reminder(task: Task, owner_id: str) -> None:
    """A proactively-detected task with a due date, once explicitly Accepted, also gets a real
    Google Calendar event and a real Reminder - the Accept click is the human confirmation, so
    neither needs its own interrupt() step. Best-effort: the task itself must stay accepted even
    if Calendar/Reminder creation fails."""
    start_iso = task.due_at.isoformat()
    end_iso = (task.due_at + timedelta(minutes=30)).isoformat()
    try:
        event = calendar_service.create_event(summary=task.title, start_iso=start_iso, end_iso=end_iso)
        await calendar_service.broadcast_change(
            "calendar_event_created", {"event": calendar_service.to_out_dict(event)}
        )
    except Exception:  # noqa: BLE001 - best-effort, must not block the task Accept
        logger.exception("Auto-create calendar event for accepted task %s failed", task.id)

    try:
        await reminder_service.schedule_reminder(
            workspace_id=task.workspace_id,
            owner_id=owner_id,
            title=task.title,
            due_at_iso=start_iso,
            lead_minutes=30,
            source="proactive",
        )
    except Exception:  # noqa: BLE001 - best-effort, must not block the task Accept
        logger.exception("Auto-create reminder for accepted task %s failed", task.id)


@router.patch("/tasks/{task_id}/status", response_model=TaskOut)
async def update_task_status(
    task_id: str,
    request: UpdateTaskStatusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskOut:
    task = await _get_own_task_or_404(task_id, current_user, db)
    is_accepting_proactive_schedule = (
        task.status == "suggested"
        and request.status == "pending"
        and task.source == "proactive"
        and task.due_at is not None
    )
    task.status = request.status
    await db.commit()
    await db.refresh(task)
    out = _to_out(task)
    await manager.broadcast_to_users([current_user.id], {"type": "task_updated", "task": out.model_dump(mode="json")})

    if is_accepting_proactive_schedule:
        await _add_to_calendar_and_reminder(task, current_user.id)

    return out


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    task = await _get_own_task_or_404(task_id, current_user, db)
    await db.delete(task)
    await db.commit()
    await manager.broadcast_to_users([current_user.id], {"type": "task_deleted", "task_id": task_id})
