from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.db.models import AIPermission, Conversation, ConversationParticipant, Message, User, WorkspaceMembership
from src.models.auth_schemas import UserPublic
from src.models.chat_schemas import ConversationSummary, MessageOut
from src.models.schemas import ChatMessage, MessageScope
from src.services.authorization_service import (
    get_authorized_participant_ids,
    require_workspace_member,
)
from src.services.workspace_service import resolve_workspace_for_user


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def format_local_timestamp(iso_value: str) -> str | None:
    """Render a message's ISO timestamp in local calendar_timezone, same style as the "current
    datetime" the planner already grounds the LLM with (planner_node._build_system_prompt) - used
    both by _format_messages (api/routes.py) and the search_messages agent tool, so every path
    that hands message content to the LLM presents timestamps the same way."""
    try:
        dt = datetime.fromisoformat(iso_value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    local = dt.astimezone(ZoneInfo(get_settings().calendar_timezone))
    return local.strftime("%A, %Y-%m-%d %H:%M")


def serialize_message(message: Message, sender: User) -> MessageOut:
    return MessageOut(
        id=message.id,
        conversation_id=message.conversation_id,
        sender_id=message.sender_id,
        sender_name=sender.display_name,
        content=message.content,
        created_at=_iso(message.created_at),
    )


async def _get_participant(db: AsyncSession, conversation_id: str, user_id: str) -> ConversationParticipant | None:
    return (
        await db.execute(
            select(ConversationParticipant).where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
        )
    ).scalar_one_or_none()


async def assert_participant(db: AsyncSession, conversation_id: str, user_id: str) -> None:
    participant = await _get_participant(db, conversation_id, user_id)
    if participant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return participant


async def get_participant_ids(db: AsyncSession, conversation_id: str) -> list[str]:
    return await get_authorized_participant_ids(db, conversation_id)


async def get_ai_permission(db: AsyncSession, conversation_id: str, user_id: str) -> AIPermission | None:
    return (
        await db.execute(
            select(AIPermission).where(
                AIPermission.conversation_id == conversation_id,
                AIPermission.user_id == user_id,
            )
        )
    ).scalar_one_or_none()


async def set_ai_permission(db: AsyncSession, conversation_id: str, user_id: str, granted: bool) -> AIPermission:
    permission = await get_ai_permission(db, conversation_id, user_id)
    if permission is None:
        permission = AIPermission(conversation_id=conversation_id, user_id=user_id, granted=granted)
        db.add(permission)
    else:
        permission.granted = granted
    await db.commit()
    await db.refresh(permission)
    return permission


async def assert_ai_permission(db: AsyncSession, conversation_id: str, user_id: str) -> None:
    permission = await get_ai_permission(db, conversation_id, user_id)
    if permission is None or not permission.granted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="AI permission not granted for this conversation"
        )


async def create_message(db: AsyncSession, conversation_id: str, sender_id: str, content: str) -> Message:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    message = Message(conversation_id=conversation_id, sender_id=sender_id, content=content)
    db.add(message)
    conversation.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(message)
    return message


async def mark_read(db: AsyncSession, conversation_id: str, user_id: str) -> None:
    participant = await _get_participant(db, conversation_id, user_id)
    if participant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant of this conversation")
    participant.last_read_at = datetime.now(UTC)
    await db.commit()


async def _assert_workspace_participants(
    db: AsyncSession,
    workspace_id: str,
    user_ids: set[str],
) -> None:
    if not user_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one participant is required")
    rows = (
        (
            await db.execute(
                select(WorkspaceMembership.user_id).where(
                    WorkspaceMembership.workspace_id == workspace_id,
                    WorkspaceMembership.user_id.in_(user_ids),
                    WorkspaceMembership.status == "active",
                )
            )
        )
        .scalars()
        .all()
    )
    if set(rows) != user_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Participant is outside the workspace")


async def get_or_create_direct_conversation(
    db: AsyncSession,
    user_a_id: str,
    user_b_id: str,
    workspace_id: str | None = None,
) -> Conversation:
    if user_a_id == user_b_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot create a conversation with self")
    if workspace_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id is required")
    workspace = await resolve_workspace_for_user(db, user_a_id, workspace_id)
    if workspace.type != "organization":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Direct conversations require an organization workspace",
        )
    await require_workspace_member(db, await db.get(User, user_a_id), workspace_id)
    await _assert_workspace_participants(db, workspace_id, {user_a_id, user_b_id})

    candidate_ids = (
        (
            await db.execute(
                select(ConversationParticipant.conversation_id)
                .join(Conversation, Conversation.id == ConversationParticipant.conversation_id)
                .where(
                    Conversation.workspace_id == workspace_id,
                    Conversation.type == "direct",
                    ConversationParticipant.user_id == user_a_id,
                    ConversationParticipant.revoked_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    for cid in candidate_ids:
        participant_ids = (
            (
                await db.execute(
                    select(ConversationParticipant.user_id).where(
                        ConversationParticipant.conversation_id == cid,
                        ConversationParticipant.revoked_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        if set(participant_ids) == {user_a_id, user_b_id}:
            return await db.get(Conversation, cid)

    conversation = Conversation(workspace_id=workspace_id, type="direct", name=None, created_by=user_a_id)
    db.add(conversation)
    await db.flush()
    db.add_all(
        [
            ConversationParticipant(
                conversation_id=conversation.id,
                user_id=user_a_id,
                principal_kind="workspace_user",
                resource_role="manager",
                invited_by_user_id=user_a_id,
            ),
            ConversationParticipant(
                conversation_id=conversation.id,
                user_id=user_b_id,
                principal_kind="workspace_user",
                resource_role="participant",
                invited_by_user_id=user_a_id,
            ),
        ]
    )
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def create_group_conversation(
    db: AsyncSession,
    creator_id: str,
    member_ids: list[str],
    name: str,
    workspace_id: str | None = None,
) -> Conversation:
    if workspace_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id is required")
    workspace = await resolve_workspace_for_user(db, creator_id, workspace_id)
    if workspace.type != "organization":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Group conversations require an organization workspace",
        )
    await _assert_workspace_participants(db, workspace_id, {creator_id, *member_ids})
    conversation = Conversation(workspace_id=workspace_id, type="group", name=name, created_by=creator_id)
    db.add(conversation)
    await db.flush()
    all_member_ids = {creator_id, *member_ids}
    db.add_all(
        [
            ConversationParticipant(
                conversation_id=conversation.id,
                user_id=member_id,
                principal_kind="workspace_user",
                resource_role="manager" if member_id == creator_id else "participant",
                invited_by_user_id=creator_id,
            )
            for member_id in all_member_ids
        ]
    )
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def build_conversation_summary(
    db: AsyncSession, conversation: Conversation, current_user_id: str
) -> ConversationSummary:
    participant_rows = (
        await db.execute(
            select(User, ConversationParticipant)
            .join(ConversationParticipant, ConversationParticipant.user_id == User.id)
            .where(
                ConversationParticipant.conversation_id == conversation.id,
                ConversationParticipant.revoked_at.is_(None),
            )
        )
    ).all()
    participants = [
        UserPublic(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role,
            platform_role=user.platform_role,
        )
        for user, _ in participant_rows
    ]
    my_participant = next((cp for _, cp in participant_rows if cp.user_id == current_user_id), None)

    if conversation.type == "group":
        name = conversation.name or "Group"
    else:
        other = next((user for user, _ in participant_rows if user.id != current_user_id), None)
        name = other.display_name if other else "Direct message"

    last_message_row = (
        await db.execute(
            select(Message, User)
            .join(User, User.id == Message.sender_id)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
    ).first()
    last_message = serialize_message(last_message_row[0], last_message_row[1]) if last_message_row else None

    unread_count = 0
    if my_participant is not None:
        unread_count = (
            await db.execute(
                select(func.count(Message.id)).where(
                    Message.conversation_id == conversation.id,
                    Message.created_at > my_participant.last_read_at,
                    Message.sender_id != current_user_id,
                )
            )
        ).scalar_one()

    return ConversationSummary(
        id=conversation.id,
        workspace_id=conversation.workspace_id,
        type=conversation.type,
        name=name,
        participants=participants,
        last_message=last_message,
        unread_count=unread_count,
        updated_at=_iso(conversation.updated_at),
    )


# ---------------------------------------------------------------- AI panel "Permission scope"


def _local_now() -> datetime:
    return datetime.now(ZoneInfo(get_settings().calendar_timezone))


def _local_midnight_utc(days_ago: int = 0) -> datetime:
    local = _local_now() - timedelta(days=days_ago)
    return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


def _local_week_start_utc() -> datetime:
    """Monday 00:00 of the current local week."""
    now = _local_now()
    monday = now - timedelta(days=now.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


def _parse_scope_datetime(value: str) -> datetime:
    """Same convention as reminder_service.create_reminder: a naive value (no UTC offset) is
    assumed to already be in calendar_timezone, not the server's local zone."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(get_settings().calendar_timezone))
    return dt


async def get_scoped_messages(
    db: AsyncSession, conversation_id: str, user_id: str, scope: MessageScope
) -> list[ChatMessage]:
    """Resolve the AI panel's "Permission scope" selection against the DB directly, rather than
    trusting whatever slice of messages the client already had loaded (which is at most the last
    50 - see Frontend/src/hooks/useMessages.js) - the only way any scope beyond "N latest" can be
    correct for a conversation with more history than what's currently loaded client-side."""
    base = select(Message, User).join(User, User.id == Message.sender_id).where(
        Message.conversation_id == conversation_id
    )

    if scope.kind == "latest_n":
        stmt = base.order_by(Message.created_at.desc()).limit(scope.count or 20)
        rows = list(reversed((await db.execute(stmt)).all()))
    elif scope.kind == "unread":
        participant = await _get_participant(db, conversation_id, user_id)
        if participant is None:
            return []
        # Same predicate as build_conversation_summary's unread_count above, so this scope
        # matches what the conversation-list unread badge already means.
        stmt = base.where(
            Message.created_at > participant.last_read_at, Message.sender_id != user_id
        ).order_by(Message.created_at.asc())
        rows = (await db.execute(stmt)).all()
    elif scope.kind == "today":
        stmt = base.where(Message.created_at >= _local_midnight_utc()).order_by(Message.created_at.asc())
        rows = (await db.execute(stmt)).all()
    elif scope.kind == "yesterday":
        stmt = base.where(
            Message.created_at >= _local_midnight_utc(days_ago=1),
            Message.created_at < _local_midnight_utc(),
        ).order_by(Message.created_at.asc())
        rows = (await db.execute(stmt)).all()
    elif scope.kind == "this_week":
        stmt = base.where(Message.created_at >= _local_week_start_utc()).order_by(Message.created_at.asc())
        rows = (await db.execute(stmt)).all()
    elif scope.kind == "rolling_hours":
        since = datetime.now(UTC) - timedelta(hours=scope.hours or 1)
        stmt = base.where(Message.created_at >= since).order_by(Message.created_at.asc())
        rows = (await db.execute(stmt)).all()
    elif scope.kind == "custom_range":
        stmt = base
        if scope.since:
            stmt = stmt.where(Message.created_at >= _parse_scope_datetime(scope.since))
        if scope.until:
            stmt = stmt.where(Message.created_at <= _parse_scope_datetime(scope.until))
        rows = (await db.execute(stmt.order_by(Message.created_at.asc()))).all()
    else:
        rows = []

    return [
        ChatMessage(role="user", sender=sender.display_name, content=message.content, timestamp=_iso(message.created_at))
        for message, sender in rows
    ]


# ---------------------------------------------------------------- Agent "search old messages" tool


def _escape_ilike(value: str) -> str:
    """Escape ILIKE wildcard/escape chars so a literal '%'/'_' in the query is matched literally,
    not treated as a wildcard."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def search_messages(db: AsyncSession, conversation_id: str, query: str, limit: int = 20) -> list[ChatMessage]:
    """Case-insensitive substring search over one conversation's message history, for the agent's
    search_messages tool (src/agents/tools/search_tool.py) - plain Postgres ILIKE, not semantic
    search (the project deliberately doesn't run a vector store, see ARCHITECTURE.md). Selects the
    `limit` most recent matches, then re-orders them chronologically (oldest first) for
    readability - same convention get_scoped_messages' latest_n branch above already uses."""
    if not query.strip():
        return []
    limit = max(1, min(limit, 50))  # defensive clamp - limit ultimately comes from the LLM's tool call
    stmt = (
        select(Message, User)
        .join(User, User.id == Message.sender_id)
        .where(
            Message.conversation_id == conversation_id,
            Message.content.ilike(f"%{_escape_ilike(query)}%", escape="\\"),
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    rows = list(reversed((await db.execute(stmt)).all()))
    return [
        ChatMessage(role="user", sender=sender.display_name, content=message.content, timestamp=_iso(message.created_at))
        for message, sender in rows
    ]
