# Product Delivery Agent — Implementation Readiness

> Status: **B1–B3 fixture/read-only runtime boundary verified**. Production integration, durable publication and every side effect remain gated by the shared-platform decisions below.
>
> Companion document: [7-day Delivery plan](ROLE_B_PRODUCT_DELIVERY_AGENT_7_DAY_PLAN.md).

## Current baseline, verified

| Capability | State | Evidence |
|---|---|---|
| Product Delivery profile, workspace scope and feature flags | Available, flags default off | `AgentProfile.PRODUCT_DELIVERY`, `context_builder`, profile registry |
| Membership, linked conversation and consent resolution | Available; member scope is intersected with active conversation participation | scope resolver and resource guard revalidate at each tool boundary |
| Common `SourceReference`, `ToolResult`, `ActionProposal`, `WorkspaceBrief` contracts | Available | `src/agents/contracts.py` |
| Delivery profile/schema/pure business rules | Prepared in PR-B1 | `src/agents/profiles/product_delivery.py`, `src/agents/schemas/delivery.py` |
| Scoped Delivery task retrieval | **Blocked** | `Task` has no `agent_workspace_id`; no safe query policy exists |
| Milestone, release target and dependency store | **Blocked** | no durable model/service exists |
| Delivery invocation preparation and read-only executor boundary | Available as an explicit composition contract | `prepare_product_delivery_invocation` → `resolve_prepared_delivery_read_scope` → `ProductDeliveryReadOnlyExecutor`; only explicitly bound Delivery read tools may run, after workspace/resource revalidation |
| Delivery invocation endpoint, brief persistence and durable proposal executor | **Blocked** | shared runtime executor/store/HITL interface is not yet wired |

## Decisions that are now locked for Delivery implementation

1. Canonical profile enum is `product_delivery`; canonical workspace key is `product-delivery`. They are intentionally different fields and must be mapped explicitly, never inferred from a client string.
2. A Delivery fact is only present when it has one or more `SourceReference` records from the target Agent Workspace. A recommendation links to returned source IDs; it is not represented as a fact.
3. All timestamps received or emitted by Delivery include an offset. Domain comparison uses timezone-aware instants; UI may render the organization calendar timezone.
4. A non-terminal item is **overdue** when `due_at < now`, **due soon** when `now <= due_at <= now + 7 days`, and **on track** otherwise. Terminal states are `completed`, `dismissed`, `invalidated`. A blocker is explicit source-backed state, never inferred from sentiment/message counts. Missing assignee or deadline is `unassigned`/`data_gap`, not a guess.
5. Product Delivery must not score people, rank employees, or derive performance from counts, activity, tone or sentiment.
6. `WorkspaceBrief.release_readiness` is prohibited for Delivery; it belongs to Quality only.
7. No Delivery proposal may execute inside an agent/tool. It can only create an immutable preview for the shared executor.

## Required shared-platform decisions before production code

These are ownership items for A. They should be accepted in one small shared-contract PR before B starts PR-B2 integration.

| ID | Required decision/interface | Acceptance criterion |
|---|---|---|
| A-DLV-01 | Add `Task.agent_workspace_id` (nullable for legacy data) plus an index bound to organization/workspace/status. Backfill only when source conversation is linked to exactly one active Agent Workspace. | A scoped query receives organization ID, target Agent Workspace ID and resolved resource IDs; it never falls back to a company-wide task scan. Negative cross-workspace test passes. |
| A-DLV-02 | Choose a durable source for milestones/release targets/dependencies. Prefer a typed work-item/milestone model; until it exists, the tool returns `PARTIAL` with `MILESTONE_SOURCE_NOT_AVAILABLE`. | There is no model-generated milestone from unstructured chat alone; every record has provenance and freshness. |
| A-DLV-03 | Publish one invocation interface that performs router → context builder → profile allowlist before model/tools. | **Partial:** the server-side composition now prepares context, resolves read scope and executes only explicit read bindings. A public API/model adapter and audit of early denials are still required. |
| A-DLV-04 | Persist `WorkspaceBrief` with producer, source IDs, consent hash, generated/expiry timestamps and trace/audit lineage. | Consumer D can read a typed brief after restart/multi-worker deployment. |
| A-DLV-05 | Persist `ActionProposal` and confirm it transactionally. | Confirm re-resolves membership/consent/resource scope, validates all attendees in organization/workspace, checks calendar conflict, hashes edited payload, expires proposals and enforces idempotency across workers. |
| A-DLV-06 | Resolve member group scope as linked/AI-enabled groups intersected with the user's active conversation participation. | **Implemented:** member scope is the active-participant intersection; participant-mismatch integration test returns an empty allowlist before retrieval. |
| A-DLV-07 | Provide a server-filtered group capability/selected-group resolver. | **Partial:** `resolve_prepared_delivery_read_scope` treats a selected ID as untrusted and revalidates it through the resource guard before issuing `GROUP` scope; member selection is rejected. A capability-list/API and DB-backed selector evidence remain required. |
| A-DLV-08 | Persist a typed DeliveryDecision or equivalent approved store. | A member sees only decisions where they are audience/assignee; confirmation, source and audit are verifiable. |
| A-DLV-09 | Bind task reads to Agent Workspace/source conversation and establish assignee semantics. | A single-group request cannot scan unrelated or legacy-unproven tasks. |

`A-DLV-01` is a security gate: until it lands, B may use only synthetic fixtures or records whose linked source conversation appears in the trusted `allowed_resource_ids`. It must not query every task in the Company Root.

## PR cut and ownership

| PR | May start now | Must wait for | Exit gate |
|---|---|---|---|
| B1 — schema/profile/rules | Yes | — | strict schema + pure-rule tests green |
| B2 — scoped reads | interface/fixture tests only | A-DLV-01, A-DLV-02, A-DLV-06, A-DLV-07 and A-DLV-09 for real records | guard is called at every read; no fallback query |
| B3 — runtime/brief candidate | preparation, selected-scope and explicit read-only executor contract | A-DLV-03 public API/model adapter and A-DLV-04 to publish | 15 golden structural cases and source coverage = 100% |
| B4 — UI/HITL | fixture UI only | A-DLV-03 and A-DLV-05 for real approvals | outsider/revoke/replay/refresh checks pass |
| B5–B7 — evaluation/release | test assets and evaluation mapping | all applicable gates | live E2E evidence, flag/rollback proof |

## Definition of a production-ready Delivery action

An approve button is not sufficient. Before a reminder or meeting can be enabled, the confirm path must: reload the persisted proposal; reject expiry, replay and changed payload; re-run actor membership and AI-consent scope; validate each attendee against the same organization and allowed workspace; check calendar conflict; execute exactly once; and write an audit event without raw conversation content. Any missing condition keeps the action feature-flagged off.

## Day-0 checklist

- [ ] A accepts A-DLV-01 through A-DLV-09 and assigns a target PR/implementer.
- [ ] Create a synthetic Product Delivery Agent Workspace with a lead, a member, an outsider and a QA workspace for denial tests.
- [ ] Link two consented group conversations; keep one private/direct and one unconsented conversation as negative fixtures.
- [ ] Pin the calendar timezone for the test organization and record it in the fixture manifest.
- [ ] Keep `MULTI_AGENT_ENABLED=false` and `PRODUCT_DELIVERY_AGENT_ENABLED=false` until B6 gates are green.
- [ ] Add one issue per blocked decision; do not hide it inside B's feature PR.

## Commands for the first implementation checkpoint

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m pytest tests\test_agents\test_product_delivery.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_agent_workspaces.py -q
.\.venv\Scripts\python.exe scripts\generate_multi_agent_dataset.py --check
.\.venv\Scripts\python.exe scripts\validate_multi_agent_dataset.py
git diff --check
```

The `generate_multi_agent_dataset.py` and `validate_multi_agent_dataset.py` commands are availability checks: if either script is absent, record it as a shared evaluator dependency instead of silently treating the gate as green.
