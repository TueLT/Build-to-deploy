import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.agents.nodes.personal_plan_node import personal_plan_node


@pytest.mark.asyncio
async def test_calendar_write_asks_for_missing_action_slots():
    result = await personal_plan_node(
        {
            "messages": [HumanMessage(content="Đặt lịch họp với team")],
            "personal_intent": "calendar",
        }
    )

    assert result["action_requires_clarification"] is True
    assert result["personal_plan"]["status"] == "needs_clarification"
    assert result["personal_plan"]["missing_fields"] == ["ngày", "giờ bắt đầu", "thời lượng"]
    assert "messages" not in result


@pytest.mark.asyncio
async def test_fully_specified_calendar_write_is_ready_for_tools():
    result = await personal_plan_node(
        {
            "messages": [HumanMessage(content="Đặt lịch họp ngày mai lúc 10:00 trong 30 phút")],
            "personal_intent": "calendar",
        }
    )

    assert result["action_requires_clarification"] is False
    assert result["personal_plan"]["status"] == "ready"
    assert result["personal_plan"]["max_tool_calls"] == 8


@pytest.mark.asyncio
async def test_reminder_write_asks_for_date_and_time():
    result = await personal_plan_node(
        {
            "messages": [HumanMessage(content="Nhắc tôi gửi báo cáo")],
            "personal_intent": "reminder",
        }
    )

    assert result["action_requires_clarification"] is True
    assert result["personal_plan"]["missing_fields"] == ["ngày cần nhắc", "giờ cần nhắc"]


@pytest.mark.asyncio
async def test_short_answer_after_clarification_continues_existing_plan():
    result = await personal_plan_node(
        {
            "messages": [
                HumanMessage(content="Đặt lịch họp"),
                AIMessage(content="Sếp muốn họp vào lúc nào?"),
                HumanMessage(content="10 giờ sáng mai, 30 phút"),
            ],
            "personal_intent": "calendar",
        }
    )

    assert result["action_requires_clarification"] is False


@pytest.mark.asyncio
async def test_repeated_action_command_is_not_mistaken_for_slot_filling():
    result = await personal_plan_node(
        {
            "messages": [
                HumanMessage(content="Đặt lịch họp với team"),
                AIMessage(content="Bạn muốn họp vào ngày nào, lúc mấy giờ và trong bao lâu?"),
                HumanMessage(content="Đặt lịch họp với team"),
            ],
            "personal_intent": "calendar",
        }
    )

    assert result["action_requires_clarification"] is True
    assert result["personal_plan"]["missing_fields"] == ["ngày", "giờ bắt đầu", "thời lượng"]


@pytest.mark.asyncio
async def test_task_calendar_plan_contains_multiple_grounded_steps():
    result = await personal_plan_node(
        {
            "messages": [HumanMessage(content="Lên kế hoạch task và lịch tuần này")],
            "personal_intent": "task_management",
        }
    )

    assert len(result["personal_plan"]["steps"]) >= 4
    assert "Đối chiếu với Google Calendar" in result["personal_plan"]["steps"]
