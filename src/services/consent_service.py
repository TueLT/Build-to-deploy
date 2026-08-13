"""Build the only conversation-message view that AI code is allowed to consume.

Conversation membership answers whether a human may read a chat.  It does not answer whether an
external model may process every participant's content.  This module enforces the stricter,
author-controlled rule before any text reaches a planner/tool prompt.
"""

from dataclasses import dataclass
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import AIPermission, Conversation, Message, User
from src.services.authorization_service import get_authorized_participant_ids


@dataclass(frozen=True)
class AuthorizedMessageView:
    conversation_id: str
    text: str
    source_message_ids: list[str]
    included_participant_ids: list[str]
    included_participant_names: list[str]
    excluded_participant_ids: list[str]
    excluded_participant_names: list[str]
    included_message_count: int
    window_message_count: int
    consent_scope_hash: str

    @property
    def coverage(self) -> float:
        if self.window_message_count == 0:
            return 1.0
        return self.included_message_count / self.window_message_count


async def _participant_permission_rows(
    db: AsyncSession, conversation_id: str
) -> tuple[list[User], dict[str, AIPermission]]:
    authorized_ids = await get_authorized_participant_ids(db, conversation_id)
    users = list(
        (
            await db.execute(
                select(User).where(User.id.in_(authorized_ids), User.is_active.is_(True)).order_by(User.id)
            )
        )
        .scalars()
        .all()
    )
    permissions = list(
        (
            await db.execute(
                select(AIPermission).where(AIPermission.conversation_id == conversation_id)
            )
        )
        .scalars()
        .all()
    )
    return users, {permission.user_id: permission for permission in permissions}


def _scope_hash(users: list[User], permissions: dict[str, AIPermission]) -> str:
    parts: list[str] = []
    for user in users:
        permission = permissions.get(user.id)
        if permission is None:
            parts.append(f"{user.id}:0:0:none")
        else:
            updated_at = permission.updated_at.isoformat() if permission.updated_at else "none"
            parts.append(
                f"{user.id}:{int(permission.granted)}:{int(permission.contribution_allowed)}:{updated_at}"
            )
    return sha256("|".join(parts).encode("utf-8")).hexdigest()


async def get_consent_scope_hash(db: AsyncSession, conversation_id: str) -> str:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is not None and conversation.type == "group":
        return sha256(
            f"group:{conversation.id}:{int(conversation.ai_enabled)}:{conversation.ai_policy_version}".encode()
        ).hexdigest()
    users, permissions = await _participant_permission_rows(db, conversation_id)
    return _scope_hash(users, permissions)


async def validate_authorized_source_ids(
    db: AsyncSession,
    conversation_id: str,
    source_message_ids: list[str],
) -> bool:
    if not source_message_ids:
        return False
    conversation = await db.get(Conversation, conversation_id)
    users, permissions = await _participant_permission_rows(db, conversation_id)
    if conversation is not None and conversation.type == "group":
        if not conversation.ai_enabled:
            return False
        allowed_ids = {user.id for user in users}
    else:
        allowed_ids = {
            user.id
            for user in users
            if (permission := permissions.get(user.id)) is not None and permission.contribution_allowed
        }
    rows = (
        await db.execute(
            select(Message.id, Message.sender_id).where(
                Message.conversation_id == conversation_id,
                Message.id.in_(source_message_ids),
            )
        )
    ).all()
    return len(rows) == len(set(source_message_ids)) and all(sender_id in allowed_ids for _, sender_id in rows)


async def build_authorized_message_view(
    db: AsyncSession,
    conversation_id: str,
    limit: int,
) -> AuthorizedMessageView:
    conversation = await db.get(Conversation, conversation_id)
    users, permissions = await _participant_permission_rows(db, conversation_id)
    if conversation is not None and conversation.type == "group" and conversation.ai_enabled:
        allowed_ids = {user.id for user in users}
    else:
        allowed_ids = {
            user.id
            for user in users
            if (permission := permissions.get(user.id)) is not None and permission.contribution_allowed
        }

    # Scope means the latest N conversation messages, then author consent filters that exact
    # window.  Fetching N *authorized* messages could silently reach farther back than the user
    # selected and would make the UI's "20 latest messages" claim untrue.
    rows = (
        await db.execute(
            select(Message, User)
            .join(User, User.id == Message.sender_id)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
    ).all()
    rows.reverse()
    eligible_rows = [(message, sender) for message, sender in rows if sender.id in allowed_ids]

    included_users = [user for user in users if user.id in allowed_ids]
    excluded_users = [user for user in users if user.id not in allowed_ids]
    return AuthorizedMessageView(
        conversation_id=conversation_id,
        text="\n".join(f"{sender.display_name}: {message.content}" for message, sender in eligible_rows),
        source_message_ids=[message.id for message, _ in eligible_rows],
        included_participant_ids=[user.id for user in included_users],
        included_participant_names=[user.display_name for user in included_users],
        excluded_participant_ids=[user.id for user in excluded_users],
        excluded_participant_names=[user.display_name for user in excluded_users],
        included_message_count=len(eligible_rows),
        window_message_count=len(rows),
        consent_scope_hash=(
            sha256(
                f"group:{conversation.id}:{int(conversation.ai_enabled)}:{conversation.ai_policy_version}".encode()
            ).hexdigest()
            if conversation is not None and conversation.type == "group"
            else _scope_hash(users, permissions)
        ),
    )
