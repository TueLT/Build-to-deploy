# Thiết kế nền tảng Workspace và phân quyền

**Ngày:** 2026-08-03
**Trạng thái:** Đã được duyệt qua thảo luận thiết kế
**Phạm vi:** Nền tảng authorization và data boundary cho Personal Workspace, Organization Workspace, guest và external contact

## 1. Mục tiêu

Thiết kế lại ranh giới dữ liệu của Orbit theo hướng internal-workspace-first:

- Mỗi người dùng có một Personal Workspace riêng.
- Công ty hoặc nhóm làm việc sử dụng Organization Workspace.
- Người ngoài chỉ được tham gia tài nguyên cụ thể với tư cách guest hoặc external contact.
- Quyền quản trị hệ thống, quyền quản trị workspace và quyền truy cập nội dung là ba hệ quyền độc lập.
- AI và WebSocket dùng chung một cơ chế authorization, không dựa vào việc frontend đã ẩn route.
- Migration từ schema hiện tại phải idempotent, có dry-run và không thể tạo organization workspace không có owner.

Nền tảng này là điều kiện tiên quyết cho Contact/Relationship Graph, AI permissions, project, task, calendar và group chat nâng cao.

## 2. Ngoài phạm vi của thiết kế này

Các nội dung sau sẽ có design spec riêng sau khi nền tảng này được triển khai:

- AI tự suy luận relationship và tạo relationship suggestion.
- Task/project/calendar nghiệp vụ hoàn chỉnh.
- Billing provider và thanh toán thực tế.
- Public user discovery hoặc mạng xã hội công khai.
- Voice/video call, attachment storage và end-to-end encryption.
- Quy trình pháp lý đầy đủ cho export, retention và data residency.

Thiết kế hiện tại vẫn tạo các điểm mở rộng cần thiết để các tính năng trên không phải phá vỡ authorization model về sau.

## 3. Nguyên tắc kiến trúc

### 3.1 Ba lớp authorization

```text
Platform authorization
├── user
└── platform_admin

Workspace authorization
├── owner
├── admin
├── member
└── guest

Resource authorization
├── manager
├── participant
└── viewer
```

`platform_admin` không đồng nghĩa với workspace owner hoặc quyền đọc nội dung.

### 3.2 Hai loại principal của resource

```text
workspace_user
external_contact
```

Owner, admin, member và guest không được lưu trong `ConversationParticipant`. Role hiện tại luôn được đọc động từ `WorkspaceMembership`. Việc nâng guest thành member vì vậy không yêu cầu cập nhật participant và không tạo dữ liệu lệch.

### 3.3 Deny by default

Nếu không tìm thấy grant phù hợp, request bị từ chối. Frontend route guard chỉ phục vụ UX; backend luôn kiểm tra lại quyền cho REST request, WebSocket connect, subscribe, reconnect và từng inbound message.

### 3.4 Quyền quản trị tách khỏi quyền nội dung

Platform admin và workspace admin không được tự động đọc private conversation, task, calendar hoặc AI memory. Quyền quản lý metadata không suy ra quyền truy cập nội dung.

## 4. Mô hình dữ liệu

### 4.1 User

Thay `User.role` hiện tại bằng trường platform-scoped:

```text
User
- id
- email
- password_hash
- display_name
- platform_role: user | platform_admin
- is_active
- created_at
```

Email được chuẩn hóa lowercase trước khi lưu và so sánh. Platform role không được dùng để quyết định quyền trong organization workspace.

### 4.2 Workspace

```text
Workspace
- id
- type: personal | organization
- name
- slug nullable
- personal_owner_user_id nullable
- status: active | suspended | deleting
- created_at
- updated_at
```

Ràng buộc:

- `type = personal` khi và chỉ khi `personal_owner_user_id` có giá trị.
- Mỗi user có đúng một active personal workspace.
- Personal workspace không có `WorkspaceMembership` và không thể mời thành viên.
- Organization workspace không dùng `personal_owner_user_id` và phải có ít nhất một active owner membership.

### 4.3 WorkspaceMembership

```text
WorkspaceMembership
- id
- workspace_id
- user_id
- role: owner | admin | member | guest
- status: invited | active | suspended | removed
- invited_by_user_id nullable
- joined_at nullable
- created_at
- updated_at
```

Ràng buộc:

- Unique `(workspace_id, user_id)`.
- Chỉ áp dụng cho organization workspace.
- Mọi transaction remove, suspend hoặc demote owner phải khóa các owner membership liên quan và xác nhận `active_owner_count >= 1` trước khi commit.
- Owner cuối cùng không thể tự rời, bị xóa, suspend hoặc demote.

### 4.4 WorkspaceInvitation

```text
WorkspaceInvitation
- id
- workspace_id
- email
- intended_role: admin | member | guest
- token_hash
- invited_by_user_id
- status: pending | accepted | expired | revoked
- expires_at
- accepted_by_user_id nullable
- created_at
- accepted_at nullable
```

Invitation lưu hash của token, không lưu token thô. Chỉ owner được mời admin; owner hoặc admin được mời member/guest. Workspace policy có thể cho member gửi invitation request nhưng không tự cấp membership.

### 4.5 ExternalContact

External contact không phải workspace membership và không xuất hiện trong directory nội bộ.

```text
ExternalContact
- id
- workspace_id
- email
- display_name
- organization nullable
- linked_user_id nullable
- status: invited | active | revoked
- created_by_user_id
- created_at
- updated_at
```

`linked_user_id` được điền khi external contact nhận lời mời và đăng nhập bằng một Orbit account. Một external contact chỉ có thể truy cập resource đã gán trực tiếp cho `external_contact_id`; `linked_user_id` không biến họ thành workspace member.

### 4.6 Conversation

```text
Conversation
- id
- workspace_id
- type: direct | group
- name nullable
- created_by_user_id
- created_at
- updated_at
```

Mọi conversation thuộc đúng một workspace. Direct conversation giữa hai workspace users được deduplicate trong cùng workspace. Conversation có external contact không được tự suy ra quyền directory hoặc quyền vào conversation khác.

### 4.7 ConversationParticipant

```text
ConversationParticipant
- id
- conversation_id
- principal_kind: workspace_user | external_contact
- user_id nullable
- external_contact_id nullable
- resource_role: manager | participant | viewer
- invited_by_user_id nullable
- joined_at
- last_read_at
- revoked_at nullable
```

Ràng buộc bắt buộc:

```text
CHECK exactly_one(user_id, external_contact_id)

CHECK principal_kind = workspace_user
      <=> user_id IS NOT NULL

CHECK principal_kind = external_contact
      <=> external_contact_id IS NOT NULL

UNIQUE(conversation_id, user_id)
UNIQUE(conversation_id, external_contact_id)
```

Do SQLite coi nhiều giá trị `NULL` là khác nhau, hai unique constraint phải được tạo dưới dạng partial unique index để bảo đảm đúng ngữ nghĩa và có thể migrate sang PostgreSQL tương đương.

Participant bị thu hồi được giữ lại với `revoked_at` để phục vụ audit. Mọi query nội dung chỉ xét participant chưa bị revoke.

### 4.8 SupportAccessGrant

```text
SupportAccessGrant
- id
- platform_admin_id
- workspace_id
- requested_scope
- reason
- status: requested | approved | expired | revoked | rejected
- approved_by_owner_id nullable
- created_at
- approved_at nullable
- expires_at
- revoked_at nullable
```

Quy tắc:

- Platform admin không được tự phê duyệt grant của chính mình.
- Người phê duyệt phải là active workspace owner tại thời điểm approve.
- Grant có scope cụ thể, thời hạn ngắn và không được hiểu là toàn quyền workspace.
- Grant được kiểm tra lại tại mỗi REST request, WebSocket subscribe/reconnect và inbound message.
- Grant hết hạn hoặc bị revoke có hiệu lực ngay với request tiếp theo.

### 4.9 AuditLog

```text
AuditLog
- id
- workspace_id nullable
- actor_user_id nullable
- actor_type: user | platform_admin | system
- action
- target_type
- target_id nullable
- metadata_json
- ip_address nullable
- created_at
```

Audit log là append-only ở tầng service. Không API nào cho phép update hoặc delete audit record. Nội dung message, task hoặc memory không được copy vào `metadata_json`; chỉ lưu identifier và metadata cần thiết.

## 5. Authorization service

Business logic không đặt trực tiếp trong route handler. Tạo các service có ranh giới rõ ràng:

```text
src/services/workspace_service.py
src/services/authorization_service.py
src/services/invitation_service.py
src/services/external_contact_service.py
src/services/conversation_service.py
src/services/audit_service.py
```

Các hàm authorization chủ đạo:

```text
require_platform_admin(user)
require_workspace_role(user, workspace_id, allowed_roles)
require_workspace_member(user, workspace_id)
require_conversation_access(user, conversation_id, minimum_resource_role)
require_support_scope(user, workspace_id, scope)
```

`require_conversation_access` thực hiện:

1. Kiểm tra account active.
2. Tải conversation và workspace.
3. Với `workspace_user`, kiểm tra participant active và membership hiện tại.
4. Owner/admin/member được authorize theo resource role và workspace policy.
5. Guest chỉ được authorize khi có participant/resource grant cụ thể.
6. Với external contact, ánh xạ current user qua `ExternalContact.linked_user_id` và kiểm tra participant active.
7. Không cho platform admin bypass nếu không có `SupportAccessGrant` phù hợp.

## 6. Role capabilities

### 6.1 Platform admin

Được phép:

- Lock/unlock platform account.
- Xem workspace metadata, health, quota và aggregate metrics.
- Xử lý abuse/security report.
- Khởi tạo quy trình owner recovery.
- Yêu cầu support access có thời hạn.

Không được phép mặc định:

- Đọc hoặc xóa conversation content.
- Đọc task, calendar, contact graph hoặc AI memory.
- Tự cấp support access.
- Tự thêm mình vào workspace.

### 6.2 Workspace owner

- Quản lý cấu hình, policy, billing metadata và retention.
- Bổ nhiệm hoặc hạ quyền admin.
- Bổ nhiệm thêm owner và chuyển ownership.
- Quản lý member, guest và external contact.
- Xem audit log.
- Xóa workspace qua quy trình xác nhận riêng.

Owner chỉ đọc private conversation khi chính họ là participant hoặc có resource grant hợp lệ.

### 6.3 Workspace admin

- Quản lý invitation, member, guest và tài nguyên hằng ngày.
- Tạo team/project/channel khi policy cho phép.
- Xử lý report trong workspace.

Admin không được:

- Xóa workspace hoặc thay đổi billing quan trọng.
- Bổ nhiệm owner hoặc admin.
- Hạ quyền owner cuối cùng.
- Đọc private conversation nếu không tham gia.
- Đọc personal workspace hoặc AI memory cá nhân.

### 6.4 Member và guest

Member tạo và tham gia resource theo workspace policy. Guest chỉ truy cập resource được cấp và không thấy directory toàn workspace. External contact còn hẹp hơn guest: không có membership và chỉ truy cập conversation cụ thể.

## 7. API boundary

### 7.1 Platform routes

```text
/api/v1/platform/accounts
/api/v1/platform/workspaces
/api/v1/platform/support-grants
/api/v1/platform/reports
```

Không trả message content hoặc dữ liệu nghiệp vụ riêng tư.

### 7.2 Workspace routes

```text
/api/v1/workspaces
/api/v1/workspaces/{workspace_id}/members
/api/v1/workspaces/{workspace_id}/invitations
/api/v1/workspaces/{workspace_id}/external-contacts
/api/v1/workspaces/{workspace_id}/audit-log
```

### 7.3 Conversation routes

Các route conversation hiện tại được thêm `workspace_id` rõ ràng hoặc xác định workspace từ conversation rồi authorize bằng service chung. Route không tự viết lại logic role.

```text
/api/v1/workspaces/{workspace_id}/conversations
/api/v1/conversations/{conversation_id}/participants
/api/v1/conversations/{conversation_id}/messages
```

## 8. WebSocket authorization

WebSocket vẫn xác thực account khi connect nhưng không giữ một quyết định authorization vĩnh viễn.

Mỗi `send_message` phải:

1. Decode identity từ connection đã xác thực.
2. Kiểm tra account vẫn active.
3. Gọi `require_conversation_access` với conversation hiện tại.
4. Kiểm tra membership/resource grant chưa bị revoke.
5. Ghi message.
6. Broadcast chỉ tới connection của participant đang còn quyền.

Khi reconnect hoặc subscribe lại, toàn bộ authorization được tính lại. Việc suspend user, remove membership, revoke participant hoặc revoke support grant phải chặn request tiếp theo mà không cần restart server.

Connection manager chỉ quản lý transport; không chứa business authorization.

## 9. Luồng nghiệp vụ

### 9.1 Đăng ký user

1. Tạo `User` với `platform_role=user`.
2. Trong cùng transaction, tạo Personal Workspace có `personal_owner_user_id` là user mới.
3. Nếu bước tạo workspace thất bại, rollback cả user để không tạo account thiếu personal workspace.

### 9.2 Mời thành viên nội bộ

1. Owner/admin nhập email trong Organization Workspace.
2. Authorization kiểm tra người mời và intended role.
3. Tạo invitation với token hash và expiry.
4. Người nhận đăng nhập/đăng ký và accept.
5. Tạo hoặc activate membership trong transaction.
6. Ghi audit log.

### 9.3 Mời external contact vào conversation

1. Conversation manager nhập email external contact.
2. Tạo hoặc tái sử dụng `ExternalContact` trong workspace.
3. Tạo invitation chỉ mang scope conversation cụ thể.
4. Khi accept, liên kết Orbit user với external contact.
5. Tạo `ConversationParticipant(principal_kind=external_contact)`.
6. External contact chỉ nhìn thấy conversation được cấp.

### 9.4 Tạo direct conversation nội bộ

1. Current user chọn member trong directory của workspace.
2. Backend xác nhận cả hai có active membership phù hợp.
3. Tìm direct conversation hiện có trong cùng workspace.
4. Có thì trả lại; chưa có thì tạo conversation và hai participant.

Guest không được directory search. Direct chat với guest chỉ được tạo khi policy/resource grant cho phép.

### 9.5 Thay đổi membership

Role thay đổi không cập nhật `ConversationParticipant`. Request tiếp theo đọc role mới từ membership. Khi membership chuyển suspended/removed, user mất quyền ngay cả khi participant record vẫn còn để phục vụ audit.

## 10. Migration từ schema hiện tại

### 10.1 Preflight và dry-run

Migration command hỗ trợ `--dry-run` và xuất báo cáo không chứa secret hoặc message content:

- Số user active/inactive.
- Danh sách candidate owner ID/email đã mask.
- Số conversation và participant cần gắn workspace.
- Constraint hoặc dữ liệu orphan cần xử lý.
- Migration version hiện tại.

### 10.2 Chọn bootstrap owner

1. Nếu `BOOTSTRAP_OWNER_USER_ID` được cấu hình, user phải tồn tại, active và có platform admin role cũ phù hợp.
2. Nếu không cấu hình, chỉ tự chọn khi có đúng một active admin hiện tại.
3. Nếu có 0 hoặc nhiều active admin, dừng trước khi ghi dữ liệu.
4. Không chọn theo thứ tự ID, email hoặc thời gian tạo.

### 10.3 Các bước migration

1. Chạy preflight; nếu không đạt thì dừng trước khi tạo migration state.
2. Upsert migration state `running` với version cố định trong một transaction ngắn riêng.
3. Mở một transaction nguyên tử cho toàn bộ thay đổi dữ liệu.
4. Đổi platform role hiện tại theo mapping đã định nghĩa.
5. Tạo Personal Workspace cho từng user nếu chưa tồn tại.
6. Tạo Organization Workspace mặc định nếu chưa tồn tại.
7. Tạo owner membership theo bootstrap decision.
8. Tạo member membership cho các user còn lại theo policy migration.
9. Gắn conversation hiện tại vào organization workspace.
10. Chuyển participant hiện tại thành `workspace_user`.
11. Kiểm tra foreign key, unique constraint và owner invariant.
12. Chỉ sau khi toàn bộ validation pass mới commit transaction dữ liệu.
13. Cập nhật migration state thành `completed` trong transaction ngắn riêng.

Nếu bất kỳ bước dữ liệu nào thất bại, transaction dữ liệu bị rollback toàn bộ. Sau rollback, migration state được cập nhật thành `failed` cùng mã lỗi đã lọc secret. Trạng thái `running` còn sót lại sau process crash được coi là interrupted; lần chạy tiếp theo phải chạy lại preflight trước khi tiếp tục.

### 10.4 Idempotency

Migration dùng stable migration key và upsert theo natural key. Chạy lại sau khi thành công không tạo workspace, membership hoặc participant trùng. Nếu lần trước thất bại hoặc process bị ngắt, transaction dữ liệu không để lại trạng thái nghiệp vụ dở dang; migration state cho phép nhận diện, chạy lại preflight và thực thi an toàn sau khi nguyên nhân được sửa.

## 11. Xử lý lỗi

- `401`: token thiếu, sai hoặc hết hạn.
- `403`: account inactive, thiếu workspace role/resource grant hoặc support scope.
- `404`: resource không tồn tại hoặc caller không được phép biết resource tồn tại.
- `409`: invitation/membership/participant trùng, owner invariant hoặc transition không hợp lệ.
- `410`: invitation hết hạn hoặc participant đã bị revoke khi endpoint cần biểu đạt trạng thái này.
- `422`: request/schema không hợp lệ.

Không trả stack trace, membership nội bộ hoặc thông tin directory cho external contact. Những lỗi authorization nhạy cảm dùng thông báo chung và ghi chi tiết vào server audit/security log.

## 12. Tổ chức mã nguồn

Không đặt business logic vào route hoặc React component.

```text
src/
├── api/
│   ├── platform_routes.py
│   ├── workspace_routes.py
│   ├── invitation_routes.py
│   ├── external_contact_routes.py
│   └── conversation_routes.py
├── auth/
│   ├── dependencies.py
│   └── permissions.py
├── db/
│   ├── models.py
│   ├── migrations/
│   └── session.py
├── models/
│   ├── workspace_schemas.py
│   ├── invitation_schemas.py
│   ├── external_contact_schemas.py
│   └── conversation_schemas.py
└── services/
    ├── authorization_service.py
    ├── workspace_service.py
    ├── invitation_service.py
    ├── external_contact_service.py
    ├── conversation_service.py
    └── audit_service.py

Frontend/src/
├── api/
│   ├── workspaces.js
│   ├── invitations.js
│   ├── contacts.js
│   └── conversations.js
├── hooks/
│   ├── useWorkspaces.js
│   ├── useWorkspaceMembers.js
│   └── useConversationParticipants.js
├── components/
│   ├── workspace/
│   ├── contacts/
│   └── chat/
└── pages/
    ├── WorkspaceSettingsPage.jsx
    ├── WorkspaceMembersPage.jsx
    └── ExternalContactsPage.jsx
```

Nếu `src/db/models.py` trở nên quá lớn, model được tách thành package `src/db/models/` theo domain trong một migration riêng, tránh vừa đổi schema vừa refactor import không cần thiết.

## 13. Kiểm thử

### 13.1 Unit tests

- Role capability matrix cho owner/admin/member/guest/platform admin.
- Owner cuối cùng không thể remove/suspend/demote.
- Membership role thay đổi được phản ánh mà không sửa participant.
- Support grant expiry/revoke và scope matching.
- Exactly-one principal constraints.

### 13.2 API integration tests

- User registration luôn tạo Personal Workspace.
- Platform admin không đọc được conversation content mặc định.
- Owner/admin không đọc private conversation nếu không là participant.
- Guest không list được directory.
- External contact chỉ truy cập conversation được mời.
- Invitation accept/revoke/expire và duplicate handling.
- Direct conversation được deduplicate trong cùng workspace nhưng không deduplicate xuyên workspace.

### 13.3 WebSocket tests

- Active participant gửi/nhận message realtime.
- Suspended membership bị từ chối ở inbound frame tiếp theo.
- Revoked participant mất quyền sau reconnect.
- External contact không subscribe conversation khác.
- Platform admin không dùng WebSocket để bypass content authorization.
- Support grant hết hạn bị từ chối mà không restart app.

### 13.4 Migration tests

- Dry-run không ghi database.
- Chạy hai lần không tạo bản ghi trùng.
- Có nhiều admin và không cấu hình owner thì dừng.
- Không có owner hợp lệ thì rollback toàn bộ.
- Dữ liệu orphan làm migration thất bại trước commit.
- Migration thành công giữ nguyên message history và participant access hợp lệ.

## 14. Tiêu chí hoàn thành

- Mọi user có đúng một Personal Workspace.
- Mọi conversation có workspace và participant principal hợp lệ.
- Organization workspace luôn có ít nhất một active owner.
- Platform admin không có content access mặc định.
- Owner/admin không bypass private conversation membership.
- Guest và external contact không thấy directory hoặc resource ngoài scope.
- REST và WebSocket dùng chung authorization service.
- Migration dry-run, idempotency và rollback được test.
- Backend test, Ruff và frontend production build đều pass.
- Tài liệu API và migration guide được cập nhật trước khi rollout.

## 15. Thứ tự triển khai sau khi spec được duyệt

1. Schema và migration framework/preflight.
2. Workspace creation và membership invariants.
3. Authorization service và chuyển platform admin routes.
4. Conversation participant migration và REST authorization.
5. WebSocket authorization theo request/frame.
6. Invitation và external contact flow.
7. Frontend workspace/member/contact UI.
8. Security, migration và end-to-end verification.

Contact/Relationship Graph và AI permission chi tiết sẽ được thiết kế trên các principal, workspace boundary và authorization service này, không thêm shortcut song song.
