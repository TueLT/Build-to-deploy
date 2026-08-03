from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import User, Workspace, WorkspaceMembership


async def get_personal_workspace(db: AsyncSession, user_id: str) -> Workspace | None:
    return (
        await db.execute(
            select(Workspace).where(
                Workspace.type == "personal",
                Workspace.personal_owner_user_id == user_id,
                Workspace.status == "active",
            )
        )
    ).scalar_one_or_none()


async def create_personal_workspace(db: AsyncSession, user: User) -> Workspace:
    existing = await get_personal_workspace(db, user.id)
    if existing is not None:
        return existing

    workspace = Workspace(
        type="personal",
        name=f"{user.display_name}'s Workspace",
        personal_owner_user_id=user.id,
    )
    db.add(workspace)
    await db.flush()
    return workspace


async def create_organization_workspace(db: AsyncSession, name: str, owner_user_id: str) -> Workspace:
    owner = await db.get(User, owner_user_id)
    if owner is None or not owner.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active workspace owner not found")
    workspace = Workspace(type="organization", name=name.strip())
    db.add(workspace)
    await db.flush()
    db.add(
        WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=owner_user_id,
            role="owner",
            status="active",
            invited_by_user_id=owner_user_id,
        )
    )
    await db.flush()
    return workspace


async def require_active_owner_after_change(
    db: AsyncSession,
    workspace_id: str,
    excluded_membership_id: str | None = None,
) -> None:
    stmt = select(func.count(WorkspaceMembership.id)).where(
        WorkspaceMembership.workspace_id == workspace_id,
        WorkspaceMembership.role == "owner",
        WorkspaceMembership.status == "active",
    )
    if excluded_membership_id is not None:
        stmt = stmt.where(WorkspaceMembership.id != excluded_membership_id)
    owner_count = (await db.execute(stmt)).scalar_one()
    if owner_count < 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization workspace must retain at least one active owner",
        )


async def update_membership_role(
    db: AsyncSession,
    membership_id: str,
    new_role: str,
) -> WorkspaceMembership:
    membership = await db.get(WorkspaceMembership, membership_id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace membership not found")
    if membership.role == "owner" and new_role != "owner":
        await require_active_owner_after_change(db, membership.workspace_id, membership.id)
    membership.role = new_role
    membership.updated_at = datetime.now(UTC)
    await db.flush()
    return membership


async def add_workspace_member(
    db: AsyncSession,
    workspace_id: str,
    user_id: str,
    role: str,
    invited_by_user_id: str | None,
) -> WorkspaceMembership:
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if workspace.type != "organization":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Personal workspaces cannot have memberships",
        )
    membership = WorkspaceMembership(
        workspace_id=workspace.id,
        user_id=user_id,
        role=role,
        status="active",
        invited_by_user_id=invited_by_user_id,
    )
    db.add(membership)
    await db.flush()
    return membership


async def list_user_workspaces(db: AsyncSession, user_id: str) -> list[Workspace]:
    result = await db.execute(
        select(Workspace)
        .outerjoin(
            WorkspaceMembership,
            and_(
                WorkspaceMembership.workspace_id == Workspace.id,
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.status == "active",
            ),
        )
        .where(
            Workspace.status == "active",
            or_(
                and_(Workspace.type == "personal", Workspace.personal_owner_user_id == user_id),
                and_(Workspace.type == "organization", WorkspaceMembership.id.is_not(None)),
            ),
        )
        .order_by(Workspace.created_at.asc())
    )
    return list(result.scalars().all())
