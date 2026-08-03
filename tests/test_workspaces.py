import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from src.db import session as db_session
from src.db.models import Workspace, WorkspaceMembership
from src.services import workspace_service


@pytest.mark.asyncio
async def test_register_creates_exactly_one_personal_workspace(client):
    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "workspace-owner@example.com",
            "password": "password123",
            "display_name": "Workspace Owner",
        },
    )
    assert registered.status_code == 200
    payload = registered.json()
    headers = {"Authorization": f"Bearer {payload['access_token']}"}

    response = await client.get("/api/v1/workspaces", headers=headers)

    assert response.status_code == 200
    workspaces = response.json()
    assert len(workspaces) == 1
    assert workspaces[0]["type"] == "personal"
    assert workspaces[0]["personal_owner_user_id"] == payload["user"]["id"]


@pytest.mark.asyncio
async def test_organization_workspace_is_listed_for_its_owner(client):
    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "organization-owner@example.com",
            "password": "password123",
            "display_name": "Organization Owner",
        },
    )
    payload = registered.json()

    async with db_session.async_session_maker() as db:
        organization = await workspace_service.create_organization_workspace(
            db,
            name="Orbit Engineering",
            owner_user_id=payload["user"]["id"],
        )
        await db.commit()
        organization_id = organization.id

    headers = {"Authorization": f"Bearer {payload['access_token']}"}
    response = await client.get("/api/v1/workspaces", headers=headers)

    assert response.status_code == 200
    workspaces = response.json()
    assert len(workspaces) == 2
    assert workspaces[0]["type"] == "personal"
    assert workspaces[1]["id"] == organization_id
    assert workspaces[1]["type"] == "organization"
    assert workspaces[1]["name"] == "Orbit Engineering"


@pytest.mark.asyncio
async def test_last_owner_cannot_be_demoted(client):
    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "last-owner@example.com",
            "password": "password123",
            "display_name": "Last Owner",
        },
    )
    owner_id = registered.json()["user"]["id"]

    async with db_session.async_session_maker() as db:
        organization = await workspace_service.create_organization_workspace(
            db,
            name="Owner Invariant",
            owner_user_id=owner_id,
        )
        await db.commit()
        membership = (
            await db.execute(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == organization.id,
                    WorkspaceMembership.user_id == owner_id,
                )
            )
        ).scalar_one()

        with pytest.raises(HTTPException) as exc_info:
            await workspace_service.update_membership_role(db, membership.id, "admin")

        assert exc_info.value.status_code == 409
        await db.refresh(membership)
        assert membership.role == "owner"


@pytest.mark.asyncio
async def test_personal_workspace_rejects_membership(client):
    owner = await client.post(
        "/api/v1/auth/register",
        json={"email": "personal-owner@example.com", "password": "password123", "display_name": "Personal Owner"},
    )
    other = await client.post(
        "/api/v1/auth/register",
        json={"email": "other-member@example.com", "password": "password123", "display_name": "Other Member"},
    )
    owner_payload = owner.json()
    headers = {"Authorization": f"Bearer {owner_payload['access_token']}"}
    personal_workspace = (await client.get("/api/v1/workspaces", headers=headers)).json()[0]

    async with db_session.async_session_maker() as db:
        with pytest.raises(HTTPException) as exc_info:
            await workspace_service.add_workspace_member(
                db,
                workspace_id=personal_workspace["id"],
                user_id=other.json()["user"]["id"],
                role="member",
                invited_by_user_id=owner_payload["user"]["id"],
            )

        assert exc_info.value.status_code == 409
        memberships = (
            await db.execute(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == personal_workspace["id"]
                )
            )
        ).scalars().all()
        assert memberships == []


@pytest.mark.asyncio
async def test_organization_workspace_requires_active_owner(client):
    async with db_session.async_session_maker() as db:
        with pytest.raises(HTTPException) as exc_info:
            await workspace_service.create_organization_workspace(
                db,
                name="Invalid Organization",
                owner_user_id="missing-user-id",
            )

        assert exc_info.value.status_code == 404
        organization_count = (
            await db.execute(select(func.count()).select_from(Workspace))
        ).scalar_one()
        assert organization_count == 0


@pytest.mark.asyncio
async def test_user_can_create_organization_workspace(client):
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": "workspace-creator@example.com", "password": "password123", "display_name": "Creator"},
    )
    payload = registered.json()
    headers = {"Authorization": f"Bearer {payload['access_token']}"}

    response = await client.post(
        "/api/v1/workspaces",
        json={"name": "Product Team"},
        headers=headers,
    )

    assert response.status_code == 201
    organization = response.json()
    assert organization["type"] == "organization"
    assert organization["name"] == "Product Team"
    async with db_session.async_session_maker() as db:
        membership = (
            await db.execute(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == organization["id"],
                    WorkspaceMembership.user_id == payload["user"]["id"],
                )
            )
        ).scalar_one()
        assert membership.role == "owner"
        assert membership.status == "active"
