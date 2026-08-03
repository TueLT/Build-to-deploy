from langchain_core.tools import tool
from langgraph.types import interrupt

from src.services import calendar_service


@tool
async def create_calendar_event(
    summary: str,
    start_iso: str,
    end_iso: str,
    description: str = "",
    attendees: list[str] | None = None,
) -> str:
    """Draft a Google Calendar event. Requires the user's explicit confirmation before it is
    actually created.

    Args:
        summary: Event title.
        start_iso: Event start time as an ISO 8601 datetime string.
        end_iso: Event end time as an ISO 8601 datetime string.
        description: Optional event details.
        attendees: Optional list of attendee email addresses.
    """
    draft = {
        "summary": summary,
        "start": start_iso,
        "end": end_iso,
        "description": description,
        "attendees": attendees or [],
    }
    decision = interrupt({"type": "calendar_event", "draft": draft})
    if not decision or not decision.get("approved"):
        return "Calendar event was not created (user declined)."

    draft.update(decision.get("edits") or {})
    created = calendar_service.create_event(
        summary=draft["summary"],
        start_iso=draft["start"],
        end_iso=draft["end"],
        description=draft["description"],
        attendees=draft["attendees"],
    )
    return f"Event created: {created.get('htmlLink', created.get('id'))}"


@tool
async def list_calendar_events(time_min_iso: str, time_max_iso: str, max_results: int = 10) -> str:
    """List existing calendar events in a time range. Read-only, no confirmation needed.

    Args:
        time_min_iso: Start of the range as an ISO 8601 datetime string.
        time_max_iso: End of the range as an ISO 8601 datetime string.
        max_results: Maximum number of events to return.
    """
    items = calendar_service.list_events(time_min_iso, time_max_iso, max_results)
    if not items:
        return "No events found in that range."
    return "\n".join(f"- {e.get('summary')} ({e['start'].get('dateTime', e['start'].get('date'))})" for e in items)
