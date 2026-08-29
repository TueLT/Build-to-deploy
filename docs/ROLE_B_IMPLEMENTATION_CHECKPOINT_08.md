# Product Delivery Agent — Implementation Checkpoint 08

> Ngày cập nhật: 2026-08-22
>
> Trạng thái: **complete / verified trong phạm vi Delivery read-only MVP (API + UI)**.

## Đã triển khai

- Migration `20260822_16`: Task có `agent_workspace_id`, index scoped và trạng thái `blocked` bắt buộc lý do. Task mới chỉ bind khi source conversation đã link active Agent Workspace; task unbound không được Delivery đọc.
- Migration `20260822_17`: typed `DeliveryMilestone`, bắt buộc workspace, Agent Workspace và source conversation.
- Scoped DB repositories luôn bind Company Workspace + Agent Workspace + consented conversation allowlist; member bị lọc theo assignee/owner.
- API Delivery brief chạy router → context → live guards → scoped reads → strict brief; denial/error được chuẩn hóa và audit không chứa raw message.
- Capability API chỉ trả group Delivery server-resolved cho lead. User route `/delivery-agent` có selector, loading/error/partial/data-gap states; reminder/meeting disabled vì chưa có durable HITL.

## Kiểm thử

- `tests/test_tasks.py`: **12 passed**.
- `tests/test_agents/test_delivery_api.py`, milestone và brief suite: **11 passed**.
- Ruff, dataset 150 case/10 category, User production build và `git diff --check`: passed.

Một patch đầu checkpoint đã đặt nhầm revalidation consent của AI-extracted task. Lỗi được phát hiện trong review trước runtime, sửa về `_require_current_ai_provenance`, rồi task regression xanh. Ruff cũng sửa một import test thừa; không nới policy hoặc sửa fixture để che lỗi.

## Plan alignment

| Hạng mục | Trạng thái | Còn thiếu |
|---|---|---|
| B4 UI vertical slice | `complete` trong MVP read-only | Proposal vẫn disabled vì A-DLV-05 chưa có |
| B5 security/eval | `partial` | Cần live evaluator/E2E deployment evidence |
| B6 real integration | `partial` | Task/milestone DB read có; persistent brief/performance còn thiếu |
| A-DLV-01/02 | `complete` trong code/migration | Cần rollout migration DB thật |
| A-DLV-03/07 | `partial` | Endpoint/capability có; shared `/chat` model adapter chưa có |
| A-DLV-04/05/08 | `blocked` | Persistent brief handoff, durable HITL, typed decision store chưa có |

Feature flags giữ mặc định `false`; chỉ bật ở môi trường demo sau migration head và smoke test.
