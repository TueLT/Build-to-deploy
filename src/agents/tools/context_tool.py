from datetime import datetime
from typing import Annotated, Literal

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from sqlalchemy import select

from src.agents.state import AgentState
from src.db import session as db_session
from src.db.models import Task, User
from src.models.memory_schemas import MemoryCreateRequest
from src.services import guardrail_service, memory_service, task_visibility_service, timeline_service


def _agent_identity(state: AgentState | None) -> tuple[str, str]:
    user_id = (state or {}).get("user_id")
    workspace_id = (state or {}).get("workspace_id")
    if not user_id or not workspace_id:
        raise ValueError("Authenticated user and workspace context are required")
    return user_id, workspace_id


@tool
async def list_my_tasks(
    include_completed: bool = False,
    scope: Literal["personal", "all_assigned"] = "personal",
    state: Annotated[AgentState, InjectedState] = None,  # type: ignore[assignment]
) -> str:
    """List tasks assigned to the authenticated user.

    Use ``personal`` for private tasks in the active Personal Space. Use
    ``all_assigned`` for the user's own workload shown by My Tasks, including
    still-authorized workspace assignments. This never returns other members'
    tasks or a workspace backlog.
    """
    user_id, workspace_id = _agent_identity(state)
    if scope == "all_assigned":
        stmt = task_visibility_service.visible_assigned_tasks_statement(user_id)
    else:
        stmt = select(Task).where(
            Task.owner_id == user_id,
            Task.workspace_id == workspace_id,
            Task.agent_workspace_id.is_(None),
        )
    if not include_completed:
        stmt = stmt.where(Task.status.not_in({"completed", "dismissed"}))
    stmt = stmt.order_by(Task.due_at.is_(None), Task.due_at.asc(), Task.created_at.desc()).limit(50)
    async with db_session.async_session_maker() as db:
        tasks = list((await db.execute(stmt)).scalars().all())
    if not tasks:
        return "Không có task phù hợp trong phạm vi đã chọn."
    return "\n".join(
        f"- {task.title} | {task.status} | ưu tiên {task.priority} | "
        f"hạn {task.due_at.isoformat() if task.due_at else 'chưa đặt'} | "
        f"phạm vi {'workspace được giao' if task.agent_workspace_id else 'cá nhân'}"
        for task in tasks
    )


@tool
async def search_my_memories(
    query: str = "",
    memory_type: Literal["all", "preference", "relationship", "episodic", "semantic"] = "all",
    limit: int = 10,
    state: Annotated[AgentState, InjectedState] = None,  # type: ignore[assignment]
) -> str:
    """Search the authenticated user's private memories in the active workspace."""
    user_id, workspace_id = _agent_identity(state)
    async with db_session.async_session_maker() as db:
        memories = await memory_service.search_active_memories(
            db,
            owner_id=user_id,
            workspace_id=workspace_id,
            query=query,
            memory_types=None if memory_type == "all" else {memory_type},
            limit=max(1, min(limit, 10)),
        )
    if not memories:
        return "Không tìm thấy memory phù hợp trong workspace hiện tại."
    return "\n".join(
        "- " + guardrail_service.sanitize_untrusted_text(
            f"[{memory.memory_type}/{memory.category}] {memory.title}: {memory.detail[:500]}"
        )
        for memory in memories
    )


@tool
async def save_personal_memory(
    title: str,
    detail: str,
    category: str = "preference",
    state: Annotated[AgentState, InjectedState] = None,  # type: ignore[assignment]
) -> str:
    """Save a durable private preference only when the user explicitly asks Orbit to remember it.

    Appropriate examples include a preferred form of address, response style, communication
    preference, or work habit. Never infer or save secrets or sensitive personal attributes.
    """

    user_id, workspace_id = _agent_identity(state)
    async with db_session.async_session_maker() as db:
        user = await db.get(User, user_id)
        if user is None or not user.is_active:
            raise ValueError("Authenticated user is unavailable")
        memory = await memory_service.upsert_personal_memory(
            db,
            user,
            workspace_id,
            MemoryCreateRequest(
                workspace_id=workspace_id,
                category=category[:40] or "preference",
                title=title[:200],
                detail=detail[:10_000],
                memory_type="preference",
                confidence=1.0,
            ),
        )
    return f"Đã lưu vào Personal Memory: {memory.title} — {memory.detail}"


@tool
async def get_personal_timeline(
    from_iso: str,
    to_iso: str,
    include_messages: bool = False,
    state: Annotated[AgentState, InjectedState] = None,  # type: ignore[assignment]
) -> str:
    """List the authenticated user's tasks, reminders, calendar events and optionally
    consent-authorized messages in chronological order. The range must use ISO 8601 datetimes
    and cannot exceed 90 days."""
    user_id, workspace_id = _agent_identity(state)
    try:
        from_at = datetime.fromisoformat(from_iso.replace("Z", "+00:00"))
        to_at = datetime.fromisoformat(to_iso.replace("Z", "+00:00"))
    except ValueError:
        return "Khoảng thời gian không hợp lệ; hãy dùng ISO 8601."
    async with db_session.async_session_maker() as db:
        user = await db.get(User, user_id)
        if user is None or not user.is_active:
            raise ValueError("Authenticated user is unavailable")
        try:
            timeline = await timeline_service.get_personal_timeline(
                db,
                user=user,
                workspace_id=workspace_id,
                from_at=from_at,
                to_at=to_at,
                include_messages=include_messages,
                conversation_id=(state or {}).get("conversation_id") if include_messages else None,
                include_assigned_tasks=True,
                limit=100,
            )
        except ValueError as exc:
            return str(exc)
    lines = [
        f"- {item.occurred_at.isoformat()} | {item.kind} | {item.title} | {item.status}"
        for item in timeline.items
    ]
    source_notes = [
        f"{source.source}:{source.status}" for source in timeline.sources if source.status != "ok"
    ]
    if source_notes:
        lines.append(f"Nguồn chưa đầy đủ: {', '.join(source_notes)}")
    return "\n".join(lines) if lines else "Không có sự kiện nào trong khoảng thời gian này."
