from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents import graph as agent_graph
from src.auth.dependencies import get_current_user
from src.db.models import Conversation, Message, User
from src.db.session import get_db
from src.models.schemas import ChatMessage, ChatRequest, ChatResponse, InterruptPayload, ResumeRequest
from src.services.authorization_service import require_conversation_access
from src.services.workspace_service import resolve_workspace_for_user

router = APIRouter()

# thread_id -> owner user id. In-memory only: enough to stop one user resuming another
# user's interrupted (unconfirmed calendar/reminder) run; doesn't need to survive a restart
# since thread_ids are random UUIDs nobody else can guess anyway.
_thread_owners: dict[str, str] = {}


def _check_thread_owner(thread_id: str, current_user: User) -> None:
    owner = _thread_owners.get(thread_id)
    if owner is not None and owner != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your conversation")


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

    error = result.get("error")
    if error:
        return ChatResponse(response=error, thread_id=thread_id, status="error")

    final_text = ""
    for m in reversed(result.get("messages", [])):
        # A trailing ToolMessage means graph.py routed straight to END after a "terminal" tool
        # (summarize_conversation/extract_tasks) - its content is already the final answer.
        if isinstance(m, (AIMessage, ToolMessage)) and m.content:
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
        conversation = await db.get(Conversation, request.conversation_id)
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        if request.workspace_id is not None and request.workspace_id != conversation.workspace_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="conversation_id does not belong to workspace_id",
            )
        workspace_id = conversation.workspace_id
    else:
        workspace = await resolve_workspace_for_user(db, current_user.id, request.workspace_id)
        workspace_id = workspace.id
    thread_id = request.thread_id or str(uuid4())
    _check_thread_owner(thread_id, current_user)
    _thread_owners.setdefault(thread_id, current_user.id)
    config = {"configurable": {"thread_id": f"{current_user.id}:{thread_id}"}}
    if request.conversation_id is not None:
        context_text = await _conversation_context(db, request.conversation_id, request.context_limit)
    else:
        scoped_messages = request.messages[-request.context_limit :] if request.messages else []
        context_text = _format_messages(scoped_messages)
    inputs = {
        "messages": [HumanMessage(content=request.message)],
        "context": context_text,
        "user_id": current_user.id,
        "workspace_id": workspace_id,
    }
    try:
        result = await agent_graph.agent.ainvoke(inputs, config)
    except Exception:
        raise HTTPException(status_code=500, detail="AI service is temporarily unavailable")
    return _build_chat_response(result, thread_id)


@router.post("/chat/resume", response_model=ChatResponse)
async def resume_chat(
    request: ResumeRequest,
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Resume an interrupted agent run with the user's confirm/reject decision."""
    _check_thread_owner(request.thread_id, current_user)
    config = {"configurable": {"thread_id": f"{current_user.id}:{request.thread_id}"}}
    try:
        result = await agent_graph.agent.ainvoke(
            Command(resume={"approved": request.approved, "edits": request.edits}), config
        )
    except Exception:
        raise HTTPException(status_code=500, detail="AI service is temporarily unavailable")
    return _build_chat_response(result, request.thread_id)


@router.get("/status")
async def agent_status():
    """Kiểm tra trạng thái agent."""
    return {"status": "ready", "agent": "LangGraph Agent v1.0"}
