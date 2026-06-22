import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.memory.session_store import session_store


@pytest.mark.asyncio
async def test_add_and_get_messages():
    session_id = "test_session_1"
    await session_store.add_messages(
        session_id,
        [HumanMessage(content="你好"), AIMessage(content="你好！有什么可以帮你的？")],
        client_id="user1",
    )
    history = await session_store.get_history(session_id)
    assert len(history) == 2
    assert history[0].content == "你好"
    assert history[1].content == "你好！有什么可以帮你的？"

    await session_store.delete_session(session_id)


@pytest.mark.asyncio
async def test_truncate_by_tokens():
    messages = [
        HumanMessage(content="短消息1"),
        AIMessage(content="短消息2"),
        HumanMessage(content="这是一条非常长的消息" * 200),
    ]
    truncated = session_store._truncate_by_tokens(messages, max_tokens=100)
    assert len(truncated) < 3
    assert len(truncated) >= 1


@pytest.mark.asyncio
async def test_list_sessions():
    sid = "test_session_list"
    await session_store.add_messages(
        sid,
        [HumanMessage(content="测试列表"), AIMessage(content="回答")],
        client_id="user1",
    )
    sessions = await session_store.list_sessions(client_id="user1")
    assert len(sessions) >= 1
    found = [s for s in sessions if s["session_id"] == sid]
    assert len(found) == 1
    assert found[0]["message_count"] == 2

    await session_store.delete_session(sid)


@pytest.mark.asyncio
async def test_add_and_list_feedback():
    fid = await session_store.add_feedback(
        session_id="test_fb",
        question="怎么创建作业？",
        answer="请使用 POST /api/job/create",
        feedback="like",
        comment="很准确",
    )
    assert fid > 0
    feedbacks = await session_store.list_feedback()
    assert any(f["question"] == "怎么创建作业？" for f in feedbacks)


@pytest.mark.asyncio
async def test_add_error_log():
    eid = await session_store.add_error_log(
        session_id="test_error",
        client_id="user1",
        question="测试错误",
        error_message="LLM timeout",
        source="test",
    )
    assert eid > 0
    logs = await session_store.list_error_logs()
    assert any(e["error_message"] == "LLM timeout" for e in logs)


@pytest.mark.asyncio
async def test_delete_session():
    sid = "test_delete_me"
    await session_store.add_messages(
        sid, [HumanMessage(content="删除我")], client_id="user1"
    )
    deleted = await session_store.delete_session(sid)
    assert deleted is True
    deleted_again = await session_store.delete_session(sid)
    assert deleted_again is False


@pytest.mark.asyncio
async def test_update_title():
    sid = "test_title"
    await session_store.add_messages(
        sid, [HumanMessage(content="原标题"), AIMessage(content="回答")], client_id="user1"
    )
    await session_store.update_title(sid, "新标题")
    sessions = await session_store.list_sessions(client_id="user1")
    found = [s for s in sessions if s["session_id"] == sid]
    assert found[0]["title"] == "新标题"

    await session_store.delete_session(sid)
