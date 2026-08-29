# Product Delivery Workspace UX — Checkpoint 14

> Trạng thái: **complete / verified trong phạm vi local integration**. Workspace group UI, group chat scope và
> Workspace Agent chat đã được nối với API/database thật. Browser automation đa persona vẫn là release gate riêng.

## Phạm vi hoàn thành

- Sửa lỗi frontend không truyền `workspace_id` khi tải hội thoại và directory người dùng.
- Thêm workspace switcher ở top navigation để ngữ cảnh workspace không còn bị ẩn.
- Thêm trang `/groups` dành riêng cho group doanh nghiệp:
  - Lead thấy ba group thuộc phạm vi quản lý.
  - Member chỉ thấy group đang tham gia.
  - Hiển thị số thành viên, tin mới, tin gần nhất, vai trò trong group và trạng thái AI.
  - Mở trực tiếp group chat qua `/chat` với đúng `conversationId`.
- Nâng trang `Chats`:
  - Truy vấn hội thoại theo workspace đang chọn.
  - Bộ lọc Tất cả/Nhóm/Trực tiếp.
  - Hiển thị vai trò quản lý hoặc thành viên trên từng group.
- Tách Workspace Agent thành màn hình chat riêng tại `/workspace-agent`:
  - Không trộn với human group chat hoặc Personal Assistant.
  - Có transcript user/assistant, prompt gợi ý, loading/thinking, error và new-chat.
  - Lead có selector toàn workspace hoặc một group từ capability API.
  - Member không có selector; server tự khóa scope theo membership/assignee.
  - Hiển thị metrics, evidence group chat, freshness, data gap và guardrail notice.
  - Lịch sử tối đa 30 message được giữ cục bộ theo `user_id + agent_workspace_id` để không lẫn tài khoản.
- Giữ alias `/delivery-agent` và redirect sang `/workspace-agent` để deep link cũ không hỏng.

## Artifact

- `Frontend/user/src/api/chat.js`
- `Frontend/user/src/hooks/useConversations.js`
- `Frontend/user/src/components/chat/NewConversationModal.jsx`
- `Frontend/user/src/components/chat/ConversationList.jsx`
- `Frontend/user/src/components/layout/TopNavbar.jsx`
- `Frontend/user/src/components/layout/Sidebar.jsx`
- `Frontend/user/src/pages/ChatPage.jsx`
- `Frontend/user/src/pages/WorkspaceGroupsPage.jsx`
- `Frontend/user/src/pages/DeliveryAgentPage.jsx`
- `Frontend/user/src/router/AppRouter.jsx`
- `Frontend/user/src/workspace-agent.css`
- `Frontend/shared/styles.css`
- `docs/ROLE_B_DELIVERY_DEMO_TEST_SCRIPT.md`

## Bug phát hiện và sửa

### Frontend làm mất workspace scope

**Reproduce:** gọi `GET /api/v1/conversations` từ tài khoản demo mà không có `workspace_id` trả
`409 User has no personal workspace`; gọi cùng endpoint với Company workspace trả đúng group.

**Root cause:** `ChatPage` đã truyền `workspaceId` vào hook nhưng `useConversations` bỏ tham số; `listConversations`
và `listUsers` cũng không tạo query `workspace_id`. Modal tạo conversation không gửi `workspace_id`.

**Fix:** truyền workspace xuyên suốt Context → hook → API; create conversation bind vào workspace đang chọn.

**Regression evidence:** API thật sau fix-equivalent request trả Lead 3 group, Member 1 group; cả hai đọc được 8 message
của group đầu tiên. Member đọc ID group ngoài membership nhận HTTP `404`, tránh lộ sự tồn tại của tài nguyên.

## Kết quả kiểm thử

### Frontend production build

```powershell
cd F:\P-132\Frontend
npm run build --workspace @orbit/user
```

Kết quả: **passed**, 717 modules transformed. Vite chỉ còn warning chunk Calendar lớn đã biết, không chặn các
route group/chat/workspace-agent.

### Backend integration regression

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_agents\test_delivery_api.py tests\test_agent_workspaces.py -q
```

Kết quả: **15 passed**.

### Live authorization matrix

| Persona | Group UI/API thấy | Group messages | Capability selector | Foreign group |
|---|---:|---:|---:|---:|
| Lead | 3: Apollo, Customer Portal, Release 34 | 8/group | Có, 3 group | Trong management scope |
| Member Minh | 1: Apollo | 8 | Không | HTTP 404 |

### Live LLM turn

Tài khoản `delivery-demo-member@example.com` hỏi `List my current delivery work.`:

- API status: `success`.
- View scope: `member`.
- Group trong snapshot: chỉ `Apollo Platform`.
- Có LLM response thật.
- Kết quả trả đúng task `Hoàn thiện migration checklist` của Minh Backend.

### Static/smoke checks

- `/groups`: HTTP 200.
- `/chat`: HTTP 200.
- `/workspace-agent`: HTTP 200.
- Backend `/health`: HTTP 200.
- `git diff --check`: passed; chỉ có warning LF/CRLF của worktree Windows.
- Kiểm tra mojibake trên các file UI mới: không phát hiện.

## Phân quyền nghiệp vụ sau checkpoint

- Lead được thấy giao diện ba group vì Lead là participant/manager hợp lệ của cả ba group trong seed.
- Member không nhận danh sách group toàn workspace; endpoint conversations chỉ trả group có participant active.
- Việc sửa URL/state không cấp quyền: message endpoint revalidate conversation membership ở backend.
- Workspace Agent selector lấy từ capability API server-filtered, không lấy toàn bộ conversation rồi lọc client-side.
- Member prompt không thể tự nâng scope; request không có group selector và backend vẫn resolve member scope.
- Workspace Agent chat là UI/runtime Delivery riêng; không gọi Personal Agent graph và không trở thành thành viên chat.

## Known limits

- Chưa có Playwright/Cypress browser E2E để click tự động toàn bộ login → groups → chat → agent cho bốn persona.
- Transcript Workspace Agent hiện lưu localStorage tối đa 30 message, chưa có server-side thread store riêng cho Delivery.
- Human group chat đã realtime bằng WebSocket; Workspace Agent turn hiện dùng request/response, chưa stream token.
- Source evidence đang hiển thị excerpt an toàn nhưng chưa deep-link/scroll tới đúng message nguồn.
- Calendar chunk size warning vẫn tồn tại và thuộc tối ưu bundle hậu MVP.

## Plan-alignment review

| Plan task/capability | Trạng thái | Evidence | Còn thiếu / gate |
|---|---|---|---|
| B4-02 → B4-04 Delivery UI states | complete trong local scope | Workspace Agent chat, loading/error/empty/access UI, production build | Stale state cần fixture/browser assertion riêng |
| B4-07 UI/build/smoke | complete trong local scope | Build pass; 3 route HTTP 200 | Keyboard/browser automation chưa có |
| B6-03 E2E persona | partial | Live Lead/Member API matrix và foreign-group denial | Outsider/Admin browser E2E chưa tự động hóa |
| B6-06 demo rehearsal | complete trong local scope | Live member LLM turn success, đúng group/task | Cần rehearsal Lead UI trên staging |
| §14.6 group selector | complete | Lead selector từ capability API; Member không có selector | Không có |
| §15.1 Workspace Agent runtime riêng | complete cho UI wiring | `/workspace-agent` gọi Delivery API riêng, không dùng Personal chat route | Server-side Delivery thread persistence là hậu MVP |
| B12 conversational UI | partial | Chat transcript, prompt, tool result/evidence/freshness, local history | Latency/token UI telemetry và automated browser E2E còn thiếu |

## Kết luận

Checkpoint này hoàn thành phần thiếu mà người dùng quan sát được: group doanh nghiệp không còn “biến mất” do thiếu
workspace scope, Lead/Member có giao diện nhóm khác nhau theo quyền, group chat mở được từ trang nhóm và Workspace
Agent đã là một cuộc chat riêng. Không tuyên bố B6-03/B12 release-complete cho tới khi có browser E2E và telemetry.
