# PRD — Orbit: AI Agent trợ lý cá nhân trong Chat doanh nghiệp

> Mã đề: CHAT-01 · Phiên bản: 2.0 · Ngày: 2026-08-13
> Phạm vi delivery: MVP 7 ngày, đội 4 người

## 1. Cách đọc tài liệu

Tài liệu phân biệt rõ hai trạng thái:

- **CURRENT:** phần đang có trong repository và có thể tái sử dụng.
- **TARGET:** phần phải bổ sung để đạt demo ba role-agent trong một tuần.

Hiện tại Orbit đã có một planner dùng chung, tool calling, consent, memory, task/reminder/calendar,
HITL, audit, user UI và admin UI. Kiến trúc ba agent theo vai trò trong tài liệu này là **đích phát
triển**, chưa được xem là hoàn thành chỉ vì UI đã tách user/admin.

## 2. Tóm tắt sản phẩm

Orbit là lớp trợ lý AI gắn vào chat nội bộ. Hệ thống chỉ đọc các hội thoại đã được cấp quyền, tóm
tắt nội dung, tìm lại ngữ cảnh, trích xuất cam kết/task/deadline, gợi ý reminder và sự kiện lịch.
Mọi thao tác gây tác động ra ngoài đều phải qua Policy Engine và Human-in-the-loop (HITL).

Sản phẩm phục vụ đúng ba vai trò nghiệp vụ:

1. **Sếp:** cần bức tranh tổng hợp, rủi ro và ưu tiên của đơn vị.
2. **Trưởng phòng:** cần quản trị task, deadline, cam kết và tải công việc của phòng.
3. **Nhân viên:** cần xử lý chat cá nhân, task, reminder và lịch của mình.

`platform_admin` chỉ vận hành hệ thống, không phải vai trò nghiệp vụ và không có quyền đọc raw chat
mặc định.

## 3. Mục tiêu và phi mục tiêu

### 3.1 Mục tiêu MVP

- Tóm tắt hội thoại theo yêu cầu với source references.
- Trích task/deadline/assignee có confidence và trạng thái cần làm rõ.
- Tạo reminder/calendar sau xác nhận; đồng bộ Google Calendar theo tài khoản người dùng.
- Chủ động phát hiện cam kết khi message mới tới và gửi suggestion, không tự thực thi.
- Định tuyến tới Executive, Manager hoặc Employee Agent theo identity, intent và data scope.
- Giữ memory theo user/workspace/consent scope, có revoke và TTL phù hợp.
- Cung cấp Team Inbox cho trưởng phòng và Executive Brief cho sếp.
- Có audit, quota/token alert, xử lý lỗi cơ bản và bộ eval định lượng.

### 3.2 Phi mục tiêu trong một tuần

- Không tự động đọc toàn bộ chat của tổ chức.
- Không coi chức danh hiển thị là bằng chứng quyền truy cập.
- Không cho agent tự gửi tin, mời người khác hoặc thay đổi lịch mà thiếu xác nhận.
- Không fine-tune model, xây mobile native hoặc tự xây lớp mã hóa E2E.
- Không làm đầy đủ quy trình nghiệp vụ HR/Sales như hai ảnh tham khảo đầu; chỉ học mô hình
  supervisor + specialist + policy + HITL.

## 4. Persona, quyền và phạm vi dữ liệu

### 4.1 Ma trận vai trò nghiệp vụ

| Vai trò | Agent mặc định | Scope mặc định | Đầu ra ưu tiên | Không được mặc định |
|---|---|---|---|---|
| Sếp | Executive Agent | Dữ liệu aggregate của đơn vị được entitlement cho phép | Executive summary, risk, decision, KPI, cross-team dependency | Đọc mọi raw chat, xem chat riêng, bypass manager |
| Trưởng phòng | Manager Agent | Nhóm/phòng quản lý, team task, aggregate/member data được policy cho phép | Team inbox, overdue, workload, follow-up | Đọc chat riêng không liên quan, xem phòng khác |
| Nhân viên | Employee Agent | Chat tham gia + AI consent, task/memory/calendar cá nhân | Summary, action list, reminder, calendar | Xem dữ liệu đồng nghiệp hoặc đại diện người khác |

### 4.2 Mapping với RBAC hiện có

Trong tuần MVP, tránh thay toàn bộ schema quyền:

| Business role | Mapping đề xuất | Điều kiện bổ sung |
|---|---|---|
| Sếp | `workspace.owner` | Có entitlement `executive:aggregate:read` |
| Trưởng phòng | `workspace.admin` hoặc department manager | Có `department_id` và quan hệ quản lý hợp lệ |
| Nhân viên | `workspace.member` | Có conversation membership và AI consent |
| Platform admin | `platform_admin` | Chỉ control plane; support grant riêng nếu cần chẩn đoán |

Quyền thực tế luôn lấy từ DB/authorization service. Không dùng system prompt, tên chức danh hoặc
nội dung người dùng tự khai để nâng quyền.

### 4.3 Bốn data scope chuẩn

- `personal`: task, calendar, memory và chat được consent của chính user.
- `team`: dữ liệu nhóm/phòng thuộc quan hệ quản lý đã xác thực.
- `aggregate`: số liệu/tóm tắt đã loại hoặc mask dữ liệu cá nhân theo policy.
- `sensitive`: raw chat riêng, HR/payroll, bí mật hoặc dữ liệu ngoài entitlement; mặc định deny.

## 5. Jobs to be done và user stories

### Nhân viên

- Khi quay lại một nhóm nhiều tin, tôi muốn biết nhanh quyết định và việc của mình.
- Khi một lời hứa/deadline xuất hiện, tôi muốn được gợi ý task nhưng không bị tạo nhắc sai.
- Khi đã đồng ý, tôi muốn tạo reminder hoặc lịch mà không nhập lại thông tin.
- Khi thông tin mơ hồ, tôi muốn agent hỏi đúng một câu ngắn để hoàn thiện.

### Trưởng phòng

- Khi bắt đầu ngày, tôi muốn thấy task trễ hạn/sắp đến hạn và cam kết chưa có owner trong phòng.
- Khi chuẩn bị họp, tôi muốn summary theo nguồn và không lộ hội thoại ngoài quyền.
- Khi có hành động liên quan nhân viên khác, tôi muốn có bước review/confirm rõ ràng.

### Sếp

- Khi hỏi tình hình đơn vị, tôi muốn nhận insight tổng hợp, rủi ro và quyết định cần chốt.
- Khi cần đào sâu, tôi muốn biết dữ liệu nào hỗ trợ kết luận và phần nào bị policy giới hạn.
- Khi yêu cầu vượt scope, tôi muốn hệ thống từ chối rõ lý do thay vì bịa hoặc rò rỉ dữ liệu.

## 6. Kiến trúc hành vi bắt buộc

Mọi request đi theo chuỗi:

`Authenticate → Resolve role/scope → Classify intent → Policy pre-check → Retrieve least context →
Role-agent plan → Policy tool-check → HITL nếu cần → Execute → Verify → Audit → Respond`

Không agent nào được gọi thẳng DB/tool ngoài Orchestrator và Policy layer. Mỗi tool call mang
`actor_id`, `workspace_id`, `role`, `purpose`, `resource_ids`, `consent_scope_hash` và `trace_id`.

## 7. Yêu cầu chức năng

### FR-01 — Identity, RBAC và scope resolution (P0)

- Xác thực user và workspace trước khi chạy agent.
- Resolve business role, department hierarchy, conversation membership và consent.
- Từ chối hoặc mask tài nguyên ngoài scope trước khi tạo prompt.
- Hiển thị role/scope đang dùng trên UI để người dùng hiểu kết quả.

**Acceptance:** giả mạo “tôi là sếp” trong prompt không thay đổi quyền; truy vấn chéo phòng bị deny;
mọi policy decision có trace nhưng không chứa raw message.

### FR-02 — Conversation consent và ingestion (P0)

- User bật/tắt AI cho từng conversation; có thời điểm và người cấp quyền.
- Event Listener nhận message mới trong vùng đã giải mã của user.
- Revoke consent làm dữ liệu đó không còn được retrieve; summary/cache liên quan phải invalidated.
- Không chép raw message vào log, analytics hoặc vector metadata.

**Acceptance:** conversation chưa consent không xuất hiện trong search/summary/proactive detector.

### FR-03 — Orchestrator và role router (P0)

- Chọn Executive/Manager/Employee Agent dựa trên identity + intent + requested scope.
- Request đơn giản được đi đường nhanh; request đa bước tạo plan có giới hạn bước/tool.
- Router không tự mở rộng scope; một request có thể hạ xuống Employee Agent nếu chỉ hỏi dữ liệu cá nhân.
- Có fallback an toàn khi router/model lỗi.

**Acceptance:** ≥95% route đúng trên eval set; role-agent được ghi vào trace.

### FR-04 — Employee Agent (P0)

- Tóm tắt chat, tìm message cũ, trích task/deadline/assignee và quản lý task cá nhân.
- Đề xuất reminder/calendar; hỏi lại khi thiếu ngày, giờ, múi giờ hoặc đối tượng.
- Chỉ dùng personal scope và conversation được consent.
- Kết quả trích xuất gồm source message, confidence và trạng thái `suggested|needs_clarification`.

### FR-05 — Manager Agent (P0)

- Tổng hợp team task, deadline, owner, cam kết chưa follow-up và workload cơ bản.
- Tạo Team Inbox ưu tiên theo overdue, due soon, blocked và unassigned.
- Chỉ đọc team scope của đúng department; raw message chỉ được retrieve nếu conversation policy cho phép.
- Mọi reminder/event tác động người khác phải HITL; cross-department yêu cầu thêm policy/approval.

### FR-06 — Executive Agent (P0)

- Tổng hợp dữ liệu aggregate, rủi ro, quyết định, xu hướng và phụ thuộc liên phòng.
- Ưu tiên số liệu/tóm tắt đã policy-filter thay vì raw message.
- Kết quả tách `facts`, `risks`, `decisions_needed`, `recommendations`, `sources`, `data_gaps`.
- Nếu không đủ quyền/chứng cứ, nêu khoảng trống; không suy diễn thành fact.

### FR-07 — Summarization và search (P0)

- Hỗ trợ scope: unread, time range, thread/conversation và semantic query.
- Summary phải giữ decision, owner, deadline, open question, disagreement quan trọng.
- Mọi kết luận có source IDs hoặc chỉ rõ “không đủ nguồn”.
- Cache theo scope hash + message cursor + prompt/model version; invalidation khi message/consent đổi.

### FR-08 — Task extraction và Inbox (P0)

- Schema: `title`, `description`, `assignee`, `due_at`, `timezone`, `priority`, `source_ids`, `confidence`,
  `ambiguities` và `status`.
- Confidence thấp hoặc thiếu trường quan trọng không tự tạo; hỏi làm rõ hoặc để suggestion.
- Có personal inbox và team inbox; lọc overdue/due soon/blocked/unassigned.
- Cho phép accept/edit/dismiss suggestion và dùng feedback làm eval data đã khử nội dung nhạy cảm.

### FR-09 — Reminder và Calendar HITL (P0)

- Preview đầy đủ title, thời gian, timezone, participants, target account và nguồn trước Confirm.
- Create/update/delete event, reminder cho người khác, gửi/chia sẻ đều là side effect cần HITL.
- Confirmation token ràng buộc với actor, payload hash, tool và expiry; sửa payload phải xác nhận lại.
- Calendar OAuth per user, token mã hóa; webhook sync hai chiều là P1 nếu thời gian cho phép.

### FR-10 — Proactive detector (P0)

- Event path không chặn message send; enqueue detector bất đồng bộ.
- Phát hiện cam kết/lịch hẹn, chấm confidence và gửi suggestion qua WebSocket.
- Deduplicate theo source IDs + normalized task/date + user.
- Không gọi model với mọi message: rule gate/batching/cache trước model.
- User có thể snooze, dismiss, tắt theo conversation hoặc toàn bộ.

### FR-11 — Memory (P0)

- Phân biệt preference, entity/relationship, episodic summary và task/calendar state.
- Mỗi memory có owner, workspace, source, purpose, consent scope, TTL và sensitivity.
- Memory retrieve theo least privilege; user xem/sửa/xóa memory cá nhân.
- Không lưu raw conversation như “memory” mặc định.

**CURRENT đã triển khai:** short-term LangGraph checkpoint có compact message history; metadata thread
có owner/workspace/TTL. Long-term memory có bốn type, provenance, consent snapshot, sensitivity,
confidence và expiry; memory hết hạn hoặc mất consent bị loại khỏi agent retrieval. Retrieval hiện là
keyword search, vector/semantic ranking vẫn là TARGET/P1.

### FR-11A — Personal timeline (P0)

- Hợp nhất task, reminder và Google Calendar của user trong một projection sắp xếp theo timezone user.
- Có thể thêm message khi user yêu cầu; message luôn qua conversation authorization và AI consent.
- Khoảng truy vấn tối đa 90 ngày, giới hạn item và không ghi đè dữ liệu nguồn.
- Mỗi source trả `ok|not_connected|unavailable`; Calendar lỗi không làm mất task/reminder.
- Agent gọi `get_personal_timeline` cho câu hỏi lịch trình đa nguồn.

**CURRENT đã triển khai:** `GET /api/v1/timeline` và agent tool `get_personal_timeline`.

### FR-12 — Admin control plane (P0)

- Quản lý user/workspace, health, model config, quota/budget, prompt version và audit metadata.
- Không hiển thị raw message trong dashboard/log.
- Support access yêu cầu grant có scope, lý do và thời hạn; mọi lần dùng được audit.
- Cảnh báo token/user/day, cost/workspace/day, lỗi tool và queue lag.

### FR-13 — Error handling (P0)

- Model timeout: retry giới hạn hoặc trả partial result có cảnh báo.
- Tool lỗi: không báo thành công; giữ trạng thái confirmation có thể retry an toàn.
- Calendar conflict/timezone ambiguity: hỏi lại hoặc hiển thị conflict.
- WebSocket mất kết nối: notification lưu bền và fetch lại khi reconnect.

## 8. Policy, guardrail và HITL

Policy Engine trả đúng một quyết định:

| Decision | Khi dùng | Hành vi |
|---|---|---|
| `ALLOW` | Read/action trong scope, không side effect nhạy cảm | Tiếp tục với context tối thiểu |
| `MASK` | Có thể trả kết quả sau khi ẩn PII/nội dung nhạy cảm | Mask trước khi LLM/response |
| `ASK_CLARIFY` | Thiếu thời gian, người nhận, scope hoặc confidence thấp | Hỏi một câu cụ thể |
| `HITL` | Side effect hoặc hành động tác động người khác | Dừng, preview, chờ confirm |
| `DENY` | Không có quyền/consent hoặc policy cấm | Từ chối và audit metadata |

Guardrail bắt buộc gồm privacy, permission, extraction quality, cost/latency, prompt injection,
tool allowlist, step/token limit, output schema và audit. Chi tiết nằm trong
[Agent System Design](AGENT_SYSTEM_DESIGN.md).

## 9. UI/UX

### User application

- Home theo role: My Day, Team Inbox hoặc Executive Brief.
- Chat/Assistant có scope picker, source chips, approval card và trạng thái tool.
- Tasks/Inbox, Calendar, Reminders, Memory/Consent và Profile/Integration.
- Mobile-first; approval không bị ẩn trong text chat.

### Admin application

- Operations dashboard, users/workspaces, AI/prompt config, usage/budget, audit và health.
- Không trộn admin navigation với trải nghiệm ba role nghiệp vụ.

Chi tiết màn hình và sequence flow: [UI Flow](UI_FLOW.md).

## 10. Dữ liệu và thay đổi schema đề xuất

Tận dụng bảng user/workspace/conversation/message/task/reminder/calendar/memory/audit hiện tại, bổ
sung tối thiểu:

- `departments(id, workspace_id, name, manager_user_id)`
- `department_members(department_id, user_id, business_role)`
- `agent_runs(trace_id, actor_id, selected_agent, intent, status, model_version, prompt_version)`
- `policy_decisions(trace_id, decision, policy_code, resource_type, resource_id_hash)`
- `task_suggestions(source_fingerprint, payload, confidence, ambiguities, disposition)`
- `approval_requests(actor_id, tool_name, payload_hash, preview, expires_at, status)`
- `conversation_consents(user_id, conversation_id, purpose, granted_at, revoked_at)` nếu schema hiện
  tại chưa lưu đủ purpose/version.

Chỉ migration thực sự cần cho demo mới vào Day 1; không tái cấu trúc toàn bộ authorization trong tuần.

## 11. API/event contract tối thiểu

- `POST /agent/runs`: request + requested scope; trả `trace_id` và stream trạng thái.
- `POST /agent/runs/{id}/confirm`: confirmation token + optional edits.
- `POST /agent/runs/{id}/reject`
- `GET /inbox/personal`, `GET /inbox/team`, `GET /brief/executive`
- `PUT /conversations/{id}/ai-consent`
- `GET/DELETE /memories/{id}`
- `message.created` → proactive queue → `suggestion.created` → WebSocket.

Contract hiện có được giữ nếu tương đương; đây là logical contract, không yêu cầu đổi tên endpoint chỉ
để khớp tài liệu.

## 12. Yêu cầu phi chức năng

| Nhóm | Yêu cầu MVP |
|---|---|
| Security | Deny by default, RBAC + resource authorization, encrypted OAuth tokens, secret hygiene |
| Privacy | Consent-scoped, no raw content in logs/audit/vector metadata, delete/revoke path |
| Reliability | Idempotency cho side effects, bounded retry, durable notification |
| Latency | P95 interactive <5s; proactive enqueue overhead <300ms |
| Cost | Small model cho classify/summarize/extract; large model chỉ cho plan phức tạp; budget alert |
| Auditability | Trace từ request → policy → tool → confirmation → result |
| Accessibility | Keyboard, focus, contrast, label; mobile 360px không vỡ luồng chính |
| Observability | Error rate, latency, token, cache hit, queue lag, policy/HITL counters |

## 13. Metrics và release gate

Release chỉ khi:

- Task extraction precision ≥0.90, recall ≥0.80, F1 ≥0.85.
- Deadline/timezone accuracy ≥0.90.
- Role routing accuracy ≥0.95.
- 100% side effects trong test matrix đi qua HITL.
- 0 unauthorized disclosure trong red-team permission set.
- P95 summarize/search <5 giây ở dataset MVP.
- Backend tests, frontend user/admin lint/build đều pass.

Phương pháp benchmark và dataset: [Metrics & Benchmark](../metric.md).

## 14. Rủi ro và biện pháp

| Rủi ro | Tác động | Biện pháp MVP |
|---|---|---|
| Ba agent chỉ khác prompt nhưng chung quyền | Rò rỉ dữ liệu | Policy/code authorization độc lập với prompt |
| False reminder | Mất niềm tin | Confidence, source, suggestion state, confirm/edit/dismiss |
| Proactive quá ồn | User tắt tính năng | Rule gate, threshold, dedupe, per-chat preference |
| Context dài, tốn tiền | Chậm và vượt budget | Search-first, cache, compact summary, model routing |
| Scope role mơ hồ | Kết quả sai quyền | Department mapping + entitlement, không dựa title |
| Một tuần quá ngắn | Demo không ổn định | Giữ current core, vertical slice trước, P1/cut list rõ |

## 15. Definition of Done

Một flow chỉ “done” khi có authorization/policy, happy path, denial/error path, audit trace, automated
test tương ứng và UI state. Một agent chỉ “done” khi prompt đã version, tool allowlist khóa, output
schema validate và eval vượt ngưỡng. “Có màn hình” hoặc “model trả lời được” chưa được tính là hoàn thành.

## 16. Liên kết

- [Product Brief](BRIEF.md)
- [Kiến trúc và sơ đồ các nhánh](architecture_diagram.md)
- [System prompt, tool và guardrail](AGENT_SYSTEM_DESIGN.md)
- [UI và workflow](UI_FLOW.md)
- [Bản đồ kiểm thử toàn hệ thống](TESTING_OVERVIEW.md)
- [Kế hoạch 7 ngày cho 4 người](ONE_WEEK_PLAN.md)
- [Metrics và benchmark](../metric.md)
