# Product Delivery Agent — Implementation Checkpoint 05

> Ngày cập nhật: 2026-08-22
>
> Trạng thái: **complete / verified trong phạm vi router compatibility và runtime preparation** — đã port các policy core tương thích từ router của Tuấn, nhưng chưa wire Delivery vào global graph/API hay bật feature flag.
>
> Tiền đề: [Checkpoint 04](ROLE_B_IMPLEMENTATION_CHECKPOINT_04.md)
>
> Protocol áp dụng: [Checkpoint Completion Protocol](ROLE_B_CHECKPOINT_COMPLETION_PROTOCOL.md)

## 1. Mục tiêu và quyết định tích hợp

`origin/develop` có router runtime của Tuấn, nhưng endpoint của nó gọi `delivery_tool.py` với Delivery schema/service khác Role B. Port nguyên endpoint sẽ làm mất strict source/scope/freshness contract đã kiểm thử ở Checkpoint 01–04.

Quyết định được thực hiện: **giữ Role B làm Delivery source of truth**, chỉ port phần router/policy dùng chung tương thích và thêm adapter chuẩn bị invocation. Không import endpoint hoặc `delivery_tool.py` không tương thích; không thay đổi `ALL_TOOLS`; không bật `MULTI_AGENT_ENABLED` hay `PRODUCT_DELIVERY_AGENT_ENABLED`.

## 2. Artifact và hành vi đã triển khai

| Artifact | Hành vi đã hoàn tất |
|---|---|
| `src/agents/policies/scope_resolver.py` | Với Lead: scope là toàn bộ linked, AI-enabled group. Với Member: scope là intersection với `ConversationParticipant` active (`revoked_at`/`hidden_at` đều null). Không có participant thì trả allowlist rỗng, không tiết lộ group khác. |
| `src/agents/policies/resource_guard.py` | Thêm `enforce_agent_workspace_access`: revalidate live scope, yêu cầu workspace ID đúng với trusted context, chặn workspace ID do tool/model thay thế. |
| `src/agents/router.py` | Làm rõ router chỉ chọn profile deterministic từ workspace server-side; scope client không phải grant và context/resource guard vẫn bắt buộc. |
| `src/agents/profiles/product_delivery_runner.py` | Thêm `prepare_product_delivery_invocation`: intent Delivery được server cố định, gọi theo thứ tự router → context builder → prompt/profile allowlist; sai profile dừng trước context/model preparation. Kết quả là immutable prepared invocation, chưa phải executable agent. |
| `tests/test_agent_workspaces.py` | Integration test xác nhận member không là active participant có scope rỗng; workspace guard cho workspace đúng pass và ID workspace khác bị `DENY_WRONG_WORKSPACE`. |
| `tests/test_agents/test_product_delivery_runner.py` | Test thứ tự router trước context và chặn Quality route trước context/model preparation. |
| `ROLE_B_PRODUCT_DELIVERY_IMPLEMENTATION_READINESS.md` | Cập nhật A-DLV-03 là `partial`, A-DLV-06 là implemented; các gate runtime/persistence còn lại giữ blocked. |

## 3. Kiểm thử và bằng chứng

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_agents\test_contracts.py tests\test_agents\test_router.py tests\test_agents\test_product_delivery.py tests\test_agents\test_product_delivery_runner.py tests\test_agents\test_delivery_scope.py tests\test_agents\test_delivery_tools.py tests\test_agents\test_delivery_messages.py tests\test_agents\test_delivery_brief.py tests\test_agents\test_delivery_milestones_people.py tests\test_agent_workspaces.py tests\test_multi_agent_dataset.py -q
.\.venv\Scripts\python.exe scripts\generate_multi_agent_dataset.py --check
.\.venv\Scripts\python.exe scripts\validate_multi_agent_dataset.py
.\.venv\Scripts\python.exe -m ruff check src\agents\contracts.py src\agents\router.py src\agents\context_builder.py src\agents\policies src\agents\profiles src\agents\schemas\delivery.py src\services\delivery_workspace_service.py src\agents\tools\delivery_tasks.py src\agents\tools\delivery_messages.py src\agents\tools\delivery_brief.py src\agents\tools\delivery_milestones.py src\agents\tools\delivery_people.py tests\test_agents\test_contracts.py tests\test_agents\test_router.py tests\test_agents\test_product_delivery.py tests\test_agents\test_product_delivery_runner.py tests\test_agents\test_delivery_scope.py tests\test_agents\test_delivery_tools.py tests\test_agents\test_delivery_messages.py tests\test_agents\test_delivery_brief.py tests\test_agents\test_delivery_milestones_people.py tests\test_agent_workspaces.py tests\test_multi_agent_dataset.py
git diff --check
```

Kết quả final verification: **74 tests passed**; dataset canonical hợp lệ 150 case/10 category; Ruff và `git diff --check` passed.

## 4. Test failure và xử lý bug

Không có test failure trong final suite.

Ruff đã phát hiện một import `RequestedScope` không dùng trong runner mới. Import được bỏ, rồi toàn bộ lint/regression suite chạy lại xanh. Đây là lỗi static hygiene, không phải bypass quyền hay lỗi nghiệp vụ. Không có bug P0/P1 đã biết trong scope checkpoint.

## 5. Plan-alignment review

| Plan task/capability/gate | Trạng thái thực | Evidence | Phạm vi còn thiếu / gate |
|---|---|---|---|
| B3-01 | `partial` | `prepare_product_delivery_invocation`, runner tests | Đã có handler preparation, chưa có model/tool executor thật |
| B3-02 | `partial` | Router trả profile-owned allowlist; runner preserve immutable allowlist | Global graph vẫn bind `ALL_TOOLS`; chưa có adapter bind tool object chỉ theo Delivery allowlist |
| B4-01 | `blocked` | Không port endpoint không tương thích của Tuấn | Cần API invocation adapter dùng strict Role B DTO/tool contracts |
| A-DLV-03 | `partial` | Router → context → allowlist order test; wrong profile dừng sớm | Public executor/audit endpoint trước model/tool chưa tồn tại |
| A-DLV-06 | `complete` | Active `ConversationParticipant` intersection + integration test | Selected-group resolution vẫn là gate khác |
| A-DLV-07 | `blocked` | Không có capability API/selected-group resolver | Cần server-filtered selector/API trước group snapshot runtime |
| A-DLV-01/02/04/08/09 | `blocked` | Readiness document | DB source/persistence/decision semantics vẫn cần platform contracts |

Kết luận: checkpoint đưa router policy tiến gần runtime mà không đổi source of truth hoặc hạ chuẩn an toàn Role B. Nó **không** chứng minh Delivery Agent đã chạy qua `/chat`, đã gọi LLM/tool, hay đã production-ready.

## 6. Bước kế tiếp

1. Thiết kế/implement shared executor chỉ nhận `PreparedProductDeliveryInvocation`, bind Delivery tool objects theo allowlist và revalidate scope trước từng read; không dùng `ALL_TOOLS`.
2. Sau khi A-DLV-07 có selected-group resolver và A-DLV-01/02/09 có source DB đúng nghĩa, nối executor vào API để có read-only demo.
3. Khi A-DLV-04 có persistent brief store, thêm API/UI stale/partial behavior và typed handoff cho Executive.
4. Feature flags vẫn off cho đến khi checkpoint integration/E2E tương ứng pass theo [Completion Protocol](ROLE_B_CHECKPOINT_COMPLETION_PROTOCOL.md).
