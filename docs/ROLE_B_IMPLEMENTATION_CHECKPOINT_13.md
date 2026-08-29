# Product Delivery Agent — Enterprise Dataset and Tool Snapshot Checkpoint 13

> Trạng thái: **complete / verified trong phạm vi local enterprise demo**. Dataset là synthetic nhưng
> được lưu thành record thật, có quan hệ và source provenance trong PostgreSQL Docker.

## Đã triển khai

- Mở rộng Product Delivery workspace thành 3 team: `Apollo Platform`, `Customer Portal`, `Release 34`.
- Mỗi team có đúng 5 participant; tổng cộng 13 người Delivery vì Lead tham gia cả ba team.
- Mỗi team có 8 message doanh nghiệp, 5 task và 3 milestone; task bao phủ pending, in-progress,
  completed, blocked, overdue/due-soon và đều bind về source message cùng conversation.
- Nội dung chat bao phủ giao việc, owner, deadline, blocker, dependency, cập nhật tiến độ,
  phương án fallback và quyết định go/no-go.
- Giữ `QA Internal — not linked` làm negative source để chứng minh dữ liệu ngoài capability không lọt
  vào Product Delivery Agent.
- Thêm production repository read-only cho people và bounded message evidence; runtime resolve
  `allowed_person_ids` server-side và revalidate từng group trước query.
- Snapshot LLM nay chứa `groups`, `people`, `message_evidence` cùng brief đã scope; UI hiển thị các
  phần này và cho phép người dùng nhập câu hỏi thật thay vì gửi prompt cố định.
- Compact model snapshot và giới hạn output 384 token để chạy ổn định trong Groq on-demand 8.000 TPM.

## Artifact

- `scripts/seed_delivery_demo.py`
- `src/services/delivery_workspace_service.py`
- `src/agents/profiles/product_delivery_runner.py`
- `src/agents/profiles/workspace_delivery_graph.py`
- `src/api/delivery_routes.py`
- `src/config.py`, `src/services/llm.py`, `.env.example`
- `Frontend/user/src/pages/DeliveryAgentPage.jsx`
- `tests/test_delivery_demo_seed.py`
- `tests/test_agents/test_delivery_api.py`
- `tests/test_agents/test_product_delivery_runner.py`

## Database evidence

| Group | Thành viên | Messages | Tasks | Milestones |
|---|---:|---:|---:|---:|
| Apollo Platform | 5 | 8 | 5 | 3 |
| Customer Portal | 5 | 8 | 5 | 3 |
| Release 34 | 5 | 8 | 5 | 3 |

Agent Workspace có 13 active memberships; cả 15 Delivery tasks đều có `source_message_ids`.
Seed chạy lại theo upsert không làm tăng các count canonical. Một milestone synthetic cũ bị trùng đã
được xóa chính xác theo ID/workspace/title trước khi verification; không có production/user data bị xóa.

## Bug phát hiện và sửa

1. **Test contract:** expected people projection chứa `schema_version` không tồn tại. Sửa expected theo
   API contract thật.
2. **Runner fixture:** unit DB giả thiếu `execute` sau khi thêm people resolution. Bổ sung result double
   và assert `allowed_person_ids`.
3. **LLM source format:** Groq có lúc không dùng đúng nhãn citation. Prompt nay yêu cầu dòng cuối
   `Nguồn: <group name> (<group id>)`; output guard vẫn từ chối factual response không nhắc nguồn.
4. **Groq TPM:** workspace snapshot ban đầu yêu cầu 122.622 token vì completion mặc định không bounded;
   sau compact còn 8.320/8.001, vẫn vượt quota 8.000. Thêm `LLM_MAX_OUTPUT_TOKENS=384`, compact bỏ
   handoff duplication; live overview sau fix trả `200/success` và không có runtime gap.
5. **UI usability:** form cũ hard-code câu hỏi. Thêm textarea để test agent, mapping assignee name,
   danh sách người và bằng chứng group chat.

## Kiểm thử

- Relevant Delivery/Agent Workspace/migration/config suite: **87 passed**.
- Focused config + workspace graph regression: **13 passed**.
- Ruff trên toàn bộ file thay đổi của checkpoint: **passed**.
- Frontend production build: **passed**, 737 modules transformed.
- Live Groq workspace overview: HTTP `200`, status `success`, 3 groups, 13 people, 7 matching chat
  evidence, 3 blockers, 9 milestones, source line present, không có `DELIVERY_AGENT_RUNTIME_FAILED`.
- Live Apollo group: HTTP `200`, status `success`, đúng 1 group/5 people, trả blocker, owner và nguồn.

## Known limits

- Message evidence dùng bounded keyword matching trong cửa sổ tối đa 90 ngày; chưa có semantic search.
- Decision/dependency hiện xuất hiện trong chat evidence nhưng chưa có typed DeliveryDecision store;
  agent không được phép biến message thành quyết định đã duyệt nếu chưa có record có thẩm quyền.
- Calendar bundle vẫn có Vite size warning; không chặn Delivery page nhưng cần code-split trước release.
- Reminder/meeting giữ disabled tới khi A-DLV-05/HITL executor hoàn tất.

## Plan-alignment review

| Plan task/capability | Trạng thái | Evidence | Còn lại / gate |
|---|---|---|---|
| §14.6 tool-first snapshot | complete (local) | Scoped task/message/people repositories + API regression | Semantic retrieval là hậu MVP |
| §14.10 demo dataset | complete | 3×5 teams, 24 messages, 15 source-bound tasks, 9 milestones | Staging rehearsal trước demo chính thức |
| B6-02 | complete | Idempotent seed chạy hai lần + DB counts | Không dùng production data |
| B6-03 | partial | Lead/member/outsider authorization đã có | Còn admin browser E2E |
| B6-06 | complete (local demo) | Workspace và single-group Groq turns success | Rehearse latency trên staging |
| B11 | complete (checkpoint scope) | 87 regression tests + live source guard | Production eval dataset là release gate |
| B12 | partial | Conversational input, evidence UI, build, TPM fix | Còn browser automation và latency report |

Kết luận: Product Delivery Agent hiện có đủ mật độ dữ liệu và đường đọc thật để kiểm tra khả năng AI
tổng hợp toàn workspace hoặc riêng một group mà vẫn giữ membership, consent, source và no-company-scan.
