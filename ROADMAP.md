# Roadmap — hoàn thiện "AI Agent Trợ lý cá nhân trong Chat" theo đề bài

Đề bài gốc: [Frontend/detai.md](Frontend/detai.md). Kiến trúc/quyết định công nghệ chi tiết:
[ARCHITECTURE.md](ARCHITECTURE.md). Tài liệu này chỉ theo dõi **tiến độ theo giai đoạn** — cập
nhật trạng thái mỗi khi một mục hoàn thành.

## Bảng hiện trạng (gap analysis)

| Yêu cầu | Trạng thái | Ghi chú |
| --- | --- | --- |
| Deploy online, đăng nhập, ≥2 role | 🟡 Một phần | Auth+role xong; `docker-compose.yml` chỉ có backend, chưa deploy thật, chưa có CD |
| Tóm tắt hội thoại theo yêu cầu | 🟢 Xong | Nút Summarize trong `AIPanel.jsx` đã nối `/api/v1/chat` thật |
| Trích xuất task + tạo nhắc việc có xác nhận | 🔴 Chưa có | Không có tool/table nào cho "task"; `TaskPage.jsx` 100% mock (nhưng shape mock đã khớp sẵn) |
| Hiển thị lịch cá nhân | 🔴 Chưa có | `calendar_tool.py` có `list_calendar_events` thật nhưng `CalendarPage.jsx` chưa gọi |
| Memory hội thoại | 🟡 Một phần | Chỉ có memory trong 1 thread (LangGraph `MemorySaver`, mất khi restart), không có memory dài hạn |
| Xử lý lỗi cơ bản | 🟡 Một phần | Lỗi LLM bị nuốt thành response rỗng thay vì báo lỗi rõ cho user |
| Reminder có xác nhận | 🟡 Một phần | `reminder_tool.py` có human-in-the-loop nhưng lưu in-memory, mất khi restart, không đẩy realtime khi fired |
| Agent chủ động phát hiện cam kết | 🔴 Chưa có | WebSocket `send_message` handler không có bước phân tích nào |
| Đồng bộ Google Calendar 2 chiều | 🔴 Chưa có | Chỉ tạo (ghi 1 chiều) + đọc rời rạc, không sync/diff |
| Dashboard "inbox nhiệm vụ" ưu tiên | 🔴 Chưa có | Mock only |
| Cảnh báo vượt hạn mức token/chi phí | 🔴 Chưa có | Không có usage tracking |
| Đánh giá độ chính xác trích xuất task | 🔴 Chưa có | Không có eval harness |

🟢 Xong · 🟡 Một phần · 🔴 Chưa có

## Giai đoạn 0 — Hạ tầng nền (làm trước, mọi giai đoạn sau phụ thuộc vào đây)

- [ ] Migrate SQLite → PostgreSQL (Supabase): `alembic init`, migration đầu từ schema hiện tại,
      thêm driver `asyncpg`, cập nhật `_async_url()` trong `src/db/session.py`.
- [ ] Bảng `ai_permissions` (conversation_id, user_id, granted, scope) + endpoint
      `GET/PUT /api/v1/conversations/{id}/ai-permission`, thay cho toggle local trong `AIPanel.jsx`.
- [ ] Sửa `_build_chat_response` (`src/api/routes.py`) để trả lỗi rõ ràng thay vì response rỗng
      khi `planner_node` bắt exception.

## Giai đoạn 1 — Hoàn thành "Cơ bản" còn thiếu

- [ ] **Trích xuất Task**: tool `extract_tasks` (`src/agents/tools/task_tool.py`) + bảng `tasks`,
      nối nút "Extract tasks" đã có sẵn (chưa có onClick) trong `AIPanel.jsx`.
- [ ] **Reminder bền vững + realtime**: bảng `reminders`, `src/services/reminder_service.py` dùng
      chung cho LangGraph tool và endpoint `POST /api/v1/tasks/{id}/confirm`; `_fire_reminder` đẩy
      WebSocket khi đến giờ.
- [ ] **Lịch cá nhân thật**: `CalendarPage.jsx` nối `GET /api/v1/calendar/events` (dựa trên
      `list_calendar_events` đã có).
- [ ] **Memory dài hạn**: bật `chromadb`, `src/services/memory_service.py`, `planner_node.py`
      truy vấn top-k memory liên quan trước khi trả lời, `MemoryPage.jsx` nối API thật.
- [ ] **Deploy online thật**: backend lên Render/Railway, frontend lên Vercel, DB Supabase (Giai
      đoạn 0), thêm `.github/workflows/deploy.yml`.

## Giai đoạn 2 — "Nâng cao"

- [ ] **Agent chủ động**: hook phân tích trong `src/websocket/routes.py` sau khi tin nhắn mới tới
      (chỉ chạy nếu `ai_permissions` cho phép + lọc rẻ trước để tiết kiệm chi phí) → tool
      `detect_commitment` → tạo `tasks` row `source="proactive"` → đẩy WS event `"suggestion"`.
      Không tự tạo reminder — vẫn cần người dùng xác nhận trong dashboard.
- [ ] **Đồng bộ Google Calendar 2 chiều**: polling định kỳ qua `syncToken`, bảng `calendar_events`
      cache local, lưu `google_event_id` khi tạo event từ app.
- [ ] **Dashboard inbox ưu tiên**: `TaskPage.jsx` nối `GET /api/v1/tasks` (sort priority + due_at),
      tái dùng `TaskTable.jsx`.
- [ ] **Cảnh báo token/chi phí**: bảng `llm_usage`, setting `monthly_token_budget`, stat card cảnh
      báo trong `AdminDashboardPage.jsx`.
- [ ] **Eval harness**: `tests/eval/fixtures/*.json` + `scripts/eval_task_extraction.py` tính
      precision/recall cho `extract_tasks`.

## Thứ tự ưu tiên nếu thời gian có hạn

Giai đoạn 0 → 1 là **bắt buộc** (điểm sàn "Cơ bản"). Trong Giai đoạn 2, ưu tiên theo thứ tự:
1. Agent chủ động — điểm nhấn rõ nhất của đề bài.
2. Dashboard inbox — tận dụng UI có sẵn, effort thấp.
3. Eval harness — dễ làm, chứng minh độ chính xác cho giám khảo.
4. Cảnh báo chi phí — effort thấp.
5. Đồng bộ Calendar 2 chiều — effort cao nhất, ưu tiên thấp nhất nếu thiếu thời gian.

## Ngoài phạm vi (quyết định có chủ đích)

- Không đổi frontend sang Next.js, không đổi backend sang NestJS.
- Không tự implement mã hoá E2E thật cho tin nhắn — thay vào đó thực thi đúng tinh thần "chỉ đọc
  hội thoại được cấp quyền" qua bảng `ai_permissions` (Giai đoạn 0).
- Không dùng BullMQ/Redis/Socket.IO — giữ nguyên APScheduler + WebSocket thuần đã có.

---
Mỗi mục ở trên đủ lớn để cần một phiên plan + review riêng trước khi code — không gộp chung nhiều
mục vào 1 lần triển khai.
