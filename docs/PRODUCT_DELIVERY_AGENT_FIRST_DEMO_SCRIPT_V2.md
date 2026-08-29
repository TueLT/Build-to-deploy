# Product Delivery Agent-first Multi-Agent — kịch bản demo Lead và Member

> Ngày kiểm chứng: 2026-08-27  
> UI: `http://localhost:5173/workspace-agent`  
> Mục tiêu: chứng minh cùng một Product Delivery Workspace Agent nhưng phạm vi dữ liệu, quyền nghiệp vụ và workflow agent được xác định theo vai trò thực của người đăng nhập.

## 1. Thông điệp nghiệp vụ của buổi demo

Người dùng chỉ giao tiếp với **Product Delivery Workspace Agent**. Workspace Agent nhận yêu cầu, ủy quyền cho một hoặc nhiều specialist agent, kiểm tra kết quả rồi trả một câu trả lời thống nhất.

- Lead dùng agent để quan sát toàn workspace, drill-down group, phân tích blocker/risk/plan, quản lý control plane và release handoff.
- Member dùng cùng agent nhưng chỉ trong group được cấp quyền và task/milestone thuộc chính mình.
- Vai trò không được lấy từ nội dung prompt. Backend lấy vai trò từ `agent_workspace_memberships` và tính lại source scope trước khi gọi tool/LLM.
- Agent không làm tăng quyền của người dùng. Kết quả agent trước cũng không cấp thêm quyền cho agent sau.

## 2. Điều kiện và tài khoản

Các service cần ở trạng thái ready:

| Thành phần | Địa chỉ |
|---|---|
| Frontend | `http://localhost:5173` |
| Backend | `http://localhost:8000` |
| Product Delivery runtime | `http://localhost:8010` |
| QA runtime | `http://localhost:8011` |
| PostgreSQL | `localhost:5432` |

Tài khoản:

| Persona | Email | Mật khẩu |
|---|---|---|
| Delivery Lead | `delivery-demo-lead@example.com` | `Demo123!` |
| Delivery Member | `delivery-demo-member@example.com` | `Demo123!` |
| Outsider đối chứng | `delivery-demo-outsider@example.com` | `Demo123!` |

The current idempotent fixture also provides 3 Delivery groups, 13 assigned Delivery members,
24 source messages, 15 tasks, 9 checkpoints, 3 dependencies and 3 decisions. QA test data
provides 2 groups, 5 assigned members, 8 work items and release `R-DEMO`.

During a business request, the response area displays the live orchestration phases and only
the specialists selected for that request. For example, `tiến độ task của các nhóm như thế nào rồi`
shows `task_intelligence` and `planning_forecast`, then completes synthesis; a greeting must not
show a business specialist DAG.

Product Delivery Demo hiện có 3 group được liên kết, 15 task và 9 milestone. Dashboard Lead hiện hiển thị 14 participant duy nhất; bảng membership của Agent Workspace có 1 Lead và 12 Member. Một participant trong Customer Portal chưa có Agent Workspace membership, được ghi ở mục phát hiện cuối tài liệu.

## 3. Ma trận quyền cần chứng minh

| Năng lực | Lead | Member |
|---|---:|---:|
| Sử dụng Product Delivery Workspace Agent | Có | Có |
| Xem toàn bộ 3 linked group | Có | Không |
| Chọn một group để phân tích | Có | Không |
| Xem task/milestone toàn scope được chọn | Có | Không |
| Xem task của chính mình | Có | Có |
| Phân tích blocker bằng multi-agent | Có | Có, nhưng chỉ trên dữ liệu Member scope |
| Quản lý dependency/decision control plane | Có | Không |
| Quản lý release handoff | Có | Không |
| Tạo action proposal | Có | Có |
| Cập nhật task của chính mình qua policy/HITL | Có | Có |
| Xem workflow của người khác | Có | Không |
| Truy cập group/workspace không được cấp quyền | Không | Không |

Capability envelope đã kiểm chứng:

```text
Lead   : view_scope=workspace, can_select_group=true,
         can_manage_control_plane=true, can_manage_release_handoffs=true
Member : view_scope=member, can_select_group=false,
         can_manage_control_plane=false, can_manage_release_handoffs=false
```

## 4. Kịch bản demo Lead — 8 phút

### L1. Đăng nhập và chứng minh capability

1. Đăng nhập bằng `delivery-demo-lead@example.com` / `Demo123!`.
2. Mở menu **Workspace Agent**.
3. Xác nhận workspace là **Product Delivery Demo** và role là `lead`.
4. Mở group selector.

Kết quả đạt:

- Có lựa chọn toàn bộ workspace.
- Có đúng `Apollo Platform`, `Customer Portal`, `Release 34`.
- Không có group QA/unlinked.
- Lead có control plane, approval queue và release handoff UI.

### L2. Một specialist agent cho truy vấn task chính xác

Chọn toàn workspace và nhập:

```text
Xem task 36d178c086d15d2ea84c17314ba8ea2e
```

Kết quả đạt:

- UI hiển thị `Workspace Agent → Specialist`.
- Intent là `task_lookup`.
- Specialist là `Task Intelligence`.
- Tool là `get_delivery_task_details`.
- Có ít nhất 2 LLM call: specialist và Workspace Agent response/synthesis boundary.
- Task trả về là `Ổn định vendor sandbox cho OAuth E2E`, trạng thái `blocked`.
- Workflow ID, model, prompt version, token usage và tool call được lưu trong backend.

Điểm thuyết trình: đây không phải đường đọc database rồi gắn nhãn Agent. Task Intelligence thực sự gọi tool được cấp quyền, dùng LLM giải thích kết quả và trả typed result cho Workspace Agent.

### L3. Multi-agent phân tích blocker toàn workspace

Nhập:

```text
Phân tích blocker hiện tại và ảnh hưởng tới kế hoạch giao hàng của toàn workspace.
```

Kết quả đạt:

```text
Task Intelligence
  -> Risk & Dependency
  -> Planning & Forecast
  -> Workspace Agent tổng hợp
```

- UI hiển thị `Workspace Agent → Multi-agent DAG`.
- Task Intelligence chạy trước.
- Risk và Planning nhận upstream result hash của Task.
- UI hiển thị tool của từng agent và tổng số LLM call.
- Kết quả có thể là `partial` nếu thiếu workflow history hoặc provider/synthesis fallback. `partial` là trạng thái minh bạch, không phải tự động đồng nghĩa với workflow lỗi.
- Không có dữ liệu QA-only trong sources.

### L4. Drill-down đúng một group

1. Chọn `Apollo Platform`.
2. Nhập:

```text
Phân tích blocker của Apollo Platform và ảnh hưởng tới kế hoạch.
```

Kết quả đạt:

- Vẫn chạy Task → Risk + Planning.
- Tất cả source ID chỉ thuộc Apollo Platform.
- Không xuất hiện Customer Portal hoặc Release 34.
- Blocker chính liên quan vendor sandbox trả lỗi 429.

Lặp nhanh với Customer Portal hoặc Release 34 nếu cần chứng minh isolation giữa các group.

### L5. Quyền quản trị nghiệp vụ của Lead

Trên cùng trang, mở các phần control plane/approval/handoff nếu có dữ liệu:

- Lead có thể quản lý dependency và decision theo state transition hợp lệ.
- Lead có thể xem/duyệt action proposal.
- Lead có thể tạo hoặc cập nhật release handoff sang QA theo policy.
- Mutation quan trọng không được LLM tự thực thi; phải đi qua proposal/HITL, expected row version và audit log.

Không tạo mutation trong demo chính nếu chưa chuẩn bị record riêng để tránh làm thay đổi dữ liệu cho các lượt demo sau.

## 5. Kịch bản demo Member — 6 phút

### M1. Đăng nhập và chứng minh scope tự động

1. Đăng xuất Lead.
2. Đăng nhập `delivery-demo-member@example.com` / `Demo123!`.
3. Mở **Workspace Agent**.

Kết quả đạt:

- Workspace vẫn là Product Delivery Demo nhưng role là `member`.
- Không có group selector để Member tự mở rộng phạm vi.
- Capability chỉ có Apollo Platform.
- Dashboard chỉ có 1 group, 5 participant, 1 task thuộc Minh và 0 milestone thuộc Minh.
- Không có control-plane management hoặc release-handoff management.

### M2. My Work chạy một Task Intelligence Agent

Nhập đúng câu không chứa từ `blocker` để trình diễn single-specialist rõ ràng:

```text
Công việc của tôi hiện tại là gì và ưu tiên ra sao?
```

Kết quả đạt:

- Mode `single_specialist`.
- Intent `my_work_priority`.
- Specialist `Task Intelligence`.
- Tool `get_delivery_tasks`.
- Chỉ có task `Hoàn thiện migration checklist`.
- Không có task của Huy, Lan, Đức hoặc team khác.

### M3. Member vẫn dùng multi-agent nhưng không được mở rộng dữ liệu

Nhập:

```text
Task của tôi có blocker nào và ảnh hưởng tới kế hoạch như thế nào?
```

Kết quả đạt:

- Có thể chạy Task → Risk + Planning vì đây là câu hỏi cross-domain.
- Task facts vẫn chỉ gồm task của Minh.
- Các agent sau chỉ nhận result hash từ Task Agent trong Member scope.
- Multi-agent tăng năng lực phân tích, không tăng quyền đọc dữ liệu.

### M4. Chứng minh không rò rỉ task ngoài scope

Nhập ID task thuộc scope Lead nhưng không thuộc Minh:

```text
Xem task 36d178c086d15d2ea84c17314ba8ea2e
```

Kết quả đạt:

- Workflow vẫn được audit dưới intent `task_lookup`.
- Không trả task.
- `facts=0`.
- Data gap là `TASK_NOT_FOUND_IN_AUTHORIZED_SCOPE`.
- Không phân biệt “task không tồn tại” với “task tồn tại nhưng không được phép xem”, tránh information disclosure.

### M5. Quyền action của Member

- Member có thể đề xuất action và cập nhật task thuộc chính mình theo policy.
- Member không được quản lý dependency/decision control plane.
- Member không được tạo release handoff.
- Member chỉ xem workflow do chính mình tạo; Lead có thể xem workflow trong scope quản trị.

## 6. Negative security demo

### S1. Outsider

1. Đăng nhập `delivery-demo-outsider@example.com`.
2. Mở Workspace Agent.

Kết quả mong đợi:

- Không có Product Delivery Agent Workspace được gán.
- Gọi trực tiếp Delivery capability/chat API phải trả `403` trước tool và LLM.

### S2. Member sửa request để chọn Customer Portal

Đây là test qua DevTools/API vì UI không gửi `selected_conversation_id` cho Member.

Kết quả nghiệp vụ yêu cầu: HTTP `403`, không gọi tool/LLM, không trả dữ liệu.

**Trạng thái kiểm chứng hiện tại:** đạt. Backend trả HTTP 403 trước tool/LLM và không trả dữ liệu.

## 7. Cách đọc bằng chứng multi-agent trên UI

Trong mỗi response, kiểm tra:

1. `Workspace Agent → Specialist` hoặc `Workspace Agent → Multi-agent DAG`.
2. Tên specialist được gọi.
3. Tool từng specialist sử dụng.
4. Số kết quả agent upstream mà specialist nhận.
5. Tổng số lượt gọi LLM.
6. Workflow status và fallback/data gap nếu có.

System prompt đầy đủ không hiển thị trên UI để tránh prompt leakage. Backend lưu `prompt_version`, model, usage, allowed tools, tool calls, dependency và upstream hashes để audit.

## 8. Live proof đã chạy

| Case | Workflow | Kết quả |
|---|---|---|
| Lead exact task | `2637a8be9ca842179f7a0e662eda668b` | Task Intelligence, LLM=true, 2 LLM call, exact-task tool |
| Lead multi-agent blocker | `d63d65ee4081495e9b36ec180ea29f05` | Task/Risk/Planning, 4 LLM call |
| Lead Apollo isolation | `8f417b3882eb4bd283ea9b5d819c104f` | Chỉ source Apollo |
| Member My Work | `b3e8dcee7e424501a08b9f0aa8e0c092` | Task Intelligence, 1 fact của Minh |
| Member foreign task | `16981d6c46e34c659bce6ee0dfdfc1dd` | 0 fact, authorized-scope gap |

## 9. Tiêu chí kết luận demo đạt

- Cả Lead và Member chỉ thấy một Product Delivery Workspace Agent được gán cho mình.
- Lead quan sát được toàn workspace hoặc một linked group do Lead chọn.
- Member không có cơ chế UI/API hợp lệ để mở rộng khỏi Member scope.
- Mọi chat hợp lệ gọi ít nhất một LLM-backed specialist.
- Multi-agent DAG thể hiện upstream result chaining, không phải một agent gọi hàng loạt tool dưới nhiều nhãn.
- Tool, model, token, prompt version, hash, fallback và source được audit.
- Missing data/provider/guardrail failure hiển thị thành gap/fallback, không bị che giấu.
- Mutation quan trọng luôn qua policy và human approval.

## 10. Việc dữ liệu cần xử lý trước demo chính thức

Quyết định dữ liệu của `delivery-demo-huong@example.com`: thêm Agent Workspace membership hợp lệ hoặc loại participant này khỏi số liệu demo. Hiện dashboard Lead có 14 participant nhưng Agent Workspace chỉ có 13 active membership.
