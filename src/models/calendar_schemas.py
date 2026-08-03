from pydantic import BaseModel, Field


class CalendarEventOut(BaseModel):
    id: str
    title: str
    start: str
    end: str | None
    url: str | None


class CalendarEventCreateRequest(BaseModel):
    summary: str = Field(..., min_length=1, max_length=200)
    start_iso: str
    end_iso: str
    description: str = ""
    attendees: list[str] | None = None
