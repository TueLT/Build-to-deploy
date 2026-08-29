# Product Delivery — Golden Case to Capability Matrix

Nguồn chuẩn: `eval/datasets/multi_agent_workspace_v1.jsonl`, category `delivery_summary`.
Mục đích của ma trận là khóa expectation nghiệp vụ cho B1/B3; nó không thay thế security
cases ở category `workspace_permission`, `prompt_injection` hay `membership_consent_revoke`.

| Case | Fact bắt buộc | Rule/capability Delivery | Source bắt buộc |
|---|---|---|---|
| DLV-001 | API đăng nhập: blocked | `DLV-C02`, `DLV-C03`, `DLV-C06`, `DLV-C08` | `delivery-message-001`, `delivery-task-001` |
| DLV-002 | Migration workspace: overdue | `DLV-C02`, `DLV-C06`, `DLV-C08` | `delivery-message-002`, `delivery-task-002` |
| DLV-003 | Trang release: due soon | `DLV-C02`, `DLV-C06`, `DLV-C08` | `delivery-message-003`, `delivery-task-003` |
| DLV-004 | Notification service: blocked | `DLV-C02`, `DLV-C03`, `DLV-C06`, `DLV-C08` | `delivery-message-004`, `delivery-task-004` |
| DLV-005 | Calendar integration: due soon | `DLV-C02`, `DLV-C06`, `DLV-C08` | `delivery-message-005`, `delivery-task-005` |
| DLV-006 | Audit dashboard: in progress | `DLV-C02`, `DLV-C08` | `delivery-message-006`, `delivery-task-006` |
| DLV-007 | Agent router: blocked | `DLV-C02`, `DLV-C03`, `DLV-C06`, `DLV-C08` | `delivery-message-007`, `delivery-task-007` |
| DLV-008 | Task extraction: in progress | `DLV-C02`, `DLV-C08` | `delivery-message-008`, `delivery-task-008` |
| DLV-009 | Workspace switcher: due soon | `DLV-C02`, `DLV-C06`, `DLV-C08` | `delivery-message-009`, `delivery-task-009` |
| DLV-010 | Consent revoke: blocked | `DLV-C02`, `DLV-C03`, `DLV-C06`, `DLV-C12` | `delivery-message-010`, `delivery-task-010` |
| DLV-011 | Prompt registry: unassigned | `DLV-C02`, `DLV-C06`, `DLV-C08` | `delivery-message-011`, `delivery-task-011` |
| DLV-012 | Deployment runbook: in progress | `DLV-C02`, `DLV-C08` | `delivery-message-012`, `delivery-task-012` |
| DLV-013 | Usage metrics: due soon | `DLV-C02`, `DLV-C06`, `DLV-C08` | `delivery-message-013`, `delivery-task-013` |
| DLV-014 | Assistant thread: overdue | `DLV-C02`, `DLV-C06`, `DLV-C08` | `delivery-message-014`, `delivery-task-014` |
| DLV-015 | Release candidate: blocked | `DLV-C02`, `DLV-C03`, `DLV-C06`, `DLV-C08` | `delivery-message-015`, `delivery-task-015` |

Rules used by the producer:

- `blocked` requires explicit source-backed blocked state/reason.
- `overdue` requires non-terminal work with `due_at < generated_at`.
- `due_soon` requires non-terminal work with `generated_at <= due_at <= generated_at + 7 days`.
- `unassigned` requires no assignee; it is never inferred from message content.
- `in_progress` is a task status, not automatically a risk. It may appear in facts but not in an
  overdue/due-soon/blocked bucket without supporting domain rules.
- Every required task/message ID must become a returned `SourceReference`; an otherwise-correct
  summary with missing evidence fails the case.
