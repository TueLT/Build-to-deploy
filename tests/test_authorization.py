from importlib import import_module

import pytest

from src.db import session as db_session
from src.db.models import User


async def _create_private_conversation(client, auth_headers, other_auth_headers):
    other = (await client.get("/api/v1/auth/me", headers=other_auth_headers)).json()
    response = await client.post(
        "/api/v1/conversations",
        json={"type": "direct", "participant_ids": [other["id"]]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_current_user_exposes_platform_role(client, auth_headers):
    response = await client.get("/api/v1/auth/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["platform_role"] == "user"
    assert "role" not in response.json()


@pytest.mark.asyncio
async def test_regular_user_cannot_access_platform_stats(client, auth_headers):
    response = await client.get("/api/v1/platform/stats", headers=auth_headers)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_platform_admin_can_read_aggregate_platform_stats(client, platform_admin_headers):
    response = await client.get("/api/v1/platform/stats", headers=platform_admin_headers)

    assert response.status_code == 200
    assert set(response.json()) == {
        "total_users",
        "total_conversations",
        "total_messages",
        "new_users_last_7_days",
    }


@pytest.mark.asyncio
async def test_platform_admin_cannot_read_original_conversation_messages(
    client,
    admin_auth_headers,
    auth_headers,
    other_auth_headers,
):
    conversation = await _create_private_conversation(client, auth_headers, other_auth_headers)
    sent = await client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"content": "private message"},
        headers=auth_headers,
    )
    assert sent.status_code == 200

    participant_route = await client.get(
        f"/api/v1/conversations/{conversation['id']}/messages",
        headers=admin_auth_headers,
    )
    removed_admin_route = await client.get(
        f"/api/v1/admin/conversations/{conversation['id']}/messages",
        headers=admin_auth_headers,
    )

    assert participant_route.status_code == 404
    assert removed_admin_route.status_code == 404
    assert "private message" not in participant_route.text
    assert "private message" not in removed_admin_route.text


@pytest.mark.asyncio
async def test_platform_admin_conversation_management_route_is_removed(
    client,
    admin_auth_headers,
    auth_headers,
    other_auth_headers,
):
    await _create_private_conversation(client, auth_headers, other_auth_headers)

    response = await client.get("/api/v1/admin/conversations", headers=admin_auth_headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_audit_service_records_identifier_metadata_without_content(client, auth_headers):
    current_user = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()
    audit_service = import_module("src.services.audit_service")

    async with db_session.async_session_maker() as db:
        actor = await db.get(User, current_user["id"])
        record = await audit_service.record_audit_event(
            db,
            actor=actor,
            action="conversation.created",
            target_type="conversation",
            target_id="conversation-123",
            metadata={"source": "api"},
        )
        await db.commit()

        assert record.actor_user_id == actor.id
        assert record.actor_type == "user"
        assert record.metadata_json == {"source": "api"}


@pytest.mark.asyncio
@pytest.mark.parametrize("forbidden_key", ["content", "message", "memory", "token", "secret"])
async def test_audit_service_rejects_sensitive_metadata(client, auth_headers, forbidden_key):
    current_user = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()
    audit_service = import_module("src.services.audit_service")

    async with db_session.async_session_maker() as db:
        actor = await db.get(User, current_user["id"])

        with pytest.raises(ValueError, match="sensitive"):
            await audit_service.record_audit_event(
                db,
                actor=actor,
                action="conversation.inspected",
                target_type="conversation",
                target_id="conversation-123",
                metadata={forbidden_key: "must not be stored"},
            )
