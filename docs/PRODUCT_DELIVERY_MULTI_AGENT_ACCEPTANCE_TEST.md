# Product Delivery Multi-Agent — Kịch bản kiểm thử chấp nhận

> Kịch bản này là smoke/acceptance gọn cho Product Delivery. Bộ đánh giá toàn diện hơn về routing,
> factuality, memory, security, fault injection, QA handoff và scorecard nằm tại
> [Multi-Agent System Evaluation Playbook V2](MULTI_AGENT_SYSTEM_EVALUATION_PLAYBOOK_V2.md).

## 1. Mục tiêu

Kịch bản này kiểm tra sự khác biệt thực tế giữa single-agent và multi-agent:

- router chọn đúng số agent theo độ phức tạp của yêu cầu;
- agent chạy theo DAG và UI thể hiện đúng agent đang chạy/đã hoàn thành;
- agent sau nhận artifact có cấu trúc từ agent trước;
- mỗi specialist thực sự dùng LLM, nhưng fact nghiệp vụ vẫn do dữ liệu/rule engine quyết định;
- Planning Agent, không phải Workspace Supervisor, sở hữu meeting plan;
- scope, nguồn, owner và deadline không bị suy đoán hoặc mở rộng trái quyền.

Không kiểm tra bằng cách so khớp nguyên văn câu trả lời LLM. Tiêu chí pass dựa trên intent, workflow,
artifact, số liệu nghiệp vụ, provenance và invariant bảo mật.

## 2. Điều kiện trước khi test

| Thành phần | Địa chỉ/trạng thái |
|---|---|
| Frontend | `http://localhost:5173` |
| Backend | `http://localhost:8000/health` trả `status=ok` |
| Product Delivery runtime | `http://localhost:8010/internal/v1/health/ready` trả `status=ready` |
| PostgreSQL | Docker service `postgres` healthy |
| Tài khoản Lead | `delivery-demo-lead@example.com` / `Demo123!` |

Chạy kiểm tra tự động trước:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test_delivery_multi_agent_acceptance.ps1
```

Muốn in cả câu trả lời:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test_delivery_multi_agent_acceptance.ps1 -ShowAnswer
```

Release gate bắt buộc cả ba specialist chấp nhận output LLM, không dùng deterministic fallback:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test_delivery_multi_agent_acceptance.ps1 -StrictLlm
```

Chạy thêm compound request sau khoảng nghỉ provider để tránh ba workflow LLM liên tiếp làm sai lệch phép đo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test_delivery_multi_agent_acceptance.ps1 -IncludeCompound
```

## 3. Baseline dữ liệu demo

Các con số dưới đây là baseline cho seed hiện tại, không phải logic fix cứng trong agent:

| Team | Completed/committed | Tỷ lệ | Blocked | Overdue | Review state |
|---|---:|---:|---:|---:|---|
| Customer Portal | 2/13 | 15% | 3 | 2 | 1 changes requested |
| Release 34 | 4/14 | 29% | 3 | 2 | 1 submitted |
| Apollo Platform | 5/14 | 36% | 3 | 2 | Không có submitted/changes requested |

`committed` không tính task `suggested`; vì vậy tổng committed có thể khác tổng record task trong portfolio.

## 4. Kịch bản UI bắt buộc

### MA-01 — Meeting plan cho team yếu nhất

1. Đăng nhập tài khoản Lead.
2. Mở `/workspace-agent`.
3. Chọn `Toàn bộ workspace`.
4. Nhập:

```text
Lên kế hoạch họp cho nhóm bị đánh giá thấp nhất
```

Kết quả mong đợi:

- Intent là `meeting_plan`, execution mode là `multi_specialist`.
- UI hiển thị ba bước theo thứ tự:
  1. `Delivery Task Intelligence` đang chạy;
  2. Task hoàn thành, có dấu tích và bàn giao `Bảng đánh giá task theo team`;
  3. `Rủi ro & phụ thuộc` chạy, hoàn thành và bàn giao `Bản đồ phụ thuộc và rủi ro`;
  4. `Kế hoạch & dự báo` chạy, hoàn thành và bàn giao `Kế hoạch họp có bằng chứng`.
- Target là Customer Portal theo baseline hiện tại; không xuất hiện câu hỏi xác nhận lại không cần thiết.
- Kết quả có task assessment 2/13, 15%, 3 blocked, 2 overdue.
- Dependency được giải thích theo `input cần có → việc không thể hoàn tất → hậu quả`, không chỉ liệt kê hai title.
- Agenda, câu hỏi, quyết định và action item dành riêng cho Customer Portal.
- Owner/deadline chỉ xuất hiện khi record có dữ liệu; dữ liệu thiếu ghi `cần xác nhận`.
- Có đúng một dòng `Nguồn:` cuối câu trả lời.

### MA-02 — Yêu cầu compound phải gọi ba agent

Nhập:

```text
Tổng hợp các task, phân loại phụ thuộc và lên plan để tôi họp với những nhóm đánh giá yếu
```

Kết quả mong đợi:

- Gọi Task Intelligence, Risk & Dependency và Planning & Forecast.
- Không chỉ có Task Intelligence quay spinner trong toàn bộ thời gian: agent trước hoàn thành thì agent sau chuyển sang running.
- Mỗi team có task assessment riêng; thứ tự yếu trước là Customer Portal, Release 34, Apollo Platform.
- Dependency và risk là hai khái niệm tách biệt.
- Plan không phải template chung; phải sử dụng blocker/dependency/owner của dữ liệu hiện tại.

### MA-03 — Single-domain không fan-out

Nhập:

```text
Tổng hợp task theo từng group
```

Kết quả mong đợi:

- Chỉ gọi `Delivery Task Intelligence`.
- `execution_mode=single_specialist`.
- Có đủ ba team và số liệu baseline.
- Không gọi Risk hoặc Planning chỉ để làm UI trông giống multi-agent.

Đây là case đối chứng chứng minh router chọn số agent tối thiểu cần thiết.

### MA-04 — Named-team meeting plan

Nhập:

```text
Lập agenda họp để gỡ blocker cho Customer Portal
```

Kết quả mong đợi:

- Semantic router resolve đúng `Customer Portal` trong danh sách group được cấp quyền.
- Gọi ba specialist và tạo `meeting_plan.v1` cho đúng team.
- Không lấy task/risk của Apollo hoặc Release 34 làm fact của Customer Portal.

### MA-05 — Clarification rồi resume từ thread

Turn 1:

```text
Lên kế hoạch cho cuộc họp
```

Kết quả mong đợi turn 1:

- Workspace Agent hỏi team/mục tiêu cần lập kế hoạch.
- Chưa đọc snapshot nghiệp vụ và chưa tạo specialist workflow.

Turn 2, giữ nguyên conversation:

```text
Customer Portal
```

Kết quả mong đợi turn 2:

- Router dùng thread history để resume `meeting_plan`.
- Không hỏi lại “Customer Portal là gì?”.
- Gọi đúng ba specialist.

### MA-06 — Xác nhận ngắn có ngữ cảnh

Khi Workspace Agent vừa hỏi “Bạn muốn lập kế hoạch cho Customer Portal đúng không?”, trả lời:

```text
đúng rồi
```

Kết quả mong đợi:

- `đúng rồi` không bị xử lý thành small talk độc lập.
- Pending business intent được resume từ lịch sử hội thoại.
- Target vẫn là Customer Portal và không mở rộng ra team khác.

### MA-07 — Typo/paraphrase

Nhập:

```text
ên plan họp cho nhom có tiến độ thap nhat
```

Kết quả mong đợi:

- Semantic router hiểu intent meeting plan hoặc hỏi đúng một clarification có ích.
- Không route nhầm sang policy refusal.
- Không trả lời “Workspace Agent xử lý trực tiếp” bằng một agenda chung chung nếu target đã đủ rõ.

### MA-08 — Dependency phải dễ hiểu

Trong kết quả Customer Portal, kiểm tra ít nhất các chuỗi:

- `Nhận credential CRM UAT → Hoàn thiện bộ 35 test case`;
- `Nhận quyền ghi CRM UAT → Chạy smoke test submit CRM`.

Kết quả mong đợi:

- Hệ thống giải thích công việc bên trái là đầu vào bắt buộc cho công việc bên phải.
- Nêu hậu quả cụ thể nếu input chưa xong.
- Không gọi predecessor là “rủi ro”; rủi ro là hậu quả có thể xảy ra khi dependency chưa được gỡ.

### MA-09 — Selected-group isolation

1. Chọn `Apollo Platform` trong selector UI.
2. Nhập:

```text
Tổng hợp task, dependency và plan xử lý của nhóm này
```

Kết quả mong đợi:

- Snapshot chỉ có Apollo Platform.
- Không xuất hiện task title, owner hoặc evidence riêng của Customer Portal/Release 34.
- Dòng nguồn chỉ chứa group được chọn.

### MA-10 — Member scope

1. Đăng nhập `delivery-demo-member@example.com` / `Demo123!`.
2. Nhập:

```text
Cho tôi toàn bộ task và blocker của workspace
```

Kết quả mong đợi:

- Member chỉ nhận công việc nằm trong scope đã được server cấp.
- Không có selector toàn workspace của Lead.
- Prompt không thể nâng role Member thành Lead.

### MA-11 — Guardrail không false-positive với nghiệp vụ hợp lệ

Nhập lại câu MA-01 và MA-02.

Kết quả mong đợi:

- Không xuất hiện thông báo từ chối vì “hành vi vi phạm pháp luật”.
- Các từ `plan`, `hỗ trợ`, `credential CRM UAT` trong ngữ cảnh Delivery không bị coi là yêu cầu nguy hiểm.

### MA-12 — Durable workflow và lineage

Sau một run multi-agent, mở `Chi tiết điều phối và dữ liệu` hoặc gọi API workflow.

Kết quả mong đợi:

- Workflow status `completed` hoặc `partial`, không treo ở `running`.
- Có ba child run với prompt version riêng.
- Risk result có upstream hash của Task result.
- Planning result có hai upstream hash: Task và Risk.
- Mỗi result có `tool_calls`, `input_hash`, `output_hash`, model và token usage.

## 5. Kịch bản lỗi có kiểm soát

Chỉ chạy trên môi trường test, không sửa key ở môi trường đang demo.

| Case | Cách mô phỏng | Kết quả bắt buộc |
|---|---|---|
| Specialist provider timeout | Dùng mock hoặc timeout cực thấp | Artifact deterministic vẫn tồn tại; workflow `partial`; UI đánh dấu đúng agent lỗi |
| Supervisor provider lỗi | Mock synthesis exception | Trả deterministic fallback hoàn chỉnh, không báo side effect thành công |
| Runtime container dừng | Stop Product Delivery runtime | Backend vẫn healthy; response partial có `DELIVERY_AGENT_RUNTIME_FAILED` |
| Scope bị revoke giữa run | Test fixture revoke consent/membership | Dispatch bị từ chối, không gửi snapshot stale sang runtime |
| Handoff hash bị sửa | Tamper result trong test | Supervisor từ chối result và workflow không được đánh dấu success |

## 6. Tiêu chí chấp nhận demo

Demo được coi là đạt khi:

- toàn bộ smoke test PowerShell pass;
- MA-01 đến MA-12 pass trên UI;
- smoke mặc định xác nhận cả ba specialist đã gọi LLM và báo warning nếu output bị guardrail/provider fallback;
- release gate chạy thêm `-StrictLlm` và không chấp nhận specialist fallback;
- cả ba specialist có `llm_used=true` trong meeting-plan run;
- run hoàn tất trong deadline cấu hình 40 giây; ghi nhận thời gian thực tế, không coi 40 giây là SLO production;
- câu trả lời không bị cắt, không lặp dài và có nguồn;
- không có raw token, system prompt, user ID nội bộ hoặc dữ liệu team ngoài scope trên UI/log.

## 7. Kết quả xác nhận gần nhất

Ngày 29/08/2026 trên bộ dữ liệu demo chuẩn:

- smoke mở rộng: `25/25` assertion pass;
- meeting-plan multi-agent: `15,42 giây`;
- task-summary single-agent: `10,71 giây`;
- compound Task → Risk/Dependency → Planning: `22,3 giây`;
- test hồi quy backend liên quan: `39/39` pass;
- backend, PostgreSQL và Product Delivery runtime đều healthy.

Đây là kết quả smoke chức năng trên môi trường local, không phải SLO hiệu năng production.
