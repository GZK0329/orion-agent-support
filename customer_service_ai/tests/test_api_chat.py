import pytest

API = "/chat/"


@pytest.mark.asyncio
async def test_chat_empty_question(client):
    resp = await client.post(API, json={"question": "", "session_id": "test_empty"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_chat_question_too_long(client):
    resp = await client.post(API, json={
        "question": "x" * 2001,
        "session_id": "test_long",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_chat_missing_question(client):
    resp = await client.post(API, json={"session_id": "test_missing"})
    assert resp.status_code == 422
