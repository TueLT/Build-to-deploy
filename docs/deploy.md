# Deploy online

Tài liệu deploy chính thức đã được hợp nhất tại [`../DEPLOYMENT.md`](../DEPLOYMENT.md).

Không làm theo các bản hướng dẫn cũ dùng `main`, `ADMIN_BOOTSTRAP_KEY`, `deploy.yml` hoặc tạo thủ
công một database khác. Nhánh hiện tại deploy từ `deploy`, dùng Alembic và hỗ trợ hai Blueprint:

- `render.yaml`: demo miễn phí, một backend embedded và một PostgreSQL Free.
- `render.production.yaml`: production trả phí với hai private agent runtime.

Luôn kiểm tra tổng giá trên trang Review Blueprint trước khi nhấn Deploy.
