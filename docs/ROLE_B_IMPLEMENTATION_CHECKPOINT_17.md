# Personal Scope Consistency & Provisioning — Checkpoint 17

> Trạng thái: **complete / verified trong local Docker integration scope**. Checkpoint sửa invariant dữ liệu, API contract
> và UI context giữa Personal với Organization Workspace; không tuyên bố R4 tách Personal thành service đã hoàn thành.

## 1. Mục tiêu và kết quả

Loại bỏ lỗi `User has no personal workspace` khỏi luồng người dùng Personal bằng cách sửa nguyên nhân gốc: một số tài khoản
demo/import được tạo trực tiếp nên không đi qua registration provisioning. Sau checkpoint:

- Mọi tài khoản hiện có trong PostgreSQL có đúng một Personal Space nội bộ.
- Password login, Google login, registration và Delivery demo seed cùng dùng một hàm ensure idempotent.
- Personal UI không cần biết hoặc gửi Personal Workspace ID.
- Personal Assistant không thể bị đổi sang Organization scope chỉ bằng `workspace_id` không kèm conversation đã cấp quyền.
- Navbar phân biệt rõ “Không gian cá nhân” và selector Organization Workspace.

## 2. Artifact đã triển khai

- `src/services/workspace_service.py`: thêm `ensure_personal_workspace()` có row lock, repair trạng thái và
  `resolve_personal_workspace_for_user()`; giữ alias provisioning cũ để tương thích.
- `src/api/auth_routes.py`: register/password login/Google login đều enforce invariant trước khi hoàn tất auth transaction.
- `src/db/migrations/versions/20260824_19_backfill_personal_workspaces.py`: backfill mọi user thiếu Personal Space,
  idempotent và không downgrade phá dữ liệu.
- `scripts/seed_delivery_demo.py`: 15 demo account đều được provision Personal Space kể cả khi seed lặp.
- `src/api/routes.py`, `src/models/schemas.py`: Personal Assistant không conversation tự resolve từ JWT; client-supplied
  `workspace_id` không còn là cách chọn scope Personal.
- `Frontend/user/src/components/layout/TopNavbar.jsx`, `Frontend/shared/styles.css`: context Personal/Organization tách rõ;
  selector Workspace chỉ liệt kê organization.
- `tests/test_auth.py`, `tests/test_delivery_demo_seed.py`, `tests/test_workspace_migration.py`: regression cho legacy login,
  bốn Personal flow, seed idempotency và migration backfill.

## 3. Nghiệp vụ và security behavior

```text
Lead/Member login
  -> ensure exactly one Personal Space
  -> JWT
  -> Personal Assistant / Tasks / Memory / Reminders
  -> server resolves Personal Space by user_id
  -> no organization workspace_id required
```

Organization Workspace vẫn dùng membership và business role riêng. Chat có `conversation_id` tiếp tục resolve workspace từ
conversation đã qua participant/AI-consent check; ID do client gửi chỉ dùng đối chiếu consistency, không cấp quyền.

Nếu invariant bị phá sau migration/provisioning, backend trả lỗi server-side `Personal Space provisioning is incomplete`
thay vì hướng người dùng sửa một `workspace_id` mà họ không có trách nhiệm quản lý.

## 4. Kiểm thử và evidence

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_auth.py tests/test_delivery_demo_seed.py -q
```

Kết quả: **11 passed**.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_workspace_migration.py -q
```

Kết quả: **10 passed**; database mới, legacy audit table và post-foundation user đều migrate đúng.

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m pytest -q
```

Kết quả: Ruff **passed**; full regression **435 passed, 1 skipped, 30 warnings** trong khoảng 5 phút 58 giây.

```powershell
cd Frontend\user
npm run build
```

Kết quả: **passed**, 717 modules transformed. Cảnh báo Calendar chunk >500 kB là known warning ngoài scope.

`git diff --check`: không có whitespace error; chỉ có cảnh báo line-ending LF/CRLF trên Windows.

## 5. Docker và live smoke

- Compose config hợp lệ; PostgreSQL, backend và Product Delivery runtime đều healthy.
- Backend startup chạy migration `20260824_18 -> 20260824_19` thành công.
- Delivery fixture seed lại thành công: 15 users, 3 linked groups, 24 messages, 15 tasks, 9 milestones.
- SQL audit thực tế: `users_without_personal_space = 0`.
- Lead `delivery-demo-lead@example.com`: login, Tasks, Memories, Reminders đều HTTP 200 không truyền `workspace_id`;
  có đúng một Personal Space.
- Member `delivery-demo-member@example.com`: cùng bốn gate đều HTTP 200 và có đúng một Personal Space.
- Live Personal AI với câu ngoài domain trả HTTP 200 + clarification an toàn, không còn trả lỗi thiếu Personal Workspace.
- Frontend development server đang phục vụ HTTP 200 tại `http://localhost:5173`.

## 6. Bug/failure phát hiện và đã sửa

1. Root cause `test_fixture/provisioning`: demo seed tạo User trực tiếp nhưng không tạo Personal Space. Sửa bằng shared ensure
   service + seed regression.
2. Root cause `legacy_data`: migration foundation chỉ backfill user tồn tại tại thời điểm cũ; user thêm sau có thể thiếu.
   Sửa bằng revision 19 và login self-healing.
3. Root cause `API boundary`: Personal Agent từng chấp nhận organization `workspace_id` khi không có conversation, làm mờ
   ranh giới Personal/Workspace. Sửa bằng principal-only resolve và validation 422 cho request sai contract.
4. Root cause `UI context`: navbar luôn hiển thị selector Organization kể cả màn Personal. Sửa route-aware context và lọc
   chỉ organization workspace.
5. Migration regression ban đầu fail vì hai expected head revision vẫn là `20260824_18`; cập nhật expected và thêm test
   riêng cho backfill 19, sau đó toàn bộ suite xanh.

## 7. Known limits

- Personal Space vẫn là namespace DB nội bộ trong cùng schema; checkpoint không tách Personal Agent thành container/service.
- Tasks/Memory/Reminders API vẫn hỗ trợ `workspace_id` tùy chọn cho các luồng workspace-scoped có chủ đích; khi bỏ trống,
  contract mặc định là Personal và không yêu cầu frontend biết ID nội bộ.
- Calendar production còn phụ thuộc credential Google của từng user; invariant Personal Space không tự tạo OAuth credential.
- Calendar bundle size warning cần một performance checkpoint riêng, không ảnh hưởng tính đúng của scope.

## 8. Plan-alignment review

| Plan task/capability | Trạng thái | Evidence | Còn thiếu / gate |
|---|---|---|---|
| PERS-01 Provisioning invariant | `complete` | auth/seed tests; DB audit = 0 missing | Staging migration rehearsal |
| PERS-02 Personal API contract | `complete` local | Lead/Member live HTTP 200; Personal AI smoke | Browser E2E automation |
| PERS-03 Migration | `complete` local | revision 19 + 10 migration tests | Production backup/change window |
| PERS-04 UI boundary | `complete` build scope | route-aware navbar; production build | Visual browser regression automation |
| PERS-05 Regression | `complete` local | Ruff, 435/1, build, live Docker | CI/staging gate |
| R4 Personal service extraction | `not_started` | Personal remains inside Core | Requires R3 design/implementation |
| Product Delivery agent behavior | `unchanged` | 117-agent suite included in full regression | Existing Role B gates remain as report 16 |

## 9. Kết luận

Lỗi không còn được “che” ở UI mà đã được loại bỏ tại invariant dữ liệu và provisioning lifecycle. Personal features giờ có
contract nhất quán: user đăng nhập là đủ, server tự resolve Personal Space; Organization Workspace chỉ xuất hiện ở các luồng
Workspace có membership/scope rõ ràng. Local database, backend và frontend đã sẵn sàng để test lại bằng Lead hoặc Member.
