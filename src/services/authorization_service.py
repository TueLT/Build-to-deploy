from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Conversation, ConversationParticipant, User

_RESOURCE_ROLE_RANK = {"viewer": 1, "participant": 2, "manager": 3}


def require_platform_admin(user: User) -> User:
    if user.platform_role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required",
        )
    return user


async def require_conversation_access(
    db: AsyncSession,
    user: User,
    conversation_id: str,
    minimum_resource_role: str = "viewer",
) -> ConversationParticipant:
    """Authorize exclusively through active conversation participation.

    Platform administrators intentionally receive no bypass. This keeps original message content
    private even from platform operations staff.
    """
    if minimum_resource_role not in _RESOURCE_ROLE_RANK:
        raise ValueError(f"Unknown resource role: {minimum_resource_role}")
    if await db.get(Conversation, conversation_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    participant = (
        await db.execute(
            select(ConversationParticipant).where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user.id,
                ConversationParticipant.revoked_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if participant is None:
        # Return 404 so callers cannot use this endpoint to enumerate private conversations.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if _RESOURCE_ROLE_RANK.get(participant.resource_role, 0) < _RESOURCE_ROLE_RANK[minimum_resource_role]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conversation access denied")
    return participant


async def get_authorized_participant_ids(db: AsyncSession, conversation_id: str) -> list[str]:
    if await db.get(Conversation, conversation_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    rows = (
        await db.execute(
            select(ConversationParticipant.user_id, User.is_active)
            .join(User, User.id == ConversationParticipant.user_id)
            .where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.revoked_at.is_(None),
            )
        )
    ).all()
    return [user_id for user_id, is_active in rows if is_active]
