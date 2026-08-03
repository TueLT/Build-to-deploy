from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.db.models import User
from src.db.session import get_db
from src.models.workspace_schemas import OrganizationWorkspaceCreate, WorkspaceOut
from src.services.workspace_service import create_organization_workspace, list_user_workspaces

router = APIRouter()


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: OrganizationWorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceOut:
    workspace = await create_organization_workspace(db, request.name, current_user.id)
    await db.commit()
    await db.refresh(workspace)
    return WorkspaceOut.model_validate(workspace)


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WorkspaceOut]:
    workspaces = await list_user_workspaces(db, current_user.id)
    return [WorkspaceOut.model_validate(workspace) for workspace in workspaces]
