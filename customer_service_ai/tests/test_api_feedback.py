import pytest


@pytest.mark.asyncio
async def test_submit_feedback(client):
    resp = await client.post("/feedback/", json={
        "session_id": "test_session",
        "question": "你好",
        "answer": "你好！",
        "feedback": "like",
        "comment": "不错",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["message"] == "反馈已记录"
    assert data["id"] > 0


@pytest.mark.asyncio
async def test_submit_feedback_invalid_type(client):
    resp = await client.post("/feedback/", json={
        "session_id": "test",
        "question": "q",
        "answer": "a",
        "feedback": "invalid",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_feedback_missing_required(client):
    resp = await client.post("/feedback/", json={
        "session_id": "test",
    })
    assert resp.status_code == 422
