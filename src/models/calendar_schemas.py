from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class CalendarEventOut(BaseModel):
    id: str
    title: str
    start: str
    end: str | None
    url: str | None


class CalendarEventCreateRequest(BaseModel):
    workspace_id: str
    summary: str = Field(..., min_length=1, max_length=200)
    start_iso: datetime
    end_iso: datetime
    description: str = Field(default="", max_length=5000)
    attendees: list[EmailStr] | None = None

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_iso <= self.start_iso:
            raise ValueError("end_iso must be later than start_iso")
        return self


class CalendarEventUpdateRequest(BaseModel):
    summary: str | None = Field(default=None, min_length=1, max_length=200)
    start_iso: datetime | None = None
    end_iso: datetime | None = None
    description: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def validate_range(self):
        if self.start_iso is not None and self.end_iso is not None and self.end_iso <= self.start_iso:
            raise ValueError("end_iso must be later than start_iso")
        return self
