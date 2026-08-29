# Delivery Agentic Runtime Runbook

## Enable demo

1. Run migration head, including `20260822_16` and `20260822_17`.
2. Confirm a Product Delivery workspace, active lead/member, linked group and group AI consent.
3. Set `MULTI_AGENT_ENABLED=true` and `PRODUCT_DELIVERY_AGENT_ENABLED=true` only in the demo environment.

## Seed dữ liệu demo thật

Không dùng mock UI cho kiểm thử agent. Sau khi migration đạt `head`, chạy script idempotent sau trong
môi trường `development` (script tự từ chối `APP_ENV=production`):

```powershell
.\.venv\Scripts\python.exe scripts\seed_delivery_demo.py --apply
```

Script không xóa dữ liệu nghiệp vụ. Nó tạo/cập nhật namespace `delivery-demo`: Product Delivery Demo
Workspace, 13 thành viên Delivery, ba group `Apollo Platform`, `Customer Portal`, `Release 34`
(mỗi group 5 người, 8 tin nhắn, 5 task source-bound, 3 milestone) và group kiểm soát
`QA Internal — not linked`. UI/LLM snapshot nhận group directory, people projection, chat evidence và task
blocked/overdue/due-soon, milestone và message evidence..

| Tài khoản | Mật khẩu demo | Mục đích |
|---|---|---|
| `delivery-demo-admin@example.com` | `Demo123!` | Cấu hình Admin |
| `delivery-demo-lead@example.com` | `Demo123!` | Tổng quan và chọn từng group |
| `delivery-demo-member@example.com` | `Demo123!` | Chỉ scope Apollo/My Work |
| `delivery-demo-outsider@example.com` | `Demo123!` | Negative authorization |

Nếu dùng PostgreSQL pooler giới hạn connection, cấu hình demo nên giữ `DB_POOL_SIZE=2`,
`DB_MAX_OVERFLOW=0`, `AGENT_CHECKPOINTER_POOL_SIZE=2`; scheduler job store chỉ mở một connection.
4. Verify lead overview, lead selected-group, member My Work, outsider denial and consent revoke.

## Rollback / kill switch

Set either `PRODUCT_DELIVERY_AGENT_ENABLED=false` or `MULTI_AGENT_ENABLED=false`, then restart/reload settings. New Delivery requests stop before LLM/tool execution; Personal Agent remains unaffected. Do not delete task/milestone data as a rollback step.

## Safety signals

- `DELIVERY_AGENT_RUNTIME_FAILED`: LLM graph failed; validated brief remains available as partial.
- `DENY_CONSENT_CHANGED`: consent/source changed during a turn; retry only after the user has current access.
- Missing source citation: graph replaces the LLM prose with a safe refusal.

## Operational limits

The graph has one server-bound snapshot tool and recursion limit eight. It has no action tool. Reminder/meeting remains disabled until durable HITL is available.
