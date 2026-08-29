# Product Delivery Agent — Local Runtime and Live LLM Verification Checkpoint 12

> Trạng thái: **complete / verified trong phạm vi local demo runtime**. Đây không phải xác nhận
> production release; side-effect/HITL vẫn giữ ngoài phạm vi cho tới khi gate tương ứng được duyệt.

## Phạm vi và kết quả

- Chuyển môi trường development khỏi Supabase sang PostgreSQL riêng của dự án tại
  `localhost:5432/orbit` và giữ database bằng Docker Compose.
- Chạy Alembic tới `20260824_18`, seed lại fixture Delivery idempotent và xác nhận PostgreSQL healthy.
- Chạy backend trên `http://localhost:8000`, frontend trên `http://localhost:5173`.
- Chạy live Groq turn qua Delivery API: Lead chọn `Apollo`, agent trả brief `success`, có
  `agent_response`, source, milestone, overdue, due-soon và blocked item.
- Xác nhận policy live: Lead thấy `Apollo, Release 34`; Member không được chọn group workspace;
  Outsider bị từ chối `403`.
- Xác nhận audit `delivery_brief.generated` được ghi đúng `workspace_id` trên database local.

## Artifact thêm/sửa

- `src/db/migrations/versions/20260824_18_repair_audit_log_schema.py`
- `tests/test_workspace_migration.py`
- `.env` development: `DATABASE_URL` chuyển sang PostgreSQL local; secret Groq hiện có được giữ nguyên.

## Bug phát hiện và cách sửa

### Legacy `audit_logs` thiếu workspace columns

- **Reproduce:** live Delivery brief hoàn tất phần tool/LLM nhưng trả HTTP 500 khi ghi audit.
- **Classify:** `schema`.
- **Root cause:** migration workspace cũ chỉ tạo `audit_logs` khi bảng chưa tồn tại; database legacy đã
  có bảng nên Alembic ở head nhưng thiếu `workspace_id` và `ip_address`.
- **Fix:** migration repair idempotent bổ sung column, foreign key và index còn thiếu mà không xóa
  audit data; downgrade cố ý không xóa các cột vốn đã thuộc contract từ revision cũ.
- **Regression:** tạo SQLite ở revision `20260822_17`, thay bằng audit table legacy, upgrade head hai
  lần và kiểm tra đủ column/index/revision.

### Runtime vô tình trỏ database ngoài local

- **Reproduce:** process cũ nạp `DATABASE_URL` Supabase từ `.env`.
- **Classify:** `infrastructure` / configuration.
- **Fix:** dừng worker cũ, đổi `.env` sang PostgreSQL local, migrate + seed lại và xác minh target
  `localhost:5432/orbit` trước live smoke.

## Kiểm thử và evidence

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\test_workspace_migration.py `
  tests\test_agent_workspaces.py `
  tests\test_agents\test_workspace_delivery_graph.py `
  tests\test_agents\test_product_delivery_runner.py `
  tests\test_agents\test_product_delivery_executor.py `
  tests\test_agents\test_product_delivery.py `
  tests\test_agents\test_delivery_tools.py `
  tests\test_agents\test_delivery_scope.py `
  tests\test_agents\test_delivery_milestones_people.py `
  tests\test_agents\test_delivery_messages.py `
  tests\test_agents\test_delivery_brief.py `
  tests\test_agents\test_delivery_api.py -q
```

Kết quả: **78 passed**, 24 deprecation warnings từ adapter SQLite; không có test failure sau fix.
Ruff trên migration/test/runtime liên quan: **passed**.

Frontend production build: **passed**, 737 modules transformed. Vite còn cảnh báo chunk Calendar lớn
hơn 500 kB; cảnh báo này không chặn Delivery demo nhưng cần code-split trước tối ưu production.

Live smoke: login `200`, capability `200`, brief `200/success`, agent response có nội dung, audit đúng
workspace; member capability `200/can_select_group=false`, outsider `403`.

## Known limits và bước tiếp theo

- Local demo đang dùng dữ liệu synthetic; chưa phải production data migration rehearsal.
- Chưa có browser automation cho toàn bộ thao tác click; API E2E và frontend production build đã xanh.
- Admin persona và consent revoke/HITL E2E đầy đủ vẫn thuộc B6-03/B6-04 tiếp theo.
- Reminder/meeting executor tiếp tục disabled cho tới A-DLV-05; checkpoint này không tạo side effect.
- Trước release cần xử lý Calendar chunk warning, chạy performance/latency-token evidence và staging
  rehearsal trên database tách biệt.

## Plan-alignment review

| Plan task/capability | Trạng thái thực | Evidence | Phạm vi còn thiếu / gate |
|---|---|---|---|
| A-DLV-06/07/09 | complete (local code gate) | Lead/member/outsider live smoke; scoped capability + task source tests | Cần platform owner duyệt trước production |
| B6-01/B6-02 | complete | PostgreSQL local migrate head + idempotent seed; migration regression | Cần staging data rehearsal |
| B6-03 | partial | Lead/member/outsider live authorization | Còn admin persona browser/API E2E |
| B6-04 | partial | Revalidation/security unit-integration tests | Còn consent revoke/HITL live E2E; A-DLV-05 |
| B6-06 / §14.10 | complete (local demo) | Apollo brief live qua Groq, source/gap/audit có evidence | Rehearse lại trên staging trước demo chính thức |
| B11 | complete (checkpoint scope) | Agentic graph, guardrail, tool, scope, hallucination/source regression trong bộ 78 test | Production eval dataset vẫn là release gate riêng |
| B12 | partial | UI route + production build + runbook + live turn | Còn latency/token evidence và browser automation |

Kết luận: checkpoint 12 khép lại blocker của checkpoint 11 và chứng minh Delivery Workspace Agent
chạy end-to-end bằng LLM trên database local. Nó không mở rộng tuyên bố sang side-effect hoặc
production release khi các gate nêu trên chưa hoàn tất.
