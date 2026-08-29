# Product Delivery Agent — Agentic Runtime Checkpoint 09

> Trạng thái: **complete / verified trong phạm vi agentic Delivery MVP**.

> Cập nhật kiến trúc: báo cáo này ghi nhận runtime MVP đã được wire và kiểm thử tại thời điểm
> checkpoint 09. Tuy nhiên, runtime khi đó vẫn dùng `AgentState` và output guardrail node chung
> của Personal Agent. Biên giới module độc lập đầy đủ được hoàn tất và xác nhận tại
> [Checkpoint 10](ROLE_B_IMPLEMENTATION_CHECKPOINT_10.md); không dùng checkpoint 09 để kết luận
> rằng hai agent đã tách implementation hoàn toàn.

## Hoàn tất

- Delivery LangGraph riêng, không dùng Personal Agent graph hoặc `ALL_TOOLS`.
- LLM bắt buộc gọi một tool `get_delivery_snapshot` server-bound; không có scope/resource/tool action input từ model.
- Delivery-specific input guardrail chặn injection/secret trước LLM; output guardrail chạy sau LLM.
- Source validator thay câu trả lời factual thiếu `Nguồn:` bằng phản hồi an toàn.
- Delivery API đã wire graph, fail-safe về brief validated + `DELIVERY_AGENT_RUNTIME_FAILED` khi runtime LLM lỗi.
- UI hiển thị prose LLM và brief/source structured; runbook enable/rollback tại [ROLE_B_DELIVERY_AGENTIC_RUNBOOK.md](ROLE_B_DELIVERY_AGENTIC_RUNBOOK.md).

## Evidence

`pytest tests/test_agents/test_workspace_delivery_graph.py tests/test_agents/test_delivery_api.py tests/test_agents/test_product_delivery.py tests/test_agents/test_delivery_scope.py -q`: **29 passed**. Ruff, `git diff --check` và `npm --prefix Frontend/user run build` passed.

## Known limits

Không bật action: durable HITL, typed decision store, persistent Executive brief handoff và live production latency/token evidence vẫn là shared-platform work. Feature flags mặc định vẫn tắt; runbook quy định bật demo sau migration/smoke test.
