# Kế hoạch 7 ngày — Người B: Product Delivery Agent

> **Implementation readiness:** Xem [Product Delivery implementation readiness](ROLE_B_PRODUCT_DELIVERY_IMPLEMENTATION_READINESS.md) trước khi bắt đầu B1. Tài liệu này khóa rule nghiệp vụ, phân biệt phần có thể làm ngay và các shared-platform gate bắt buộc.

> **Owner:** B — Product Delivery Agent Owner
>
> **Thời lượng:** 7 ngày làm việc
>
> **Mục tiêu:** hoàn thành một Delivery vertical slice từ scoped data → tools → Agent → WorkspaceBrief → UI → HITL → eval, không vượt ranh giới Product Delivery Workspace.
>
> **Foundation:** Product Delivery Workspace phải có trước khi bắt đầu; xem [Enterprise Workspace Foundation](ENTERPRISE_WORKSPACE_FOUNDATION.md).

## 1. Kết quả cuối tuần

Người B phải bàn giao được một Product Delivery Agent có thể:

1. Nhận request trong `product-delivery` Workspace từ lead/member hợp lệ.
2. Đọc đúng nguồn Delivery đã link và đang có AI consent.
3. Tổng hợp milestone, overdue, due soon, blocker, unassigned item và dependency.
4. Phân biệt fact, inference, recommendation và data gap.
5. Trả mọi fact quan trọng kèm `SourceReference`.
6. Sinh `WorkspaceBrief(brief_type=delivery)` đúng contract v1.
7. Đề xuất reminder/meeting dưới dạng `ActionProposal`, không tự thực thi.
8. Hiển thị kết quả trên User UI với loading, empty, denied, partial, stale và error state.
9. Vượt qua golden dataset, cross-workspace denial, prompt-injection và consent-revoke tests.

Không coi Agent hoàn thành nếu chỉ có prompt hoặc chỉ chạy bằng mock.

## 2. Baseline trước ngày 1

### 2.1 Đã có

- Company Root single-company..
- Product Delivery Workspace với key canonical `product-delivery`.
- Lead/member lifecycle và user discovery.
- Conversation mapping `classification=delivery`.
- `AgentContext`, `AgentState`, router, scope resolver và resource guard.
- Product Delivery profile/tool names trong registry.
- `ToolResult`, `SourceReference`, `ActionProposal` và `WorkspaceBrief` contract v1.
- Feature flags `MULTI_AGENT_ENABLED` và `PRODUCT_DELIVERY_AGENT_ENABLED`, mặc định tắt.
- 15 case `delivery_summary` trong golden dataset.

### 2.2 Chưa có và phải xử lý trong tuần

- Product Delivery prompt/profile implementation.
- Delivery output schema/validator.
- Delivery scoped service và tool implementations.
- Agent invocation path tích hợp profile runtime.
- Delivery WorkspaceBrief producer/store integration.
- Delivery UI.
- Durable HITL integration cho proposal Delivery.
- Live evaluator và E2E evidence.

### 2.3 Dependency phải khóa với A

Trước khi nối DB thật, B phải nhận câu trả lời rõ cho ba interface:

| Dependency | Owner | B được làm trước bằng gì | Điều kiện nối thật |
|---|---|---|---|
| Invocation API/profile runner | A | Gọi profile handler trực tiếp trong test | Router + context builder chạy trước model |
| `Task.agent_workspace_id` hoặc scoped task query | A | Fixture/task từ allowed conversation IDs | Migration/query policy có negative test |
| WorkspaceBrief persistence/publication | A + D | Validate contract và trả object in-memory | Store có lineage, expiry và audit |
| Durable ActionProposal executor | A | Tạo proposal object, mock executor | Revalidation + idempotency tests xanh |
| Shared Workspace UI shell | A | Component Delivery độc lập bằng fixture | Workspace context/capability API ổn định |

Nếu `Task.agent_workspace_id` chưa có, B **không được** query mọi task trong Company Root. Chỉ được dùng fixture hoặc task chứng minh được nguồn từ `allowed_resource_ids`.

## 3. Phạm vi sở hữu

### 3.1 B được tạo và sửa

```text
src/agents/profiles/product_delivery.py
src/agents/schemas/delivery.py
src/agents/tools/delivery_tasks.py
src/agents/tools/delivery_messages.py
src/agents/tools/delivery_milestones.py
src/agents/tools/delivery_people.py
src/agents/tools/delivery_brief.py
src/agents/tools/delivery_actions.py
src/services/delivery_workspace_service.py
Frontend/user/src/components/agents/delivery/*
Frontend/user/src/pages/DeliveryAgentPage.jsx
eval/fixtures/delivery_*.json
tests/test_agents/test_product_delivery.py
tests/test_agents/test_delivery_tools.py
tests/test_agents/test_delivery_security.py
```

Tên file có thể gộp nếu module quá nhỏ, nhưng phải giữ ranh giới profile/schema/tool/service/UI/test.

### 3.2 Shared files không tự sửa

```text
src/agents/contracts.py
src/agents/state.py
src/agents/graph.py
src/agents/router.py
src/agents/context_builder.py
src/agents/tools/registry.py
src/db/models.py
src/config.py
src/db/migrations/versions/*
```

Nếu B cần đổi shared contract, mở PR riêng, mô tả consumer impact và cần A cùng D review trước khi tiếp tục integration.

## 4. Contract của Delivery Agent

### 4.1 Input

```text
AgentContext
├── runtime.agent_profile = product_delivery
├── request.requested_scope = workspace
├── request.intent = delivery_brief
├── request.target_agent_workspace_id = product-delivery workspace ID
├── actor.business_role = lead | member
└── authorization
    ├── decision = ALLOW
    ├── allowed_agent_workspace_ids = [target]
    ├── allowed_resource_ids = [linked, consented Delivery sources]
    └── consent_scope_hash
```

Sai bất kỳ điều kiện nào phải fail trước model/tool.

### 4.2 Domain output

Tạo strict Pydantic schema `DeliveryBriefPayload`:

```json
{
  "headline": "string",
  "milestones": [],
  "overdue_items": [],
  "due_soon_items": [],
  "blocked_items": [],
  "unassigned_items": [],
  "dependencies": [],
  "decisions_needed": [],
  "recommendations": [],
  "data_gaps": [],
  "source_ids": [],
  "generated_at": "ISO-8601"
}
```

Mỗi item quan trọng tối thiểu có `id`, `title`, `status`, `assignee_id?`, `due_at?`, `source_ids` và `confidence` nếu là extraction.

### 4.3 WorkspaceBrief handoff

Delivery producer ánh xạ payload vào common `WorkspaceBrief`:

- `brief_type=delivery`.
- `producer_profile=product_delivery`.
- Không có `release_readiness`.
- Source phải cùng Agent Workspace.
- `generated_at`, `expires_at`, period và timezone hợp lệ.
- Thiếu nguồn hoặc dữ liệu phải vào `data_gaps`, không được bịa.

## 5. Tool behavior

| Tool | Trách nhiệm | Side effect | Test bắt buộc |
|---|---|:---:|---|
| `get_delivery_tasks` | Lấy task/work item scoped, normalize state/deadline/assignee | Không | Cross-workspace, overdue, unassigned |
| `search_delivery_messages` | Tìm trong linked group conversation đã consent | Không | Resource allowlist, revoke consent, injection |
| `get_delivery_milestones` | Lấy milestone/release target có cấu trúc | Không | Missing/stale/duplicate |
| `get_delivery_people` | Resolve assignee tối thiểu | Không | Không trả PII dư thừa |
| `build_delivery_brief` | Validate và tạo Delivery WorkspaceBrief | Không | Contract/source/freshness |
| `propose_delivery_reminder` | Tạo preview proposal | Có sau approval | Không execute trực tiếp |
| `propose_delivery_meeting` | Tạo preview proposal | Có sau approval | Payload hash/expiry/idempotency |

Mọi read tool nhận trusted context, gọi resource guard trước khi đọc và trả `ToolResult`, không trả ORM object/raw exception.

## 6. Lịch thực hiện 7 ngày

## Ngày 1 — Khóa Delivery contract, skeleton và test-first

### Sáng — 3 giờ

- Xác nhận Workspace `product-delivery`, lead/member và feature flag đang tắt.
- Đọc/map 15 case `delivery_summary` và các case permission/injection/revoke liên quan; xem [Delivery case matrix](ROLE_B_DELIVERY_CASE_MATRIX.md).
- Chốt `DeliveryBriefPayload`, state enum và quy tắc overdue/due soon/blocker/unassigned.
- Chốt prompt responsibilities và refusal rules.
- Tạo fixture tối thiểu: happy, empty, partial, ambiguous, tool error.

### Chiều — 4 giờ

- Tạo `profiles/product_delivery.py` và `schemas/delivery.py`.
- Viết output validator trước khi nối LLM.
- Tạo test profile chỉ nhận `workspace + delivery_brief`.
- Tạo test prompt không có quyền tự mở rộng source/tool.
- So sánh output producer dự kiến với `eval/fixtures/delivery_brief_v1.json`.

### PR-B1 — Delivery schema/profile skeleton

Deliverable:

- Strict schema và pure validation functions.
- Versioned prompt constant.
- Ít nhất 10 unit tests.

Gate cuối ngày:

- Invalid/extra field bị reject.
- Delivery brief không nhận `release_readiness`.
- Không sửa shared contract.
- Ruff, unit tests và dataset validation xanh.

## Ngày 2 — Scoped read service và read-only tools

### Sáng — 3 giờ

- Viết `delivery_workspace_service.py` với query nhận explicit Company ID, Agent Workspace ID và allowed resource IDs.
- Chuẩn hóa task state và deadline bằng pure functions.
- Thiết kế data gap khi task/milestone source chưa có.
- Không dùng raw Company-wide query.

### Chiều — 4 giờ

- Implement `get_delivery_tasks`, `search_delivery_messages`, `get_delivery_milestones`, `get_delivery_people`.
- Mỗi tool trả `ToolResult + SourceReference`.
- Thêm resource-guard call và consent-hash revalidation.
- Thêm timeout/tool-error normalization.

### PR-B2 — Delivery scoped reads

Test bắt buộc:

- Lead/member Delivery được ALLOW.
- User ngoài Workspace bị DENY trước query.
- Delivery user đoán QA resource ID bị DENY.
- Private/direct conversation không đi vào source.
- Consent revoke giữa run bị `CONSENT_CHANGED`.
- Prompt injection trong message không đổi allowlist.

Gate cuối ngày:

- Unauthorized leakage bằng 0.
- Mọi returned record có source ID.
- Test không mock bỏ qua resource guard.

## Ngày 3 — Planner/profile runtime và Delivery WorkspaceBrief

### Sáng — 3 giờ

- Viết profile handler nhận trusted `AgentContext`.
- Bind đúng bảy tool trong registry; gọi tool ngoài allowlist phải fail.
- Viết system prompt: evidence-first, no productivity scoring, clarification khi assignee/date mơ hồ.
- Giới hạn tool/token budget và vòng lặp.

### Chiều — 4 giờ

- Implement `build_delivery_brief`.
- Validate source Workspace, period, generated/expiry time và data gaps.
- Nối invocation/profile runner khi A đã cung cấp API; nếu chưa, giữ adapter riêng có integration test trực tiếp.
- Phát hành DeliveryBrief candidate cho D bằng contract, chưa truyền raw message.

### PR-B3 — Delivery Agent read-only + brief producer

Gate cuối ngày:

- 15/15 `delivery_summary` structural cases pass.
- Happy path trả milestone/blocker/dependency có source.
- Empty/partial path trả data gap.
- WorkspaceBrief validate với common fixture.
- Feature flag vẫn tắt nếu API/store chưa an toàn.

## Ngày 4 — UI vertical slice và HITL proposals

### Sáng — 3 giờ

- Tạo `DeliveryAgentPage` và component cards.
- Hiển thị headline, milestone, blocker, dependency, decision, source và freshness.
- Implement loading, empty, denied, partial, stale, tool error và feature-disabled state.
- Không hiển thị raw internal policy/error stack.

### Chiều — 4 giờ

- Chỉ implement reminder/meeting proposal adapter khi A-DLV-05 đã xanh; nếu chưa, UI hiển thị action disabled thay vì proposal/executor giả.
- Khi A-DLV-05 sẵn sàng, UI approval card hiển thị actor, action, target, time, payload và expiry.
- Approve chỉ gọi shared executor; edit tạo proposal/hash mới.
- Double-click/double approve không tạo hai action.

### PR-B4 — Delivery UI + conditional proposal flow

Gate cuối ngày:

- Nếu action được enable: không side effect trước approval; revoke role trước approve làm proposal invalid; payload đổi bắt buộc confirm lại.
- Nếu A-DLV-05 chưa xanh: action UI disabled rõ lý do và không tạo proposal/executor giả.
- Keyboard/error/loading states hoạt động.
- User ngoài Delivery không mở được page bằng URL sửa tay.

## Ngày 5 — Eval, security và edge cases

### Sáng — 3 giờ

- Nối delivery subset của JSONL vào evaluator thật.
- Chạy delivery summary, routing, permission, injection, HITL và revoke cases.
- Ghi prompt/schema/policy/model version trong report.
- Phân loại failure: data, policy, tool, prompt, model hay UI.

### Chiều — 4 giờ

- Sửa ambiguity: assignee/date thiếu → clarification/data gap.
- Sửa stale/partial/tool-error behavior.
- Kiểm tra message count không bị dùng làm productivity score.
- Fuzz target Workspace/resource IDs và malicious tool instructions.

### PR-B5 — Delivery eval/security hardening

Gate cuối ngày:

- Delivery routing `>=95%`.
- Source coverage fact quan trọng `=100%`.
- Unauthorized leakage `=0`.
- Side-effect HITL coverage `=100%`.
- Không chỉnh expected dataset chỉ để làm test pass.

## Ngày 6 — Integration, performance và demo rehearsal

### Sáng — 3 giờ

- Rebase/pull integration mới nhất.
- Thay mock bằng scoped DB service, brief store và executor thật khi gate của A xanh.
- Chạy migration head trên database sạch và database có dữ liệu.
- Kiểm tra revoke/suspend/feature flag ở request tiếp theo.

### Chiều — 4 giờ

- Seed 2 consented Delivery groups, 10–15 task, 2 milestone, dependency và ambiguous inputs.
- Chạy UI smoke bằng lead/member/outsider accounts.
- Đo latency/token/tool budget; loại N+1 và retrieval dư.
- Rehearse demo “Release tuần này bị chặn ở đâu?”.

### PR-B6 — Delivery integration candidate

Gate cuối ngày:

- Read-only E2E chạy bằng dữ liệu thật.
- Brief thật thay được fixture mà D không đổi parser/contract.
- p95 read flow đạt mục tiêu PRD hoặc có data gap/waiver ghi rõ.
- Backend tests, User build và critical security tests xanh.

## Ngày 7 — Freeze, evidence và bàn giao

### Sáng — 3 giờ

- Không thêm tính năng.
- Chỉ sửa P0/P1 Delivery.
- Chạy full regression liên quan, dataset check và build.
- Pin prompt/schema/policy/model versions.

### Chiều — 4 giờ

- Chụp/ghi evidence happy, denial, stale/partial và HITL.
- Viết release note: đã có, giới hạn, flag, rollback.
- Bàn giao WorkspaceBrief sample thật cho D.
- Demo 2 phút và ký Delivery sign-off.

### PR-B7 — Delivery release evidence

Gate cuối ngày:

- Không critical/open security issue.
- Feature flag bật/tắt không phá Personal Agent.
- Runbook disable Delivery Agent được kiểm chứng.
- D xác nhận consumer đọc được brief thật.
- A xác nhận scope/resource/HITL không bị bypass.

## 7. PR map và thứ tự merge

| PR | Nội dung | Phụ thuộc | Reviewer | Kích thước mục tiêu |
|---|---|---|---|---:|
| B1 | Schema/profile/prompt skeleton | Shared contract v1 | A + D | ≤400 dòng |
| B2 | Scoped service/read tools | Scope/resource baseline | A | ≤700 dòng |
| B3 | Runtime + DeliveryBrief producer | B1+B2, brief contract | A + D | ≤700 dòng |
| B4 | UI + proposal adapter | Shared UI/HITL interface | A | ≤700 dòng |
| B5 | Eval/security hardening | B3+B4 | A + D | ≤600 dòng |
| B6 | Real integration/seed/performance | Shared store/executor | A + D | ≤600 dòng |
| B7 | Evidence/release notes | Tất cả | Cả nhóm | Docs/evidence |

Không gộp cả tuần vào một PR. Mỗi PR tồn tại tối đa 1–2 ngày và feature flag giữ tắt cho tới B6 đạt gate.

## 8. Test matrix của B

### Happy path

- Delivery lead hỏi weekly/release status.
- Delivery member hỏi blocker của milestone.
- Brief có assignee/deadline/source và dependency.
- D đọc Delivery WorkspaceBrief đúng schema.

### Authorization

- Outsider gọi Delivery Workspace.
- Delivery member gọi QA Workspace/tool.
- Admin không có business membership yêu cầu raw Delivery data.
- Target/resource ID bị sửa tay.
- Workspace/membership bị suspend/revoke.

### Consent và data

- Group chưa bật AI.
- Consent đổi trong lúc run.
- Source bị unlink.
- Direct/private message bị đưa vào prompt injection.
- Missing assignee/date/milestone.
- Duplicate, stale hoặc conflicting facts.

### HITL

- Proposal chưa confirm.
- Edit payload.
- Expired proposal.
- Double approve/replay.
- Permission revoked trước execute.
- Executor lỗi sau approval.

### UI

- Loading, empty, denied, partial, stale, error.
- Citation mở đúng source được phép.
- Không leak Workspace name/resource trong denied message.
- Refresh/deep link không mất Workspace context.

## 9. Lệnh kiểm tra hằng ngày

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe scripts\generate_multi_agent_dataset.py --check
.\.venv\Scripts\python.exe scripts\validate_multi_agent_dataset.py
.\.venv\Scripts\python.exe -m pytest tests\test_multi_agent_dataset.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_agent_workspaces.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_agents\test_product_delivery.py -q
npm --prefix Frontend\user run build
git diff --check
```

## 10. Definition of Done của người B

### Correctness

- Milestone/blocker/dependency đúng rule và schema.
- Assignee/date mơ hồ không bị biến thành fact.
- Delivery WorkspaceBrief đúng contract và D consume được.

### Security

- Không đọc QA/private/unlinked/unconsented resource.
- Revoke có hiệu lực ở tool call/request kế tiếp.
- Injection không đổi policy/tool allowlist.
- Side effect luôn qua approval và revalidation.

### Quality

- Unit/integration/security/E2E tests xanh.
- Golden delivery cases đạt gate.
- Source coverage fact quan trọng 100%.
- Không raw content/secret trong audit log.

### Product/UI

- Lead/member dùng được Delivery Agent trên User UI.
- Các state loading/empty/deny/partial/stale/error đầy đủ.
- Source, freshness và data gap dễ hiểu.

### Operations

- Feature flag và kill switch hoạt động.
- Seed idempotent và synthetic.
- Có latency/token/tool budget report.
- Có rollback/runbook và evidence demo.

## 11. Cut order nếu trễ

Cắt theo thứ tự từ trước đến sau:

1. UI animation/polish.
2. `get_delivery_people` nâng cao.
3. Meeting proposal; giữ một reminder proposal để chứng minh HITL.
4. Proactive suggestion.
5. Milestone visualization nâng cao.

Không được cắt:

- Authorization/resource guard.
- Consent/revoke behavior.
- Source/freshness/data gap.
- Delivery WorkspaceBrief contract.
- Cross-workspace denial.
- HITL cho mọi side effect còn giữ lại.

## 12. Báo cáo cuối ngày của B

Mỗi ngày cập nhật ngắn theo mẫu:

```text
Done:
- PR/commit:
- Test/evidence:

Blocked:
- Dependency assignee:
- Interface/decision cần nhận:

Risk:
- Security/data/contract risk:

Next:
- Việc đầu tiên sáng mai:
```

Không báo “xong Agent” nếu mới hoàn thành prompt, UI fixture hoặc structural dataset.

## 13. Backlog chi tiết theo từng tác vụ

Đây là bảng execution chính của B trong một tuần. Một task chỉ được chuyển `Done` khi artifact và
acceptance tương ứng đều có bằng chứng; phần code “đã viết nhưng chưa nối policy thật” vẫn là
`In progress`.

### 13.1 Các tác vụ nghiệp vụ Agent phải thực hiện

| Capability ID | Tác vụ của Agent | Input | Output bắt buộc | Không được làm | Ngày hoàn thành |
|---|---|---|---|---|---:|
| DLV-C01 | Xác định request Delivery hợp lệ | Trusted context + `delivery_brief` intent | Accept/refuse có policy reason | Tự đổi scope/profile | 1 |
| DLV-C02 | Đọc task Delivery | Allowed task/resource IDs | Normalized task + source | Query toàn Company Root | 2 |
| DLV-C03 | Tìm evidence trong group chat | Linked consented group IDs | Matching facts + source | Đọc direct/private/QA chat | 2 |
| DLV-C04 | Tổng hợp milestone/release target | Scoped structured records | Milestone, deadline, status, source | Bịa milestone thiếu dữ liệu | 2 |
| DLV-C05 | Resolve assignee tối thiểu | Scoped user IDs | ID/display name cần thiết | Trả PII/profile dư thừa | 2 |
| DLV-C06 | Phân loại health | Task/milestone facts | overdue/due soon/blocked/unassigned | Dùng message count đánh giá người | 3 |
| DLV-C07 | Xác định dependency/decision | Source-backed relations | dependency + assignee/deadline/gap | Suy đoán quan hệ như fact | 3 |
| DLV-C08 | Tạo Delivery WorkspaceBrief | Validated domain payload | Versioned brief + expiry + sources | Thêm `release_readiness` | 3 |
| DLV-C09 | Trả lời user | Brief/tool results | Headline, facts, recommendations, gaps | Che giấu data gap/tool error | 3–4 |
| DLV-C10 | Đề xuất reminder | Actor + target + time | ActionProposal preview | Tạo reminder trực tiếp | 4, chỉ sau A-DLV-05 |
| DLV-C11 | Đề xuất meeting | Actor + attendees + time | ActionProposal preview | Gửi invite trước approval | 4, chỉ sau A-DLV-05 |
| DLV-C12 | Phản ứng với revoke/stale/error | Current policy + freshness | Deny/partial/stale response | Dùng cache/quyền cũ | 5 |

### 13.2 Task board theo ngày

#### Ngày 1 — 7 giờ: contract, rule và profile

| Task ID | Thời lượng | Việc thực hiện | Artifact | Acceptance |
|---|---:|---|---|---|
| B1-01 | 0.5h | Xác nhận Workspace/profile/flag và dependency | Readiness note | Key/profile/role đúng; flag vẫn off |
| B1-02 | 1h | Đọc/map 15 delivery golden cases | Case-to-capability matrix | Mỗi case map vào rule/tool/output |
| B1-03 | 1.5h | Tạo `DeliveryBriefPayload` và item schemas | `schemas/delivery.py` | Strict, extra forbid, timezone validate |
| B1-04 | 1.5h | Viết pure rules overdue/due soon/blocked/unassigned | Rule functions | Boundary time/status tests pass |
| B1-05 | 1.5h | Viết profile/prompt v1 | `profiles/product_delivery.py` | Không tự mở scope/tool; evidence-first |
| B1-06 | 1h | Viết unit/contract tests | Test module | ≥10 tests; invalid payload bị reject |

#### Ngày 2 — 7 giờ: scoped service và tools

| Task ID | Thời lượng | Việc thực hiện | Artifact | Acceptance |
|---|---:|---|---|---|
| B2-01 | 1h | Định nghĩa scoped service interface | `delivery_workspace_service.py` | Mọi query nhận company/workspace/allowed IDs |
| B2-02 | 1.5h | Implement `get_delivery_tasks` | Delivery task tool | Không Company-wide fallback |
| B2-03 | 1.5h | Implement `search_delivery_messages` | Delivery search tool | Chỉ linked group + current consent |
| B2-04 | 1h | Implement `get_delivery_milestones` | Milestone tool | Missing/stale → data gap |
| B2-05 | 1h | Implement `get_delivery_people` | Minimal assignee resolver | Không lộ PII dư thừa |
| B2-06 | 1h | Tool/result/security tests | Tool tests | QA/private/guessed ID đều DENY |

#### Ngày 3 — 7 giờ: Agent runtime và WorkspaceBrief

| Task ID | Thời lượng | Việc thực hiện | Artifact | Acceptance |
|---|---:|---|---|---|
| B3-01 | 1h | Tạo Delivery profile handler | Profile runner | Chỉ nhận trusted context đúng profile |
| B3-02 | 1h | Bind planner với Delivery allowlist | Tool binding adapter | Tool ngoài registry bị chặn |
| B3-03 | 1h | Implement health/dependency synthesis | Pure/domain functions | Fact/inference/gap tách rõ |
| B3-04 | 1.5h | Implement `build_delivery_brief` | Brief producer | Type/profile/source/time validate |
| B3-05 | 1h | Thêm freshness/expiry/partial behavior | Validator/service | Brief stale không trình bày là current |
| B3-06 | 1h | Contract test với fixture của D | Handoff test | D consume không parse text tự do |
| B3-07 | 0.5h | Tạo sample output cho integration | Delivery brief fixture | IDs/schema/source ổn định |

#### Ngày 4 — 7 giờ: API/UI và HITL

| Task ID | Thời lượng | Việc thực hiện | Artifact | Acceptance |
|---|---:|---|---|---|
| B4-01 | 1h | Nối profile vào invocation adapter của A | API integration | Auth/context chạy trước model |
| B4-02 | 1h | Tạo Delivery page và protected route | Page/route | Outsider sửa URL vẫn bị deny |
| B4-03 | 1.5h | Tạo cards cho milestone/blocker/dependency/source | Delivery components | Source/freshness/gap hiển thị rõ |
| B4-04 | 1h | Implement loading/empty/deny/partial/stale/error | UI states | Không dùng một empty state cho mọi lỗi |
| B4-05 | 1h | Implement reminder proposal hoặc disabled action state | Proposal adapter/card | Chỉ enable sau A-DLV-05; chưa approve không có side effect |
| B4-06 | 1h | Implement meeting proposal hoặc disabled action state | Proposal adapter/card | Chỉ enable sau A-DLV-05; edit làm đổi hash/cần approve lại |
| B4-07 | 0.5h | UI/build/smoke tests | Evidence | Keyboard + production build pass |

#### Ngày 5 — 7 giờ: eval và security hardening

| Task ID | Thời lượng | Việc thực hiện | Artifact | Acceptance |
|---|---:|---|---|---|
| B5-01 | 1h | Nối delivery cases vào live evaluator | Runner mapping | Ghi model/prompt/schema/policy version |
| B5-02 | 1h | Chạy/tune 15 delivery summary cases | Eval result | Không sửa expected để né lỗi |
| B5-03 | 1.5h | Cross-workspace/IDOR tests | Security tests | Leakage = 0 |
| B5-04 | 1h | Prompt-injection tests trong source | Injection tests | Policy/tool allowlist không đổi |
| B5-05 | 1h | Revoke/consent/source-unlink tests | Stale-auth tests | Request/tool kế tiếp fail closed |
| B5-06 | 1h | Ambiguity/conflicting fact tests | Domain tests | Clarification/data gap đúng |
| B5-07 | 0.5h | Tổng hợp failure report | Eval report | Failure được phân loại nguyên nhân |

#### Ngày 6 — 7 giờ: dữ liệu thật, E2E và hiệu năng

| Task ID | Thời lượng | Việc thực hiện | Artifact | Acceptance |
|---|---:|---|---|---|
| B6-01 | 1h | Rebase và thay mock bằng shared implementation đã qua gate | Integrated branch | Không local bypass/fallback |
| B6-02 | 1h | Seed Delivery dataset idempotent | Seed + manifest | Synthetic, chạy lại không nhân bản |
| B6-03 | 1.5h | E2E lead/member/outsider/admin | E2E evidence | Đúng allow/deny cho bốn persona |
| B6-04 | 1h | E2E consent/revoke/HITL | E2E evidence | Revalidate và idempotency pass |
| B6-05 | 1h | Đo query/LLM/tool latency và budget | Performance report | Không N+1/retrieval dư |
| B6-06 | 1h | Rehearse Delivery demo | Demo checklist | Câu hỏi release có source/gap |
| B6-07 | 0.5h | Fix P0 integration | Small patch | Không mở thêm feature |

#### Ngày 7 — 7 giờ: freeze và bàn giao

| Task ID | Thời lượng | Việc thực hiện | Artifact | Acceptance |
|---|---:|---|---|---|
| B7-01 | 1.5h | Chạy regression/dataset/build | Test report | Tất cả Delivery gates xanh |
| B7-02 | 1.5h | Chỉ sửa P0/P1 | Final fixes | Không thêm tính năng |
| B7-03 | 1h | Chụp happy/deny/stale/HITL evidence | Evidence bundle | Trace/source nhìn thấy được |
| B7-04 | 1h | Bàn giao brief thật cho D | Brief + contract proof | Executive consumer đọc được |
| B7-05 | 1h | Viết flag/rollback/known limits | Runbook | Tắt Delivery không phá Personal flow |
| B7-06 | 1h | Demo/sign-off với A, C, D | Sign-off record | Scope/consumer/release được duyệt |

### 13.3 Việc có thể bắt đầu ngay và việc đang bị chặn

| Nhóm việc | Trạng thái bắt đầu | Task tương ứng | Ghi chú |
|---|---|---|---|
| Schema, pure rules, profile, prompt | `READY_NOW` | B1-02 → B1-06 | Không cần DB/source thật |
| Tool interface + fixture implementation | `READY_NOW` | B2-01 → B2-06 | Dùng trusted context fixtures |
| Brief validator/producer in-memory | `READY_NOW` | B3-03 → B3-07 | Chưa gọi là published brief |
| UI bằng fixture | `READY_NOW` | B4-02 → B4-04 | Không tuyên bố E2E |
| Structural/golden evaluator | `READY_NOW` | B5-01 → B5-02 | Live model runner có thể nối sau |
| Real task query | `WAIT_A_SCOPE` | B2-02, B6-01 | Chờ task → Agent Workspace binding an toàn |
| Invocation API thật | `WAIT_A_RUNTIME` | B4-01 | Chờ router/context được gọi từ API |
| Durable brief publication | `WAIT_A_STORE` | B3-04, B6-01 | Chờ generic store/lineage/audit do A bàn giao |
| Side-effect execution | `WAIT_A_HITL` | B4-05 → B4-06 | Chỉ test contract object; UI/action executor giữ disabled cho tới A-DLV-05 |
| Real chat retrieval | `WAIT_SOURCE_CONSENT` | B2-03, B6-03 | Cần linked Delivery group + manager bật AI |

Trong khi chờ dependency, B tiếp tục phần `READY_NOW`; không tạo đường tắt quyền hoặc schema riêng
để “cho chạy được”.

## 14. Mô hình vận hành Delivery Agent — canonical cho MVP/demo

> Phần này là quyết định canonical cho quyền, nguồn group chat, cách gọi tool và demo. Khi có
> mâu thuẫn với các câu mô tả `lead/member` chung ở phần trước, phần này được ưu tiên.
>
> Mục tiêu MVP là **một Delivery Agent chính gọi tool có scope**, không triển khai sub-agent,
> không quét mọi group cho một câu hỏi chỉ định và không giao quyền dựa vào prompt/client.

### 14.1 Role: bỏ business role `owner`, tách quyền quản trị và nghiệp vụ

`Owner: B` ở đầu tài liệu chỉ là người chịu trách nhiệm delivery của dự án, **không phải** role
trong sản phẩm. Trong Product Delivery Workspace chỉ tồn tại hai business role:

| Principal | Quyền chính | Không mặc định có quyền |
|---|---|---|
| `platform_admin` | Tạo/suspend Agent Workspace; chọn profile; chỉ định lead/member; link/unlink source group; audit cấu hình | Đọc raw chat, tiến độ hoặc brief nghiệp vụ |
| `lead` | Xem overview của Delivery Workspace; xem các group Delivery đã link; xem blocker/milestone/dependency toàn phạm vi; tạo proposal nghiệp vụ | Đọc raw QA/private chat; tự mở rộng source scope |
| `member` | Xem việc được giao cho mình, decision/action item có mình là audience/assignee và group Delivery mà mình là participant | Xem overview toàn phòng hoặc group Delivery không tham gia |
| `executive lead` | Xem Delivery/QA **WorkspaceBrief đã validate** và aggregate cross-workspace; chốt quyết định liên phòng | Đọc raw Delivery/QA group chỉ vì cấp bậc cao hơn |
| `executive_viewer` | Xem aggregate được cấp trong Executive Workspace | Đọc raw group hoặc gọi tool nội bộ Delivery/QA |

Không tạo role `owner` ở Agent Workspace. `Task.owner_id` trong dữ liệu cũ chỉ là người chịu
trách nhiệm task, không phải access role; các DTO/màn Delivery mới phải dùng tên
`assignee_id` hoặc `responsible_user_id` để tránh nhầm lẫn. Migration rename/backward-compatible
thuộc shared PR của A, không do B tự sửa `Task`.

### 14.2 Group chat nào là nguồn hợp lệ

Delivery Agent không lấy toàn bộ conversation của công ty. Một group là source hợp lệ khi tất cả
điều kiện sau đúng:

```text
Conversation.workspace_id == Company Root
AND Conversation.type == "group"
AND Conversation.ai_enabled == true
AND được link vào target Product Delivery Agent Workspace
AND AgentWorkspaceConversation.classification == "delivery"
AND target workspace + business membership còn active
```

`direct`/DM, personal memory, AssistantThread, group QA, group chưa link và group đã tắt AI
không phải source của Delivery Agent. Một conversation chỉ link vào một Agent Workspace; không
được vừa là raw source của Delivery vừa là raw source của QA.

Group dùng policy AI chung do manager kiểm soát. Tắt AI, unlink source hoặc revoke membership phải
đổi effective scope ở request/tool tiếp theo; cache không được dùng quyền cũ.

### 14.3 Scope theo role và effective source set

Server luôn resolve scope từ identity + database; model và client chỉ có thể **đề nghị thu hẹp**
phạm vi, không thể cấp thêm quyền.

```text
lead_allowed_groups
  = tất cả Delivery group linked + AI enabled trong target workspace

member_allowed_groups
  = Delivery group linked + AI enabled
    ∩ group mà member là active participant

member_allowed_tasks
  = task có assignee_id/current owner_id = current user
    và có Agent Workspace/source scope hợp lệ

member_allowed_decisions
  = decision/action item có current user trong audience_ids hoặc assignee_ids
```

Với `lead`, `allowed_resource_ids` là toàn bộ Delivery source group. Với `member`, không được tái
sử dụng allowlist của lead: scope resolver hoặc Delivery policy layer phải trả allowlist đã intersect
với `ConversationParticipant` active. Chỉ membership ở Agent Workspace là chưa đủ.

Nếu member không có group hợp lệ, task hợp lệ hoặc decision được cấp, Agent trả trạng thái empty/
no-access an toàn; không tiết lộ tên, số lượng hay nội dung group khác.

### 14.4 Decision và action item của trưởng phòng

Không để LLM quét mọi chat rồi đoán câu nào là “quyết định của trưởng phòng”. Một quyết định được
hiển thị cho member phải là record có cấu trúc (có thể dùng fixture ở MVP, nhưng production cần
shared model/store):

```text
DeliveryDecision
- id
- agent_workspace_id
- title / decision_text
- status: proposed | confirmed | superseded | cancelled
- audience_user_ids / assignee_user_ids
- due_at?
- source_message_ids / SourceReference
- confirmed_by_lead_user_id?
- confirmed_at?
- expires_at? / freshness
```

Member chỉ xem decision khi là audience/assignee. Lead có thể xem mọi decision trong Workspace.
Decision thiếu audience/assignee, evidence hoặc trạng thái confirm không được coi là instruction
cho member; phải trả `data_gap` hoặc chỉ là recommendation/proposal.

### 14.5 Hai kiểu truy vấn: workspace overview và single-group snapshot

| Kiểu view | Ai gọi | Source scope | Output |
|---|---|---|---|
| `workspace_overview` | Lead | Tất cả group Delivery hợp lệ của Workspace | `DeliveryBrief` tổng quan phòng ban |
| `group_snapshot` | Lead; member chỉ khi là participant | Một group được server xác minh | `GroupDeliverySnapshot`, không gắn nhãn báo cáo toàn phòng |
| `my_work` | Member | Task/decision/group được cấp cho user | My tasks, blockers, decisions liên quan user |

Khi Lead chỉ định một group, effective scope luôn bị thu hẹp:

```text
requested_group_id = Apollo
effective_group_ids = lead_allowed_groups ∩ {Apollo}
```

Không có fan-out qua toàn bộ group trong trường hợp này. Nếu intersection rỗng vì ID bị sửa tay,
group không link, đã tắt AI hoặc sai Workspace, trả deny/not-available theo API policy; không fallback
sang all-groups query.

`GroupDeliverySnapshot` tối thiểu có:

```text
view_scope = group
conversation_id
period_start / period_end
generated_at / expires_at
headline
tasks / blockers / dependencies / decisions_needed / data_gaps
SourceReference cho mọi fact quan trọng
```

PR-B1 phải thêm discriminator `view_scope = workspace | group | member` vào Delivery domain schema
trước khi B3 publish/hiển thị output. Common `WorkspaceBrief` vẫn dùng cho handoff Delivery
workspace-level sang Executive; group snapshot là response/view nội bộ, không được publish nhầm
thành brief toàn Workspace.

### 14.6 Cách UI và API chọn group an toàn

Đường chính của demo là selector trên Delivery page, do capability API server-filtered cung cấp:

```text
[ Tất cả Delivery groups v ]
  - Apollo Delivery
  - Release tuần 34
  - API Integration
```

UI có thể gửi `requested_conversation_id`, nhưng đó là input untrusted. API phải validate ID thuộc
effective allowlist trước khi tạo trusted context/tool request. Không truyền tên hoặc ID group vào
system prompt để model tự quyết quyền.

Natural-language fallback chỉ resolve tên trong danh sách group mà actor đã có quyền. Nếu `Apollo`
khớp nhiều group hoặc không đủ chắc chắn, Agent hỏi clarification. Nó không search tên group toàn
công ty và không để response tiết lộ candidate ngoài scope.

### 14.7 Tool-first architecture cho MVP — không dùng sub-agent

MVP có **một** Delivery Agent chính. Agent dùng deterministic route/profile guard, rồi gọi tối đa
3–4 read-only tool đã allowlist; build brief bằng domain validator/pure functions. LLM dùng để diễn
đạt và phân biệt fact/inference/recommendation, không dùng để chọn scope, chạy SQL hay cấp quyền.

```text
UI/API request
  -> router + context builder + role/source resolver
  -> trusted AgentContext (effective group/task/decision scope)
  -> Delivery Agent chính
       -> get_delivery_tasks
       -> search_delivery_messages
       -> get_delivery_milestones (hoặc PARTIAL/data gap)
       -> build_delivery_brief / build_group_snapshot
  -> strict validator + citations + UI
```

Không gọi một LLM/sub-agent cho từng group. `search_delivery_messages` nhận query, time window,
limit và trusted context; service dùng `effective_group_ids` trong query server-side. Với overview,
service query theo tập group được phép có pagination/budget; với selected group, query chỉ một ID.
Không dùng `SELECT` Company Root rồi lọc trong prompt hay trong Python sau khi lấy raw data.

Ưu tiên nguồn và giới hạn retrieval MVP:

1. Structured task/work item là nguồn chính cho status, assignee, deadline.
2. Structured milestone/dependency là nguồn chính khi A-DLV-02 đã có.
3. Group message chỉ dùng làm evidence cho blocker/decision/dependency/data gap; trả excerpt tối
   thiểu cần thiết, SourceReference và message ID, không nhét full history vào LLM.
4. Default time window 7 ngày, default total message limit 20; mọi tăng limit phải server-bounded.
5. Thiếu milestone store hoặc source hợp lệ trả `PARTIAL` + data gap, không bịa milestone.

Sub-agent/fan-out chỉ là phase sau, khi có nhiều group, brief per-group bền vững, queue/cache và
observability. Khi đó mô hình là background refresh per-group -> validated snapshot cache ->
workspace aggregation, không phải agent con được tự cấp scope.

### 14.8 Tool contract và thứ tự triển khai MVP

| Thành phần | Input được tin cậy | Hành vi MVP | Output bắt buộc | Không được làm |
|---|---|---|---|---|
| `resolve_delivery_view` (server policy/API, không expose LLM tool) | identity, target workspace, requested group/view | Resolve role, effective group/task/decision scope; reject ambiguity/IDOR | trusted view context + capability list | Tin role/group ID từ client |
| `get_delivery_tasks` | trusted context, effective group optional, period | Query task có workspace/source/assignee bind phù hợp role | `ToolResult`, item + source | Company-wide fallback |
| `search_delivery_messages` | trusted context, query, time window, limit | Search trong effective group IDs, dùng bounded excerpts | `ToolResult`, evidence + `SourceReference` | Accept arbitrary conversation ID; raw full-history dump |
| `get_delivery_milestones` | trusted context, effective group optional | Đọc structured store; nếu chưa có trả PARTIAL | milestone hoặc `MILESTONE_SOURCE_NOT_AVAILABLE` | Sinh milestone từ chat như fact |
| `get_delivery_people` | scoped assignee IDs | Resolve display name tối thiểu của assignee/audience | minimal person payload | Lộ profile/PII không cần thiết |
| `build_delivery_brief` | validated tool results + view scope | Pure synthesis/rule validation; map fact/inference/gap | DeliveryBrief hoặc GroupSnapshot | Publish Executive handoff cho group snapshot |

MVP demo không cần action executor. Nếu giữ action UI, nó chỉ render disabled “coming after
approval infrastructure”; không tạo `ActionProposal` giả để demo như thể đã gửi reminder/meeting.

### 14.9 Trình tự triển khai thực tế cho demo

**MVP-D1 — policy + schema (ngày 1):** chốt role matrix; thêm `view_scope`; fixture cho lead
overview, lead single group, member my-work, outsider deny và ambiguous group name. Ghi rõ task
assignee naming transition.

**MVP-D2 — resolver + read tools (ngày 2):** A bổ sung/duyệt member participant intersection và
trusted `requested_conversation_id` validation. B triển khai read tool fixture-first; read DB thật
chỉ sau A-DLV-01/A-DLV-02. Mỗi tool re-check membership, link và consent trước query.

**MVP-D3 — deterministic snapshot (ngày 3):** build `workspace_overview`, `group_snapshot` và
`my_work`; source coverage fact quan trọng 100%; chưa publish group snapshot sang Executive.

**MVP-D4 — UI/demo (ngày 4):** selector “Tất cả / một group”, member My Work, states loading/empty/
deny/partial/stale/error, source citation. Feature flags vẫn off mặc định.

**MVP-D5 — security/evidence (ngày 5):** IDOR, participant mismatch, revoked AI, unlink giữa run,
ambiguous group name, no-company-scan, prompt injection và source coverage. Sau gate mới chạy demo.

### 14.10 Kịch bản demo bắt buộc

Seed synthetic, idempotent: 2 Delivery group linked/AI enabled (Apollo, Release 34), 1 QA group,
1 direct chat, 1 unlinked Delivery group, 1 lead, 1 member Apollo, 1 member Release và 1 outsider.
Seed 10–15 task, trong đó có overdue/due soon/blocked/unassigned; mọi task/demo fact có source ID.

| Demo | Actor + request | Kết quả mong đợi |
|---|---|---|
| D1 | Lead: “Tiến độ Delivery tuần này?” | Workspace overview từ 2 Delivery group, facts có source, data gap rõ |
| D2 | Lead chọn Apollo: “Tiến độ group này?” | Chỉ query Apollo; không đọc Release 34; trả GroupSnapshot |
| D3 | Member Apollo: “Việc và quyết định nào đang chờ tôi?” | Chỉ task assigned/audience và Apollo participant scope |
| D4 | Member Apollo cố chọn Release 34 | Deny/not-available, không leak tên/nội dung Release |
| D5 | Lead cố chọn QA hoặc direct chat | Deny trước tool/query |
| D6 | Manager tắt AI hoặc unlink Apollo giữa run | Tool kế tiếp trả consent/source changed; không dùng cache cũ |
| D7 | Gõ “Apollo” nhưng có nhiều group hợp lệ | Clarification, không tự chọn group |

### 14.11 Gate thay đổi shared-platform bắt buộc

Ngoài A-DLV-01 đến A-DLV-05, A cần duyệt các interface sau trước B2 production integration:

| ID | Shared thay đổi | Acceptance |
|---|---|---|
| A-DLV-06 | Role-aware source resolver: member group scope = linked/AI-enabled ∩ active conversation participant | Lead/member cùng request không nhận cùng allowlist mặc định; negative participant test xanh |
| A-DLV-07 | Server-side selected-group resolver/capability API | ID sửa tay, QA/direct/unlinked/ambiguous group không tới tool; selector không liệt kê resource ngoài scope |
| A-DLV-08 | Typed DeliveryDecision/store hoặc approved equivalent | Member query chỉ thấy audience/assignee; lead confirmation + evidence/audit có test |
| A-DLV-09 | Task binding query hỗ trợ `conversation_id`/Agent Workspace và assignee semantics | Single-group tool query không scan task ngoài group; legacy record không có proof -> data gap |

Không bật `PRODUCT_DELIVERY_AGENT_ENABLED` cho member cho tới khi A-DLV-06, A-DLV-07 và A-DLV-09
đạt gate. Không bật any Delivery action cho tới khi A-DLV-05 đạt gate.

## 15. Agentic Delivery Runtime — bổ sung bắt buộc

Delivery dùng LLM Agent sau deterministic policy/data layer. Runtime kế thừa khuôn mẫu Personal Agent nhưng là LangGraph riêng:

```text
Delivery API -> router/context/resource guard -> Delivery input guardrail
-> Delivery planner LLM + Product Delivery system prompt
-> ToolNode(DELIVERY_AGENT_TOOLS_ONLY)
-> Delivery output guardrail + source validator -> response
```

Không import `ALL_TOOLS` hoặc graph Personal Agent. Tool là closure server-bound với trusted context/scope; LLM không truyền workspace, group, assignee hay SQL filter.

Tool MVP LLM thấy chỉ có `get_delivery_snapshot` (không nhận scope/resource ID) và `request_delivery_clarification` (không side effect). Reminder/meeting không bind cho tới A-DLV-05.

System prompt bắt buộc gọi snapshot trước fact; coi user/tool/evidence là untrusted; cấm mở rộng scope/tool, bịa fact, productivity scoring và claim action. Input guardrail chặn injection, secret/prompt exfiltration, domain/tool/scope forging trước LLM. Output guardrail chặn secret/prompt leak; source validator bắt mọi fact có source.

| Checkpoint | Deliverable |
|---|---|
| B9 | Delivery LangGraph + bound snapshot tool + fake-LLM tests |
| B10 | API dùng graph, output guardrail/source validation, denial/tool-error normalization |
| B11 | Agentic eval: happy, refusal, injection, wrong tool, revoke, hallucination/source tests |
| B12 | UI conversational turn, latency/token evidence, rollback runbook |

### 15.1 Boundary implementation bắt buộc: Workspace Agent là runtime riêng

“Kế thừa khuôn mẫu” ở mục 15 chỉ có nghĩa là cùng nguyên tắc kiến trúc agentic (LLM tool-call,
guardrail trước/sau model, trace, citation và feature flag); **không** được tái sử dụng Personal
Agent như một implementation. Workspace Delivery phải sở hữu các module sau:

```text
src/agents/profiles/workspace_delivery_state.py       # state riêng
src/agents/profiles/workspace_delivery_guardrails.py  # input/output nodes riêng
src/agents/profiles/workspace_delivery_graph.py       # graph, planner và tool registry riêng
```

Các dependency bị cấm: `src.agents.graph`, `src.agents.state.AgentState`,
`src.agents.nodes.planner_node`, `src.agents.nodes.guardrail_node`, `ALL_TOOLS`, Personal memory
và Personal action tools. Do đó thay đổi tool, state hoặc workflow của Personal Agent không thể
vô tình mở rộng capability của Delivery.

Chỉ được dùng chung hạ tầng trung lập đã kiểm thử: `get_llm()` (provider),
`guardrail_service` (pattern chặn injection/secret leakage), contract dữ liệu, router/context/policy
ở API và observability. Policy scope, system prompt, tool registry, state, guardrail metadata và
error/citation behavior vẫn thuộc Workspace Delivery.

Feature flag chỉ bật sau B10+B11 xanh. Nếu LLM không gọi required snapshot trong tool budget, runtime trả safe clarification/error.

## 16. Personal Scope và Organization Workspace — invariant tích hợp bắt buộc

Product Delivery Workspace Agent và Personal Agent là hai capability boundary khác nhau. Việc backend dùng một bản ghi
`Workspace(type=personal)` làm namespace dữ liệu **không** có nghĩa người dùng phải chọn hoặc truyền Workspace tổ chức khi
dùng Personal Assistant, Tasks, Memory, Calendar hay Reminders.

Contract bắt buộc:

```text
Personal UI/API
  -> JWT user_id
  -> server tự resolve đúng một Personal Space nội bộ
  -> không nhận organization workspace_id làm điều kiện hoạt động

Organization/Delivery UI/API
  -> JWT user_id + organization workspace selection
  -> membership/business-role policy
  -> agent_workspace_id + authorized group scope
```

Quy tắc provisioning và dữ liệu:

- Mỗi `User` phải có đúng một Personal Space; unique owner constraint bảo đảm “không quá một”, còn register/login,
  administrative/demo seed và migration backfill bảo đảm “ít nhất một”.
- Password và Google login phải repair idempotent tài khoản legacy/import thiếu Personal Space trước khi phát JWT response.
- Personal Assistant không có `conversation_id` luôn resolve Personal Space từ JWT. `workspace_id` chỉ hợp lệ để đối chiếu
  cùng một `conversation_id` đã qua participant/consent authorization; không được dùng để đổi Personal Assistant sang
  Workspace Agent.
- Navbar trên route Personal hiển thị “Không gian cá nhân”; selector organization chỉ xuất hiện ở route Workspace và chỉ
  liệt kê `type=organization`.
- Seed demo phải chạy idempotent và tạo Personal Space cho cả Lead/Member để cùng một tài khoản test được hai boundary mà
  không trộn dữ liệu.

Acceptance gate bổ sung:

| Gate | Evidence bắt buộc |
|---|---|
| PERS-01 Provisioning invariant | Legacy/direct user login tạo đúng một Personal Space; login lặp không tạo trùng |
| PERS-02 Personal API contract | Lead và Member gọi Assistant/Tasks/Memory/Reminders không gửi `workspace_id` đều không lỗi |
| PERS-03 Migration | Database ở revision trước được backfill idempotent; số user thiếu Personal Space bằng 0 |
| PERS-04 UI boundary | Personal route không hiển thị organization selector; Workspace route không cho chọn Personal Space |
| PERS-05 Regression | Full backend tests, Ruff, migration tests và frontend production build xanh |

Đây là data/API/UI consistency gate, chưa được diễn giải thành R4 “Personal service extraction”. Personal Agent hiện vẫn ở
Core process cho tới khi R3 Registry/Gateway và kế hoạch R4 được triển khai riêng.
