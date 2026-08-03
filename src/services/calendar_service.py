from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src.config import get_settings

_SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    settings = get_settings()
    creds = Credentials.from_authorized_user_file(settings.google_token_path, _SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(settings.google_token_path, "w") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def list_events(time_min_iso: str, time_max_iso: str, max_results: int = 50) -> list[dict]:
    settings = get_settings()
    service = get_calendar_service()
    resp = (
        service.events()
        .list(
            calendarId=settings.google_calendar_id,
            timeMin=time_min_iso,
            timeMax=time_max_iso,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return resp.get("items", [])


def create_event(
    summary: str, start_iso: str, end_iso: str, description: str = "", attendees: list[str] | None = None
) -> dict:
    settings = get_settings()
    service = get_calendar_service()
    body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_iso, "timeZone": settings.calendar_timezone},
        "end": {"dateTime": end_iso, "timeZone": settings.calendar_timezone},
        "attendees": [{"email": a} for a in (attendees or [])],
    }
    return service.events().insert(calendarId=settings.google_calendar_id, body=body).execute()
