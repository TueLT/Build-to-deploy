import pytest

from src.services.scheduler import scheduler


async def _personal_workspace(client, headers):
    response = await client.get("/api/v1/workspaces", headers=headers)
    assert response.status_code == 200
    return next(workspace for workspace in response.json() if workspace["type"] == "personal")


async def _approve_support_scope(client, admin_headers, owner_headers, workspace_id, scope):
    requested = await client.post(
        "/api/v1/platform/support-grants",
        json={
            "workspace_id": workspace_id,
            "requested_scope": scope,
            "reason": "Investigate an owner-approved support request",
            "duration_minutes": 30,
        },
        headers=admin_headers,
    )
    assert requested.status_code == 201
    approved = await client.post(
        f"/api/v1/workspaces/{workspace_id}/support-grants/{requested.json()['id']}/approve",
        headers=owner_headers,
    )
    assert approved.status_code == 200, approved.text
    return approved.json()


@pytest.mark.asyncio
async def test_me_includes_role(client, auth_headers):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "user"


@pytest.mark.asyncio
async def test_non_admin_cannot_access_admin_routes(client, auth_headers):
    resp = await client.get("/api/v1/admin/stats", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_view_stats(client, admin_auth_headers, auth_headers):
    resp = await client.get("/api/v1/admin/stats", headers=admin_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_users"] >= 2
    assert "total_conversations" in body
    assert "total_messages" in body
    assert "new_users_last_7_days" in body
    assert body["prompt_tokens_today"] == 0
    assert body["completion_tokens_today"] == 0
    assert body["estimated_cost_usd_today"] == 0
    assert body["unpriced_tokens_today"] == 0


@pytest.mark.asyncio
async def test_admin_can_view_system_health(client, admin_auth_headers):
    resp = await client.get("/api/v1/admin/system-health", headers=admin_auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["overall_status"] in {"operational", "degraded", "down"}
    assert body["checked_at"]
    components = {component["key"]: component for component in body["components"]}
    assert set(components) == {"database", "scheduler", "websocket", "llm", "calendar"}
    assert components["database"]["status"] == "operational"
    assert all("detail" in component for component in components.values())


@pytest.mark.asyncio
async def test_non_admin_cannot_access_system_health(client, auth_headers):
    resp = await client.get("/api/v1/admin/system-health", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_view_ai_management(client, admin_auth_headers):
    resp = await client.get("/api/v1/admin/ai-management", headers=admin_auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"]
    assert body["model"]
    assert body["human_confirmation_required"] is True
    assert body["conversation_consent_required"] is True
    assert body["granted_permissions"] >= 0
    assert body["proactive_suggestions"] >= 0
    assert "google" in body["model_options"]
    assert "openai" in body["model_options"]


@pytest.mark.asyncio
async def test_admin_can_select_and_apply_ai_model(client, admin_auth_headers, monkeypatch):
    from src.config import get_settings
    from src.services import ai_config_service

    settings = get_settings()
    previous = (settings.llm_provider, settings.model_name, settings.llm_temperature)
    monkeypatch.setattr(settings, "google_api_key", "test-google-api-key")
    try:
        resp = await client.patch(
            "/api/v1/admin/ai-management",
            json={"provider": "google", "model": "gemini-2.5-flash-lite", "temperature": 0.2},
            headers=admin_auth_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["provider"] == "google"
        assert body["model"] == "gemini-2.5-flash-lite"
        assert body["temperature"] == 0.2
        assert settings.model_name == "gemini-2.5-flash-lite"

        audit = await client.get(
            "/api/v1/admin/audit-log?q=platform.ai_model_changed&actor_type=platform_admin",
            headers=admin_auth_headers,
        )
        assert audit.status_code == 200
        assert audit.json()["items"][0]["target_id"] == "gemini-2.5-flash-lite"
    finally:
        ai_config_service.apply_ai_configuration(*previous)


@pytest.mark.asyncio
async def test_ai_model_selection_rejects_provider_without_api_key(client, admin_auth_headers, monkeypatch):
    from src.config import get_settings

    monkeypatch.setattr(get_settings(), "openai_api_key", "")
    resp = await client.patch(
        "/api/v1/admin/ai-management",
        json={"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.7},
        headers=admin_auth_headers,
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_admin_can_view_ai_usage_report(client, admin_auth_headers):
    resp = await client.get("/api/v1/admin/ai-usage?days=7", headers=admin_auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["days"] == 7
    assert len(body["daily"]) == 7
    assert body["totals"]["total_tokens"] == 0
    assert body["models"] == []


@pytest.mark.asyncio
async def test_admin_can_search_audit_log(client, admin_auth_headers, auth_headers):
    users = (await client.get("/api/v1/admin/users", headers=admin_auth_headers)).json()
    user = next(item for item in users if item["email"] == "alice@example.com")
    changed = await client.patch(
        f"/api/v1/admin/users/{user['id']}/status",
        json={"is_active": False},
        headers=admin_auth_headers,
    )
    assert changed.status_code == 200

    resp = await client.get(
        "/api/v1/admin/audit-log?q=user_status_changed&actor_type=platform_admin",
        headers=admin_auth_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    event = body["items"][0]
    assert event["action"] == "platform.user_status_changed"
    assert event["actor_email"] == "admin@example.com"
    assert event["metadata"] == {"is_active": False}


@pytest.mark.asyncio
async def test_audit_log_records_user_activity_without_raw_content(client, admin_auth_headers, auth_headers):
    created = await client.post(
        "/api/v1/tasks",
        json={"title": "Confidential customer follow-up", "priority": "High"},
        headers=auth_headers,
    )
    assert created.status_code == 201

    resp = await client.get(
        "/api/v1/admin/audit-log?q=task.created&actor_type=user",
        headers=admin_auth_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    event = next(item for item in body["items"] if item["target_id"] == created.json()["id"])
    assert event["actor_email"] == "alice@example.com"
    assert event["target_type"] == "task"
    assert event["metadata"] == {"source": "manual", "priority": "High"}
    assert "Confidential customer follow-up" not in str(event)


@pytest.mark.asyncio
async def test_audit_log_records_user_login(client, admin_auth_headers, auth_headers):
    resp = await client.get(
        "/api/v1/admin/audit-log?q=auth.login_succeeded&actor_type=user",
        headers=admin_auth_headers,
    )

    assert resp.status_code == 200
    event = next(item for item in resp.json()["items"] if item["actor_email"] == "alice@example.com")
    assert event["metadata"] == {"method": "password"}


@pytest.mark.asyncio
async def test_non_admin_cannot_access_ai_admin_routes(client, auth_headers):
    for path in ("ai-management", "ai-usage", "audit-log"):
        resp = await client.get(f"/api/v1/admin/{path}", headers=auth_headers)
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_list_users(client, admin_auth_headers, auth_headers):
    resp = await client.get("/api/v1/admin/users", headers=admin_auth_headers)
    assert resp.status_code == 200
    emails = {u["email"] for u in resp.json()}
    assert "admin@example.com" in emails
    assert "alice@example.com" in emails


@pytest.mark.asyncio
async def test_admin_can_promote_and_demote_other_user(client, admin_auth_headers, auth_headers):
    users_resp = await client.get("/api/v1/admin/users", headers=admin_auth_headers)
    alice = next(u for u in users_resp.json() if u["email"] == "alice@example.com")

    resp = await client.patch(
        f"/api/v1/admin/users/{alice['id']}/role", json={"role": "admin"}, headers=admin_auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"

    resp = await client.patch(
        f"/api/v1/admin/users/{alice['id']}/role", json={"role": "user"}, headers=admin_auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "user"


@pytest.mark.asyncio
async def test_admin_cannot_change_own_role(client, admin_auth_headers):
    me = await client.get("/api/v1/auth/me", headers=admin_auth_headers)
    resp = await client.patch(
        f"/api/v1/admin/users/{me.json()['id']}/role", json={"role": "user"}, headers=admin_auth_headers
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_admin_cannot_deactivate_own_account(client, admin_auth_headers):
    me = await client.get("/api/v1/auth/me", headers=admin_auth_headers)
    resp = await client.patch(
        f"/api/v1/admin/users/{me.json()['id']}/status", json={"is_active": False}, headers=admin_auth_headers
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_deactivated_user_loses_access(client, admin_auth_headers, auth_headers):
    users_resp = await client.get("/api/v1/admin/users", headers=admin_auth_headers)
    alice = next(u for u in users_resp.json() if u["email"] == "alice@example.com")

    resp = await client.patch(
        f"/api/v1/admin/users/{alice['id']}/status", json={"is_active": False}, headers=admin_auth_headers
    )
    assert resp.status_code == 200

    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_platform_admin_can_list_view_and_delete_conversations(
    client,
    admin_auth_headers,
    auth_headers,
    other_auth_headers,
):
    bob = (await client.get("/api/v1/auth/me", headers=other_auth_headers)).json()
    workspace = (
        await client.post(
            "/api/v1/workspaces",
            json={"name": "Private Team"},
            headers=auth_headers,
        )
    ).json()
    await client.post(
        f"/api/v1/workspaces/{workspace['id']}/members",
        json={"email": bob["email"], "role": "member"},
        headers=auth_headers,
    )
    conv = (
        await client.post(
            "/api/v1/conversations",
            json={
                "type": "direct",
                "participant_ids": [bob["id"]],
                "workspace_id": workspace["id"],
            },
            headers=auth_headers,
        )
    ).json()
    message = await client.post(
        f"/api/v1/conversations/{conv['id']}/messages",
        json={"content": "admin-visible message"},
        headers=auth_headers,
    )
    assert message.status_code == 200

    resp = await client.get("/api/v1/admin/conversations", headers=admin_auth_headers)
    assert resp.status_code == 200
    listed = next(item for item in resp.json() if item["id"] == conv["id"])
    assert listed["participant_count"] == 2
    assert listed["message_count"] == 1

    resp = await client.get(f"/api/v1/admin/conversations/{conv['id']}/messages", headers=admin_auth_headers)
    assert resp.status_code == 200
    assert resp.json()[0]["content"] == "admin-visible message"

    resp = await client.delete(f"/api/v1/admin/conversations/{conv['id']}", headers=admin_auth_headers)
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/admin/conversations/{conv['id']}/messages", headers=admin_auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_non_admin_cannot_access_new_admin_routes(client, auth_headers):
    for path in ("/api/v1/admin/tasks", "/api/v1/admin/reminders", "/api/v1/admin/memories"):
        resp = await client.get(path, headers=auth_headers)
        assert resp.status_code == 403, path


@pytest.mark.asyncio
async def test_admin_can_list_and_delete_tasks(client, admin_auth_headers, auth_headers):
    alice = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()
    workspace = await _personal_workspace(client, auth_headers)
    created = (
        await client.post("/api/v1/tasks", json={"title": "Admin-visible task"}, headers=auth_headers)
    ).json()

    await _approve_support_scope(
        client, admin_auth_headers, auth_headers, workspace["id"], "personal_data:read"
    )
    resp = await client.get(
        f"/api/v1/admin/tasks?workspace_id={workspace['id']}", headers=admin_auth_headers
    )
    assert resp.status_code == 200
    listed = next(t for t in resp.json() if t["id"] == created["id"])
    assert listed["owner_id"] == alice["id"]
    assert listed["owner_email"] == "alice@example.com"
    assert listed["owner_display_name"] == alice["display_name"]
    assert listed["conversation_label"] is None

    await _approve_support_scope(
        client, admin_auth_headers, auth_headers, workspace["id"], "personal_data:manage"
    )
    resp = await client.delete(
        f"/api/v1/admin/tasks/{created['id']}?workspace_id={workspace['id']}",
        headers=admin_auth_headers,
    )
    assert resp.status_code == 204

    resp = await client.get("/api/v1/tasks", headers=auth_headers)
    assert created["id"] not in [t["id"] for t in resp.json()]


@pytest.mark.asyncio
async def test_admin_tasks_owner_filter(client, admin_auth_headers, auth_headers, other_auth_headers):
    alice = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()
    bob = (await client.get("/api/v1/auth/me", headers=other_auth_headers)).json()
    workspace = (
        await client.post("/api/v1/workspaces", json={"name": "Shared tasks"}, headers=auth_headers)
    ).json()
    await client.post(
        f"/api/v1/workspaces/{workspace['id']}/members",
        json={"email": bob["email"], "role": "member"},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/tasks",
        json={"title": "Alice task", "workspace_id": workspace["id"]},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/tasks",
        json={"title": "Bob task", "workspace_id": workspace["id"]},
        headers=other_auth_headers,
    )
    await _approve_support_scope(
        client, admin_auth_headers, auth_headers, workspace["id"], "personal_data:read"
    )

    resp = await client.get(
        f"/api/v1/admin/tasks?workspace_id={workspace['id']}&owner_id={alice['id']}",
        headers=admin_auth_headers,
    )
    assert resp.status_code == 200
    owners = {t["owner_id"] for t in resp.json()}
    assert owners == {alice["id"]}


@pytest.mark.asyncio
async def test_admin_can_list_and_delete_memories(client, admin_auth_headers, auth_headers):
    alice = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()
    workspace = await _personal_workspace(client, auth_headers)
    created = (
        await client.post(
            "/api/v1/memories", json={"category": "Work", "title": "Admin-visible memory"}, headers=auth_headers
        )
    ).json()

    await _approve_support_scope(
        client, admin_auth_headers, auth_headers, workspace["id"], "personal_data:read"
    )
    resp = await client.get(
        f"/api/v1/admin/memories?workspace_id={workspace['id']}", headers=admin_auth_headers
    )
    assert resp.status_code == 200
    listed = next(m for m in resp.json() if m["id"] == created["id"])
    assert listed["owner_id"] == alice["id"]
    assert listed["owner_email"] == "alice@example.com"

    await _approve_support_scope(
        client, admin_auth_headers, auth_headers, workspace["id"], "personal_data:manage"
    )
    resp = await client.delete(
        f"/api/v1/admin/memories/{created['id']}?workspace_id={workspace['id']}",
        headers=admin_auth_headers,
    )
    assert resp.status_code == 204

    resp = await client.get("/api/v1/memories", headers=auth_headers)
    assert created["id"] not in [m["id"] for m in resp.json()]


@pytest.mark.asyncio
async def test_admin_can_list_and_delete_reminders_and_cancels_scheduler_job(
    client, admin_auth_headers, auth_headers
):
    alice = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()
    workspace = await _personal_workspace(client, auth_headers)
    created = (
        await client.post(
            "/api/v1/reminders",
            json={"title": "Admin-visible reminder", "due_at_iso": "2099-08-10T15:00:00"},
            headers=auth_headers,
        )
    ).json()
    assert scheduler.get_job(created["id"]) is not None

    await _approve_support_scope(
        client, admin_auth_headers, auth_headers, workspace["id"], "personal_data:read"
    )
    resp = await client.get(
        f"/api/v1/admin/reminders?workspace_id={workspace['id']}", headers=admin_auth_headers
    )
    assert resp.status_code == 200
    listed = next(r for r in resp.json() if r["id"] == created["id"])
    assert listed["owner_id"] == alice["id"]
    assert listed["owner_email"] == "alice@example.com"
    assert listed["status"] == "scheduled"

    await _approve_support_scope(
        client, admin_auth_headers, auth_headers, workspace["id"], "personal_data:manage"
    )
    resp = await client.delete(
        f"/api/v1/admin/reminders/{created['id']}?workspace_id={workspace['id']}",
        headers=admin_auth_headers,
    )
    assert resp.status_code == 204

    # Hard-deleted (unlike the user-facing DELETE, which only soft-cancels) and the underlying
    # APScheduler job must actually be gone, not just the DB row.
    assert scheduler.get_job(created["id"]) is None
    resp = await client.get("/api/v1/reminders", headers=auth_headers)
    assert created["id"] not in [r["id"] for r in resp.json()]


@pytest.mark.asyncio
async def test_admin_delete_reminder_404_when_missing(
    client, admin_auth_headers, auth_headers
):
    workspace = await _personal_workspace(client, auth_headers)
    await _approve_support_scope(
        client, admin_auth_headers, auth_headers, workspace["id"], "personal_data:manage"
    )
    resp = await client.delete(
        f"/api/v1/admin/reminders/does-not-exist?workspace_id={workspace['id']}",
        headers=admin_auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_private_data_requires_owner_approved_grant(
    client, admin_auth_headers, auth_headers
):
    workspace = await _personal_workspace(client, auth_headers)
    resp = await client.get(
        f"/api/v1/admin/reminders?workspace_id={workspace['id']}", headers=admin_auth_headers
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Active support access grant required"
