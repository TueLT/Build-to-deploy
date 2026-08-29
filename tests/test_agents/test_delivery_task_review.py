from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

import src.db.session as db_session
from src.db.models import AgentWorkspaceConversation, Conversation, ConversationParticipant, User
from src.services.agent_workspace_service import add_agent_workspace_member
from src.services.workspace_service import add_workspace_member
from tests.test_agent_workspaces import _seed_agent_workspaces


async def _setup_review_flow(client, auth_headers):
    seed = await _seed_agent_workspaces(client, auth_headers)
    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "delivery-review-member@example.com",
            "password": "password123",
            "display_name": "Review Member",
        },
    )
    assert registered.status_code == 201
    async with db_session.async_session_maker() as db:
        lead = await db.get(User, seed["delivery_user_id"])
        member = await db.scalar(select(User).where(User.email == "delivery-review-member@example.com"))
        await add_workspace_member(db, seed["organization_id"], member.id, "member", lead.id)
        await add_agent_workspace_member(db, seed["delivery_id"], member.id, "member")
        group = Conversation(
            workspace_id=seed["organization_id"],
            type="group",
            name="Review Flow",
            created_by=lead.id,
            ai_enabled=True,
            ai_policy_version=1,
        )
        db.add(group)
        await db.flush()
        db.add_all(
            [
                AgentWorkspaceConversation(
                    agent_workspace_id=seed["delivery_id"],
                    conversation_id=group.id,
                    classification="delivery",
                    linked_by_user_id=lead.id,
                ),
                ConversationParticipant(
                    conversation_id=group.id,
                    principal_kind="workspace_user",
                    user_id=lead.id,
                    resource_role="manager",
                    invited_by_user_id=lead.id,
                ),
                ConversationParticipant(
                    conversation_id=group.id,
                    principal_kind="workspace_user",
                    user_id=member.id,
                    resource_role="participant",
                    invited_by_user_id=lead.id,
                ),
            ]
        )
        await db.commit()
    lead_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "delivery@example.com", "password": "password123"},
    )
    member_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "delivery-review-member@example.com", "password": "password123"},
    )
    return {
        **seed,
        "group_id": group.id,
        "member_id": member.id,
        "lead_headers": {"Authorization": f"Bearer {lead_login.json()['access_token']}"},
        "member_headers": {"Authorization": f"Bearer {member_login.json()['access_token']}"},
    }


@pytest.mark.asyncio
async def test_delivery_review_required_task_runs_auditable_closed_loop(client, auth_headers):
    seed = await _setup_review_flow(client, auth_headers)
    root = (
        f"/api/v1/workspaces/{seed['organization_id']}"
        f"/agent-workspaces/{seed['delivery_id']}/delivery"
    )
    created = await client.post(
        f"{root}/tasks",
        headers=seed["lead_headers"],
        json={
            "source_conversation_id": seed["group_id"],
            "owner_id": seed["member_id"],
            "title": "Submit OAuth pull request evidence",
            "due_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "priority": "High",
            "requires_review": True,
        },
    )
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["status"] == "pending"
    assert task["requires_review"] is True

    direct_complete = await client.patch(
        f"/api/v1/tasks/{task['id']}/status",
        headers=seed["member_headers"],
        json={"status": "completed", "expected_row_version": task["row_version"]},
    )
    assert direct_complete.status_code == 409

    submitted = await client.post(
        f"/api/v1/tasks/{task['id']}/submission",
        headers=seed["member_headers"],
        json={
            "submission_note": "OAuth callback and rollback tests are green.",
            "evidence_urls": ["https://github.example/pull/42"],
            "expected_row_version": task["row_version"],
        },
    )
    assert submitted.status_code == 200, submitted.text
    first_submission = submitted.json()
    assert first_submission["status"] == "submitted"

    governed_delete = await client.delete(
        f"/api/v1/tasks/{task['id']}",
        headers=seed["member_headers"],
    )
    assert governed_delete.status_code == 409

    queue = await client.get(f"{root}/task-reviews", headers=seed["lead_headers"])
    assert queue.status_code == 200, queue.text
    assert [item["id"] for item in queue.json()] == [task["id"]]

    rejected = await client.patch(
        f"{root}/tasks/{task['id']}/review",
        headers=seed["lead_headers"],
        json={
            "decision": "changes_requested",
            "review_note": "Add security scan evidence.",
            "expected_row_version": first_submission["row_version"],
        },
    )
    assert rejected.status_code == 200, rejected.text
    changes = rejected.json()
    assert changes["status"] == "changes_requested"
    assert changes["review_note"] == "Add security scan evidence."

    restarted = await client.patch(
        f"/api/v1/tasks/{task['id']}/status",
        headers=seed["member_headers"],
        json={"status": "in_progress", "expected_row_version": changes["row_version"]},
    )
    assert restarted.status_code == 200, restarted.text
    resubmitted = await client.post(
        f"/api/v1/tasks/{task['id']}/submission",
        headers=seed["member_headers"],
        json={
            "submission_note": "Added security scan and rollback proof.",
            "evidence_urls": [
                "https://github.example/pull/42",
                "https://security.example/scans/42",
            ],
            "expected_row_version": restarted.json()["row_version"],
        },
    )
    assert resubmitted.status_code == 200, resubmitted.text
    accepted = await client.patch(
        f"{root}/tasks/{task['id']}/review",
        headers=seed["lead_headers"],
        json={
            "decision": "accepted",
            "review_note": "Evidence verified.",
            "expected_row_version": resubmitted.json()["row_version"],
        },
    )
    assert accepted.status_code == 200, accepted.text
    completed = accepted.json()
    assert completed["status"] == "completed"
    assert completed["completed_at"] is not None
    assert completed["reviewed_by_user_id"] == seed["delivery_user_id"]


@pytest.mark.asyncio
async def test_member_cannot_create_team_task_or_review_submission(client, auth_headers):
    seed = await _setup_review_flow(client, auth_headers)
    root = (
        f"/api/v1/workspaces/{seed['organization_id']}"
        f"/agent-workspaces/{seed['delivery_id']}/delivery"
    )
    denied_create = await client.post(
        f"{root}/tasks",
        headers=seed["member_headers"],
        json={
            "source_conversation_id": seed["group_id"],
            "owner_id": seed["member_id"],
            "title": "Unauthorized assignment",
        },
    )
    assert denied_create.status_code == 403
    denied_queue = await client.get(f"{root}/task-reviews", headers=seed["member_headers"])
    assert denied_queue.status_code == 403
