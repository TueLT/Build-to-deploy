# Product Delivery Agent — Implementation Checkpoint 03

> Ngày cập nhật: 2026-08-22
>
> Trạng thái: **complete / verified trong phạm vi fixture-safe của checkpoint** — đã có milestone fallback và people resolver với allowlist tối thiểu; chưa có structured source, DB repository, runtime binding hay release.
>
> Tiền đề: [Checkpoint 02](ROLE_B_IMPLEMENTATION_CHECKPOINT_02.md)
>
> Protocol áp dụng: [Checkpoint Completion Protocol](ROLE_B_CHECKPOINT_COMPLETION_PROTOCOL.md)

## 1. Phạm vi checkpoint

Checkpoint này hoàn thiện phần còn lại của ngày 2 ở ranh giới an toàn:

1. Không có nguồn milestone đã được phê duyệt thì Agent phải báo thiếu dữ liệu, không trích xuất/bịa milestone từ chat.
2. Chỉ resolve người được server allowlist, trả đúng projection tối thiểu cần cho Delivery (`user_id`, `display_name`).
3. Bổ sung regression test cho evidence từ QA/private conversation ngoài scope và guessed person ID.

Checkpoint **không** triển khai repository thật, migration, registry/planner/API/UI. Vì vậy đây không phải là trạng thái hoàn thành PR-B2, Day 2 hay Delivery Agent production..

## 2. Artifact và hành vi đã triển khai

| Artifact | Hành vi đã hoàn tất |
|---|---|
| `src/agents/tools/delivery_milestones.py` | `get_delivery_milestones` xây `DeliveryQueryScope`, revalidate từng group đã được scope trước khi trả kết quả. Khi structured milestone source chưa tồn tại, tool trả `PARTIAL`, danh sách rỗng và `MILESTONE_SOURCE_NOT_AVAILABLE`; không tạo milestone suy đoán từ message. |
| `src/agents/schemas/delivery.py` | Thêm `DeliveryPerson` strict/minimal và `allowed_person_ids` vào immutable `DeliveryReadScope`. |
| `src/services/delivery_workspace_service.py` | Propagate `person_ids` vào `DeliveryQueryScope`; repository sau này phải bind predicate cho group/task/decision/person thay vì mở rộng query. |
| `src/agents/tools/delivery_people.py` | `get_delivery_people` kiểm tra ID unique và là subset của server allowlist **trước** khi gọi repository; revalidate group, chuẩn hoá outage thành lỗi an toàn, từ chối repository trả person ngoài requested allowlist, và chỉ serialize hai field tối thiểu. |
| `tests/test_agents/test_delivery_milestones_people.py` | Test fallback milestone, minimal people projection và từ chối guessed/extra user ID trước repository call. |
| `tests/test_agents/test_delivery_messages.py` | Regression test parameterized chặn evidence từ `group-qa` và `direct-private-lead` khi chúng không thuộc effective group scope. |

## 3. Kiểm thử và bằng chứng

Sau khi implementation hoàn tất, các lệnh sau đã chạy xanh:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_agents\test_product_delivery.py tests\test_agents\test_delivery_scope.py tests\test_agents\test_delivery_tools.py tests\test_agents\test_delivery_messages.py tests\test_agents\test_delivery_brief.py tests\test_agents\test_delivery_milestones_people.py tests\test_multi_agent_dataset.py -q
.\.venv\Scripts\python.exe scripts\generate_multi_agent_dataset.py --check
.\.venv\Scripts\python.exe scripts\validate_multi_agent_dataset.py
.\.venv\Scripts\python.exe -m ruff check src\agents\schemas\delivery.py src\services\delivery_workspace_service.py src\agents\profiles\product_delivery.py src\agents\tools\delivery_tasks.py src\agents\tools\delivery_messages.py src\agents\tools\delivery_brief.py src\agents\tools\delivery_milestones.py src\agents\tools\delivery_people.py tests\test_agents\test_product_delivery.py tests\test_agents\test_delivery_scope.py tests\test_agents\test_delivery_tools.py tests\test_agents\test_delivery_messages.py tests\test_agents\test_delivery_brief.py tests\test_agents\test_delivery_milestones_people.py tests\test_multi_agent_dataset.py
git diff --check
```

Kết quả tại lần kiểm thử đầy đủ ban đầu: **42 tests passed**; dataset canonical hợp lệ với 150 case/10 category; Ruff và `git diff --check` passed. Sau khi bổ sung regression case cho private conversation, toàn bộ final verification được chạy lại: **43 tests passed**, dataset vẫn hợp lệ, Ruff và `git diff --check` tiếp tục passed.

## 4. Test failure và xử lý bug

Không có failure trong bộ kiểm thử đã chạy cho checkpoint này.

Ruff ban đầu phát hiện một lỗi sắp xếp import trong `delivery_milestones.py`; đây là violation static check, không phải lỗi nghiệp vụ/runtime. Import đã được formatter chuẩn hoá, sau đó toàn bộ Ruff check và integrity check đã pass. Không có bug P0/P1 đã biết trong fixture scope này.

## 5. Plan-alignment review

| Plan task/capability/gate | Trạng thái thực | Evidence | Phạm vi còn thiếu / gate |
|---|---|---|---|
| B2-01 | `complete` | `DeliveryQueryScope` tiếp tục bind `person_ids`; Checkpoint 01 | Chưa có DB query thật |
| B2-02, B2-03 | `partial` | Task/message fixture adapters và scope tests từ Checkpoint 01 | Chờ A-DLV-01/06/07/09 để dùng source/repository thật |
| B2-04 / DLV-C04 | `partial` | `get_delivery_milestones` revalidate + `PARTIAL` data-gap test | Chờ A-DLV-02 cung cấp milestone/release/dependency source bền vững; chưa có milestone retrieval thật |
| B2-05 / DLV-C05 | `partial` | `DeliveryPerson`, allowlist boundary, `get_delivery_people` và tests | Chờ A-DLV-01/09 cho server-derived assignee relation và DB repository thật |
| B2-06 | `complete` trong fixture security scope | QA/private evidence deny, guessed-ID deny, source-scope tests | Chưa chứng minh authorization/revoke trên DB/API runtime thật |
| A-DLV-01/02/06/07/09 | `blocked` | [Readiness](ROLE_B_PRODUCT_DELIVERY_IMPLEMENTATION_READINESS.md) và checkpoint evidence | Shared platform owner A |
| A-DLV-03/04 | `blocked` | Không wire registry/planner hoặc persistent brief store | Shared platform owner A; feature flags vẫn off |

Kết luận đối chiếu: checkpoint đáp ứng đúng hướng **fail-safe tool contract** của B2-04/B2-05 và security regression của B2-06. Các task chỉ được ghi `partial` khi vẫn cần dữ liệu/platform thật; không mock/bypass để diễn giải là production complete.

## 6. Giới hạn và bước kế tiếp

1. Owner A cần hoàn tất A-DLV-01/02/06/07/09 để B thay fixture adapter bằng repository có join/binding server-side và revoke-aware.
2. Khi structured source đã có, B thay milestone fallback bằng query chỉ lấy milestone/release/dependency thuộc `DeliveryQueryScope`, bổ sung stale-source test và provenance test.
3. Sau A-DLV-03, B triển khai profile runner/tool allowlist; sau A-DLV-04 mới publish `WorkspaceBrief` persistent. Feature flag chỉ xét bật sau integration/E2E tương ứng.
4. Checkpoint kế tiếp phải tiếp tục theo [Completion Protocol](ROLE_B_CHECKPOINT_COMPLETION_PROTOCOL.md): test, xử lý failure (nếu có), plan-alignment review, rồi mới báo cáo trạng thái.
