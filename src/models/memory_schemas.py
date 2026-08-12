from datetime import datetime

from pydantic import BaseModel, Field


class MemoryOut(BaseModel):
    id: str
    workspace_id: str
    category: str
    title: str
    detail: str
    created_at: datetime
    updated_at: datetime


class MemoryCreateRequest(BaseModel):
    workspace_id: str | None = None
    category: str = Field(..., min_length=1, max_length=40)
    title: str = Field(..., min_length=1, max_length=200)
    detail: str = Field(default="", max_length=10000)


class MemoryUpdateRequest(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=40)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    detail: str | None = Field(default=None, max_length=10000)
