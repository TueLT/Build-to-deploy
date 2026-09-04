from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.agents.tools import summarize_tool


@pytest.mark.asyncio
async def test_summarize_conversation_reads_context_from_state(monkeypatch):
    fake_llm = AsyncMock()
    fake_llm.ainvoke.return_value = AsyncMock(content="A short summary.")
    monkeypatch.setattr(summarize_tool, "get_llm", lambda: fake_llm)

    state = {"context": "Alice: hi\nBob: let's meet tomorrow"}
    result = await summarize_tool.summarize_conversation.coroutine(style="brief", state=state)

    assert result == "A short summary."
    fake_llm.ainvoke.assert_awaited_once()
    prompt = fake_llm.ainvoke.await_args.args[0]
    assert "Alice: hi" in prompt
    assert "brief" in prompt


@pytest.mark.asyncio
async def test_summarize_conversation_no_context(monkeypatch):
    fake_llm = AsyncMock()
    monkeypatch.setattr(summarize_tool, "get_llm", lambda: fake_llm)

    result = await summarize_tool.summarize_conversation.coroutine(style="brief", state={})

    assert "No conversation text" in result
    fake_llm.ainvoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_summarize_conversation_preserves_numbered_point_count(monkeypatch):
    fake_llm = AsyncMock()
    fake_llm.ainvoke.return_value = AsyncMock(content="1. One\n2. Two\n3. Three")
    monkeypatch.setattr(summarize_tool, "get_llm", lambda: fake_llm)
    state = {
        "context": "Linh: Gate is at risk.\nMai: Evidence is incomplete.",
        "messages": [HumanMessage(content="Tóm tắt cuộc hội thoại này thành 3 ý và đánh số.")],
    }

    await summarize_tool.summarize_conversation.coroutine(style="brief", state=state)

    prompt = fake_llm.ainvoke.await_args.args[0]
    assert "numbered list" in prompt
    assert "exactly 3 distinct items" in prompt
    assert "markers 1., 2., 3." in prompt


@pytest.mark.asyncio
async def test_summarize_conversation_recovers_format_from_follow_up(monkeypatch):
    fake_llm = AsyncMock()
    fake_llm.ainvoke.return_value = AsyncMock(content="1. One\n2. Two\n3. Three")
    monkeypatch.setattr(summarize_tool, "get_llm", lambda: fake_llm)
    state = {
        "context": "Linh: Gate is at risk.\nMai: Evidence is incomplete.",
        "messages": [
            HumanMessage(content="Tóm tắt thành 3 ý."),
            AIMessage(content="A paragraph summary."),
            HumanMessage(content="Đánh số ở phần tóm tắt trước đi."),
        ],
    }

    await summarize_tool.summarize_conversation.coroutine(style="brief", state=state)

    prompt = fake_llm.ainvoke.await_args.args[0]
    assert "numbered list" in prompt
    assert "exactly 3 distinct items" in prompt


def test_state_hidden_from_llm_tool_schema():
    assert list(summarize_tool.summarize_conversation.args.keys()) == ["style", "point_count"]
