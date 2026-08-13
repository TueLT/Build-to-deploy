from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from src.db import session as db_session
from src.db.models import Task
from src.services import proactive_service


@pytest.mark.parametrize(
    "text,expected",
    [
        ("let's meet tomorrow at 3pm", True),
        ("don't forget the deadline is Friday", True),
        ("họp lúc 9 giờ sáng mai nhé", True),
        ("haha nice one", False),
        ("thanks!", False),
    ],
)
def test_looks_like_commitment(text, expected):
    assert proactive_service._looks_like_commitment(text) is expected


async def _create_conversation(client, creator_headers, other_headers):
    other = (await client.get("/api/v1/auth/me", headers=other_headers)).json()
    workspace = (
        await client.post("/api/v1/workspaces", json={"name": "Proactive test team"}, headers=creator_headers)
    ).json()
    add_member = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/members",
        json={"email": other["email"], "role": "member"},
        headers=creator_headers,
    )
    assert add_member.status_code == 201
    conv = await client.post(
        "/api/v1/conversations",
        json={"type": "direct", "participant_ids": [other["id"]], "workspace_id": workspace["id"]},
        headers=creator_headers,
    )
    assert conv.status_code == 200
    return conv.json()["id"], workspace["id"]


async def _grant_ai_permission(client, conversation_id, headers):
    await client.put(
        f"/api/v1/conversations/{conversation_id}/ai-permission",
        json={"granted": True, "contribution_allowed": True},
        headers=headers,
    )


@pytest.mark.asyncio
async def test_maybe_suggest_task_skips_llm_when_no_signal(monkeypatch):
    fake_llm = AsyncMock()
    monkeypatch.setattr(proactive_service, "get_llm", lambda: fake_llm)

    await proactive_service.maybe_suggest_task(conversation_id="c1", sender_id="u1", content="thanks!")

    fake_llm.ainvoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_maybe_suggest_task_skips_when_ai_permission_not_granted(
    client, auth_headers, other_auth_headers, monkeypatch
):
    fake_llm = AsyncMock()
    monkeypatch.setattr(proactive_service, "get_llm", lambda: fake_llm)

    sender_id = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"]
    conversation_id, _ = await _create_conversation(client, auth_headers, other_auth_headers)
    # Permission was never granted for this conversation - default deny.

    await proactive_service.maybe_suggest_task(
        conversation_id=conversation_id, sender_id=sender_id, content="đừng quên deadline gửi báo cáo thứ hai nhé"
    )

    fake_llm.ainvoke.assert_not_awaited()
    async with db_session.async_session_maker() as db:
        tasks = (await db.execute(select(Task).where(Task.owner_id == sender_id))).scalars().all()
    assert tasks == []


@pytest.mark.asyncio
async def test_maybe_suggest_task_creates_suggested_task(client, auth_headers, other_auth_headers, monkeypatch):
    fake_llm = AsyncMock()
    fake_llm.ainvoke.return_value = AsyncMock(
        content=(
            '{"has_sender_commitment": true, "title": "Gửi báo cáo", '
            '"due_at": "2026-08-10T09:00:00", "confidence": 0.97}'
        )
    )
    monkeypatch.setattr(proactive_service, "get_llm", lambda: fake_llm)

    sender_id = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"]
    conversation_id, workspace_id = await _create_conversation(client, auth_headers, other_auth_headers)
    await _grant_ai_permission(client, conversation_id, auth_headers)

    await proactive_service.maybe_suggest_task(
        conversation_id=conversation_id, sender_id=sender_id, content="đừng quên deadline gửi báo cáo thứ hai nhé"
    )

    async with db_session.async_session_maker() as db:
        tasks = (await db.execute(select(Task).where(Task.owner_id == sender_id))).scalars().all()
    assert len(tasks) == 1
    assert tasks[0].title == "Gửi báo cáo"
    assert tasks[0].source == "proactive"
    assert tasks[0].status == "suggested"
    assert tasks[0].workspace_id == workspace_id
    prompt = fake_llm.ainvoke.await_args.args[0]
    assert proactive_service.get_settings().calendar_timezone in prompt
    assert str(proactive_service.datetime.now().year) in prompt


@pytest.mark.asyncio
async def test_maybe_suggest_task_no_op_when_llm_says_no_commitment(
    client, auth_headers, other_auth_headers, monkeypatch
):
    fake_llm = AsyncMock()
    fake_llm.ainvoke.return_value = AsyncMock(
        content='{"has_sender_commitment": false, "title": "", "due_at": null, "confidence": 0}'
    )
    monkeypatch.setattr(proactive_service, "get_llm", lambda: fake_llm)

    sender_id = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"]
    conversation_id, _ = await _create_conversation(client, auth_headers, other_auth_headers)
    await _grant_ai_permission(client, conversation_id, auth_headers)

    await proactive_service.maybe_suggest_task(
        conversation_id=conversation_id, sender_id=sender_id, content="meeting tomorrow, just kidding"
    )

    async with db_session.async_session_maker() as db:
        tasks = (await db.execute(select(Task).where(Task.owner_id == sender_id))).scalars().all()
    assert tasks == []


@pytest.mark.asyncio
async def test_maybe_suggest_task_skips_llm_when_over_budget(client, auth_headers, other_auth_headers, monkeypatch):
    fake_llm = AsyncMock()
    monkeypatch.setattr(proactive_service, "get_llm", lambda: fake_llm)

    async def _over_budget():
        return True

    monkeypatch.setattr(proactive_service.usage_service, "is_over_budget", _over_budget)

    sender_id = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"]
    conversation_id, _ = await _create_conversation(client, auth_headers, other_auth_headers)
    await _grant_ai_permission(client, conversation_id, auth_headers)

    await proactive_service.maybe_suggest_task(
        conversation_id=conversation_id, sender_id=sender_id, content="đừng quên deadline gửi báo cáo thứ hai nhé"
    )

    fake_llm.ainvoke.assert_not_awaited()
    async with db_session.async_session_maker() as db:
        tasks = (await db.execute(select(Task).where(Task.owner_id == sender_id))).scalars().all()
    assert tasks == []


@pytest.mark.asyncio
async def test_maybe_suggest_task_never_raises_on_llm_error(client, auth_headers, other_auth_headers, monkeypatch):
    fake_llm = AsyncMock()
    fake_llm.ainvoke.side_effect = RuntimeError("boom")
    monkeypatch.setattr(proactive_service, "get_llm", lambda: fake_llm)

    sender_id = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"]
    conversation_id, _ = await _create_conversation(client, auth_headers, other_auth_headers)
    await _grant_ai_permission(client, conversation_id, auth_headers)

    await proactive_service.maybe_suggest_task(
        conversation_id=conversation_id, sender_id=sender_id, content="meeting tomorrow"
    )


@pytest.mark.asyncio
async def test_assignment_to_somebody_else_is_not_a_sender_commitment(
    client, auth_headers, other_auth_headers, monkeypatch
):
    fake_llm = AsyncMock()
    fake_llm.ainvoke.return_value = AsyncMock(
        content='{"has_sender_commitment": false, "title": "", "due_at": null, "confidence": 0.98}'
    )
    monkeypatch.setattr(proactive_service, "get_llm", lambda: fake_llm)

    sender_id = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"]
    conversation_id, _ = await _create_conversation(client, auth_headers, other_auth_headers)
    await _grant_ai_permission(client, conversation_id, auth_headers)

    await proactive_service.maybe_suggest_task(
        conversation_id=conversation_id,
        sender_id=sender_id,
        content="Susan gửi proposal trước thứ Sáu nhé",
        message_id="message-assignment",
    )

    async with db_session.async_session_maker() as db:
        tasks = (await db.execute(select(Task).where(Task.owner_id == sender_id))).scalars().all()
    assert tasks == []


@pytest.mark.asyncio
async def test_revoking_source_consent_invalidates_unconfirmed_candidate(
    client, auth_headers, other_auth_headers, monkeypatch
):
    fake_llm = AsyncMock()
    fake_llm.ainvoke.return_value = AsyncMock(
        content=(
            '{"has_sender_commitment": true, "title": "Gửi báo cáo", '
            '"due_at": null, "confidence": 0.95}'
        )
    )
    monkeypatch.setattr(proactive_service, "get_llm", lambda: fake_llm)

    sender_id = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"]
    conversation_id, _ = await _create_conversation(client, auth_headers, other_auth_headers)
    await _grant_ai_permission(client, conversation_id, auth_headers)
    await proactive_service.maybe_suggest_task(
        conversation_id=conversation_id,
        sender_id=sender_id,
        content="Tôi sẽ gửi báo cáo trước deadline",
        message_id="source-message-1",
    )

    await client.put(
        f"/api/v1/conversations/{conversation_id}/ai-permission",
        json={"contribution_allowed": False},
        headers=auth_headers,
    )

    async with db_session.async_session_maker() as db:
        task = (await db.execute(select(Task).where(Task.owner_id == sender_id))).scalar_one()
        assert task.status == "invalidated"
        assert task.invalidated_reason == "source_consent_revoked"

    response = await client.patch(
        f"/api/v1/tasks/{task.id}/status",
        json={"status": "pending"},
        headers=auth_headers,
    )
    assert response.status_code == 409
