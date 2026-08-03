# Workspace Authorization Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây nền tảng Personal/Organization Workspace, phân quyền ba tầng, participant theo principal, external contact và authorization thống nhất cho REST/WebSocket mà không làm mất dữ liệu chat hiện có.

**Architecture:** FastAPI route chỉ validate/serialize; toàn bộ quyết định quyền nằm trong service dùng chung. SQLAlchemy lưu workspace, membership, invitation, external contact và participant; Alembic quản lý migration idempotent. React tiếp tục gọi API qua `Frontend/src/api/` và hook theo feature, không gọi `fetch` trực tiếp trong component.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic 2, SQLAlchemy 2 async, Alembic, SQLite/aiosqlite, JWT/PyJWT, bcrypt, WebSocket, React 18, Vite 5, pytest, pytest-asyncio, httpx, Ruff.

## Global Constraints

- Design source of truth: `docs/superpowers/specs/2026-08-03-workspace-authorization-foundation-design.md`.
- `principal_kind` chỉ nhận `workspace_user | external_contact`; workspace role luôn đọc động từ membership hiện tại.
- Organization workspace phải luôn có ít nhất một active owner.
- Personal workspace có một `personal_owner_user_id`, không có membership và không mời thành viên.
- Platform admin không có quyền đọc nội dung mặc định.
- REST và WebSocket phải gọi cùng authorization service.
- Mọi migration có preflight, dry-run, idempotency và rollback test.
- Mọi hành động tạo event/reminder vẫn yêu cầu human-in-the-loop.
- Không stage hoặc commit `.env`/secret; không ghi đè thay đổi `.env.example` hiện có ngoài một task được người dùng yêu cầu riêng.
- Sau mỗi task hoàn thành: đánh dấu checkbox, cập nhật bảng trạng thái và commit riêng task đó.

## Progress

| Task | Trạng thái | Commit |
| --- | --- | --- |
| 1. Branch README và dependency baseline | Hoàn thành | `docs: document branch scope and technology stack` |
| 2. Workspace models và Personal Workspace registration | Chưa làm | — |
| 3. Alembic migration, preflight và backfill | Chưa làm | — |
| 4. Authorization service và Platform Admin boundary | Chưa làm | — |
| 5. Conversation principal và REST authorization | Chưa làm | — |
| 6. WebSocket authorization | Chưa làm | — |
| 7. Invitation và External Contact | Chưa làm | — |
| 8. Frontend Workspace/Contact/Group integration | Chưa làm | — |
| 9. Full verification và handoff docs | Chưa làm | — |

---

### Task 1: Branch README và dependency baseline

**Files:**
- Create: `docs/branches/G19-T132-Luong-Tri-Tue.md`
- Modify: `README.md`
- Modify: `requirements.txt`
- Modify: `pyproject.toml`
- Modify: `docs/superpowers/plans/2026-08-03-workspace-authorization-foundation.md`

**Interfaces:**
- Consumes: lịch sử commit của branch `G19-T132-Lương-Trí-Tuệ` và design spec đã duyệt.
- Produces: tài liệu branch có trạng thái `Implemented`, `Partial`, `Designed`; dependency manifest đồng bộ và có Alembic.

- [x] **Step 1: Viết branch report không nhận nhầm trạng thái**

Branch report phải phân biệt rõ:

```markdown
## Đã triển khai
- Chat 1-1/group realtime qua WebSocket
- JWT/bcrypt auth, admin hiện tại, LangGraph/Groq tools

## Đã thiết kế, chưa triển khai
- Workspace authorization foundation
- Contact/Relationship Graph và controlled external guests
```

- [x] **Step 2: Cập nhật root README**

Thêm liên kết branch report, hướng dẫn chạy PowerShell/macOS/Linux, bảng công nghệ, trạng thái mock/real và link tới spec/plan. Không mô tả Workspace là đã chạy trước khi Task 2–8 hoàn thành.

- [x] **Step 3: Đồng bộ dependencies**

Kích hoạt Alembic trong `requirements.txt`:

```text
alembic>=1.14.0
```

Đồng bộ `pyproject.toml` với runtime packages đang được import: SQLAlchemy, aiosqlite, Alembic, PyJWT, bcrypt, email-validator, APScheduler và Google Calendar clients.

- [x] **Step 4: Xác minh tài liệu và manifest**

Run:

```powershell
git diff --check -- README.md requirements.txt pyproject.toml docs/branches/G19-T132-Luong-Tri-Tue.md
.\.venv\Scripts\python.exe -m ruff check src tests
```

Expected: không có whitespace error; Ruff exit 0.

- [x] **Step 5: Cập nhật progress và commit**

Đánh dấu Task 1 hoàn thành, ghi commit hash sau khi commit:

```powershell
git add README.md requirements.txt pyproject.toml docs/branches/G19-T132-Luong-Tri-Tue.md docs/superpowers/plans/2026-08-03-workspace-authorization-foundation.md
git commit -m "docs: document branch scope and technology stack"
```

---

### Task 2: Workspace models và Personal Workspace registration

**Files:**
- Modify: `src/db/models.py`
- Create: `src/models/workspace_schemas.py`
- Create: `src/services/workspace_service.py`
- Create: `src/api/workspace_routes.py`
- Modify: `src/api/auth_routes.py`
- Modify: `src/models/auth_schemas.py`
- Modify: `src/main.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_workspaces.py`

**Interfaces:**
- Produces: `Workspace`, `WorkspaceMembership`; `create_personal_workspace(db, user) -> Workspace`; `require_active_owner_after_change(db, workspace_id, excluded_membership_id=None) -> None`.
- Consumes later: authorization, migration, invitations và conversation scoping.

- [ ] **Step 1: Viết failing model/registration tests**

```python
@pytest.mark.asyncio
async def test_register_creates_exactly_one_personal_workspace(client, auth_headers):
    me = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()
    workspaces = (await client.get("/api/v1/workspaces", headers=auth_headers)).json()
    personal = [w for w in workspaces if w["type"] == "personal"]
    assert len(personal) == 1
    assert personal[0]["personal_owner_user_id"] == me["id"]
```

Thêm test personal workspace không nhận membership và organization workspace không thể mất owner cuối cùng.

- [ ] **Step 2: Chạy test để xác nhận fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_workspaces.py -v -p no:cacheprovider
```

Expected: FAIL vì model/service/route workspace chưa tồn tại.

- [ ] **Step 3: Thêm model và constraint tối thiểu**

Model fields phải khớp spec; enum được lưu dưới dạng string constants có validate ở service/Pydantic. `Workspace.personal_owner_user_id` có unique partial semantics cho personal workspace; `WorkspaceMembership` unique `(workspace_id, user_id)`.

- [ ] **Step 4: Tạo workspace service**

```python
async def create_personal_workspace(db: AsyncSession, user: User) -> Workspace:
    existing = await get_personal_workspace(db, user.id)
    if existing:
        return existing
    workspace = Workspace(type="personal", name=f"{user.display_name}'s Workspace", personal_owner_user_id=user.id)
    db.add(workspace)
    await db.flush()
    return workspace
```

Registration gọi service trong cùng transaction với user creation; chỉ commit sau khi workspace được tạo.

- [ ] **Step 5: Thêm workspace list endpoint và chạy test**

Endpoint `GET /api/v1/workspaces` nằm trong `workspace_routes.py`, trả personal workspace và organization workspaces có active membership. Đăng ký router trong `src/main.py`, sau đó chạy lại test file và toàn bộ auth tests.

- [ ] **Step 6: Ruff, progress và commit**

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests
git add src tests docs/superpowers/plans/2026-08-03-workspace-authorization-foundation.md
git commit -m "feat: add workspace ownership foundation"
```

---

### Task 3: Alembic migration, preflight và backfill

**Files:**
- Create: `alembic.ini`
- Create: `src/db/migrations/env.py`
- Create: `src/db/migrations/script.py.mako`
- Create: `src/db/migrations/versions/20260803_01_workspace_foundation.py`
- Create: `src/services/migration_service.py`
- Create: `scripts/migrate_workspace_foundation.py`
- Modify: `src/config.py`
- Create: `tests/test_workspace_migration.py`

**Interfaces:**
- Produces: `preflight_workspace_migration(db, bootstrap_owner_user_id) -> MigrationPreflightReport`; CLI `--dry-run`; Alembic revision `20260803_01`.
- Consumes: Task 2 models and owner invariant.

- [ ] **Step 1: Viết failing migration tests**

```python
def test_preflight_rejects_multiple_admins_without_config(session):
    report = preflight_workspace_migration(session, bootstrap_owner_user_id=None)
    assert report.can_run is False
    assert report.error_code == "ambiguous_bootstrap_owner"
```

Thêm test dry-run không ghi DB, migration chạy hai lần không trùng, orphan participant rollback và owner invariant.

- [ ] **Step 2: Chạy test để xác nhận fail**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_workspace_migration.py -v -p no:cacheprovider
```

- [ ] **Step 3: Cấu hình Alembic async**

`env.py` đọc `get_settings().database_url`, đổi `sqlite:///` thành `sqlite+aiosqlite:///`, import `Base.metadata`, và dùng `async_engine_from_config`.

- [ ] **Step 4: Viết preflight và dry-run**

```python
@dataclass(frozen=True)
class MigrationPreflightReport:
    can_run: bool
    owner_user_id: str | None
    user_count: int
    conversation_count: int
    orphan_count: int
    error_code: str | None = None
```

CLI chỉ in count và email đã mask; không in message hoặc secret.

- [ ] **Step 5: Viết revision idempotent và backfill**

Revision đầu chỉ tạo/backfill nền tảng đã có model ở Task 2: `platform_role`, workspace, membership và `conversation.workspace_id`. Việc chuyển participant/external contact thuộc revision kế tiếp trong Task 5. Owner resolution tuân đúng preflight; failure rollback data transaction và migration state được ghi `failed` sau rollback.

- [ ] **Step 6: Chạy migration tests và upgrade test database**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_workspace_migration.py -v -p no:cacheprovider
.\.venv\Scripts\python.exe scripts/migrate_workspace_foundation.py --dry-run
```

Không chạy upgrade lên `data/app.db` thật nếu dry-run chưa pass hoặc owner còn ambiguous.

- [ ] **Step 7: Progress và commit**

```powershell
git add alembic.ini src/db/migrations src/services/migration_service.py scripts/migrate_workspace_foundation.py src/config.py tests/test_workspace_migration.py docs/superpowers/plans/2026-08-03-workspace-authorization-foundation.md
git commit -m "feat: add idempotent workspace migration"
```

---

### Task 4: Authorization service và Platform Admin boundary

**Files:**
- Create: `src/auth/permissions.py`
- Create: `src/services/authorization_service.py`
- Create: `src/services/audit_service.py`
- Create: `src/api/platform_routes.py`
- Modify: `src/api/admin_routes.py`
- Modify: `src/auth/dependencies.py`
- Modify: `src/main.py`
- Modify: `src/db/models.py`
- Create: `src/db/migrations/versions/20260803_02_conversation_principals.py`
- Create: `src/models/platform_schemas.py`
- Modify: `tests/test_admin.py`
- Create: `tests/test_authorization.py`

**Interfaces:**
- Produces: `require_platform_admin`, `require_workspace_role`, `require_workspace_member`, `require_conversation_access`, `require_support_scope`.
- Produces: append-only `record_audit_event(db, actor, action, target_type, target_id, workspace_id, metadata)`.

- [ ] **Step 1: Viết failing authorization tests**

```python
@pytest.mark.asyncio
async def test_platform_admin_cannot_read_private_conversation(client, platform_admin_headers, private_conversation):
    response = await client.get(
        f"/api/v1/conversations/{private_conversation.id}/messages",
        headers=platform_admin_headers,
    )
    assert response.status_code == 403
```

Thêm capability matrix và last-owner transaction tests.

- [ ] **Step 2: Chạy test để xác nhận fail**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_authorization.py tests/test_admin.py -v -p no:cacheprovider
```

- [ ] **Step 3: Tách platform role khỏi workspace role**

`get_current_user` tiếp tục kiểm tra `is_active`. `require_platform_admin` chỉ kiểm tra `platform_role`; không trả content scope.

- [ ] **Step 4: Tạo authorization và audit service**

Route chỉ gọi dependency/service. Audit metadata từ chối key `content`, `message`, `memory`, `token`, `secret` để tránh copy dữ liệu nhạy cảm.

- [ ] **Step 5: Thay admin route nội dung**

Platform routes chỉ trả account/workspace metadata và aggregate counts. Route đọc/xóa conversation cũ bị loại khỏi platform admin hoặc chuyển sang participant/resource authorization; không giữ compatibility làm lộ nội dung.

- [ ] **Step 6: Chạy test, Ruff, progress và commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_authorization.py tests/test_admin.py -v -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check src tests
git add src tests docs/superpowers/plans/2026-08-03-workspace-authorization-foundation.md
git commit -m "feat: separate platform and workspace authorization"
```

---

### Task 5: Conversation principal và REST authorization

**Files:**
- Modify: `src/db/models.py`
- Modify: `src/models/chat_schemas.py`
- Modify: `src/services/chat_service.py`
- Create: `src/services/conversation_service.py`
- Modify: `src/api/chat_routes.py`
- Modify: `tests/test_chat.py`
- Create: `tests/test_conversation_access.py`

**Interfaces:**
- Produces: model `ExternalContact`; `add_workspace_participant`, `add_external_participant`, `revoke_participant`, `get_authorized_participant_ids`.
- Consumes: Task 4 `require_conversation_access` và Task 2 workspace membership.

- [ ] **Step 1: Viết failing participant tests**

```python
@pytest.mark.asyncio
async def test_guest_role_change_does_not_rewrite_participant(db, guest_membership, participant):
    original_participant_id = participant.id
    guest_membership.role = "member"
    await db.commit()
    await db.refresh(participant)
    assert participant.id == original_participant_id
    assert participant.principal_kind == "workspace_user"
```

Thêm exactly-one constraint, duplicate partial index, cross-workspace denial và revoked participant tests.

- [ ] **Step 2: Chạy test để xác nhận fail**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_conversation_access.py -v -p no:cacheprovider
```

- [ ] **Step 3: Chuyển model participant**

Thêm model `ExternalContact` theo spec trước khi tạo foreign key. Chuyển participant sang `id`, `principal_kind`, nullable principal columns, `resource_role`, `invited_by_user_id`, `revoked_at`. Revision `20260803_02` tạo external contact table, backfill participant cũ thành `workspace_user`, tạo check constraint/partial unique indexes và không lưu workspace membership role trong participant.

- [ ] **Step 4: Chuyển conversation routes sang workspace scope**

Create/list direct/group conversation yêu cầu `workspace_id`; list user dùng workspace directory và không trả directory cho guest. API vẫn giữ route message theo `conversation_id` nhưng authorize bằng service chung.

- [ ] **Step 5: Chạy regression tests**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_chat.py tests/test_conversation_access.py -v -p no:cacheprovider
```

- [ ] **Step 6: Progress và commit**

```powershell
git add src tests docs/superpowers/plans/2026-08-03-workspace-authorization-foundation.md
git commit -m "feat: scope conversations to workspace principals"
```

---

### Task 6: WebSocket authorization

**Files:**
- Modify: `src/websocket/routes.py`
- Modify: `src/websocket/manager.py`
- Modify: `src/services/chat_service.py`
- Modify: `tests/test_websocket.py`

**Interfaces:**
- Consumes: `require_conversation_access`, active membership và participant revocation.
- Produces: frame authorization trên từng `send_message`; broadcast chỉ tới authorized current principals.

- [ ] **Step 1: Viết failing revoke/suspend tests**

```python
def test_suspended_member_is_rejected_on_next_frame(ws_client, suspended_member_socket, conversation_id):
    suspended_member_socket.send_json({
        "type": "send_message",
        "conversation_id": conversation_id,
        "content": "blocked",
    })
    assert suspended_member_socket.receive_json()["code"] == "conversation_access_denied"
```

Thêm reconnect, external cross-conversation và inactive account tests.

- [ ] **Step 2: Chạy test để xác nhận fail**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_websocket.py -v -p no:cacheprovider
```

- [ ] **Step 3: Authorize mỗi frame**

Connection chỉ cache authenticated `user_id`; mỗi frame mở DB session mới, tải trạng thái account/membership/participant và gọi authorization service trước khi tạo message.

- [ ] **Step 4: Làm broadcast chịu lỗi socket**

Mỗi socket send được bọc riêng; socket lỗi bị disconnect khỏi manager nhưng không làm message đã commit trả lỗi cho toàn bộ participant.

- [ ] **Step 5: Chạy tests, progress và commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_websocket.py tests/test_chat.py -v -p no:cacheprovider
git add src/websocket src/services/chat_service.py tests/test_websocket.py docs/superpowers/plans/2026-08-03-workspace-authorization-foundation.md
git commit -m "feat: enforce websocket conversation authorization"
```

---

### Task 7: Invitation và External Contact

**Files:**
- Modify: `src/db/models.py`
- Create: `src/db/migrations/versions/20260803_03_workspace_invitations.py`
- Create: `src/models/invitation_schemas.py`
- Create: `src/models/external_contact_schemas.py`
- Create: `src/services/invitation_service.py`
- Create: `src/services/external_contact_service.py`
- Create: `src/api/invitation_routes.py`
- Create: `src/api/external_contact_routes.py`
- Modify: `src/main.py`
- Create: `tests/test_invitations.py`
- Create: `tests/test_external_contacts.py`

**Interfaces:**
- Produces: `create_workspace_invitation`, `accept_workspace_invitation`, `revoke_invitation`, `invite_external_to_conversation`, `link_external_contact`.
- Consumes: workspace/role authorization và conversation manager role.

- [ ] **Step 1: Viết failing invitation tests**

Test token chỉ lưu hash, owner-only admin invitation, expiry, revoke, duplicate pending invitation, external scope và external không list directory.

```python
assert invitation.token_hash != raw_token
assert await can_access_conversation(external_user, invited_conversation.id)
assert not await can_access_conversation(external_user, other_conversation.id)
```

- [ ] **Step 2: Chạy test để xác nhận fail**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_invitations.py tests/test_external_contacts.py -v -p no:cacheprovider
```

- [ ] **Step 3: Implement token lifecycle**

Token tạo bằng `secrets.token_urlsafe(32)`, chỉ trả token thô đúng một lần, lưu SHA-256 hash, expiry mặc định 72 giờ và status transition được validate trong service.

- [ ] **Step 4: Implement external contact scope**

External contact model đã được tạo ở Task 5. Task này thêm invitation model/revision `20260803_03`, service lifecycle, unique normalized email trong workspace, liên kết optional với user account, và chỉ cho conversation manager có quyền thêm external contact.

- [ ] **Step 5: Chạy tests, progress và commit**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_invitations.py tests/test_external_contacts.py -v -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check src tests
git add src tests docs/superpowers/plans/2026-08-03-workspace-authorization-foundation.md
git commit -m "feat: add scoped workspace and external invitations"
```

---

### Task 8: Frontend Workspace/Contact/Group integration

**Files:**
- Create: `Frontend/src/api/workspaces.js`
- Create: `Frontend/src/api/invitations.js`
- Create: `Frontend/src/api/contacts.js`
- Create: `Frontend/src/hooks/useWorkspaces.js`
- Create: `Frontend/src/hooks/useWorkspaceMembers.js`
- Create: `Frontend/src/hooks/useConversationParticipants.js`
- Create: `Frontend/src/context/WorkspaceContext.jsx`
- Create: `Frontend/src/pages/WorkspaceMembersPage.jsx`
- Create: `Frontend/src/pages/ExternalContactsPage.jsx`
- Create: `Frontend/src/pages/WorkspaceSettingsPage.jsx`
- Create: `Frontend/src/components/workspace/WorkspaceSwitcher.jsx`
- Create: `Frontend/src/components/workspace/MemberTable.jsx`
- Create: `Frontend/src/components/contacts/ExternalContactModal.jsx`
- Modify: `Frontend/src/components/chat/NewConversationModal.jsx`
- Modify: `Frontend/src/components/layout/Sidebar.jsx`
- Modify: `Frontend/src/router/AppRouter.jsx`
- Modify: `Frontend/src/main.jsx`

**Interfaces:**
- Consumes: workspace/member/invitation/contact APIs từ Task 2 và Task 7.
- Produces: selected workspace context; internal member picker; group creation; external invitation UI; role-aware settings routes.

- [ ] **Step 1: Tạo API modules và context**

```js
export const listWorkspaces = token => apiFetch('/workspaces', { token })
export const listMembers = (token, workspaceId) => apiFetch(`/workspaces/${workspaceId}/members`, { token })
```

`WorkspaceContext` persist `orbit_workspace_id`, nhưng luôn xác nhận workspace vẫn nằm trong API response trước khi dùng.

- [ ] **Step 2: Chuyển NewConversationModal sang workspace directory**

Modal chỉ tìm active internal member của selected workspace; guest không nhận directory response. Group request gửi `workspace_id`, `type`, `name`, `participant_ids`.

- [ ] **Step 3: Thêm member/contact/settings pages**

Route guard dựa vào workspace role chỉ phục vụ UX; backend vẫn là authority. Owner/admin thấy invitation và external contact controls; member/guest không thấy action không được phép.

- [ ] **Step 4: Build và manual two-account test**

```powershell
cd Frontend
npm run build
```

Expected: Vite build exit 0. Test thủ công owner tạo group, member nhận message realtime, guest không thấy directory, external chỉ mở conversation được mời.

- [ ] **Step 5: Progress và commit**

```powershell
git add Frontend/src docs/superpowers/plans/2026-08-03-workspace-authorization-foundation.md
git commit -m "feat: add workspace-aware chat management UI"
```

---

### Task 9: Full verification và handoff docs

**Files:**
- Modify: `README.md`
- Modify: `docs/branches/G19-T132-Luong-Tri-Tue.md`
- Modify: `ARCHITECTURE.md`
- Modify: `SYSTEM_OVERVIEW.md`
- Modify: `docs/superpowers/plans/2026-08-03-workspace-authorization-foundation.md`

**Interfaces:**
- Consumes: toàn bộ implementation Tasks 1–8.
- Produces: verified documentation phản ánh code thật và completed plan checklist.

- [ ] **Step 1: Chạy backend tests đầy đủ**

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v --tb=short -p no:cacheprovider
```

Expected: 0 failed.

- [ ] **Step 2: Chạy lint**

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests scripts
```

Expected: `All checks passed!`.

- [ ] **Step 3: Chạy frontend build**

```powershell
cd Frontend
npm run build
```

Expected: Vite exit 0.

- [ ] **Step 4: Kiểm tra migration trên database tạm**

Tạo SQLite database tạm trong workspace, chạy upgrade hai lần và xác nhận lần hai không đổi row counts. Không dùng `data/app.db` thật cho verification tự động.

- [ ] **Step 5: Cập nhật tài liệu theo trạng thái thực**

Chuyển các mục Workspace từ `Designed` sang `Implemented` chỉ khi verification tương ứng pass. Ghi rõ external invitation nào cần email delivery provider nếu MVP chỉ trả invitation token.

- [ ] **Step 6: Final progress và commit**

```powershell
git add README.md ARCHITECTURE.md SYSTEM_OVERVIEW.md docs/branches/G19-T132-Luong-Tri-Tue.md docs/superpowers/plans/2026-08-03-workspace-authorization-foundation.md
git commit -m "docs: complete workspace authorization handoff"
```

Plan hoàn thành khi toàn bộ checkbox được đánh dấu, bảng Progress có commit cho từng task và verification commands đều có fresh evidence.
