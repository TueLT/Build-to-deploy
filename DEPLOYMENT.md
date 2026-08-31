# Deploy Orbit

Kiến trúc production của nhánh `deploy`:

- Vercel project 1: User SPA (`Frontend/user`).
- Vercel project 2: Admin SPA (`Frontend/admin`).
- Render Blueprint: một backend public, hai agent runtime private và PostgreSQL 16.

Backend phải giữ đúng **một instance**. WebSocket manager và APScheduler hiện lưu trạng thái theo
process, vì vậy không bật horizontal scaling trước khi chuyển hai phần này sang hạ tầng dùng chung.

## 1. Đưa nhánh deploy lên GitHub

CI chạy trên `deploy`, gồm Ruff, hai ma trận feature flag, migration PostgreSQL sạch, toàn bộ pytest,
frontend audit và hai production build. Render Blueprint cũng theo dõi chính nhánh này và chỉ tự
deploy khi các check thành công.

Docker và CI cài từ `requirements.lock` để cùng một commit luôn dùng đúng bộ dependency đã kiểm thử.

```powershell
git push -u origin deploy
```

Không commit `.env`, `.env.local`, file `*.dump` hoặc bất kỳ secret nào.

## 2. Tạo Render Blueprint

Tạo Blueprint từ `render.yaml`. Blueprint tạo bốn tài nguyên cùng region `singapore`:

- `orbit-postgres`
- `orbit-backend`
- `orbit-agent-product-delivery`
- `orbit-agent-quality-assurance`

Điền các biến `sync: false` của backend trong lần tạo đầu tiên:

| Biến | Giá trị production |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter key thật |
| `CORS_ORIGINS` | Hai origin Vercel chính xác, cách nhau bằng dấu phẩy; không có `*` |
| `OPENROUTER_SITE_URL` | Origin User Vercel |
| `FRONTEND_ORIGIN` | Origin User Vercel |
| `GOOGLE_OAUTH_CLIENT_ID` | Client ID đăng nhập Google; có thể để trống nếu không dùng |
| `GOOGLE_CALENDAR_CLIENT_ID` | Calendar OAuth client ID; có thể để trống nếu không dùng |
| `GOOGLE_CALENDAR_CLIENT_SECRET` | Calendar OAuth secret; có thể để trống nếu không dùng |
| `GOOGLE_CALENDAR_REDIRECT_URI` | `https://<backend>/api/v1/calendar/oauth/callback` |
| `CREDENTIAL_ENCRYPTION_KEY` | Giữ nguyên key của database P132 nếu import dữ liệu cũ |
| `INITIAL_ADMIN_EMAIL` | Email được phép bootstrap platform admin đầu tiên |

`SECRET_KEY` và hai runtime secret do Render tự sinh. Database URL và private host/port được nối tự
động, không copy tay. Hai runtime ID trong Blueprint khớp với database P132 hiện tại.

Sau deploy, `https://<backend>/health` phải trả HTTP 200. Không đưa URL private của agent ra Vercel.

## 3. Chuyển đúng database P132 lên Render

`docker-compose.override.yml` local đang dùng volume `p-132_postgres_data`; volume này không thể được
gắn trực tiếp lên cloud. Dùng script dưới đây để dump đúng volume đó rồi restore sang Render.

1. Trong Render, suspend backend và hai private service để không có request/job ghi dữ liệu lúc restore.
2. Trong database `orbit-postgres`, tạm whitelist IP hiện tại và lấy **External Database URL**.
3. Chạy:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/migrate_p132_database.ps1 `
  -TargetDatabaseUrl "postgresql://<user>:<password>@<host>/<database>"
```

Script luôn tạo `orbit-p132.dump`, sao lưu target trước, hỏi xác nhận rồi mới thay schema `public`.
Sau khi thành công:

1. Gỡ IP public khỏi database (Blueprint mặc định `ipAllowList: []`).
2. Kiểm tra `CREDENTIAL_ENCRYPTION_KEY` trên Render giống key local; nếu khác, token Calendar đã import
   sẽ không giải mã được.
3. Resume/redeploy hai agent rồi backend. Pre-deploy command sẽ chạy `alembic upgrade head`.
4. Kiểm tra log không có `Runtime target mismatch`; Product Delivery ID là
   `9ff3ceb2b31f57238014e93e2402c0c8`, Quality Assurance ID là
   `311fe424edfa41989a495316b6925c84`.

File dump chứa toàn bộ dữ liệu và password hash, phải giữ kín và xóa an toàn sau khi xác nhận production.

## 4. Tạo hai Vercel project

Import cùng Git repository hai lần, chọn Production Branch là `deploy`.

| Project | Root Directory | Build | Output |
|---|---|---|---|
| Orbit User | `Frontend/user` | `npm run build` | `dist` |
| Orbit Admin | `Frontend/admin` | `npm run build` | `dist` |

Hai `vercel.json` chạy `npm ci --prefix ..` để dùng duy nhất lockfile của npm workspace tại
`Frontend/package-lock.json`; không override Install Command trong dashboard.

User project:

```text
VITE_API_BASE_URL=https://<backend>/api/v1
VITE_WS_BASE_URL=wss://<backend>/api/v1/ws
VITE_ADMIN_APP_URL=https://<admin-vercel-domain>
VITE_GOOGLE_CLIENT_ID=<optional-google-sign-in-client-id>
```

Admin project:

```text
VITE_API_BASE_URL=https://<backend>/api/v1
VITE_USER_APP_URL=https://<user-vercel-domain>
```

Khai báo các biến cho cả Production và Preview nếu dùng preview. Build production chủ động thất bại
nếu API/WebSocket/cross-app URL bị thiếu hoặc dùng giao thức không an toàn ngoài localhost.

Sau khi biết hai domain Vercel, cập nhật lại `CORS_ORIGINS`, `FRONTEND_ORIGIN`,
`OPENROUTER_SITE_URL` trên Render rồi redeploy backend.

## 5. Google OAuth (nếu bật)

- Google Sign-In client: thêm User Vercel origin vào Authorized JavaScript origins.
- Calendar client: thêm chính xác backend callback vào Authorized redirect URIs.
- Nếu consent screen còn Testing, thêm tất cả Gmail thử nghiệm vào Test users.
- Google Sign-In và Google Calendar là hai OAuth client khác nhau.

## 6. Release smoke test

- Refresh trực tiếp một nested route trên cả User và Admin không được 404.
- Đăng nhập user và admin; thử một request cần quyền admin.
- Gửi/nhận một tin qua WebSocket.
- Chạy một AI turn, một Product Delivery turn và một Quality Assurance turn.
- Tạo reminder và kiểm tra scheduler thực thi đúng timezone.
- Kết nối Google Calendar, tạo rồi xóa một event nếu OAuth được bật.
- Xác nhận login/chat burst bị giới hạn bằng HTTP 429.
- Xác nhận browser không gọi `localhost`, `ws://` hoặc private agent hostname.

One-click demo login bị vô hiệu cưỡng chế khi `APP_ENV=production`. Dữ liệu P132 vẫn được import, nhưng
không nên phát hành tài khoản có mật khẩu demo cố định trên một deployment chứa dữ liệu thật.
