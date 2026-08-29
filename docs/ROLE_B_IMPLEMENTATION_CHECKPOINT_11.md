# Product Delivery Agent — Demo Data and Runtime Readiness Checkpoint 11

> Trạng thái: **verified / partial**. Fixture, migration và unit/integration checks đã hoàn tất;
> smoke test live với Groq đang bị chặn bởi giới hạn connection session của PostgreSQL pooler.

> Cập nhật: blocker này đã được khép lại bằng PostgreSQL local và live Groq smoke tại
> [Checkpoint 12](ROLE_B_IMPLEMENTATION_CHECKPOINT_12.md). Phần dưới giữ nguyên làm lịch sử evidence.

## Đã triển khai

- Bổ sung `scripts/seed_delivery_demo.py`: seed idempotent, không xóa dữ liệu, từ chối
  `APP_ENV=production` và tạo Product Delivery demo data thật.
- Đã chạy migration lên `20260822_17 (head)` và seed thành công database development.
- Fixture gồm bốn account demo, một Product Delivery workspace, Apollo/Release 34 linked+AI enabled,
  QA unlinked, task blocked/overdue/due-soon, unassigned milestone và message evidence.
- Xác nhận qua Capability API với Lead: chỉ trả `Apollo, Release 34`; QA không nằm trong allowlist.
- Giữ Groq provider từ `.env` (`LLM_PROVIDER=groq`, model tool-calling đã cấu hình); bật hai feature
  flag Delivery cho môi trường demo.
- Hạ budget session: async DB pool `2+0`, LangGraph checkpointer tối đa 2, scheduler job store 1.
- Vá migration legacy: chuẩn hóa `memory_type` không hợp lệ (ví dụ `fact`) thành `semantic` trước
  constraint; làm migration SQLite/fresh-schema idempotent với future table/FK.

## Artifact

- `scripts/seed_delivery_demo.py`
- `src/config.py`, `src/agents/graph.py`, `src/services/scheduler.py`
- `src/db/migrations/versions/20260805_04_production_resources.py`
- `src/db/migrations/versions/20260810_07_strict_ai_consent.py`
- `src/db/migrations/versions/20260813_12_timeline_memory.py`
- `src/db/migrations/versions/20260822_16_delivery_task_binding.py`
- `src/db/migrations/versions/20260822_17_delivery_milestones.py`
- `tests/test_agents/test_delivery_api.py`, `tests/test_workspace_migration.py`
- `docs/ROLE_B_DELIVERY_AGENTIC_RUNBOOK.md`

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_agents\test_workspace_delivery_graph.py tests\test_agents\test_delivery_api.py tests\test_agents\test_product_delivery.py tests\test_agents\test_delivery_scope.py tests\test_agents\test_delivery_tools.py tests\test_agents\test_delivery_messages.py tests\test_agents\test_delivery_brief.py tests\test_workspace_migration.py tests\test_config.py -q
```

Kết quả: **61 passed**. Ruff và `git diff --check` xanh. Trong quá trình test đã phát hiện và sửa:

1. Seed dùng `@orbit.local`, bị email validator từ chối; chuyển sang `@example.com` và upsert theo
   deterministic ID để chạy lại vẫn cập nhật đúng fixture.
2. Test default-off đọc nhầm feature flag demo trong `.env`; test nay explicit dùng
   `Settings(_env_file=None)`, không gọi Groq thật.
3. Migration fail vì `memory_type=fact` legacy; chuẩn hóa trước constraint.
4. Fresh SQLite migration fail do future table/FK; thêm guard idempotent và test migration xanh.

## Live smoke và giới hạn

Login Lead và Capability API đã pass. Brief endpoint không thể hoàn tất live smoke vì Supabase session
pool báo `EMAXCONNSESSION` (limit 15); backend khởi động dừng ở LangGraph checkpointer. Đây là lỗi
hạ tầng/connection capacity, không phải policy hoặc LLM. Đã dừng các backend test do checkpoint khởi tạo.

Khi pool được giải phóng hoặc tăng limit, chạy lại backend rồi Lead brief để xác nhận Groq end-to-end.
Không bật production/release chỉ dựa vào fixture này.

## Plan-alignment review

| Plan capability | Trạng thái | Evidence | Còn lại |
|---|---|---|---|
| §14.10 synthetic demo seed | complete | seed script + DB `SEED COMPLETE` | Không dùng production data |
| B11 integration/security evidence | partial | 61 test, capability API allowlist | Groq live brief bị DB pool block |
| B12 demo readiness/runbook | partial | runbook + pool hardening | Cần live smoke sau khi DB capacity sẵn sàng |
