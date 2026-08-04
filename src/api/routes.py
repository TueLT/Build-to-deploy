from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.graph import agent
from src.auth.dependencies import get_current_user
from src.db.models import Message, User
from src.db.session import get_db
from src.models.schemas import ChatMessage, ChatRequest, ChatResponse, InterruptPayload, ResumeRequest
from src.services.authorization_service import require_conversation_access

router = APIRouter()


def _format_messages(messages: list[ChatMessage]) -> str:
    return "\n".join(f"{m.sender or m.role}: {m.content}" for m in messages)


async def _conversation_context(db: AsyncSession, conversation_id: str, limit: int = 50) -> str:
    rows = (
        await db.execute(
            select(Message, User)
            .join(User, User.id == Message.sender_id)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
    ).all()
    return "\n".join(f"{sender.display_name}: {message.content}" for message, sender in reversed(rows))


def _build_chat_response(result: dict, thread_id: str) -> ChatResponse:
    interrupts = result.get("__interrupt__")
    if interrupts:
        payload = interrupts[0].value
        return ChatResponse(
            response="Please confirm the proposed action.",
            thread_id=thread_id,
            status="interrupted",
            interrupt=InterruptPayload(**payload),
        )

    final_text = ""
    for m in reversed(result.get("messages", [])):
        if isinstance(m, AIMessage) and m.content:
            final_text = m.content
            break
    return ChatResponse(response=final_text, thread_id=thread_id, status="completed")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Chat với AI agent."""
    if request.conversation_id is not None:
        await require_conversation_access(db, current_user, request.conversation_id, "viewer")
    thread_id = request.thread_id or str(uuid4())
    config = {"configurable": {"thread_id": f"{current_user.id}:{thread_id}"}}
    if request.conversation_id is not None:
        context_text = await _conversation_context(db, request.conversation_id)
    else:
        context_text = _format_messages(request.messages) if request.messages else ""
    inputs = {"messages": [HumanMessage(content=request.message)], "context": context_text}
    try:
        result = await agent.ainvoke(inputs, config)
    except Exception:
        raise HTTPException(status_code=500, detail="AI service is temporarily unavailable")
    return _build_chat_response(result, thread_id)


@router.post("/chat/resume", response_model=ChatResponse)
async def resume_chat(
    request: ResumeRequest,
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Resume an interrupted agent run with the user's confirm/reject decision."""
    config = {"configurable": {"thread_id": f"{current_user.id}:{request.thread_id}"}}
    try:
        result = await agent.ainvoke(Command(resume={"approved": request.approved, "edits": request.edits}), config)
    except Exception:
        raise HTTPException(status_code=500, detail="AI service is temporarily unavailable")
    return _build_chat_response(result, request.thread_id)


@router.get("/status")
async def agent_status():
    """Kiểm tra trạng thái agent."""
    return {"status": "ready", "agent": "LangGraph Agent v1.0"}
