from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.db.models import Memory, User
from src.db.session import get_db
from src.models.memory_schemas import MemoryCreateRequest, MemoryOut, MemoryUpdateRequest
from src.services.audit_service import record_audit_event
from src.services.workspace_service import resolve_workspace_for_user

router = APIRouter()


def _to_out(memory: Memory) -> MemoryOut:
    return MemoryOut(
        id=memory.id, category=memory.category, title=memory.title, detail=memory.detail,
        workspace_id=memory.workspace_id, created_at=memory.created_at, updated_at=memory.updated_at,
    )


async def _get_own_memory_or_404(memory_id: str, current_user: User, db: AsyncSession) -> Memory:
    memory = (
        await db.execute(select(Memory).where(Memory.id == memory_id, Memory.owner_id == current_user.id))
    ).scalar_one_or_none()
    if memory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    await resolve_workspace_for_user(db, current_user.id, memory.workspace_id)
    return memory


@router.get("/memories", response_model=list[MemoryOut])
async def list_memories(
    workspace_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[MemoryOut]:
    workspace = await resolve_workspace_for_user(db, current_user.id, workspace_id)
    memories = (
        await db.execute(
            select(Memory)
            .where(Memory.owner_id == current_user.id, Memory.workspace_id == workspace.id)
            .order_by(Memory.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).scalars().all()
    return [_to_out(m) for m in memories]


@router.post("/memories", response_model=MemoryOut, status_code=status.HTTP_201_CREATED)
async def create_memory(
    request: MemoryCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemoryOut:
    workspace = await resolve_workspace_for_user(db, current_user.id, request.workspace_id)
    memory = Memory(
        workspace_id=workspace.id,
        owner_id=current_user.id,
        category=request.category,
        title=request.title,
        detail=request.detail,
    )
    db.add(memory)
    await db.flush()
    await record_audit_event(
        db,
        actor=current_user,
        action="memory.created",
        target_type="memory",
        target_id=memory.id,
        workspace_id=workspace.id,
        metadata={"category": memory.category},
    )
    await db.commit()
    await db.refresh(memory)
    return _to_out(memory)


@router.patch("/memories/{memory_id}", response_model=MemoryOut)
async def update_memory(
    memory_id: str,
    request: MemoryUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemoryOut:
    memory = await _get_own_memory_or_404(memory_id, current_user, db)
    changes = request.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(memory, field, value)
    await record_audit_event(
        db,
        actor=current_user,
        action="memory.updated",
        target_type="memory",
        target_id=memory.id,
        workspace_id=memory.workspace_id,
        metadata={"fields": sorted(changes)},
    )
    await db.commit()
    await db.refresh(memory)
    return _to_out(memory)


@router.delete("/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    memory = await _get_own_memory_or_404(memory_id, current_user, db)
    await record_audit_event(
        db,
        actor=current_user,
        action="memory.deleted",
        target_type="memory",
        target_id=memory.id,
        workspace_id=memory.workspace_id,
        metadata={"category": memory.category},
    )
    await db.delete(memory)
    await db.commit()
