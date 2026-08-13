from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import require_platform_admin
from src.db.models import Conversation, Message, User
from src.db.session import get_db
from src.models.platform_schemas import PlatformStats

router = APIRouter(dependencies=[Depends(require_platform_admin)])


@router.get("/stats", response_model=PlatformStats)
async def get_platform_stats(db: AsyncSession = Depends(get_db)) -> PlatformStats:
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total_conversations = (await db.execute(select(func.count()).select_from(Conversation))).scalar_one()
    total_messages = (await db.execute(select(func.count()).select_from(Message))).scalar_one()
    since = datetime.now(UTC) - timedelta(days=7)
    new_users = (await db.execute(select(func.count()).select_from(User).where(User.created_at >= since))).scalar_one()
    return PlatformStats(
        total_users=total_users,
        total_conversations=total_conversations,
        total_messages=total_messages,
        new_users_last_7_days=new_users,
    )
