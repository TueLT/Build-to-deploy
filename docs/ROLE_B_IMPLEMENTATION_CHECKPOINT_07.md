# Product Delivery Agent — Implementation Checkpoint 07

> Ngày cập nhật: 2026-08-22
>
> Trạng thái: **complete / verified trong phạm vi B3 read-only runtime boundary** — đã hoàn tất phần có thể triển khai an toàn của nửa đầu plan (B1–B3), không coi đây là API/model/production completion.
>
> Tiền đề: [Checkpoint 06](ROLE_B_IMPLEMENTATION_CHECKPOINT_06.md)
>
> Protocol áp dụng: [Checkpoint Completion Protocol](ROLE_B_CHECKPOINT_COMPLETION_PROTOCOL.md)

## 1. Phạm vi và quyết định

Checkpoint này hoàn tất đoạn còn thiếu của B3 theo kiến trúc tool-first:

```text
router → trusted AgentContext → prepared invocation
       → server-resolved DeliveryReadScope → explicit read-only tool binding
```

Không có model, global `ALL_TOOLS`, endpoint, publish/store hay action executor trong đường đi này. Giữ các phần đó ngoài scope là chủ ý: chúng còn phụ thuộc các gate persistence/API và không được mô phỏng như production.

## 2. Artifact và hành vi đã triển khai

| Artifact | Hành vi hoàn tất |
|---|---|
| `src/services/delivery_workspace_service.py` | Thêm `resolve_delivery_read_scope`. Lead không chọn group nhận workspace overview từ đúng allowlist; lead chọn một ID phải qua resource revalidation rồi mới được `GROUP` scope; member chỉ nhận `MEMBER`/My Work và bị chặn nếu cố chọn group snapshot. |
| `src/agents/profiles/product_delivery_runner.py` | Thêm `resolve_prepared_delivery_read_scope`, composition server-side gọi `enforce_agent_workspace_access` trước, rồi `enforce_agent_resource_access` cho selected ID. ID từ UI/model không trở thành query predicate trực tiếp. |
| `src/agents/profiles/product_delivery_executor.py` | Thêm `ProductDeliveryReadOnlyExecutor`. Chỉ nhận binding tường minh của năm read tool Delivery; reject Quality, proposal/action, tool không nằm trong prepared allowlist, scope/context bị tráo và binding thiếu. Executor revalidate workspace trước khi gọi tool. |
| `tests/test_agents/test_delivery_scope.py` | Regression cho selected-group capability và member selector denial. |
| `tests/test_agents/test_product_delivery_runner.py` | Regression xác nhận composition gọi workspace guard rồi resource guard cho selected group. |
| `tests/test_agents/test_product_delivery_executor.py` | Regression cho explicit binding, no-action execution, context mismatch và Quality/action binding rejection. |
| `ROLE_B_PRODUCT_DELIVERY_IMPLEMENTATION_READINESS.md` | Cập nhật chính xác trạng thái B1–B3, A-DLV-03 và A-DLV-07. |

## 3. Kiểm thử và bằng chứng

```powershell
# Checkpoint-specific runtime/scope tests
.\.venv\Scripts\python.exe -m pytest tests\test_agents\test_product_delivery_runner.py tests\test_agents\test_product_delivery_executor.py tests\test_agents\test_delivery_scope.py -q

# Full Role B regression, tách workspace integration để lấy exit result rõ ràng
.\.venv\Scripts\python.exe -m pytest tests\test_agents\test_contracts.py tests\test_agents\test_router.py tests\test_agents\test_product_delivery.py tests\test_agents\test_product_delivery_runner.py tests\test_agents\test_product_delivery_executor.py tests\test_agents\test_delivery_scope.py tests\test_agents\test_delivery_tools.py tests\test_agents\test_delivery_messages.py tests\test_agents\test_delivery_brief.py tests\test_agents\test_delivery_milestones_people.py tests\test_multi_agent_dataset.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_agent_workspaces.py::test_specialist_scope_allows_own_workspace_and_denies_other_workspace tests\test_agent_workspaces.py::test_executive_gets_aggregate_scope_but_not_specialist_scope tests\test_agent_workspaces.py::test_organization_owner_is_not_implicitly_a_specialist tests\test_agent_workspaces.py::test_revoked_agent_workspace_membership_is_effective_on_next_resolution tests\test_agent_workspaces.py::test_revoked_organization_membership_blocks_agent_workspace_immediately tests\test_agent_workspaces.py::test_context_builder_uses_db_role_and_feature_flags tests\test_agent_workspaces.py::test_context_builder_fails_closed_when_profile_flag_is_disabled -q
.\.venv\Scripts\python.exe -m pytest tests\test_agent_workspaces.py::test_workspace_configuration_api_is_platform_admin_only tests\test_agent_workspaces.py::test_platform_admin_assigns_one_lead_and_explicitly_enrolls_membership tests\test_agent_workspaces.py::test_conversation_mapping_enters_scope_only_with_active_group_consent tests\test_agent_workspaces.py::test_member_scope_excludes_linked_group_when_the_member_is_not_an_active_participant tests\test_agent_workspaces.py::test_delivery_scope_rejects_wrong_classification_even_if_mapping_is_inserted_outside_api tests\test_agent_workspaces.py::test_agent_workspace_membership_revoke_api_takes_effect_immediately -q

.\.venv\Scripts\python.exe scripts\generate_multi_agent_dataset.py --check
.\.venv\Scripts\python.exe scripts\validate_multi_agent_dataset.py
.\.venv\Scripts\python.exe -m ruff check src\agents\contracts.py src\agents\router.py src\agents\context_builder.py src\agents\policies src\agents\profiles src\agents\schemas\delivery.py src\services\delivery_workspace_service.py src\agents\tools\delivery_tasks.py src\agents\tools\delivery_messages.py src\agents\tools\delivery_brief.py src\agents\tools\delivery_milestones.py src\agents\tools\delivery_people.py tests\test_agents\test_contracts.py tests\test_agents\test_router.py tests\test_agents\test_product_delivery.py tests\test_agents\test_product_delivery_runner.py tests\test_agents\test_product_delivery_executor.py tests\test_agents\test_delivery_scope.py tests\test_agents\test_delivery_tools.py tests\test_agents\test_delivery_messages.py tests\test_agents\test_delivery_brief.py tests\test_agents\test_delivery_milestones_people.py tests\test_agent_workspaces.py tests\test_multi_agent_dataset.py
git diff --check
```

Kết quả final verification:

- checkpoint-specific: **13 passed**;
- Role B regression: **69 + 7 + 6 = 82 passed**;
- dataset canonical: **150 cases / 10 categories** hợp lệ;
- Ruff và `git diff --check`: passed.

## 4. Failure phát hiện và xử lý

Lần chạy đầu của test composition báo `NameError` vì test mới thiếu import `PreparedProductDeliveryInvocation`; Ruff đồng thời báo import order. Phân loại: `test_fixture/static hygiene`.

- Đã thêm import đúng và để Ruff sắp xếp import.
- Chạy lại checkpoint-specific suite: 13 passed.
- Chạy lại toàn bộ Role B regression, dataset, Ruff và diff integrity như mục 3: xanh.

Không có P0/P1 đã biết trong scope checkpoint. Không nới policy, không đổi expected fixture và không bypass guard để làm test xanh.

## 5. Plan-alignment review

| Plan task/capability/gate | Trạng thái thực | Evidence | Phạm vi còn thiếu / gate |
|---|---|---|---|
| B1 — schema/profile/rules | `complete` trong phạm vi fixture/contract | Checkpoint 01–02, domain tests | Không thay thế E2E production evidence |
| B2 — scoped read tools | `partial` | Read-only fixture tools + guard contracts | Real task/milestone/decision stores chờ A-DLV-01/02/08/09 |
| B3-01 — profile runtime | `complete` trong phạm vi read-only composition | runner + executor + 13 checkpoint tests | Chưa có model loop/API/audit |
| B3-02 — bind Delivery tools theo allowlist | `complete` trong phạm vi executor contract | `ProductDeliveryReadOnlyExecutor`; Quality/action/global tools bị reject | Chưa wire concrete DB tool objects vào shared runtime |
| B3-03 — DeliveryBrief candidate | `complete` trong phạm vi pure producer | `delivery_brief.py`, golden/brief tests | Chưa persistence/publication |
| A-DLV-03 | `partial` | router → context → scope → explicit read binding | Public API/model adapter và early-denial audit còn thiếu |
| A-DLV-06 | `complete` | participant intersection + integration tests | Không thay thế selected-group API |
| A-DLV-07 | `partial` | selected ID revalidated server-side; member selector deny | Capability-list/API, ambiguous-name resolver và DB-backed selector evidence còn thiếu |
| A-DLV-01/02/04/05/08/09 | `blocked` | Readiness document | Shared DB binding, stores, durable HITL/publish chưa có |

Kết luận: **đã xử lý xong nửa đầu plan B1–B3 theo đúng ranh giới an toàn hiện có**. Đây không phải tuyên bố Product Delivery Agent production-ready: feature flags vẫn phải tắt và không có endpoint/model/action nào được mở.

## 6. Phần tiếp theo sau mốc một nửa

1. A cung cấp A-DLV-01/02/04/08/09 để nối DB source, persistent brief và decision semantics; A-DLV-03 cần API/audit adapter.
2. B triển khai B4 UI fixture-first: overview/group/My Work state, citation, disabled actions; chỉ nối HITL khi A-DLV-05 xanh.
3. Chỉ sau đó mới chạy B5–B7: live evaluator/security, real integration/performance, evidence/release. `MULTI_AGENT_ENABLED` và `PRODUCT_DELIVERY_AGENT_ENABLED` tiếp tục `false` đến B6 gate.
