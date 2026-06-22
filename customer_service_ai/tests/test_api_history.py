import pytest

from app.memory.session_store import session_store


@pytest.mark.asyncio
async def test_list_sessions_empty(client):
    resp = await client.get("/history/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_nonexistent_session(client):
    resp = await client.get("/history/nonexistent_session")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_session(client):
    resp = await client.delete("/history/nonexistent_session")
    assert resp.status_code == 404
