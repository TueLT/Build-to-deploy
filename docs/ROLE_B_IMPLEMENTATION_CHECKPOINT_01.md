# Product Delivery Agent — Implementation Checkpoint 01

> Ngày cập nhật: 2026-08-22
>
> Trạng thái: **PR-B1 hoàn tất; PR-B2 fixture-safe boundary hoàn tất; chưa production-integrated.**
>
> Plan nguồn: [ROLE_B_PRODUCT_DELIVERY_AGENT_7_DAY_PLAN.md](ROLE_B_PRODUCT_DELIVERY_AGENT_7_DAY_PLAN.md)

## 1. Mục tiêu checkpoint

Checkpoint này hoàn thành phần có thể triển khai độc lập mà không vượt shared-platform policy:

1. Khóa Delivery domain contract, business rules và profile prompt.
2. Chuyển 15 golden `delivery_summary` case thành ma trận capability có thể review.
3. Tạo read boundary/tool adapter fixture-first để chứng minh scope không bị mở rộng.
4. Không wire tool vào runtime, không query DB thật, không bật feature flag khi A-DLV gates chưa hoàn tất.

## 2. Đã triển khai

### 2.1 Delivery domain schema và rule thuần

File: `src/agents/schemas/delivery.py`

- `DeliveryItem`, `DeliveryDependency`, `DeliveryRecommendation` và `DeliveryBriefPayload` đều strict (`extra=forbid`) và immutable.
- DTO mới dùng `assignee_id`; `Task.owner_id` cũ không được dùng như role/quyền truy cập.
- `DeliveryViewScope` phân biệt `workspace`, `group`, `member`.
- Group snapshot bắt buộc có đúng một `conversation_id`; workspace/member view không được tự gắn một conversation.
- Tất cả fact quan trọng bắt buộc có `SourceReference` cùng Delivery Agent Workspace.
- Headline/recommendation phải trỏ tới source đã có trong fact trả về.
- Brief không có fact chỉ hợp lệ khi có `data_gaps`; không được bịa source để làm qua validation.
- `release_readiness` bị reject vì đây là trường của Quality, không thuộc Delivery.

### 2.2 Business rule Delivery

File: `src/agents/schemas/delivery.py`

| Rule | Cách triển khai |
|---|---|
| Overdue | Item non-terminal có `due_at < generated_at` |
| Due soon | Item non-terminal có deadline trong 7 ngày từ thời điểm sinh brief |
| Blocked | Phải là state explicit và có `blocked_reason` |
| Unassigned | `assignee_id` rỗng; không suy từ nội dung chat |
| Data gap | Thiếu deadline, status unknown hoặc thiếu nguồn có kiểm chứng |

Schema còn kiểm tra item được đặt trong đúng bucket output. Ví dụ task deadline ngày mai không thể bị model đặt vào `overdue_items`.

### 2.3 Product Delivery profile

File: `src/agents/profiles/product_delivery.py`

- Chỉ nhận tuple `product_delivery + workspace + delivery_brief`.
- Prompt cấm tự đổi profile/scope/allowlist hoặc coi chat/tool result là instruction.
- Yêu cầu tách fact, inference, recommendation, data gap và có evidence cho fact.
- Cấm productivity scoring dựa vào message count, tone hoặc sentiment.
- Reminder/meeting chỉ là proposal; không được tuyên bố action đã diễn ra trước shared approval executor.

### 2.4 Golden-case matrix

File: `docs/ROLE_B_DELIVERY_CASE_MATRIX.md`

- Map đầy đủ 15 `delivery_summary` case (`DLV-001` đến `DLV-015`) vào Delivery capability, rule và source ID bắt buộc.
- Bao phủ blocked, overdue, due soon, in-progress và unassigned.
- Ghi rõ in-progress không tự là risk; mỗi fact cần source task/message tương ứng.

### 2.5 Scope boundary cho mọi Delivery read

Files:

- `src/agents/schemas/delivery.py` (`DeliveryReadScope`)
- `src/services/delivery_workspace_service.py`

`DeliveryReadScope` là envelope nội bộ do server tạo sau auth/membership/consent, không phải request schema từ client. Nó bắt buộc:

- đúng profile, intent, workspace scope và `ALLOW` authorization;
- group effective là subset của `allowed_resource_ids`;
- `workspace_overview` chỉ cho Lead và dùng full allowlist đã resolve;
- `group_snapshot` có đúng một selected group đã được allow;
- `member` view chỉ cho Member;
- scope rỗng không thể gọi repository và không có Company Root fallback.

### 2.6 Task retrieval adapter fixture-first

File: `src/agents/tools/delivery_tasks.py`

- Repository được inject qua protocol; chưa có implementation DB vì A-DLV-01/09 chưa hoàn thành.
- Revalidate từng group predicate ngay trước repository call qua callback của platform resource guard.
- Chỉ trả `ToolResult` chứa item/source hợp lệ; source ngoài effective group/task scope bị reject.
- Repository timeout/OSError được chuẩn hóa thành `DELIVERY_TASK_READ_FAILED`, không leak raw exception.
- Scope rỗng trả `items=[]` và không gọi repository.

### 2.7 Group message search adapter fixture-first

Files:

- `src/agents/schemas/delivery.py` (`DeliveryMessageEvidence`)
- `src/agents/tools/delivery_messages.py`

- Repository được inject; future implementation phải bind `effective_group_ids` vào query.
- Query bắt buộc có text, khoảng thời gian timezone-aware tối đa 90 ngày và limit từ 1 đến 20.
- Revalidate source group trước query.
- Evidence từ group QA/unlinked/out-of-scope bị reject.
- Excerpt được `sanitize_untrusted_text`: dòng có dấu hiệu prompt injection bị redaction trước khi đưa về agent/UI.
- Scope không có group trả `PARTIAL + NO_CONSENTED_DELIVERY_SOURCE`, không query repository.

## 3. Test đã thêm/chạy

| Test module | Chứng minh |
|---|---|
| `tests/test_agents/test_product_delivery.py` | Profile tuple, prompt guardrail, health rule, strict schema, empty/partial brief, group snapshot, 15 golden case mapping |
| `tests/test_agents/test_delivery_scope.py` | Lead/member scope, single-group narrowing, no Company Root fallback |
| `tests/test_agents/test_delivery_tools.py` | Task revalidation, source boundary, outage normalization, empty scope |
| `tests/test_agents/test_delivery_messages.py` | Group-bound search, injection sanitation, out-of-scope rejection, bounded range, empty source handling |
| `tests/test_multi_agent_dataset.py` | Dataset canonical 150 case/10 category vẫn hợp lệ |

Lệnh đã chạy tại checkpoint:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_agents\test_product_delivery.py tests\test_agents\test_delivery_scope.py tests\test_agents\test_delivery_tools.py tests\test_agents\test_delivery_messages.py tests\test_multi_agent_dataset.py -q
.\.venv\Scripts\python.exe -m ruff check src\agents\schemas\delivery.py src\agents\profiles\product_delivery.py src\agents\tools\delivery_tasks.py src\agents\tools\delivery_messages.py src\services\delivery_workspace_service.py tests\test_agents\test_product_delivery.py tests\test_agents\test_delivery_scope.py tests\test_agents\test_delivery_tools.py tests\test_agents\test_delivery_messages.py
.\.venv\Scripts\python.exe scripts\generate_multi_agent_dataset.py --check
.\.venv\Scripts\python.exe scripts\validate_multi_agent_dataset.py
git diff --check
```

Kết quả: **35 tests passed**, Ruff passed, dataset hợp lệ 150 case/10 category, `git diff --check` passed.

## 4. Cố ý chưa triển khai

Các phần dưới đây không phải thiếu sót của checkpoint; chúng bị khóa để tránh bypass policy:

| Chưa triển khai | Gate cần có trước | Lý do |
|---|---|---|
| Repository/query Task DB thật | A-DLV-01, A-DLV-09 | Task chưa bind an toàn với Agent Workspace/group và assignee semantics |
| Member group scope thật | A-DLV-06 | Cần intersect group linked/AI-enabled với active participant |
| Group selector/API thật | A-DLV-07 | Cần selected-group resolver server-side chống IDOR/ambiguity |
| Milestone/dependency read thật | A-DLV-02 | Chưa có structured durable source |
| Member decision feed | A-DLV-08 | Chưa có typed DeliveryDecision/store có audience/assignee |
| Runtime/registry/API wire | A-DLV-03 | Shared invocation phải chạy router/context trước model/tool |
| WorkspaceBrief publish/store | A-DLV-04 | Cần persistence, lineage, expiry, audit qua restart/multi-worker |
| Reminder/meeting action | A-DLV-05 | Cần durable HITL, reauthorization và idempotency |

`MULTI_AGENT_ENABLED` và `PRODUCT_DELIVERY_AGENT_ENABLED` được xác nhận vẫn `False` ở thời điểm checkpoint.

## 5. Plan-alignment review

| Plan task/gate | Trạng thái thực | Evidence | Phạm vi còn thiếu/gate |
|---|---|---|---|
| B1-01 → B1-06 / PR-B1 | `complete` | schema, profile, case matrix và test Delivery | Không có dependency production cho scope B1; flags vẫn off |
| B2-01 | `complete` | `delivery_workspace_service.py`, `test_delivery_scope.py` | DB query thật chờ A-DLV-01/09 |
| B2-02, B2-03 | `partial` | fixture-safe task/message adapters và unit tests | Repository DB, consent/membership revalidation thật chờ A-DLV-01/06/09 |
| B2-04, B2-05 | `not_started` | — | Milestone store A-DLV-02; minimal people source/assignee binding A-DLV-09 |
| B2-06 / PR-B2 production gate | `partial` | source boundary, scope, outage và injection fixture tests | Chưa có DB-backed cross-workspace/participant/revoke integration evidence |
| A-DLV-01/06/07/09 | `blocked` | Readiness document | Shared platform owner A |

Kết luận: Checkpoint 1 hoàn thành toàn bộ B1 và phần fixture foundation của B2; **không** được
diễn giải là PR-B2 production complete.

## 6. Bước tiếp theo

1. A review/merge A-DLV-01, 06, 07 và 09 trước khi B thay fixture repository bằng DB repository.
2. B nối resource guard thật vào callback revalidation và viết integration/security test với DB.
3. B implement milestone/people/decision adapters sau các source/store tương ứng.
4. B build deterministic DeliveryBrief producer và chỉ publish workspace-level brief sau A-DLV-04.
5. Giữ feature flag tắt cho đến khi read-only E2E, revocation và IDOR gates xanh.
