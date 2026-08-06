from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from sqlalchemy import or_, select

from src.agents.state import AgentState
from src.db import session as db_session
from src.db.models import Memory, Task


def _agent_identity(state: AgentState | None) -> tuple[str, str]:
    user_id = (state or {}).get("user_id")
    workspace_id = (state or {}).get("workspace_id")
    if not user_id or not workspace_id:
        raise ValueError("Authenticated user and workspace context are required")
    return user_id, workspace_id


@tool
async def list_my_tasks(
    include_completed: bool = False,
    state: Annotated[AgentState, InjectedState] = None,  # type: ignore[assignment]
) -> str:
    """List the authenticated user's tasks in the active workspace."""
    user_id, workspace_id = _agent_identity(state)
    stmt = select(Task).where(Task.owner_id == user_id, Task.workspace_id == workspace_id)
    if not include_completed:
        stmt = stmt.where(Task.status.not_in({"completed", "dismissed"}))
    stmt = stmt.order_by(Task.due_at.is_(None), Task.due_at.asc(), Task.created_at.desc()).limit(50)
    async with db_session.async_session_maker() as db:
        tasks = list((await db.execute(stmt)).scalars().all())
    if not tasks:
        return "Không có task phù hợp trong workspace hiện tại."
    return "\n".join(
        f"- {task.title} | {task.status} | ưu tiên {task.priority} | hạn {task.due_at.isoformat() if task.due_at else 'chưa đặt'}"
        for task in tasks
    )


@tool
async def search_my_memories(
    query: str = "",
    limit: int = 10,
    state: Annotated[AgentState, InjectedState] = None,  # type: ignore[assignment]
) -> str:
    """Search the authenticated user's private memories in the active workspace."""
    user_id, workspace_id = _agent_identity(state)
    stmt = select(Memory).where(Memory.owner_id == user_id, Memory.workspace_id == workspace_id)
    if query.strip():
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(or_(Memory.title.ilike(pattern), Memory.detail.ilike(pattern), Memory.category.ilike(pattern)))
    stmt = stmt.order_by(Memory.updated_at.desc()).limit(max(1, min(limit, 10)))
    async with db_session.async_session_maker() as db:
        memories = list((await db.execute(stmt)).scalars().all())
    if not memories:
        return "Không tìm thấy memory phù hợp trong workspace hiện tại."
    return "\n".join(
        f"- [{memory.category}] {memory.title}: {memory.detail[:500]}" for memory in memories
    )
