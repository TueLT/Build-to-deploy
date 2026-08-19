# Nền móng Workspace và Membership theo nghiệp vụ doanh nghiệp

> Trạng thái: **Đề xuất canonical v1 để team review**  
> Phạm vi: Personal Workspace, Organization Workspace, Agent Workspace, membership, lead và quyền quản trị  
> Mục tiêu: thống nhất nghiệp vụ trước khi mở rộng Delivery, Quality và Executive Agent

## 1. Kết luận nghiệp vụ

Mô hình phù hợp nhất không phải là “một admin làm tất cả”. Hệ thống cần tách ba lớp trách nhiệm:

1. `platform_admin` vận hành nền tảng và provision tenant, nhưng không quản lý nhân sự hằng ngày và không tự có quyền đọc dữ liệu doanh nghiệp.
2. `organization_owner`/`organization_admin` quản trị Organization Workspace, phòng ban, thành viên và bổ nhiệm trưởng phòng.
3. `agent_workspace_lead` điều hành nghiệp vụ trong phòng, nhưng mặc định không tự cấp quyền truy cập cho người khác.

Quyết định khuyến nghị:

- User không tự tạo Organization Workspace trong chế độ doanh nghiệp.
- User không tự join Agent Workspace.
- Organization Owner/Admin là người phê duyệt cuối cùng việc vào phòng và bổ nhiệm lead.
- Lead được đề xuất hoặc yêu cầu thêm member; chỉ được thêm trực tiếp nếu Organization Owner bật delegation rõ ràng.
- Platform Admin có thể provision Organization Workspace và gán owner ban đầu, nhưng không tự trở thành owner/member/lead.
- Mỗi Agent Workspace active có đúng một `primary_lead` trong MVP. Có thể bổ sung deputy/acting lead sau này nhưng không thay thế invariant primary lead.

## 2. Phân biệt ba loại workspace

| Loại | Ý nghĩa | Ai tạo | Ai quản trị |
|---|---|---|---|
| Personal Workspace | Không gian cá nhân được tạo cùng account | System | Chính user |
| Organization Workspace | Tenant và biên bảo mật của một doanh nghiệp | Platform provisioning hoặc quy trình đăng ký doanh nghiệp được duyệt | Organization Owner/Admin |
| Agent Workspace | Phòng ban hoặc vùng nghiệp vụ trong một Organization Workspace | Organization Owner/Admin | Organization Owner/Admin; Lead điều hành nghiệp vụ |

Không dùng Agent Workspace thay cho tenant. Mọi Agent Workspace bắt buộc thuộc đúng một Organization Workspace.

## 3. Các vai trò và ranh giới trách nhiệm

### 3.1 Platform Admin

Được phép:

- Provision, suspend hoặc phục hồi Organization Workspace.
- Gán owner đầu tiên khi provision tenant.
- Xem metadata, health, quota và audit vận hành.
- Thực hiện owner recovery qua quy trình có audit.
- Yêu cầu support grant có thời hạn khi cần hỗ trợ.

Không được mặc định:

- Tự thêm mình hoặc người khác vào business membership hằng ngày.
- Tự đọc chat, task, memory, calendar hoặc dữ liệu nghiệp vụ.
- Tự cấp support grant cho mình.
- Đóng vai Delivery/Quality Lead chỉ vì có quyền platform admin.

### 3.2 Organization Owner

- Chịu trách nhiệm cao nhất với tenant.
- Bổ nhiệm/hạ quyền Organization Admin.
- Tạo, đổi trạng thái và archive Agent Workspace.
- Bổ nhiệm hoặc thay primary lead.
- Phê duyệt member/guest và chính sách delegation.
- Quản lý retention, policy và audit cấp doanh nghiệp.
- Không được đọc private resource nếu không có business entitlement/resource membership phù hợp.

Organization Workspace luôn phải có ít nhất một active owner.

### 3.3 Organization Admin

- Quản lý member hằng ngày.
- Tạo Agent Workspace khi policy cho phép.
- Phê duyệt member vào Agent Workspace.
- Bổ nhiệm/thay lead nếu owner đã cho phép bằng policy.
- Suspend/revoke membership và xử lý yêu cầu truy cập.
- Không được thay owner, xóa tenant hoặc thay chính sách nhạy cảm nếu không có quyền riêng.

### 3.4 Agent Workspace Lead

- Chịu trách nhiệm nghiệp vụ của phòng.
- Xem và sử dụng agent trong đúng workspace được phân.
- Quản lý task/process nghiệp vụ nếu resource policy cho phép.
- Đề xuất thêm hoặc loại member.
- Có thể quản lý membership trực tiếp chỉ khi có delegated capability.

Lead không được:

- Thêm người chưa thuộc Organization Workspace.
- Tự biến một user thành Organization Member.
- Tự bổ nhiệm lead mới hoặc hạ quyền primary lead.
- Truy cập Agent Workspace khác chỉ dựa vào chức danh lead.
- Đọc private resource không được map/cấp quyền.

### 3.5 Agent Workspace Member

- Dùng specialist agent trong đúng Agent Workspace đang active.
- Chỉ đọc resource nằm trong allowed resource IDs và còn consent.
- Không quản lý role, membership hoặc policy nếu không có capability riêng.

### 3.6 Executive Viewer

- Đọc validated aggregate brief được phép.
- Không tự đọc raw chat của Delivery/Quality.
- Không kế thừa quyền member/lead của specialist workspace.

## 4. Ai được cho member vào Agent Workspace?

### 4.1 Chính sách mặc định khuyến nghị: Admin-approved

Đây là lựa chọn phù hợp nhất cho nền móng hiện tại:

1. User phải là active Organization Member trước.
2. Lead chọn người từ directory nội bộ và gửi `membership_request`.
3. Organization Owner/Admin duyệt hoặc từ chối.
4. Khi duyệt, backend tạo/activate Agent Workspace Membership trong một transaction.
5. User nhận thông báo và membership có hiệu lực.
6. Hệ thống ghi đầy đủ requester, approver, role, reason và timestamp vào audit.

Lead không phải người phê duyệt cuối vì lead là bên hưởng lợi từ việc mở rộng quyền của phòng. Tách requester và approver giúp giảm cấp quyền nhầm và phù hợp separation of duty.

### 4.2 Delegated mode cho doanh nghiệp nhỏ

Organization Owner có thể bật:

```text
lead_can_manage_members = true
```

Khi bật, Lead được thêm hoặc revoke `member` trong chính Agent Workspace của họ, nhưng vẫn phải tuân thủ:

- Chỉ chọn active Organization Member.
- Không cấp role `lead` hoặc `executive_viewer`.
- Không reactivate Organization Membership đã suspended/revoked.
- Không mời account bên ngoài tổ chức.
- Mọi thao tác phải có audit và có thể bị Organization Admin thu hồi.

Không nên bật delegation mặc định.

### 4.3 User self-service

User có thể gửi yêu cầu tham gia nhưng không tự activate membership:

```text
requested -> approved -> active
          \-> rejected
```

Không hỗ trợ self-join mặc định. Nếu sau này có public/internal-open workspace thì đó phải là policy riêng, không phải hành vi chung.

## 5. Lifecycle chuẩn

### 5.1 Organization Workspace

```text
provisioning -> active -> suspended -> active
                    \-> deleting -> deleted
```

Quy tắc:

- `provisioning`: đã tạo tenant nhưng chưa hoàn tất owner/policy.
- Chỉ chuyển `active` khi có ít nhất một active owner.
- `suspended`: chặn business requests nhưng giữ dữ liệu/audit.
- `deleting`: yêu cầu confirmation, retention và background cleanup.

### 5.2 Agent Workspace

```text
draft -> active -> suspended -> active
   \        \-> archived
    \-> archived
```

Quy tắc:

- Tạo mới ở `draft`, không active ngay.
- Chỉ active khi Organization Workspace active, profile hợp lệ và có primary lead active.
- `suspended` chặn agent invocation và resource retrieval mới.
- `archived` là terminal trong luồng thường; không xuất hiện như workspace hoạt động.

### 5.3 Membership

```text
requested/invited -> active -> suspended -> active
        |              \-> revoked
        \-> rejected/expired
```

Không xóa hard-delete membership thông thường vì cần audit lịch sử.

## 6. Invariant bắt buộc ở database và service

1. Personal Workspace có đúng một personal owner và không có Organization Membership.
2. Organization Workspace active có ít nhất một active owner.
3. Agent Workspace thuộc đúng một active Organization Workspace.
4. Active Agent Workspace có đúng một active primary lead trong MVP.
5. Active Agent Workspace Membership suy ra active Organization Membership của cùng user.
6. Organization Membership bị suspend/revoke phải vô hiệu hóa mọi Agent Workspace Membership ở request kế tiếp.
7. Không thể revoke/demote primary lead trước khi gán người thay thế hoặc suspend workspace.
8. Platform role không tạo ra business entitlement.
9. Organization role không tự tạo quyền đọc private resource.
10. Guest/external contact không được làm Agent Workspace lead/member trong MVP.
11. Client không được tự gửi role/profile/allowed workspace để backend tin trực tiếp.
12. Mọi request phải authorize lại theo trạng thái hiện tại; cache phải chứa membership/policy version hoặc bị invalidate khi revoke.

## 7. Công thức quyền hiệu lực

Một user chỉ được gọi specialist agent khi toàn bộ điều kiện đều đúng:

```text
account active
∩ organization active
∩ active organization membership
∩ agent workspace active
∩ active agent workspace membership
∩ profile capability
∩ allowed resource mapping
∩ current consent
∩ purpose/policy
```

Thiếu bất kỳ điều kiện nào thì `DENY` hoặc `MASK`; không gọi retrieval/tool trước rồi mới lọc kết quả.

## 8. Ma trận quyền quản trị

| Thao tác | Platform Admin | Org Owner | Org Admin | Lead | Member |
|---|---:|---:|---:|---:|---:|
| Provision Organization Workspace | Có | Không | Không | Không | Không |
| Gán owner đầu tiên | Có, lúc provision/recovery | Không áp dụng | Không | Không | Không |
| Tạo Agent Workspace | Không mặc định | Có | Có theo policy | Không | Không |
| Bổ nhiệm/thay primary lead | Không mặc định | Có | Có theo policy | Không | Không |
| Duyệt Agent Workspace member | Không mặc định | Có | Có | Chỉ khi delegated | Không |
| Đề xuất member | Không | Có | Có | Có | Có thể gửi self-request |
| Suspend/revoke member | Không mặc định | Có | Có | Chỉ khi delegated | Không |
| Đọc raw business data | Không | Chỉ khi có entitlement | Chỉ khi có entitlement | Trong scope | Trong scope |
| Đọc Executive aggregate | Không | Khi có executive entitlement | Khi có executive entitlement | Không mặc định | Không |

“Admin” trong UI và tài liệu phải ghi rõ là Platform Admin hay Organization Admin; không dùng từ `admin` chung chung trong authorization code.

## 9. Luồng nghiệp vụ chuẩn

### 9.1 Provision doanh nghiệp

1. Platform Admin hoặc hệ thống nhận yêu cầu tenant đã được duyệt.
2. Tạo Organization Workspace ở `provisioning`.
3. Chọn một active user làm Organization Owner ban đầu.
4. Tạo owner membership trong transaction.
5. Chuyển workspace sang `active`.
6. Ghi audit; Platform Admin không được thêm làm membership.

### 9.2 Tạo phòng ban

1. Organization Owner/Admin tạo Agent Workspace ở `draft`.
2. Chọn profile Delivery hoặc Quality.
3. Chọn primary lead từ active Organization Members.
4. Tạo lead membership.
5. Cấu hình resource mapping/policy tối thiểu.
6. Activate Agent Workspace.

Không tự động biến một account ngoài tổ chức thành Organization Member chỉ vì được nhập ở ô lead. Nếu chưa là member, admin phải hoàn thành invitation/approval trước.

### 9.3 Thêm member vào phòng

1. Requester chọn active Organization Member.
2. Backend kiểm tra requester capability và target eligibility.
3. Tạo request/invitation có expiry.
4. Organization Owner/Admin duyệt; hoặc Lead thực hiện trực tiếp nếu delegated.
5. Activate Agent Workspace Membership.
6. Audit và notify.

### 9.4 Đổi trưởng phòng

Trong một transaction:

1. Khóa các active lead memberships của workspace.
2. Kiểm tra người mới là active Organization Member.
3. Promote người mới thành primary lead.
4. Demote lead cũ thành member hoặc revoke theo quyết định explicit.
5. Ghi actor, old lead, new lead, reason vào audit.

Không để khoảng thời gian active workspace có zero lead hoặc nhiều primary lead.

### 9.5 Nhân viên nghỉ việc hoặc chuyển phòng

- Revoke/suspend Organization Membership trước.
- Mọi quyền Agent Workspace bị chặn ngay ở request kế tiếp.
- Hệ thống revoke/suspend child memberships và invalidate session/cache/brief liên quan.
- Nếu người đó là primary lead, bắt buộc chuyển lead hoặc suspend Agent Workspace.
- Giữ audit và ownership history; không xóa cứng.

## 10. API boundary khuyến nghị

```text
# Platform control plane
POST  /api/v1/platform/workspaces
PATCH /api/v1/platform/workspaces/{id}/status
POST  /api/v1/platform/workspaces/{id}/owner-recovery

# Organization control plane
POST  /api/v1/workspaces/{org_id}/agent-workspaces
PATCH /api/v1/workspaces/{org_id}/agent-workspaces/{agent_id}
PATCH /api/v1/workspaces/{org_id}/agent-workspaces/{agent_id}/lead

# Membership workflow
POST  /api/v1/workspaces/{org_id}/agent-workspaces/{agent_id}/membership-requests
POST  /api/v1/workspaces/{org_id}/agent-workspaces/{agent_id}/membership-requests/{request_id}/approve
POST  /api/v1/workspaces/{org_id}/agent-workspaces/{agent_id}/membership-requests/{request_id}/reject
DELETE /api/v1/workspaces/{org_id}/agent-workspaces/{agent_id}/members/{membership_id}
```

Platform endpoint không trả raw business data. Organization endpoints phải authorize bằng Organization Membership hiện tại, không dựa vào platform role.

## 11. Audit bắt buộc

Các event tối thiểu:

- `organization_workspace.provisioned`
- `organization_workspace.owner_assigned`
- `organization_workspace.status_changed`
- `agent_workspace.created`
- `agent_workspace.activated`
- `agent_workspace.lead_changed`
- `agent_workspace.membership_requested`
- `agent_workspace.membership_approved`
- `agent_workspace.membership_rejected`
- `agent_workspace.membership_revoked`
- `agent_workspace.policy_changed`

Audit lưu actor, target, organization/agent workspace, before/after metadata đã sanitize, reason và timestamp; không log raw conversation content hoặc secret.

## 12. Đánh giá implementation hiện tại

### Đã đúng

- Tách Organization Workspace và Agent Workspace.
- Agent Workspace membership có `member`, `lead`, `executive_viewer`.
- Platform Admin không tự có quyền đọc business data.
- Có unique constraint cho một active lead.
- Không cho revoke lead hiện tại trước khi có người thay thế.
- Scope resolver kiểm tra organization + agent workspace + membership + consent.

### Chưa đúng hoàn toàn với target enterprise

1. Bất kỳ authenticated user nào vẫn có thể tự tạo Organization Workspace và trở thành owner.
2. Agent Workspace management hiện dùng `platform_admin`, thay vì Organization Owner/Admin.
3. Chọn lead hiện tự thêm/reactivate Organization Membership; target enterprise phải qua invitation/approval riêng.
4. Thêm Organization/Agent member hiện active ngay, chưa có invitation acceptance/approval lifecycle đầy đủ.
5. Agent Workspace tạo ở `active`, chưa có trạng thái `draft` để cấu hình an toàn.
6. Chưa có membership request và delegated lead policy.
7. Chưa có cascade/invalidation service rõ ràng khi Organization Membership bị suspend/revoke.

Do đó implementation hiện tại phù hợp làm **MVP bootstrap**, nhưng chưa nên gọi là hoàn chỉnh theo nghiệp vụ doanh nghiệp.

## 13. Lộ trình chỉnh code khuyến nghị

### P0 — Trước khi nối specialist agent thật

1. Chặn user tự tạo Organization Workspace trong enterprise mode; chuyển sang platform provisioning/approved signup.
2. Chuyển Agent Workspace management sang Organization Owner/Admin.
3. Không auto-add Organization Membership khi gán lead; target phải là active organization member.
4. Thêm `draft` cho Agent Workspace và validation trước activate.
5. Enforce cascade deny khi Organization Membership không active.

### P1 — Trước demo đầy đủ

1. Thêm invitation/request/approve/reject lifecycle.
2. Thêm policy `lead_can_manage_members`, mặc định `false`.
3. Thêm Admin UI đúng scope: Platform provisioning tách khỏi Organization Workspace administration.
4. Thêm audit before/after và reason cho role/membership transition.

### P2 — Khi hướng production enterprise

1. SSO/SCIM provisioning và deprovisioning.
2. Access review định kỳ và membership expiry.
3. Deputy/acting lead có thời hạn.
4. Bulk group mapping từ identity provider.
5. Policy versioning và cache/session invalidation phân tán.

## 14. Acceptance criteria nền móng

- User thường không thể tự tạo Organization/Agent Workspace trong enterprise mode.
- Platform Admin provision tenant nhưng không xuất hiện trong member directory nếu không được mời riêng.
- Org Owner/Admin tạo Agent Workspace và chọn lead chỉ từ active org members.
- Lead mặc định chỉ request member; direct add trả `403` nếu chưa delegated.
- Một active Agent Workspace luôn có đúng một primary lead.
- Revoke organization membership chặn mọi specialist agent call ở request kế tiếp.
- Owner/admin/lead không đọc private resource nếu không có resource entitlement.
- Mọi transition đều có audit và test denial tương ứng.
- Không có API nào tin `role`, `profile`, `organization_id` hoặc `agent_workspace_id` chỉ từ client mà không kiểm tra quan hệ DB.

## 15. Cơ sở thiết kế

- [NIST Role-Based Access Control](https://csrc.nist.gov/Projects/role-based-access-control/faqs): quyền được gán qua role, role authorization và transaction authorization; RBAC hỗ trợ separation of duty.
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html): least privilege, deny by default và kiểm tra permission ở mọi request.
- [OWASP Business Logic Security](https://cheatsheetseries.owasp.org/cheatsheets/Business_Logic_Security_Cheat_Sheet.html): kiểm tra lại ownership/quyền trên từng object và enforce rule phía server.
- [RFC 7644 — SCIM Protocol](https://www.rfc-editor.org/rfc/rfc7644): hướng chuẩn hóa provisioning/deprovisioning user và group khi mở rộng enterprise identity.
