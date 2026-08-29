# Product Delivery Agent — Implementation Checkpoint 06

> Ngày cập nhật: 2026-08-22
>
> Trạng thái: **complete / verified trong phạm vi router core hardening** — đã đóng hai lỗ hổng consent/classification phát hiện trong review Checkpoint 05. Chưa có executor/API Delivery.
>
> Tiền đề: [Checkpoint 05](ROLE_B_IMPLEMENTATION_CHECKPOINT_05.md)
>
> Protocol áp dụng: [Checkpoint Completion Protocol](ROLE_B_CHECKPOINT_COMPLETION_PROTOCOL.md)

## 1. Phạm vi checkpoint

Review router sau Checkpoint 05 phát hiện hai điểm không đủ chuẩn production:

1. Workspace guard revalidate membership/workspace nhưng chưa so sánh `consent_scope_hash`; revoke group AI consent giữa turn có thể không được phát hiện với workspace-level read.
2. Scope resolver chỉ dựa vào Agent Workspace mapping mà chưa filter `classification`; policy không nên chỉ tin validation của API khi dữ liệu DB có thể được ghi từ migration/admin/integration khác.

Checkpoint này sửa đúng hai root cause trên, không mở rộng sang model executor hay API endpoint..

## 2. Artifact và hành vi đã triển khai

| Artifact | Hành vi đã hoàn tất |
|---|---|
| `src/agents/policies/resource_guard.py` | `enforce_agent_workspace_access` nay so sánh live `consent_scope_hash` với trusted context sau revalidation. Hash đổi trả `DENY_CONSENT_CHANGED`, giống per-resource guard. |
| `src/agents/policies/scope_resolver.py` | Resolver nhận classification kỳ vọng theo profile: Product Delivery chỉ `delivery`, Quality Assurance chỉ `quality`; vẫn áp dụng member active-participant intersection. |
| `tests/test_agent_workspaces.py` | Regression test xác nhận workspace guard chặn consent revoked; test direct DB insertion mapping `quality` vào Delivery workspace vẫn cho Delivery allowlist rỗng. |

## 3. Kiểm thử và bằng chứng

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_agents\test_contracts.py tests\test_agents\test_router.py tests\test_agents\test_product_delivery.py tests\test_agents\test_product_delivery_runner.py tests\test_agents\test_delivery_scope.py tests\test_agents\test_delivery_tools.py tests\test_agents\test_delivery_messages.py tests\test_agents\test_delivery_brief.py tests\test_agents\test_delivery_milestones_people.py tests\test_agent_workspaces.py tests\test_multi_agent_dataset.py -q
.\.venv\Scripts\python.exe scripts\generate_multi_agent_dataset.py --check
.\.venv\Scripts\python.exe scripts\validate_multi_agent_dataset.py
.\.venv\Scripts\python.exe -m ruff check src\agents\contracts.py src\agents\router.py src\agents\context_builder.py src\agents\policies src\agents\profiles src\agents\schemas\delivery.py src\services\delivery_workspace_service.py src\agents\tools\delivery_tasks.py src\agents\tools\delivery_messages.py src\agents\tools\delivery_brief.py src\agents\tools\delivery_milestones.py src\agents\tools\delivery_people.py tests\test_agents\test_contracts.py tests\test_agents\test_router.py tests\test_agents\test_product_delivery.py tests\test_agents\test_product_delivery_runner.py tests\test_agents\test_delivery_scope.py tests\test_agents\test_delivery_tools.py tests\test_agents\test_delivery_messages.py tests\test_agents\test_delivery_brief.py tests\test_agents\test_delivery_milestones_people.py tests\test_agent_workspaces.py tests\test_multi_agent_dataset.py
git diff --check
```

Kết quả: **75 tests passed**; canonical dataset hợp lệ với 150 case/10 category; Ruff và `git diff --check` passed.

## 4. Test failure và xử lý bug

Không có test failure trong final suite. Hai lỗi ở mục 1 là review findings, đã được chuyển thành regression tests trước khi xác nhận checkpoint:

- `consent` revoke làm workspace guard deny thay vì cho workspace read tiếp tục;
- mapping sai classification bị policy query loại bỏ thay vì dựa vào API validation.

Không có bypass quyền hoặc thay đổi fixture expected để làm test xanh.

## 5. Plan-alignment review

| Plan task/capability/gate | Trạng thái thực | Evidence | Phạm vi còn thiếu / gate |
|---|---|---|---|
| B3-01 | `partial` | Prepared Delivery invocation từ Checkpoint 05 | Chưa có executor/model invocation |
| B3-02 | `partial` | Router/profile allowlist + guard revalidation | Global graph vẫn chưa bind Delivery tool objects theo allowlist |
| A-DLV-03 | `partial` | Router/context preparation và live workspace consent recheck | API/executor/audit path trước model/tool còn thiếu |
| A-DLV-06 | `complete` | Member participant intersection, classification filter, revoke regression tests | Không có selected-group capability ở scope này |
| A-DLV-07 | `blocked` | Chưa có server-filtered selected-group resolver/API | Cần trước group snapshot runtime/demo |
| A-DLV-01/02/04/08/09 | `blocked` | Readiness document | DB source, durable brief/decision semantics vẫn chưa có |

Kết luận: router core hiện đúng logic hơn cho Delivery policy: profile/classification, membership/participant và consent snapshot đều được kiểm tra tại boundary. Checkpoint không được diễn giải là Delivery Agent runtime/API production complete.

## 6. Bước kế tiếp

1. Thiết kế executor read-only chỉ nhận `PreparedProductDeliveryInvocation`, thực thi duy nhất tool object trong Delivery allowlist và gọi resource/workspace guard trước mọi read.
2. Chỉ nối endpoint sau khi executor không dùng `ALL_TOOLS` và selected-group resolver A-DLV-07 sẵn sàng.
3. Sau source DB/persistent store gate, nối real read → brief → stale/partial API/UI demo; feature flags tiếp tục off đến E2E checkpoint.
