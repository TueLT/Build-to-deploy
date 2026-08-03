from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrganizationWorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Workspace name cannot be blank")
        return normalized


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: Literal["personal", "organization"]
    name: str
    slug: str | None
    personal_owner_user_id: str | None
    status: Literal["active", "suspended", "deleting"]
    created_at: datetime
    updated_at: datetime
