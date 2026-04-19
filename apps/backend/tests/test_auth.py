import pytest

from tests.conftest import TEST_PASSWORD


@pytest.mark.asyncio
async def test_status_unauthenticated(anon_client):
    res = await anon_client.get("/auth/status")
    assert res.status_code == 200
    assert res.json() == {"authenticated": False}


@pytest.mark.asyncio
async def test_login_success_sets_cookie(anon_client):
    res = await anon_client.post("/auth/login", json={"password": TEST_PASSWORD})
    assert res.status_code == 200
    assert res.json() == {"ok": True}
    assert "fineas_session" in res.cookies

    status = await anon_client.get("/auth/status")
    assert status.json() == {"authenticated": True}


@pytest.mark.asyncio
async def test_login_wrong_password(anon_client):
    res = await anon_client.post("/auth/login", json={"password": "not-the-password"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_logout_clears_session(anon_client):
    await anon_client.post("/auth/login", json={"password": TEST_PASSWORD})
    assert (await anon_client.get("/auth/status")).json()["authenticated"] is True

    res = await anon_client.post("/auth/logout")
    assert res.status_code == 204

    status = await anon_client.get("/auth/status")
    assert status.json()["authenticated"] is False


@pytest.mark.asyncio
async def test_logout_requires_auth(anon_client):
    res = await anon_client.post("/auth/logout")
    assert res.status_code == 401
