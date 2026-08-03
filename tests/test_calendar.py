import pytest

from src.services import calendar_service


@pytest.mark.asyncio
async def test_list_events_requires_auth(client):
    resp = await client.get("/api/v1/calendar/events")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_events_maps_google_events(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        calendar_service,
        "list_events",
        lambda time_min, time_max, max_results=50: [
            {
                "id": "evt-1",
                "summary": "Team sync",
                "start": {"dateTime": "2026-08-10T10:00:00+07:00"},
                "end": {"dateTime": "2026-08-10T10:30:00+07:00"},
                "htmlLink": "https://calendar.google.com/event?eid=evt-1",
            }
        ],
    )

    resp = await client.get("/api/v1/calendar/events", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == "evt-1"
    assert body[0]["title"] == "Team sync"
    assert body[0]["start"] == "2026-08-10T10:00:00+07:00"
    assert body[0]["url"] == "https://calendar.google.com/event?eid=evt-1"


@pytest.mark.asyncio
async def test_list_events_upstream_error_returns_502(client, auth_headers, monkeypatch):
    def _boom(time_min, time_max, max_results=50):
        raise RuntimeError("token expired")

    monkeypatch.setattr(calendar_service, "list_events", _boom)

    resp = await client.get("/api/v1/calendar/events", headers=auth_headers)
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_create_event(client, auth_headers, monkeypatch):
    captured = {}

    def _fake_create(summary, start_iso, end_iso, description="", attendees=None):
        captured.update(
            summary=summary, start_iso=start_iso, end_iso=end_iso, description=description, attendees=attendees
        )
        return {
            "id": "evt-2",
            "summary": summary,
            "start": {"dateTime": start_iso},
            "end": {"dateTime": end_iso},
            "htmlLink": "https://calendar.google.com/event?eid=evt-2",
        }

    monkeypatch.setattr(calendar_service, "create_event", _fake_create)

    resp = await client.post(
        "/api/v1/calendar/events",
        json={"summary": "Design sync", "start_iso": "2026-08-11T09:00:00+07:00", "end_iso": "2026-08-11T09:30:00+07:00"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == "evt-2"
    assert body["title"] == "Design sync"
    assert captured["summary"] == "Design sync"
