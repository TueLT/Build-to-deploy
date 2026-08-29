# Product Delivery Workspace Dashboard — Checkpoint 15

> Trạng thái: **complete / verified trong local integration scope**. Trang Workspaces đã được nâng từ launcher card
> thành dashboard Delivery có dữ liệu thật, phân quyền theo Lead/Member và không gọi LLM khi tải trang.

## Vấn đề được xử lý

Trang Workspaces cũ chỉ hiển thị tên workspace, Lead và nút mở Agent. Nó không trả lời được các câu hỏi quản trị cơ bản:

- Workspace có bao nhiêu nhóm và bao nhiêu người?
- Thành viên là ai, chức danh gì, tham gia nhóm nào?
- Tiến độ task/milestone hiện tại ra sao?
- Nhóm nào bị blocker, quá hạn hoặc cần chú ý?
- Mỗi người đang có bao nhiêu task, tỷ lệ hoàn thành và blocker thế nào?
- Hoạt động chat gần nhất của từng nhóm là gì?

## Đã triển khai

### Deterministic dashboard API

Thêm endpoint:

```text
GET /api/v1/workspaces/{workspace_id}/agent-workspaces/{agent_workspace_id}/delivery/dashboard
```

Endpoint này:

- Resolve business role và resource scope bằng Product Delivery policy hiện có.
- Revalidate từng group trước khi đọc.
- Chỉ query group đã link với Delivery agent workspace.
- Bind task và milestone theo cả organization workspace, agent workspace và conversation ID.
- Không gọi LLM, không tiêu tốn token Groq và không phụ thuộc chất lượng sinh văn bản.
- Trả `403` cho tài khoản ngoài Product Delivery workspace.

### Dashboard tổng quan

- Tên workspace, Agent profile, Lead và vai trò của người đang xem.
- Số group, member, task, milestone, task blocked và task overdue.
- Tỷ lệ task hoàn thành toàn scope.
- Cơ cấu task đang làm, chờ xử lý, bị chặn và sắp đến hạn.
- Banner giải thích scope và thời điểm cập nhật.

### Tiến độ theo group

Mỗi group hiển thị:

- Tên, trạng thái cần chú ý/đúng tiến độ.
- Số member và số message.
- Tỷ lệ task hoàn thành.
- Tổng task, đang làm, blocked và milestone.
- Danh sách avatar/tên thành viên.
- Tin nhắn gần nhất và thời gian hoạt động.
- Trạng thái AI group.
- Chi tiết toàn bộ task/milestone được phép: title, owner, due date, status, blocker reason.
- Deep link mở đúng group chat.

### Member directory

Mỗi người hiển thị:

- Tên, email và chức danh.
- Delivery Lead/Member hoặc group participant.
- Danh sách group đang tham gia.
- Task total/in-progress/blocked, milestone count và completion percentage.

Với tài khoản Member, workload của những người khác trả `null` và UI hiển thị `Ẩn theo quyền`; backend không gửi số liệu
của người khác rồi mới giấu bằng CSS.

## Phân quyền thực tế

| Persona | Group | Roster | Workload |
|---|---:|---:|---|
| Lead | 3 | 13 người trong Delivery scope | Toàn bộ task/milestone của ba group |
| Member Minh | 1 Apollo | 5 participant của Apollo | Chỉ task/milestone của Minh; workload người khác bị ẩn từ API |
| Outsider | 0 | 0 | HTTP 403 trước dashboard query |

Không dùng Company-wide member scan. Roster là hợp của participant trong `effective_group_ids` đã resolve.

## Dữ liệu live đã xác nhận

### Workspace Lead

- 3 group.
- 13 member.
- 15 task.
- 9 milestone.
- 3 group có blocker.
- Apollo: 5 member, 8 message, 5 task, 3 milestone, 20% completion.
- Customer Portal: 5 member, 8 message, 5 task, 3 milestone, 0% completion.
- Release 34: 5 member, 8 message, 5 task, 3 milestone, 20% completion.

### Member Minh Backend

- 1 group: Apollo Platform.
- 5 member trong group roster.
- 1 task được phép: `Hoàn thiện migration checklist`.
- 0 milestone được gán cho Minh trong dataset hiện tại.
- Không có task Customer Portal, Release 34 hoặc task của Apollo member khác trong response.

## Artifact

- `src/models/delivery_schemas.py`
- `src/api/delivery_routes.py`
- `Frontend/user/src/api/agent.js`
- `Frontend/user/src/pages/WorkspaceManagementPage.jsx`
- `Frontend/user/src/workspace-management.css`
- `tests/test_agents/test_delivery_api.py`
- `docs/ROLE_B_DELIVERY_DEMO_TEST_SCRIPT.md`

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m ruff check `
  src\api\delivery_routes.py `
  src\models\delivery_schemas.py `
  tests\test_agents\test_delivery_api.py
```

Kết quả: **passed**.

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\test_agents\test_delivery_api.py `
  tests\test_agent_workspaces.py -q
```

Kết quả: **16 passed**.

```powershell
cd Frontend
npm run build --workspace @orbit/user
```

Kết quả: **passed**, 717 modules transformed.

Live smoke:

- Lead dashboard: HTTP 200, khoảng 153 ms.
- Member dashboard: HTTP 200, khoảng 106 ms.
- Outsider dashboard: HTTP 403.
- Frontend `/workspaces`: HTTP 200.
- `git diff --check`: passed; chỉ có warning LF/CRLF trên Windows.

## Bug/failure trong quá trình kiểm thử

1. Script PowerShell đầu tiên ghép sai biến URL nên nhận 404. Kiểm tra lại URL cụ thể xác nhận route hoạt động; đây là lỗi
   test command, không phải API.
2. Lệnh build ghép sau pytest chạy tại repository root nên npm không tìm thấy `package.json`. Chạy lại tại `Frontend`
   và build pass. Không thay đổi code để che failure hạ tầng.

## Known limits

- Chưa có biểu đồ lịch sử tiến độ theo ngày/sprint vì hiện database chỉ có trạng thái hiện tại, chưa có task status history.
- Chưa có capacity estimate/story points nên workload chỉ dựa trên số task và status, không dùng message count làm productivity score.
- Chưa có semantic risk trend; trạng thái “cần chú ý” chỉ dựa trên blocked/overdue có cấu trúc.
- Browser automation vẫn cần bổ sung để screenshot/visual regression trên nhiều viewport.
- Calendar bundle warning vẫn tồn tại và không thuộc dashboard Delivery.

## Plan-alignment review

| Plan task/capability | Trạng thái | Evidence | Còn thiếu / gate |
|---|---|---|---|
| B4-02 Delivery UI | complete trong dashboard scope | KPI, group progress, roster, task/milestone details | Trend chart cần history store |
| B4-03 source/freshness/data gap | partial | Scope banner, generated_at, structured records | Deep-link từ task source tới message còn thiếu |
| B4-04 loading/empty/denied/error | complete trong local scope | Loading, no workspace, no assignment, API error states | Visual regression automation |
| B4-07 UI/build/smoke | complete trong local scope | Build pass, route 200, responsive CSS | Browser E2E còn partial |
| B6-03 persona E2E | partial | Lead/Member/Outsider live API matrix + regression test | Admin browser flow chưa tự động hóa |
| B12 conversational UI | không thay đổi | Dashboard không gọi LLM; Workspace Agent chat vẫn tách riêng | Latency/token telemetry của Agent turn |

## Kết luận

Trang Workspaces hiện là dashboard quản trị Delivery có dữ liệu thực, không còn là card mở Agent sơ sài. Lead có đủ
thông tin nhóm, thành viên và tiến độ để theo dõi vận hành; Member có góc nhìn nhóm/công việc hợp lệ mà không đọc được
workload riêng của đồng nghiệp hoặc group ngoài membership.
