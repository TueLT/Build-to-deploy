from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.dependencies import require_admin
from src.config import get_settings
from src.db.models import AIPermission, Conversation, ConversationParticipant, Memory, Message, Reminder, Task, User
from src.db.session import get_db
from src.models.admin_schemas import (
    AdminConversationOut,
    AdminMemoryOut,
    AdminMessageOut,
    AdminReminderOut,
    AdminStats,
    AdminTaskOut,
    AdminUserOut,
    UpdateRoleRequest,
    UpdateStatusRequest,
)
from src.services import reminder_service, usage_service
from src.services.audit_service import record_audit_event
from src.services.authorization_service import require_support_scope

router = APIRouter(dependencies=[Depends(require_admin)])


async def _get_user_or_404(user_id: str, db: AsyncSession) -> User:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _conversation_label(conversation: Conversation | None) -> str | None:
    if conversation is None:
        return None
    return conversation.name or ("Direct message" if conversation.type == "direct" else "Group chat")


@router.get("/stats", response_model=AdminStats)
async def get_stats(db: AsyncSession = Depends(get_db)) -> AdminStats:
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total_conversations = (await db.execute(select(func.count()).select_from(Conversation))).scalar_one()
    total_messages = (await db.execute(select(func.count()).select_from(Message))).scalar_one()
    since = datetime.now(UTC) - timedelta(days=7)
    new_users = (
        await db.execute(select(func.count()).select_from(User).where(User.created_at >= since))
    ).scalar_one()

    budget = get_settings().daily_token_budget
    usage = await usage_service.get_usage_today()
    budget_used_pct = round(usage["total_tokens"] / budget * 100, 1) if budget else 0.0
    return AdminStats(
        total_users=total_users,
        total_conversations=total_conversations,
        total_messages=total_messages,
        new_users_last_7_days=new_users,
        tokens_used_today=usage["total_tokens"],
        requests_today=usage["request_count"],
        daily_token_budget=budget,
        budget_used_pct=budget_used_pct,
    )


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    q: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[AdminUserOut]:
    stmt = select(User).order_by(User.created_at.desc())
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where((User.email.ilike(pattern)) | (User.display_name.ilike(pattern)))
    users = (await db.execute(stmt.offset(offset).limit(limit))).scalars().all()
    return [AdminUserOut.model_validate(u, from_attributes=True) for u in users]


@router.patch("/users/{user_id}/role", response_model=AdminUserOut)
async def update_user_role(
    user_id: str,
    request: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AdminUserOut:
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own role")
    user = await _get_user_or_404(user_id, db)
    user.role = request.role
    user.platform_role = "platform_admin" if request.role == "admin" else "user"
    await record_audit_event(
        db,
        actor=current_user,
        action="platform.user_role_changed",
        target_type="user",
        target_id=user.id,
        workspace_id=None,
        metadata={"role": user.role, "platform_role": user.platform_role},
    )
    await db.commit()
    await db.refresh(user)
    return AdminUserOut.model_validate(user, from_attributes=True)


@router.patch("/users/{user_id}/status", response_model=AdminUserOut)
async def update_user_status(
    user_id: str,
    request: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AdminUserOut:
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own status")
    user = await _get_user_or_404(user_id, db)
    user.is_active = request.is_active
    await record_audit_event(
        db,
        actor=current_user,
        action="platform.user_status_changed",
        target_type="user",
        target_id=user.id,
        workspace_id=None,
        metadata={"is_active": user.is_active},
    )
    await db.commit()
    await db.refresh(user)
    return AdminUserOut.model_validate(user, from_attributes=True)


@router.get("/conversations", response_model=list[AdminConversationOut])
async def list_all_conversations(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[AdminConversationOut]:
    participant_count = (
        select(func.count(ConversationParticipant.id))
        .where(ConversationParticipant.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )
    message_count = (
        select(func.count(Message.id))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )
    rows = (
        await db.execute(
            select(Conversation, participant_count, message_count)
            .order_by(Conversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return [
        AdminConversationOut(
            id=conversation.id,
            type=conversation.type,
            name=conversation.name,
            created_by=conversation.created_by,
            created_at=conversation.created_at,
            participant_count=participants,
            message_count=messages,
        )
        for conversation, participants, messages in rows
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=list[AdminMessageOut])
async def get_conversation_messages_admin(
    conversation_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[AdminMessageOut]:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    rows = (
        await db.execute(
            select(Message, User)
            .join(User, User.id == Message.sender_id)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return [
        AdminMessageOut(
            id=message.id,
            sender_id=message.sender_id,
            sender_display_name=sender.display_name,
            content=message.content,
            created_at=message.created_at,
        )
        for message, sender in rows
    ]


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation_admin(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    await record_audit_event(
        db,
        actor=current_user,
        action="platform.conversation_deleted",
        target_type="conversation",
        target_id=conversation.id,
        workspace_id=conversation.workspace_id,
        metadata={"conversation_type": conversation.type},
    )
    await db.execute(update(Task).where(Task.conversation_id == conversation_id).values(conversation_id=None))
    await db.execute(delete(AIPermission).where(AIPermission.conversation_id == conversation_id))
    await db.execute(delete(Message).where(Message.conversation_id == conversation_id))
    await db.execute(delete(ConversationParticipant).where(ConversationParticipant.conversation_id == conversation_id))
    await db.delete(conversation)
    await db.commit()


@router.get("/tasks", response_model=list[AdminTaskOut])
async def list_all_tasks(
    workspace_id: str,
    owner_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[AdminTaskOut]:
    await require_support_scope(db, current_user, workspace_id, "personal_data:read")
    stmt = (
        select(Task)
        .options(selectinload(Task.owner), selectinload(Task.conversation))
        .where(Task.workspace_id == workspace_id)
        .order_by(Task.created_at.desc())
    )
    if owner_id:
        stmt = stmt.where(Task.owner_id == owner_id)
    tasks = (await db.execute(stmt.offset(offset).limit(limit))).scalars().all()
    return [
        AdminTaskOut(
            id=t.id,
            workspace_id=t.workspace_id,
            conversation_id=t.conversation_id,
            title=t.title,
            due_at=t.due_at,
            priority=t.priority,
            status=t.status,
            source=t.source,
            created_at=t.created_at,
            updated_at=t.updated_at,
            owner_id=t.owner_id,
            owner_email=t.owner.email,
            owner_display_name=t.owner.display_name,
            conversation_label=_conversation_label(t.conversation),
        )
        for t in tasks
    ]


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_admin(
    task_id: str,
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    await require_support_scope(db, current_user, workspace_id, "personal_data:manage")
    task = (
        await db.execute(select(Task).where(Task.id == task_id, Task.workspace_id == workspace_id))
    ).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    await record_audit_event(
        db,
        actor=current_user,
        action="platform.personal_task_deleted",
        target_type="task",
        target_id=task.id,
        workspace_id=workspace_id,
        metadata={},
    )
    await db.delete(task)
    await db.commit()


@router.get("/reminders", response_model=list[AdminReminderOut])
async def list_all_reminders(
    workspace_id: str,
    owner_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[AdminReminderOut]:
    await require_support_scope(db, current_user, workspace_id, "personal_data:read")
    stmt = (
        select(Reminder)
        .options(selectinload(Reminder.owner))
        .where(Reminder.workspace_id == workspace_id)
        .order_by(Reminder.created_at.desc())
    )
    if owner_id:
        stmt = stmt.where(Reminder.owner_id == owner_id)
    reminders = (await db.execute(stmt.offset(offset).limit(limit))).scalars().all()
    return [
        AdminReminderOut(
            id=r.id,
            workspace_id=r.workspace_id,
            title=r.title,
            message=r.message,
            due_at=r.due_at,
            fire_at=r.fire_at,
            status=r.status,
            source=r.source,
            created_at=r.created_at,
            updated_at=r.updated_at,
            owner_id=r.owner_id,
            owner_email=r.owner.email if r.owner else None,
            owner_display_name=r.owner.display_name if r.owner else None,
        )
        for r in reminders
    ]


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder_admin(
    reminder_id: str,
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    await require_support_scope(db, current_user, workspace_id, "personal_data:manage")
    reminder = (
        await db.execute(
            select(Reminder).where(Reminder.id == reminder_id, Reminder.workspace_id == workspace_id)
        )
    ).scalar_one_or_none()
    if reminder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    if reminder.status == "scheduled":
        reminder_service.remove_scheduler_job(reminder.id)
    await record_audit_event(
        db,
        actor=current_user,
        action="platform.personal_reminder_deleted",
        target_type="reminder",
        target_id=reminder_id,
        workspace_id=workspace_id,
        metadata={},
    )
    await db.delete(reminder)
    await db.commit()


@router.get("/memories", response_model=list[AdminMemoryOut])
async def list_all_memories(
    workspace_id: str,
    owner_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[AdminMemoryOut]:
    await require_support_scope(db, current_user, workspace_id, "personal_data:read")
    stmt = (
        select(Memory)
        .options(selectinload(Memory.owner))
        .where(Memory.workspace_id == workspace_id)
        .order_by(Memory.created_at.desc())
    )
    if owner_id:
        stmt = stmt.where(Memory.owner_id == owner_id)
    memories = (await db.execute(stmt.offset(offset).limit(limit))).scalars().all()
    return [
        AdminMemoryOut(
            id=m.id,
            workspace_id=m.workspace_id,
            category=m.category,
            title=m.title,
            detail=m.detail,
            created_at=m.created_at,
            updated_at=m.updated_at,
            owner_id=m.owner_id,
            owner_email=m.owner.email,
            owner_display_name=m.owner.display_name,
        )
        for m in memories
    ]


@router.delete("/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory_admin(
    memory_id: str,
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    await require_support_scope(db, current_user, workspace_id, "personal_data:manage")
    memory = (
        await db.execute(select(Memory).where(Memory.id == memory_id, Memory.workspace_id == workspace_id))
    ).scalar_one_or_none()
    if memory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    await record_audit_event(
        db,
        actor=current_user,
        action="platform.personal_memory_deleted",
        target_type="memory",
        target_id=memory.id,
        workspace_id=workspace_id,
        metadata={},
    )
    await db.delete(memory)
    await db.commit()
