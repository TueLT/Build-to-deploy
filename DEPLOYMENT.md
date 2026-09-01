# Deploy Orbit

Nhánh `deploy` hỗ trợ hai topology:

- `render.yaml`: bản demo miễn phí, một Render Web Service chạy Core API cùng Product Delivery và
  Quality Assurance ở chế độ embedded, kèm một Render Postgres Free.
- `render.production.yaml`: bản production tách hai agent thành private service và dùng PostgreSQL
  trả phí có độ bền dữ liệu tốt hơn.

Hai frontend vẫn là hai Vercel project riêng:

- User SPA: `Frontend/user`
- Admin SPA: `Frontend/admin`

## 1. Giới hạn của bản miễn phí

Topology miễn phí giữ nguyên API, phân quyền, database schema và logic hai agent, nhưng chỉ phù hợp
demo hoặc đồ án:

- Web Service có thể ngủ sau thời gian không có request; lần mở đầu tiên sẽ chậm.
- Core API, WebSocket, scheduler và hai agent dùng chung 512 MB RAM/0.1 CPU.
- `WORKSPACE_AGENT_MAX_CONCURRENCY=1` để tránh quá tải instance.
- Render Postgres Free chỉ có 1 GB, không có managed backup và hết hạn sau 30 ngày.
- OpenRouter/Google vẫn có quota hoặc chi phí API riêng; hạ tầng miễn phí không làm LLM miễn phí.

Không dùng topology này cho dữ liệu cần lưu lâu dài. Luôn giữ bản dump P132 cục bộ.

## 2. Đưa nhánh deploy lên GitHub

CI chạy Ruff, migration PostgreSQL, toàn bộ pytest, frontend audit và hai production build. Render chỉ
tự deploy sau khi check của commit trên nhánh `deploy` thành công.

```powershell
git push -u origin deploy
```

Không commit `.env`, `.env.local`, file `*.dump` hoặc secret.

## 3. Tạo Render Blueprint miễn phí

Tạo Blueprint từ `render.yaml`, branch `deploy`. Review phải chỉ có đúng hai tài nguyên và tổng compute
price phải là `$0/month`:

- `orbit-postgres` — Free PostgreSQL
- `orbit-backend` — Free Web Service

Nếu Render hiển thị hai private agent hoặc giá `$44.50/month`, Blueprint đang đọc commit/cấu hình cũ;
hủy flow đó và sync lại nhánh `deploy` mới nhất.

Điền các biến `sync: false` trong lần tạo đầu tiên:

| Biến | Giá trị ban đầu |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter key thật |
| `CORS_ORIGINS` | `https://orbit.invalid` cho lần tạo đầu; thay bằng hai Vercel origin sau |
| `OPENROUTER_SITE_URL` | `https://orbit.invalid` cho lần tạo đầu |
| `FRONTEND_ORIGIN` | `https://orbit.invalid` cho lần tạo đầu |
| `GOOGLE_OAUTH_CLIENT_ID` | Client ID đăng nhập Google; có thể để trống nếu không dùng |
| `GOOGLE_CALENDAR_CLIENT_ID` | Calendar OAuth client ID; có thể để trống nếu không dùng |
| `GOOGLE_CALENDAR_CLIENT_SECRET` | Calendar OAuth secret; có thể để trống nếu không dùng |
| `GOOGLE_CALENDAR_REDIRECT_URI` | `https://orbit.invalid/api/v1/calendar/oauth/callback` lúc tạo đầu |
| `CREDENTIAL_ENCRYPTION_KEY` | Phải giống key local nếu import database P132 |
| `INITIAL_ADMIN_EMAIL` | Email admin tin cậy, ví dụ `fanbox2004@gmail.com` |

`SECRET_KEY` và `DATABASE_URL` được Blueprint nối/tạo tự động. Không upload toàn bộ `.env` local.

Sau khi Blueprint hoàn tất, lấy URL thật của backend, ví dụ
`https://orbit-backend.onrender.com`, rồi kiểm tra:

```text
https://<backend>/health
```

## 4. Chuyển database P132 hiện tại lên Render

Không restore file `p132-before-delete-workspace-17db-...dump`, vì đó là backup trước khi xóa workspace
phụ. Hãy dump trực tiếp database local hiện tại bằng script.

1. Suspend `orbit-backend` để không có request hoặc scheduler ghi dữ liệu.
2. Trong `orbit-postgres`, tạm cho phép IP hiện tại và copy **External Database URL**.
3. Chạy:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/migrate_p132_database.ps1 `
  -TargetDatabaseUrl "postgresql://<user>:<password>@<host>/<database>"
```

Script tạo dump P132 mới, backup target và hỏi xác nhận trước khi thay schema `public`. Sau khi restore:

1. Gỡ IP public vừa cho phép.
2. Xác nhận `CREDENTIAL_ENCRYPTION_KEY` trên Render vẫn giống local.
3. Resume/redeploy `orbit-backend`; startup command tự chạy `alembic upgrade head`.
4. Kiểm tra `/health` và log migration.

## 5. Tạo hai Vercel project

Import cùng Git repository hai lần, chọn Production Branch là `deploy`.

| Project | Root Directory | Build | Output |
|---|---|---|---|
| Orbit User | `Frontend/user` | `npm run build` | `dist` |
| Orbit Admin | `Frontend/admin` | `npm run build` | `dist` |

Không override Install Command vì `vercel.json` đã dùng lockfile tại `Frontend/package-lock.json`.

User project:

```text
VITE_API_BASE_URL=https://<backend>/api/v1
VITE_WS_BASE_URL=wss://<backend>/api/v1/ws
VITE_ADMIN_APP_URL=https://<admin-vercel-domain>
VITE_GOOGLE_CLIENT_ID=<optional-google-sign-in-client-id>
VITE_SUPPORT_EMAIL=<oauth-support-email>
```

Admin project:

```text
VITE_API_BASE_URL=https://<backend>/api/v1
VITE_USER_APP_URL=https://<user-vercel-domain>
```

## 6. Cập nhật origin thật trên Render

Sau khi biết hai domain Vercel, mở Environment của `orbit-backend` và cập nhật:

```text
CORS_ORIGINS=https://<user-domain>,https://<admin-domain>
FRONTEND_ORIGIN=https://<user-domain>
OPENROUTER_SITE_URL=https://<user-domain>
GOOGLE_CALENDAR_REDIRECT_URI=https://<backend>/api/v1/calendar/oauth/callback
```

The User deployment also exposes the public pages required by Google OAuth Branding:

```text
Homepage:       https://<user-domain>/
Privacy Policy: https://<user-domain>/privacy
Terms:          https://<user-domain>/terms
```

In Google Auth Platform -> Data Access, register the least-privilege Calendar scope used by
Orbit: `https://www.googleapis.com/auth/calendar.events`.

Chọn **Save, rebuild, and deploy**.

## 7. Google OAuth nếu bật

- Google Sign-In: thêm User Vercel origin vào Authorized JavaScript origins.
- Google Calendar: thêm chính xác backend callback vào Authorized redirect URIs.
- Nếu consent screen còn Testing, thêm các Gmail thử nghiệm vào Test users.
- Google Sign-In và Google Calendar là hai OAuth client khác nhau.

## 8. Release smoke test

- Refresh nested route trên User và Admin không bị 404.
- Đăng nhập user/admin và thử một API cần quyền admin.
- Gửi/nhận WebSocket message.
- Chạy personal agent, Product Delivery và Quality Assurance.
- Xác nhận progress realtime của Product Delivery vẫn xuất hiện ở embedded mode.
- Tạo reminder và kiểm tra scheduler.
- Kết nối Calendar, tạo rồi xóa một event nếu OAuth được bật.
- Browser không gọi `localhost`, `ws://` hoặc agent hostname riêng.
- Sau cold start, thử lại khi `/health` đã trả 200.

Blueprint Free demo bật one-click demo login bằng cặp cờ
`DEMO_LOGIN_ENABLED=true` và `ALLOW_DEMO_LOGIN_IN_PRODUCTION=true`. Cấu hình production trả phí
giữ cả hai cờ ở `false`; không bật cờ thứ hai cho dữ liệu thật vì các tài khoản
demo cho phép đăng nhập công khai mà không cần mật khẩu.

## 9. Chuyển sang production trả phí

Khi cần fault isolation, không giới hạn database 30 ngày và scale agent độc lập, tạo Blueprint mới với
path `render.production.yaml`. Topology này khôi phục backend public, hai private agent runtime và
PostgreSQL trả phí. Không quản lý cùng một resource bằng hai Blueprint khác nhau.
