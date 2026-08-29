# Product Delivery Workspace Agent — Demo Test Script

> Kịch bản acceptance riêng cho stateful router, specialist artifact, handoff tuần tự và meeting plan:
> [PRODUCT_DELIVERY_MULTI_AGENT_ACCEPTANCE_TEST.md](PRODUCT_DELIVERY_MULTI_AGENT_ACCEPTANCE_TEST.md).

## 1. Điều kiện trước khi test

- PostgreSQL Docker: `localhost:5432/orbit`.
- Backend: `http://localhost:8000`.
- Frontend: `http://localhost:5173`.
- Trang nhóm: `http://localhost:5173/groups`.
- Chat nhóm: `http://localhost:5173/chat`.
- Workspace Agent riêng: `http://localhost:5173/workspace-agent`.
- Mật khẩu chung cho toàn bộ tài khoản demo: `Demo123!`.

Database canonical hiện có một Product Delivery Agent Workspace với:

- 1 active Lead.
- 12 active Member.
- 3 linked/AI-enabled group.
- Mỗi group có 5 participant, 8 message, 5 task và 3 milestone.

## 2. Ma trận quyền

| Persona | Agent Workspace role | Group scope | Có chọn một group | Dữ liệu task |
|---|---|---|---|---|
| Delivery Lead | `lead` | Cả 3 linked group | Có | Toàn bộ task/milestone trong scope |
| Delivery Member | `member` | Chỉ group đang tham gia | Không | Chỉ task/milestone được gán cho chính mình |
| Platform Admin | Không được gán | Không có | Không | Không tự động đọc dữ liệu Delivery |
| Outsider | Không được gán | Không có | Không | Bị từ chối trước tool/LLM |

Chỉ có **một active Lead** vì database có unique policy cho mỗi Agent Workspace. Admin là người quản trị
nền tảng, không đồng nghĩa với quyền đọc chat nghiệp vụ. Member không thể sửa request để chuyển thành
Lead hoặc truy vấn một group khác.

## 3. Tài khoản Lead

| Email | Tên | Chức danh | Group |
|---|---|---|---|
| `delivery-demo-lead@example.com` | Linh Delivery Lead | Head of Product Delivery | Apollo Platform, Customer Portal, Release 34 |

### Kịch bản L1 — Đăng nhập và kiểm tra capability

1. Mở `http://localhost:5173`.
2. Đăng nhập bằng Lead và mật khẩu `Demo123!`.
3. Mở `/groups`, xác nhận Lead thấy đúng ba group và có thể mở chat của từng group.
4. Mở `/workspace-agent` để vào cuộc chat riêng với Product Delivery Workspace Agent.
4. Xác nhận workspace hiển thị `Product Delivery Demo · lead`.
5. Mở selector Group.

Kết quả mong đợi:

- Có `Tất cả group được cấp quyền`.
- Có đúng `Apollo Platform`, `Customer Portal`, `Release 34`.
- Không có `QA Internal — not linked`.

### Kịch bản L2 — Tổng hợp toàn workspace

1. Chọn `Tất cả group được cấp quyền`.
2. Nhập:

```text
Tổng hợp blocker, deadline, người phụ trách và quyết định cần chốt của cả workspace.
```

3. Bấm `Hỏi Agent`.

Kết quả mong đợi:

- HTTP/API thành công và UI không hiển thị runtime gap.
- Phạm vi có 3 group và 13 người.
- Có 3 blocker chính: vendor sandbox Apollo, CRM UAT credential và crash rate iOS.
- Có 9 milestone.
- Câu trả lời có dòng `Nguồn:` trỏ về các group Delivery.
- Phần bằng chứng chat không chứa nội dung `QA-only evidence`.

### Kịch bản L3 — Chỉ định một group

1. Chọn `Apollo Platform`.
2. Nhập:

```text
Apollo đang bị chặn ở đâu, ai phụ trách và phương án xử lý là gì?
```

3. Bấm `Hỏi Agent`.

Kết quả mong đợi:

- Phạm vi chỉ còn 1 group và đúng 5 thành viên Apollo.
- Blocker là vendor sandbox trả lỗi 429.
- Người phụ trách được resolve thành tên, không chỉ có user ID.
- Bằng chứng chat và dòng nguồn chỉ thuộc Apollo.
- Dữ liệu Customer Portal, Release 34 và QA không xuất hiện.

Lặp lại với `Customer Portal` và `Release 34` để kiểm tra isolation giữa các team.

## 4. Tài khoản Member

| Email | Tên | Chức danh | Group |
|---|---|---|---|
| `delivery-demo-member@example.com` | Minh Backend | Backend Engineer | Apollo Platform |
| `delivery-demo-huy@example.com` | Huy Frontend | Frontend Engineer | Apollo Platform |
| `delivery-demo-lan@example.com` | Lan Product | Product Owner | Apollo Platform |
| `delivery-demo-duc@example.com` | Đức DevOps | DevOps Engineer | Apollo Platform |
| `delivery-demo-mai@example.com` | Mai Release | Release Manager | Release 34 |
| `delivery-demo-nam@example.com` | Nam Mobile | Mobile Engineer | Release 34 |
| `delivery-demo-thao@example.com` | Thảo Documentation | Technical Writer | Release 34 |
| `delivery-demo-phuc@example.com` | Phúc SRE | Site Reliability Engineer | Release 34 |
| `delivery-demo-an@example.com` | An UX | Product Designer | Customer Portal |
| `delivery-demo-vy@example.com` | Vy Analyst | Business Analyst | Customer Portal |
| `delivery-demo-son@example.com` | Sơn Integration | Integration Engineer | Customer Portal |
| `delivery-demo-huong@example.com` | Hương QA | QA Engineer | Customer Portal |

### Kịch bản M1 — My Work của Minh Backend

1. Đăng xuất Lead.
2. Đăng nhập `delivery-demo-member@example.com` / `Demo123!`.
3. Mở `/groups`, xác nhận Member chỉ thấy `Apollo Platform` và mở được lịch sử chat của nhóm.
4. Mở `/workspace-agent` để hỏi Agent trong scope Member.
4. Xác nhận role hiển thị `member` và selector không liệt kê các group để Member tự chọn.
5. Nhập:

```text
Công việc của tôi đang tiến triển thế nào, có deadline hoặc blocker gì?
```

6. Bấm `Hỏi Agent`.

Kết quả mong đợi:

- Scope nguồn chỉ là Apollo vì Minh chỉ tham gia Apollo.
- Task nhìn thấy thuộc `owner_id` của Minh, nổi bật là `Hoàn thiện migration checklist`.
- Không thấy task của Huy, Lan, Đức hoặc các team khác trong phần My Work.
- People/chat evidence có thể chứa thành viên và nội dung Apollo mà Minh được quyền đọc, nhưng agent
  không được biến chúng thành task cá nhân của Minh nếu owner không phải Minh.

### Kịch bản M2 — Negative authorization

- UI không cung cấp lựa chọn `Customer Portal` hay `Release 34` cho Member.
- Nếu sửa request thủ công để truyền `selected_conversation_id`, API phải trả `403`.
- Nếu dùng ID của QA/unlinked group, request phải bị từ chối trước database tool và LLM.

## 5. Admin và Outsider

| Email | Persona | Kết quả mong đợi |
|---|---|---|
| `delivery-demo-admin@example.com` | Platform Admin | Đăng nhập được nhưng không tự động có Product Delivery data scope |
| `delivery-demo-outsider@example.com` | Outsider | Không thấy Product Delivery workspace; direct capability API trả `403` |

### Kịch bản S1 — Chống nhầm Admin với trưởng phòng

1. Đăng nhập Admin.
2. Mở `/workspace-agent`.
3. Xác nhận trang báo chưa được gán vào Product Delivery workspace.

Đây là behavior đúng: quyền quản trị hệ thống không bypass membership/consent của chat doanh nghiệp.

### Kịch bản S2 — Outsider denial

1. Đăng nhập Outsider.
2. Mở `/workspace-agent`.
3. Xác nhận không có workspace để truy vấn.

Không được coi việc trả empty data là đủ; API trực tiếp phải trả `403` và không gọi Groq.

## 6. Tiêu chí demo đạt

- Lead tổng hợp được toàn workspace và drill-down từng group.
- Member chỉ nhận My Work và group evidence hợp lệ của mình.
- Group không linked không xuất hiện ở selector, snapshot hoặc câu trả lời.
- Tên người, task, deadline, blocker và source hiển thị nhất quán với database.
- Agent không tuyên bố reminder/meeting đã được thực hiện; action vẫn disabled cho tới HITL gate.
- Admin/Outsider không bypass business membership.

## 7. Kịch bản dashboard Workspaces

### W1 — Lead xem tổng quan quản trị

1. Đăng nhập `delivery-demo-lead@example.com` / `Demo123!`.
2. Mở `http://localhost:5173/workspaces`.
3. Xác nhận dashboard hiển thị 3 group, 13 member, 15 task và 9 milestone.
4. Kiểm tra từng group có 5 member, 8 message, 5 task và 3 milestone.
5. Mở phần chi tiết của group để xem title, owner, deadline, status và blocker reason.
6. Kiểm tra bảng member có chức danh, group tham gia, task count, completion percentage và blocker.
7. Bấm `Mở chat` ở một group và xác nhận điều hướng tới đúng hội thoại.

### W2 — Member xem scope cá nhân

1. Đăng nhập `delivery-demo-member@example.com` / `Demo123!`.
2. Mở `http://localhost:5173/workspaces`.
3. Xác nhận chỉ có Apollo Platform, roster gồm 5 participant và task của Minh là `Hoàn thiện migration checklist`.
4. Xác nhận workload của các member khác hiển thị `Ẩn theo quyền`.
5. Không được thấy Customer Portal, Release 34 hoặc task của người khác trong response/UI.
