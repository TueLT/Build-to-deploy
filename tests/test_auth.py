import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "password123", "display_name": "New User"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["display_name"] == "New User"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "password123", "display_name": "Dup"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_admin_bootstrap_creates_admin_without_user_registration(client, monkeypatch):
    from src.api import auth_routes

    monkeypatch.setattr(
        auth_routes,
        "get_settings",
        lambda: type("Settings", (), {"admin_bootstrap_key": "test-bootstrap-key"})(),
    )
    resp = await client.post(
        "/api/v1/auth/admin/register",
        json={
            "email": "first-admin@example.com",
            "password": "password123",
            "display_name": "First Admin",
            "bootstrap_key": "test-bootstrap-key",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "admin"

    normal_signup = await client.post(
        "/api/v1/auth/register",
        json={"email": "normal@example.com", "password": "password123", "display_name": "Normal"},
    )
    assert normal_signup.status_code == 201
    assert normal_signup.json()["user"]["role"] == "user"


@pytest.mark.asyncio
async def test_admin_bootstrap_rejects_wrong_key(client, monkeypatch):
    from src.api import auth_routes

    monkeypatch.setattr(
        auth_routes,
        "get_settings",
        lambda: type("Settings", (), {"admin_bootstrap_key": "test-bootstrap-key"})(),
    )
    resp = await client.post(
        "/api/v1/auth/admin/register",
        json={
            "email": "not-admin@example.com",
            "password": "password123",
            "display_name": "Not Admin",
            "bootstrap_key": "wrong-key",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_login_success(client):
    payload = {"email": "login@example.com", "password": "password123", "display_name": "Login"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    payload = {"email": "wrong@example.com", "password": "password123", "display_name": "Wrong"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/login", json={"email": payload["email"], "password": "nope"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_login_rejects_normal_user(client, auth_headers):
    resp = await client.post(
        "/api/v1/auth/admin/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_me_requires_token(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_with_token(client, auth_headers):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"
