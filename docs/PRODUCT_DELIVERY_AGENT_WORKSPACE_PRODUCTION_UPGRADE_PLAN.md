# Product Delivery Agent Workspace — production upgrade plan

## 1. Mục tiêu và nguyên tắc kiến trúc

Product Delivery Agent không chỉ tóm tắt hội thoại. Workspace phải là một lớp điều phối delivery có dữ liệu có cấu trúc, bằng chứng truy vết được và quyết định nghiệp vụ deterministic. LLM chỉ diễn giải snapshot đã được cấp quyền; LLM không tự quyết định health, release gate, quyền truy cập hay thực thi side effect.

Các nguyên tắc bắt buộc:

- Mỗi request được khóa vào `organization_workspace_id + agent_workspace_id + allowed_resource_ids`.
- Mọi fact quan trọng có `SourceReference`; dữ liệu thiếu được trả thành `data_gaps`, không suy đoán.
- Lead có workspace/group view; member chỉ thấy phần công việc hợp lệ của chính mình.
- Không dùng số tin nhắn, sentiment hoặc hoạt động chat để chấm điểm con người.
- Delivery runtime và QA runtime là hai failure domain riêng; giao tiếp qua `ReleaseCandidate` bền vững, không gọi runtime trực tiếp lẫn nhau.
- Reminder, meeting và release handoff là `ActionProposal`; không có side effect trước khi revalidate và phê duyệt.
- Trạng thái portfolio, risk, release và quality gate được tính bằng code có test, không do prompt quyết định.

## 2. Baseline đã kiểm chứng

Đã có:

- Router thống nhất cho Personal, Product Delivery và QA.
- Delivery LangGraph riêng, system prompt riêng, input/output guardrail riêng và process/runtime bulkhead riêng.
- Durable agent memory theo user + Agent Workspace + authorization scope hash.
- Năm read tool thực thi được: task, message, milestone, people và brief.
- Dashboard role-scoped; workspace brief source-backed; audit log; feature flags.
- `ReleaseCandidate` là handoff bền vững Delivery → QA; QA approval bị khóa bởi quality gate deterministic.

Khoảng trống trước đợt nâng cấp này:

- Chưa có dependency register, decision log, risk register, capacity/flow và portfolio health dưới dạng tool thực sự.
- Delivery chưa đọc lại trạng thái release/QA handoff trong snapshot agent.
- Hai tên proposal reminder/meeting có trong registry nhưng chưa có implementation/executor bền vững; không được tính là tool hoàn thành.
- Chưa có lịch sử transition đủ để tính lead time/cycle time/deployment frequency chính xác.

## 3. Kiến trúc đích

```text
HTTP / unified workspace router
  -> authentication + workspace membership + feature flag
  -> AgentContext + consent/resource capability
  -> scoped repositories (tasks, milestones, controls, releases)
  -> deterministic Delivery analysis
  -> immutable ToolResult snapshot + citations + data gaps
  -> isolated Product Delivery LangGraph
  -> output guardrail + audit + durable user-scoped memory

Delivery Workspace --ReleaseCandidate--> QA Workspace
Delivery reads QA state from the handoff record; it never depends on QA runtime availability.
```

## 4. Tool catalog đích

### Read tools — được phép vào read-only executor

| Tool | Kết quả nghiệp vụ | Side effect |
|---|---|---:|
| `get_delivery_tasks` | Work items theo scope/role | Không |
| `search_delivery_messages` | Evidence chat đã consent | Không |
| `get_delivery_milestones` | Milestone/release target | Không |
| `get_delivery_people` | Projection tối thiểu của assignee | Không |
| `get_delivery_dependencies` | Dependency register và blocker chain | Không |
| `get_delivery_risks` | Risk register deterministic từ blocker, overdue, dependency, release gate | Không |
| `get_delivery_decisions` | Decision log và quyết định đang chờ | Không |
| `get_delivery_release_status` | Handoff state Delivery ↔ QA | Không |
| `get_delivery_capacity_summary` | WIP/status distribution tổng hợp, không chấm điểm cá nhân | Không |
| `get_delivery_flow_metrics` | Throughput/aging khả dụng và data gap cho metric thiếu lịch sử | Không |
| `get_delivery_portfolio_health` | `ON_TRACK/AT_RISK/BLOCKED/INSUFFICIENT_DATA` deterministic | Không |
| `build_delivery_brief` | Contract/handoff Delivery chuẩn hóa | Không |

### Action tools — bắt buộc HITL

| Tool | Contract | Điều kiện production |
|---|---|---|
| `propose_delivery_reminder` | Tạo proposal, hash, expiry, idempotency key | Durable proposal store + approve/reject + revalidate + audited executor |
| `propose_delivery_meeting` | Tạo proposal, không tạo lịch | Như trên + calendar permission tại thời điểm execute |
| `propose_release_handoff` | Preview ReleaseCandidate | Delivery Lead approve; QA workspace/source/milestone revalidate |

Tên action không được quảng bá như capability chạy được nếu thiếu executor đầy đủ.

## 5. Business rules

- `BLOCKED`: có task/milestone blocked, dependency blocked, hoặc release bị QA reject.
- `AT_RISK`: có overdue, dependency open quá hạn, quyết định pending quá hạn, hoặc QA chưa approve cho release đang nhắm tới.
- `INSUFFICIENT_DATA`: không có fact, hoặc chỉ số được hỏi cần transition history chưa được thu thập.
- `ON_TRACK`: chỉ khi không vi phạm các rule trên; LLM không được đổi nhãn.
- Capacity chỉ báo WIP/status count ở cấp scope. Không xếp hạng member và không suy ra hiệu suất từ chat.
- Flow metric không được dùng `updated_at - created_at` làm cycle time nếu thiếu transition event; phải trả `WORKFLOW_HISTORY_NOT_CAPTURED`.
- Release approval chỉ do QA Lead thực hiện và chỉ khi gate trả `READY`.

## 6. Security, reliability và observability gates

- Deny trước DB/LLM cho workspace/profile/role sai.
- Revalidate từng resource ngay trước query và ngay trước side effect.
- Query luôn bind organization, Agent Workspace và source group; không có company-wide fallback.
- Optimistic concurrency (`row_version`) cho mutable domain state.
- Proposal hash + expiry + idempotency; edit tạo proposal mới.
- Audit: deny, revoke, tool error, brief generated, proposal lifecycle, release transition.
- Runtime timeout/circuit-breaker; nếu LLM lỗi vẫn trả deterministic snapshot ở trạng thái partial.
- SLO ban đầu: unauthorized leakage = 0; citation coverage = 100%; deterministic rule tests = 100%; p95 read flow đo trong staging trước khi enable flag.

## 7. Kế hoạch triển khai và trạng thái

### PD0 — Baseline và contract

- [x] Audit tool thực sự thay vì chỉ đọc registry.
- [x] Khóa role/scope/source/memory/runtime/handoff assumptions.
- [x] Tài liệu plan, DoD và giới hạn production.

### PD1 — Deterministic delivery intelligence

- [x] Schema dependency, decision, release view, risk, capacity, flow và portfolio assessment.
- [x] Pure rules và unit tests cho health/risk/metric data gaps.
- [x] Graph bắt buộc giữ nguyên portfolio health giống snapshot.

### PD2 — Scoped repositories và tools

- [x] Dependency/decision persistence có source binding và row version.
- [x] Bảy read/analysis tools mới.
- [x] Registry và read-only executor chỉ liệt kê implementation có thật.
- [x] Cross-workspace, member-view, consent-revoke và repository outage tests.

### PD3 — API và UI

- [x] Brief API gom mọi kết quả vào một immutable snapshot.
- [x] Agent UI hiển thị health, risks, decisions, dependencies và QA handoff.
- [x] Empty/partial/stale/denied/runtime-down states.

### PD4 — HITL actions

- [x] Durable proposal state machine cho dependency/decision/QA transition nội bộ.
- [ ] Approve/reject/expire/replay tests.
- [ ] Reminder/calendar adapters và release handoff executor revalidate tại thời điểm chạy.

PD4 không được giả lập bằng một endpoint “approve” chỉ đổi trạng thái mà không thực thi/ghi nhận kết quả side effect.

### PD5 — Production verification

- [x] Alembic upgrade từ DB sạch và từ revision trước; downgrade smoke.
- [x] Ruff, targeted tests, full regression, frontend build.
- [x] Runtime isolation: Delivery chết không làm QA/Personal chết và ngược lại.
- [ ] Load/latency test, alert, rollback/runbook và staged feature-flag rollout.

Đã có read-only load harness và endpoint operational metrics. Checkbox trên chỉ được đóng sau khi chạy staging soak, đặt ngưỡng alert và rehearsal rollback trên hạ tầng thật.

## 8. Definition of Done

Một capability chỉ được đánh dấu hoàn thành khi có đồng thời: domain contract, scoped implementation, guard/revalidation, audit phù hợp, positive test, negative isolation/security test và được nối vào API/runtime/UI cần thiết. Tên trong registry, prompt hoặc mock không phải bằng chứng hoàn thành.
