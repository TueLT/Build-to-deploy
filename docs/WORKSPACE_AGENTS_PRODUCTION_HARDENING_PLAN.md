# Workspace Agents Production Hardening Plan

## 1. Mục tiêu

Nâng Product Delivery và Quality Assurance Workspace Agent từ bản pilot có kiểm soát lên nền tảng có thể vận hành production theo nguyên tắc:

- authorization, routing, business status và side effect luôn do code hoặc con người quyết định;
- LLM chỉ tổng hợp snapshot đã được cấp quyền;
- một LLM call cho luồng thông thường;
- verifier LLM chỉ chạy có điều kiện cho kết luận tích cực nhưng có hậu quả cao;
- mỗi workspace có cấu hình model, runtime, usage và audit độc lập;
- lỗi một runtime không làm mất deterministic brief của workspace còn lại.

## 2. Kiến trúc đích

```text
Client
  -> trusted workspace router
  -> RBAC / consent / resource guard
  -> scoped read tools
  -> deterministic Delivery health hoặc QA readiness
  -> immutable runtime snapshot
  -> specialist synthesis LLM (1 call)
  -> conditional verifier LLM (0 hoặc 1 call)
  -> deterministic response/output guardrail
  -> memory + usage + audit
```

Verifier không có quyền thay đổi `portfolio_health`, `release_readiness`, database hay trạng thái release. Khi verifier không xác nhận được câu trả lời, hệ thống fail closed về một deterministic response có nguồn.

## 3. Phạm vi triển khai hiện tại

### P0 — correctness và security

- [x] Loại bỏ LLM call chỉ dùng để chọn snapshot tool.
- [x] Giới hạn một synthesis call cho request thông thường.
- [x] Thêm verifier có điều kiện, bounded, fail-closed cho `ON_TRACK` và `READY`.
- [x] Bảo toàn health/readiness và citation trên mọi fallback path.
- [x] Gộp đầy đủ data gap từ QA traceability và các tool thành phần.
- [x] Thêm optimistic concurrency cho QA work-item transition.
- [x] Thêm cleanup vật lý cho workspace-agent memory hết hạn.
- [x] Bắt buộc remote runtime khi bật workspace agents trong production.

### P1 — model operations và observability

- [x] Tách provider/model/temperature/output-token theo Delivery và QA.
- [x] Cho phép cấu hình verifier model riêng.
- [x] Ghi prompt version, provider, model, số LLM call và verifier state trong runtime metadata/audit.
- [x] Ghi usage nhất quán cho cả Delivery và QA.
- [x] Tăng runtime version sau thay đổi contract/graph.

### P2 — verification

- [x] Unit test một-call synthesis, conditional verifier và fail-closed fallback.
- [x] Integration test QA stale-write conflict.
- [x] Test memory retention cleanup.
- [x] Chạy Ruff, focused regression, migration head, Docker config và frontend build.

## 4. Backlog cần thiết trước enterprise GA

Các mục dưới đây không nên nhồi vào cùng một thay đổi vì cần schema/nghiệp vụ và quyết định của business owner:

- chuẩn hóa `Requirement`, `TestCase`, `TestRun`, `Defect`, `Evidence`, `Waiver`, `QualityPolicy` thay cho Task bridge;
- durable action proposal + human approval executor cho Delivery/QA;
- transactional outbox, idempotent event consumer và dead-letter queue cho Delivery-to-QA handoff;
- browser E2E, live-model eval, load/soak test, SLO/alert và canary rollout;
- UI vận hành đầy đủ dependency, decision, QA work item, release gate và waiver;
- policy sign-off cho high-severity defect, security/performance/compliance gate và release waiver.

## 5. Definition of Done cho đợt hardening

- request thông thường thực hiện đúng một LLM call;
- kết luận `ON_TRACK`/`READY` có thể đi qua verifier độc lập khi được bật;
- verifier không thể override deterministic result;
- QA stale update trả `409 Conflict`;
- mọi QA tool gap xuất hiện trong top-level brief;
- thread hết hạn được xóa cả metadata và message;
- production config từ chối chạy agents ở embedded mode;
- lint và toàn bộ test liên quan đạt.

## 6. Kết quả xác minh ngày 2026-08-26

- Ruff: đạt trên toàn repository.
- Backend regression: `468 passed, 1 skipped`.
- Alembic: `20260826_24 (head)`.
- Docker Compose config: hợp lệ.
- Frontend production build: đạt, 718 modules.
- Cảnh báo không chặn release: dependency deprecation và CalendarPage chunk lớn hơn 500 kB.

## 7. Enterprise control-plane implementation — 2026-08-26

Phần này cập nhật trạng thái mới hơn backlog ở mục 4. Các hạng mục đã được triển khai trong code, migration, API và UI:

- [x] Chuẩn hóa QA thành các entity độc lập: `Requirement`, `TestCase`, `TestRun`, `Defect`, `Evidence`, `QualityPolicy`, `Waiver`.
- [x] Readiness v2 kiểm tra requirement coverage, required test kind, verified evidence, đúng build/environment, blocking defect, waiver và policy version.
- [x] QA approval ưu tiên control plane v2; dữ liệu Task QA cũ chỉ còn là compatibility fallback khi chưa có domain v2.
- [x] Delivery release state machine hỗ trợ draft/submit/resubmit/released/cancelled với optimistic concurrency.
- [x] Transactional outbox có idempotency, bounded retry và dead-letter; hai runtime không gọi trực tiếp lẫn nhau.
- [x] Durable HITL proposal có payload hash, expiry, idempotency, Lead approval, live authorization revalidation, OCC và exactly-once domain transition.
- [x] Action HITL hiện hỗ trợ dependency status, decision status và các transition QA có rủi ro; external reminder/calendar adapter chưa được quảng bá là capability hoàn thành.
- [x] QA read-tool catalog tăng từ 10 lên 14 tool bằng normalized control plane, policy, evidence catalog và waiver reads.
- [x] Delivery/QA UI có control panel cơ bản; Delivery tạo dependency/decision/release handoff, QA tạo record chuẩn hóa, verify evidence và quyết định release.
- [x] Lead-only operational metrics cho domain state, proposals, outbox và 24-hour LLM usage.
- [x] Read-only load harness tại `scripts/workspace_agent_load_harness.py` và integration tests cho READY gate, outbox và durable approval.

Các gate không thể xác nhận chỉ bằng local repository và vẫn phải hoàn tất trước enterprise GA:

- [ ] Business/Security sign-off cho severity, security/performance/compliance gates và quyền waiver.
- [ ] Browser E2E trên trình duyệt được hỗ trợ; live-model eval với provider thật.
- [ ] Staging load/soak bằng harness, đặt SLO/p95 từ số đo thật và cấu hình alert.
- [ ] Canary rollout, container-kill rehearsal và rollback rehearsal trong hạ tầng triển khai thật.
