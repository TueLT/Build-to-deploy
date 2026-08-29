# Product Delivery Agent — Workspace Runtime Boundary Checkpoint 10

> Trạng thái: **complete / verified** trong phạm vi tách implementation của Workspace Delivery
> Agent. Đây không phải tuyên bố rằng toàn bộ Delivery Agent đã production-ready.

## Phạm vi và kết quả

Đã khắc phục phần còn thiếu sau Checkpoint 09: Delivery có graph riêng nhưng còn dùng
`AgentState` và output guardrail node của Personal Agent. Workspace Delivery hiện sở hữu đầy đủ
runtime agentic của chính nó:

- State tối thiểu riêng cho một Delivery turn; không kế thừa hoặc alias state Personal Agent.
- Input guardrail và output guardrail riêng; không gọi semantic classifier hay node guardrail của
  Personal Agent.
- Delivery graph riêng, planner riêng và registry chỉ gồm `get_delivery_snapshot` server-bound.
- Kiểm thử kiến trúc chặn bốn dependency Personal Agent: global graph, `AgentState`, planner node
  và guardrail node.

Provider LLM, primitive phát hiện injection/secret leakage, contracts và policy/router API vẫn là
hạ tầng nền tảng dùng chung. Chúng không mang tool, memory, state hoặc capability của Personal
Agent vào Delivery runtime.

## Artifact thay đổi

- `src/agents/profiles/workspace_delivery_state.py`
- `src/agents/profiles/workspace_delivery_guardrails.py`
- `src/agents/profiles/workspace_delivery_graph.py`
- `tests/test_agents/test_workspace_delivery_graph.py`
- `docs/ROLE_B_PRODUCT_DELIVERY_AGENT_7_DAY_PLAN.md` — thêm mục 15.1 về boundary bắt buộc.
- `docs/ROLE_B_IMPLEMENTATION_CHECKPOINT_09.md` — làm rõ giới hạn cũ và liên kết checkpoint này.

## Hành vi đã xác nhận

1. Request vẫn đi qua API policy/context/resource guard trước khi graph Delivery được tạo.
2. Trước LLM, Delivery guardrail chặn prompt injection, yêu cầu lộ prompt/bí mật và unsafe request.
   Từ vựng Delivery không bị đẩy sang classifier của Personal Agent.
3. LLM chỉ có một tool không nhận ID/scope: đọc snapshot đã được server authorize. Nó không thể gọi
   Personal memory, calendar, reminder hoặc toàn bộ `ALL_TOOLS`.
4. Sau LLM, Delivery output guardrail riêng chặn prompt/secret leakage; source validator vẫn thay
   câu trả lời thiếu `Nguồn:` khi snapshot có source.

## Kiểm thử và lỗi phát hiện

Đã chạy lại sau khi tách module:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_agents\test_workspace_delivery_graph.py tests\test_agents\test_delivery_api.py tests\test_agents\test_product_delivery.py tests\test_agents\test_delivery_scope.py -q
.\.venv\Scripts\python.exe -m ruff check src\agents\profiles\workspace_delivery_state.py src\agents\profiles\workspace_delivery_guardrails.py src\agents\profiles\workspace_delivery_graph.py tests\test_agents\test_workspace_delivery_graph.py
git diff --check
```

Kết quả pytest: **31 passed**. Lần chạy đầu, test output guardrail dùng câu không khớp policy leak
hiện hành nên không bị chặn; đây là lỗi `test_fixture`, không phải nới policy. Đã dùng mẫu leak thật
`The system prompt is: ...`, sau đó toàn bộ 31 test xanh. Ruff và `git diff --check` cũng xanh.

## Plan-alignment review

| Plan task/capability | Trạng thái thực | Evidence | Phạm vi còn thiếu / gate |
|---|---|---|---|
| §15, B9 — Delivery LangGraph và tool registry riêng | complete | Three runtime modules + dependency-boundary test | Không có action tool trong MVP |
| §15, B10 — guardrail/source validation khi API gọi graph | complete trong scope unit/API | `test_workspace_delivery_graph.py`, `test_delivery_api.py` | Feature flag vẫn off cho tới integration/E2E |
| §15, B11 — injection/hallucination/source evaluation | partial | Injection, no-tool và citation tests xanh | Cần revoke/live DB E2E và eval dataset trước release |
| §15, B12 — UI conversational, latency/token evidence, rollback | partial | Runbook đã có từ CP09 | Cần smoke production-like và observability thật |

## Giới hạn và bước tiếp theo

Không mở action executor, không durable HITL, không bật feature flag và không coi fixture/unit test là
production authorization proof. Bước tiếp theo là B11 integration/E2E: consent revoked hoặc unlink
giữa run, authorization với DB thật, theo dõi latency/token và smoke theo runbook; owner là Role B
phối hợp owner shared-platform của các gate A-DLV.
