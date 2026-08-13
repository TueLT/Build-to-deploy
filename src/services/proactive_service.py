import json
import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from src.config import get_settings
from src.db import session as db_session
from src.db.models import Conversation, Task
from src.services import chat_service, consent_service, usage_service
from src.services.llm import get_llm
from src.websocket.manager import manager

logger = logging.getLogger(__name__)

# Cheap pre-filter so we don't burn an LLM call on every "ok"/"thanks" message - only messages
# that at least look like they might mention a time/commitment go on to the real (LLM) check.
_SIGNAL_PATTERN = re.compile(
    r"tomorrow|tonight|next (mon|tue|wed|thu|fri|sat|sun)|deadline|due (date|by)|meeting|appointment|"
    r"remind|schedule|\d\s?(am|pm)|"
    r"ngày mai|tối nay|sáng mai|chiều mai|tuần sau|thứ (hai|ba|tư|năm|sáu|bảy)|chủ nhật|hạn chót|"
    r"cuộc họp|họp lúc|hẹn|nhắc (tôi|mình|nhở)|lịch|lúc \d|giờ \d",
    re.IGNORECASE,
)


def _looks_like_commitment(text: str) -> bool:
    return bool(_SIGNAL_PATTERN.search(text))


def _strip_fence(text: str) -> str:
    return text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()


async def maybe_suggest_task(
    *,
    conversation_id: str,
    sender_id: str,
    content: str,
    message_id: str | None = None,
) -> None:
    """Best-effort, fire-and-forget: if a new message looks like it contains a personal
    commitment/appointment/deadline, ask the LLM to confirm and, if so, drop a 'suggested' Task
    (same review flow as the manual Extract tasks action) for the sender to Accept/Dismiss.
    Requires the sender to have granted AI permission for this conversation (ai_permissions) -
    silently skips otherwise, same as the explicit /chat endpoint. Never raises - a failure here
    must not affect message delivery.
    """
    if not _looks_like_commitment(content):
        return

    try:
        async with db_session.async_session_maker() as db:
            conversation = await db.get(Conversation, conversation_id)
            permission = await chat_service.get_ai_permission(db, conversation_id, sender_id)
        if conversation is None:
            return
        if conversation.type == "group":
            if not conversation.ai_enabled:
                return
        elif permission is None or not permission.granted or not permission.contribution_allowed:
            return

        # Ràng buộc đề bài: tối ưu chi phí - đây là lệnh gọi LLM tự động chạy nền trên MỌI tin
        # nhắn mới (không phải người dùng chủ động bấm), nên là nơi cần chặn trước tiên khi đã
        # vượt ngân sách; bỏ qua lặng lẽ giống các điều kiện guard khác ở trên, không phải lỗi.
        if await usage_service.is_over_budget():
            return

        settings = get_settings()
        async with db_session.async_session_maker() as db:
            conversation = await db.get(Conversation, conversation_id)
            if conversation is None:
                return
            workspace_id = conversation.workspace_id
            consent_scope_hash = await consent_service.get_consent_scope_hash(db, conversation_id)
        llm = get_llm()
        prompt = (
            "A message was just sent in a team chat app. Decide whether the AUTHOR OF THIS MESSAGE "
            "personally commits themselves to an action, appointment, or deadline. An assignment, "
            "request, or reminder directed at somebody else is NOT a sender commitment. A question "
            "or tentative suggestion is also not a commitment. Output ONLY JSON, no prose or markdown, "
            'with exactly these keys: "has_sender_commitment" (boolean), "title" (short Vietnamese '
            'string, meaningful only when true), "due_at" (ISO 8601 datetime or null), and '
            '"confidence" (number from 0 to 1). If unsure, output '
            '{"has_sender_commitment": false, "title": "", "due_at": null, "confidence": 0}.\n\n'
            f"Message: {content}"
        )
        result = await llm.ainvoke(prompt)
        await usage_service.log_usage(
            provider=settings.llm_provider,
            model=settings.model_name,
            usage_metadata=result.usage_metadata,
            user_id=sender_id,
            workspace_id=workspace_id,
        )
        data = json.loads(_strip_fence(result.content))
        if not data.get("has_sender_commitment"):
            return

        due_at = None
        if data.get("due_at"):
            try:
                due_at = datetime.fromisoformat(data["due_at"])
                if due_at.tzinfo is None:
                    # LLM output has no UTC offset - treat it as Hanoi time, not naive/ambiguous.
                    due_at = due_at.replace(tzinfo=ZoneInfo(settings.calendar_timezone))
            except ValueError:
                due_at = None

        async with db_session.async_session_maker() as db:
            if message_id:
                existing = (
                    await db.execute(
                        select(Task).where(
                            Task.conversation_id == conversation_id,
                            Task.source == "proactive",
                            Task.source_message_ids == [message_id],
                        )
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    return
            task = Task(
                workspace_id=workspace_id,
                owner_id=sender_id,
                conversation_id=conversation_id,
                title=(data.get("title") or content)[:200],
                due_at=due_at,
                priority="Medium",
                source="proactive",
                source_message_ids=[message_id] if message_id else None,
                source_sender_id=sender_id,
                consent_scope_hash=consent_scope_hash,
            )
            db.add(task)
            await db.commit()
            await db.refresh(task)

        await manager.broadcast_to_users(
            [sender_id],
            {
                "type": "task_suggested",
                "task": {
                    "id": task.id,
                    "workspace_id": task.workspace_id,
                    "conversation_id": task.conversation_id,
                    "title": task.title,
                    "due_at": task.due_at.isoformat() if task.due_at else None,
                    "priority": task.priority,
                    "status": task.status,
                    "source": task.source,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                },
            },
        )
    except Exception:  # noqa: BLE001 - background detection must never break message delivery
        logger.exception("Proactive commitment detection failed")
