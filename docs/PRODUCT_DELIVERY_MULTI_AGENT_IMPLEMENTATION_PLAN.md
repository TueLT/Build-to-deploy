# Product Delivery Workspace Multi-Agent Implementation Plan

> Status: Canonical plan; production-MVP implementation is tracked in `PRODUCT_DELIVERY_MULTI_AGENT_IMPLEMENTATION_STATUS.md`  
> Agent-first amendment: `PRODUCT_DELIVERY_MULTI_AGENT_AGENT_FIRST_PLAN_V2.md` supersedes chatbot direct-tool routing and defines Task Intelligence plus Supervisor-mediated result chaining.  
> Adaptive orchestration amendment: `PRODUCT_DELIVERY_ADAPTIVE_ORCHESTRATION_PLAN_V3.md` supersedes mandatory specialist execution for conversational turns and removes implicit Delivery Health fallback.  
> Scope: Intra-workspace multi-agent orchestration for Product Delivery  
> Primary users: Product Delivery Lead and Product Delivery Member  
> Last reviewed: 2026-08-26  
> Principle: one workspace-facing Supervisor, bounded domain specialists, deterministic tools, human authority

## 1. Executive decision

Product Delivery Workspace will expose exactly one conversational entry point to its Lead and Members:

```text
Product Delivery Workspace Agent
```

That workspace-facing identity is backed by a hybrid orchestration path. A deterministic Request Gateway resolves identity, workspace, policy and obvious fast-path intents before any model is called. Complex requests are handed to the Supervisor Agent, which understands the business goal, selects the minimum set of specialists, tracks their runs, validates their structured results, and presents one coherent answer or action proposal.

Specialist agents are internal implementation components. They are not shown as separate sidebar entries, do not receive direct client calls, and do not own workspace membership or authorization decisions.

The target architecture is:

```text
Delivery Lead / Member
          |
          v
Request Gateway (code)
  - identity/workspace/policy
  - deterministic fast-path router
          |
          +-- simple request -> Tool Gateway -> deterministic response
          |
          `-- complex request
                   |
                   v
Product Delivery Workspace Supervisor Agent
          |
          +-- Delivery Task Intelligence Agent
          +-- Planning & Forecast Agent
          +-- Risk & Dependency Agent
          +-- Evidence & Knowledge Agent
          +-- Capacity & Flow Agent          [phase 2, data-gated]
          |
          v
Tool Gateway -> deterministic scoped tools -> source-of-truth records
          |
          v
Validated AgentResult -> deterministic rule engine -> response/proposal/HITL
```

This plan does not create one LLM agent for every repository function. It creates an agent only when a capability requires independent multi-step reasoning, bounded context, an output contract, policy, lifecycle, and evaluation suite. Simple reads remain tools.

## 2. Business outcome and pain points

The system is not considered successful merely because several agents run. It must reduce measurable Delivery coordination cost.

### 2.1 Target pain points

| Pain point | Current operational cost | Target capability |
|---|---|---|
| Members do not know which task to prioritize | Manual search across task lists and group chat | Prioritized, source-backed personal work view |
| Leads spend time preparing status reports | Repeated collection from tasks, milestones, dependencies and chat | On-demand Delivery Health workflow |
| Blockers are escalated late | Blocker, dependency and owner information live in different sources | Blocker Resolution workflow |
| Milestone risk is detected after slippage | No consistent task-to-milestone-to-dependency assessment | Planning and release forecast |
| Decisions are lost in chat | Decision evidence is not consistently captured as a record | Evidence & Knowledge verification plus Supervisor recommendation/HITL |
| Scope changes do not invalidate old assessments | Reports can remain apparently current after release changes | Versioned assessment and stale-result invalidation |
| Agent recommendations cannot safely change records | LLM output is not an authorization mechanism | Durable Action Proposal and Lead approval |
| Lead and Member need different views | Broad summaries can leak data or authority | Role-aware child capability envelopes |

### 2.2 Pilot success metrics

The pilot must record a baseline before rollout. Initial target thresholds are:

- Reduce Lead status-preparation time by at least 30%.
- Reduce median blocker age and time-to-owner assignment.
- Ensure 100% of high-impact factual claims contain valid source references.
- Produce zero cross-workspace or out-of-scope disclosures.
- Produce zero duplicate side effects.
- Preserve service availability when one specialist run fails.
- Achieve at least 70% Lead acceptance or usefulness rating for generated action proposals.
- Keep simple read requests on a low-latency fast path without unnecessary specialist LLM calls.

### 2.3 Stop conditions

Do not expand the specialist set when:

- users still need to re-enter most source data;
- outputs are mostly overridden due to missing or stale facts;
- a dashboard or deterministic query solves the workflow with less cost;
- the workflow occurs too rarely to justify orchestration;
- latency and model cost exceed the measured coordination saving;
- the underlying source-of-truth model is not ready.

## 3. Current-state assessment

### 3.1 Existing strengths

The repository already contains:

- a Product Delivery profile and explicit tool allowlist;
- server-resolved Workspace scope and Lead/Member resource boundaries;
- resource revalidation at tool boundaries;
- strict Delivery domain schemas and deterministic health rules;
- source-backed task, milestone, dependency, decision, release and message reads;
- a dedicated Delivery runtime graph with input/output guardrails;
- synthesis fallback and independent high-risk verification;
- a durable action-proposal pipeline for dependency and decision transitions;
- runtime target pinning, signed snapshots, timeout and local bulkheads;
- a durable `ReleaseCandidate` handoff foundation for later Delivery-to-QA integration.

### 3.2 Current limitations

The current Delivery graph is a one-turn synthesis graph around one prebuilt snapshot. It does not yet:

- create a parent workflow and child specialist runs;
- decompose an intent into domain tasks;
- select a minimum specialist set;
- run independent specialists in parallel;
- persist specialist results and lineage;
- wait, resume, cancel or retry a workflow;
- resolve conflicting specialist results;
- distinguish direct-tool fast paths from multi-agent workflows;
- expose workflow progress in the UI.

### 3.3 Important data gaps

- `get_delivery_flow_metrics` currently returns `WORKFLOW_HISTORY_NOT_CAPTURED`; it cannot support production cycle-time or throughput reasoning yet.
- `get_delivery_capacity_summary` counts work states. It does not model availability, allocation, skills, leave or per-person capacity.
- Message search is bounded evidence retrieval, not an official decision source.
- Delivery action proposals currently cover dependency and decision status transitions, not task assignment, due-date or milestone changes.

These gaps determine which specialist agents can be enabled now and which must remain data-gated.

## 4. Agent-versus-tool decision rule

### 4.1 Keep a capability as a deterministic tool when

- it performs one bounded query or calculation;
- it does not need a planning loop;
- the correct behavior can be expressed fully in code;
- it should return the same result for the same authorized input;
- it has no independent conversational state;
- adding an LLM would only restate the returned rows.

Examples: list scoped tasks, fetch milestones, calculate current WIP, evaluate portfolio health.

### 4.2 Create a specialist agent when

At least four of these conditions are true:

1. The capability owns an independent business goal.
2. It may need multiple tool calls or conditional steps.
3. It combines multiple sources in one domain.
4. It requires a small specialist prompt and context.
5. It produces a versioned output contract consumed by the Supervisor or another workflow step.
6. It needs its own guardrail, budget, timeout and retry policy.
7. It can report partial success and domain-specific data gaps.
8. It needs an independent evaluation dataset.
9. It may propose, but never directly execute, a business action.
10. Its failure can be isolated without failing unrelated specialists.

### 4.3 Promotion rule for a one-tool agent

A tool may later become the core of a specialist agent when its operation evolves into a workflow. For example, a single message-search tool remains a tool today. It may become an Evidence Retrieval Agent only when it must plan multiple searches, select sources, rerank, deduplicate, redact, validate freshness and assemble a reusable evidence package.

## 5. Exact selection: which current tools belong to which agent

The existing Product Delivery registry contains 12 tools. None should become a one-to-one standalone agent in the first implementation. They are assigned as follows.

| Existing tool | Classification | Owning component | Decision |
|---|---|---|---|
| `get_delivery_tasks` | Scoped data read | Delivery Task Intelligence Agent | Keep as deterministic tool; do not create `GetTasksAgent` |
| `search_delivery_messages` | Bounded evidence retrieval | Evidence & Knowledge Agent | Keep as tool initially; candidate for later Retrieval Agent promotion |
| `get_delivery_milestones` | Scoped data read | Planning & Forecast Agent | Keep as deterministic tool |
| `get_delivery_people` | Minimal identity projection | Capacity & Flow Agent / proposal validator | Keep as tool; never let it become a people-profile agent |
| `get_delivery_dependencies` | Scoped domain read | Risk & Dependency Agent | Keep as deterministic tool |
| `get_delivery_risks` | Deterministic domain calculation | Risk & Dependency Agent | Keep as rule/tool; LLM may explain but cannot change severity |
| `get_delivery_decisions` | Scoped domain read | Evidence & Knowledge Agent | Keep as deterministic tool; the specialist verifies decision evidence but does not decide |
| `get_delivery_release_status` | Scoped domain read | Planning & Forecast Agent | Keep as deterministic tool |
| `get_delivery_capacity_summary` | Deterministic aggregate | Capacity & Flow Agent | Keep as tool; insufficient alone for capacity recommendations |
| `get_delivery_flow_metrics` | Deterministic aggregate with current data gap | Capacity & Flow Agent | Keep disabled for claims requiring history until event history exists |
| `get_delivery_portfolio_health` | Authoritative rule result | Supervisor decision layer | Never turn into an LLM agent; this is the final deterministic health authority |
| `build_delivery_brief` | Deterministic output builder | Supervisor response/publication layer | Never turn into an agent; it packages validated results |

### 5.1 Specialist agents selected for phase 1

The first production slice will create four internal specialists:

1. **Delivery Task Intelligence Agent** — selected now; owns exact task, My Work and authorized group/workspace task aggregation.
2. **Risk & Dependency Agent** — selected now.
3. **Planning & Forecast Agent** — selected now for milestone/release planning, with forecasting features gated until source fields exist.
4. **Evidence & Knowledge Agent** — selected now as a bounded retrieval, provenance and conflict-verification specialist. It does not own business decisions.

### 5.2 Specialist agent deferred to phase 2

5. **Capacity & Flow Agent** — architecture and contracts may be created, but production recommendations remain disabled until workflow history and capacity facts exist.

### 5.3 Agents explicitly not created

- `GetTasksAgent`
- `GetMilestonesAgent`
- `GetPeopleAgent`
- `GetRisksAgent`
- `PortfolioHealthAgent`
- `DeliveryBriefAgent`
- `DecisionAgent`
- an unrestricted `SQLAgent`
- an agent with company-wide people search
- an autonomous notification or assignment agent

## 6. Agent responsibilities and tool ownership

### 6.0 Deterministic Request Gateway and Tool Gateway

The workspace-facing UI remains one Product Delivery Workspace Agent, but the first backend hop is code, not an LLM.

The Request Gateway owns:

- JWT identity and active Company/Workspace resolution;
- Agent Workspace membership and Lead/Member role resolution;
- request schema validation, rate limit and input size limit;
- deterministic recognition of exact-ID/simple-read intents;
- feature-flag, policy and purpose checks;
- selection of `DIRECT_TOOL` or `SUPERVISOR_REASONING` execution mode;
- creation of the initial trace and authorization snapshot.

The Tool Gateway owns:

- resolving actor and workspace again at execution time;
- binding every call to the server-resolved resource scope;
- checking the specialist's tool allowlist and purpose;
- enforcing timeout, row/page limits and data classification;
- source validation, redaction, audit and usage attribution;
- rejecting any model-requested ID outside the capability envelope.

`allowed_resource_ids` and similar fields reduce context and constrain a child task, but they are not trusted merely because they appear in a prompt or model-visible payload. The backend capability and Tool Gateway are the security boundary.

### 6.1 Product Delivery Workspace Supervisor

**User-facing role**

- Receive complex Product Delivery requests after deterministic gateway routing.
- Preserve one coherent workspace identity in the UI.
- Classify the request using deterministic routing rules where possible.
- Select direct-tool fast path, one specialist, or a multi-specialist workflow.
- Create workflow and child-run records.
- Delegate only server-authorized capability envelopes.
- Validate every `SpecialistResult`.
- Apply deterministic business rules.
- Request evidence or human input when data is incomplete.
- Create action proposals; never execute a write itself.
- Return one response with facts, inferences, sources, freshness and data gaps.

**Supervisor capabilities**

```text
run_direct_read
delegate_work_assessment
delegate_planning_assessment
delegate_risk_assessment
delegate_evidence_knowledge_assessment
delegate_capacity_assessment       [feature-gated]
wait_for_specialist_results
validate_specialist_results
compute_delivery_health
create_action_proposal
request_human_approval
build_delivery_response
```

The Supervisor does not receive direct database credentials and does not expose internal specialist selection fields to the client. It can recommend and formulate trade-offs, but a deterministic policy and an authorized human remain responsible for business decisions and mutations.

### 6.2 Delivery Task Intelligence Agent

**Business goal:** determine what work exists, its health, priority and ownership inside the authorized Delivery scope.

**Owned existing tools**

- `get_delivery_tasks`

**Allowed supporting reads**

- `get_delivery_milestones` only through an authorized task envelope when task-to-milestone context is required.
- Evidence packages from Evidence & Knowledge Agent; no unrestricted raw message browsing.

**New deterministic tools required**

- `get_delivery_task_detail`
- `get_delivery_tasks_by_milestone`
- `get_delivery_tasks_by_release`
- `get_delivery_task_history`
- `get_delivery_blocker_age`
- `get_delivery_stale_tasks`
- `get_delivery_unowned_tasks`
- `get_delivery_work_completion_summary`

**Output contract:** `WorkAssessment`.

```text
scope_subject
total_items
completed_items
in_progress_items
blocked_items
overdue_items
due_soon_items
stale_items
unowned_items
priority_order
facts
inferences
source_references
data_gaps
generated_at
expires_at
```

The agent cannot create, assign, complete or reschedule a task. It may emit a proposal candidate.

### 6.3 Risk & Dependency Agent

**Business goal:** identify delivery threats, dependency impact, critical paths and mitigation gaps.

**Owned existing tools**

- `get_delivery_dependencies`
- `get_delivery_risks`

**New deterministic tools required**

- `get_delivery_dependency_graph`
- `get_delivery_critical_path`
- `get_delivery_dependency_sla_breaches`
- `get_delivery_risk_history`
- `get_delivery_risk_owner_coverage`
- `evaluate_delivery_mitigation_status`
- `calculate_delivery_blast_radius`

**Output contract:** `RiskDependencyAssessment`.

```text
overall_risk
critical_risks
critical_path
blocked_dependencies
overdue_dependencies
affected_tasks
affected_milestones
unowned_risks
mitigation_gaps
source_references
data_gaps
```

Risk severity and portfolio health remain deterministic. The agent may prioritize and explain but cannot lower a severity or mark a dependency resolved.

### 6.4 Planning & Forecast Agent

**Business goal:** assess milestone status, scope consistency, schedule variance and Delivery readiness for a release.

**Owned existing tools**

- `get_delivery_milestones`
- `get_delivery_release_status`

**New deterministic tools required**

- `get_delivery_milestone_baseline`
- `get_delivery_scope_snapshot`
- `get_delivery_scope_change_diff`
- `get_delivery_schedule_variance`
- `get_delivery_release_work_items`
- `calculate_delivery_forecast`
- `simulate_delivery_date_change`

`calculate_delivery_forecast` must be feature-gated until historical completion data and estimation semantics are defined. `simulate_delivery_date_change` is read-only simulation.

**Output contract:** `PlanningForecastAssessment`.

```text
milestone_status
release_status
scope_version
scope_changes
schedule_variance
forecast_date
forecast_confidence
pending_constraints
affected_milestones
source_references
data_gaps
```

The agent cannot change scope, baseline, milestone date or release state.

### 6.5 Evidence & Knowledge Agent

**Business goal:** retrieve and verify whether an important claim or recorded decision has authoritative, current and non-conflicting evidence, then return a bounded knowledge package to the Supervisor.

**Owned existing tools**

- `get_delivery_decisions`
- `search_delivery_messages`

**New deterministic tools required**

- `get_delivery_decision_history`
- `get_delivery_decision_evidence`
- `get_delivery_unresolved_decisions`
- `validate_delivery_source_freshness`
- `detect_delivery_fact_conflicts`
- `build_delivery_evidence_package`

**Output contract:** `EvidenceKnowledgeAssessment`.

```text
confirmed_decisions
pending_decisions
unrecorded_decision_candidates
conflicting_facts
stale_sources
missing_evidence
source_references
data_gaps
```

Chat text is evidence, not an official decision. Only an approved action may create or finalize a decision record.

This specialist does not compare business alternatives, choose an outcome, accept risk or approve a recommendation. The Supervisor may combine specialist results into a recommendation; the appropriate Lead approves or rejects it.

### 6.6 Capacity & Flow Agent — data-gated

**Business goal:** assess workload distribution, WIP, bottlenecks, flow trends and feasible reassignment options.

**Owned existing tools**

- `get_delivery_people`
- `get_delivery_capacity_summary`
- `get_delivery_flow_metrics`

**Required source model before activation**

- immutable work-status transition history;
- assignment history;
- per-person allocation or availability window;
- team WIP policy;
- estimation semantics, if forecasts use effort;
- absence/leave source when business policy allows it;
- purpose-limited skill tags if assignment recommendations use skills.

**New tools after the source model exists**

- `get_delivery_workload_distribution`
- `get_delivery_capacity_forecast`
- `get_delivery_wip_limit_breaches`
- `get_delivery_cycle_time_trend`
- `get_delivery_throughput_trend`
- `find_delivery_assignment_candidates`

**Output contract:** `CapacityFlowAssessment`.

No recommendation may infer performance or competence from chat volume, response speed or private data.

## 7. Routing and execution policy

### 7.1 Routing classes

| Request class | Example | Execution |
|---|---|---|
| Direct read | “Cho tôi xem task T-123” | Request Gateway calls Tool Gateway directly; zero Supervisor/specialist LLM calls |
| Single-domain analysis | “Task nào của tôi cần ưu tiên?” | One Delivery Task Intelligence child run |
| Multi-domain analysis | “Vì sao milestone M4 đang trễ?” | Work + Planning + Risk, then synthesis |
| Decision workflow | “Nên xử lý blocker OAuth thế nào?” | Work -> Risk -> Planning, optional proposal and HITL |
| Unsupported/out-of-scope | HR, Finance, another workspace | Deny or route outside Delivery only after Core authorization |

### 7.2 Minimum-agent rule

The Supervisor must select the smallest sufficient plan. Calling all specialists for every request is prohibited.

Routing is two-stage:

1. **Code router:** handles exact identifiers, known read intents, invalid scope, feature flags and policy-denied requests. Its decisions are deterministic and auditable.
2. **Supervisor planner:** handles ambiguous or multi-domain business goals after the code router has authorized `SUPERVISOR_REASONING`. An LLM may propose a specialist plan, but code validates the plan against the intent matrix, maximum child count, dependency rules and role capability.

An LLM never decides identity, membership, permission, feature availability or the final executable tool capability.

### 7.3 Routing table

| Intent | Primary | Additional specialist when needed |
|---|---|---|
| `TASK_LOOKUP` | Direct tool | None |
| `MY_WORK_PRIORITY` | Work | Risk if blocked dependency affects priority |
| `WORK_HEALTH` | Work | Planning for milestone/release context |
| `MILESTONE_HEALTH` | Planning | Work + Risk |
| `BLOCKER_ANALYSIS` | Work | Risk, then Planning; Capacity only when enabled |
| `DEPENDENCY_ANALYSIS` | Risk | Work + Planning |
| `RELEASE_DELIVERY_READINESS` | Planning | Work + Risk + Evidence |
| `DECISION_STATUS` | Evidence | Planning/Risk when recorded-decision impact is requested |
| `DELIVERY_HEALTH` | Work + Planning + Risk | Evidence for provenance/conflict validation |
| `CAPACITY_ANALYSIS` | Capacity | Work; only after feature gate |

### 7.4 Context minimization

Each delegation contains only:

```text
workflow_id
parent_run_id
specialist_task_id
goal
subject identifiers
time window
actor role
agent_workspace_id
allowed resource IDs
allowed domain record IDs
consent/authorization scope hash
deadline
tool and token budget
```

It does not contain the complete user conversation, another specialist's scratchpad, a system prompt, secrets or raw workspace memory. When a later specialist needs facts produced earlier, the Orchestrator builds a new minimal context from the validated structured result; it never forwards the earlier agent's transcript or chain of thought.

## 8. User and role behavior

### 8.1 Shared interaction model

Lead and Member use the same Workspace Agent entry point. The server-derived role changes scope and permitted proposals, not the agent identity shown in the UI.

### 8.2 Member capabilities

- Query and analyze work inside the Member's resolved resource intersection.
- Receive a personal/member Delivery view.
- Report a blocker or provide evidence in allowed groups.
- Create proposals for allowed targets.
- See the status of their own workflow and proposals.

Members cannot:

- request a full-workspace overview;
- inspect groups they do not participate in;
- approve workspace-level actions;
- accept risk for the workspace;
- modify milestones, scope or release state;
- receive hidden capacity or private people data.

### 8.3 Lead capabilities

- Request workspace-wide analysis across all AI-enabled Delivery sources bound to the Agent Workspace.
- Run Delivery Health, Blocker Resolution, Planning and Release Delivery Readiness workflows.
- Review all workspace action proposals.
- Approve valid dependency/decision transitions and later approved action types.
- Submit a ReleaseCandidate after deterministic Delivery readiness checks.

Lead status does not grant QA, Executive, private chat, personal memory or unrestricted company data access.

## 9. Detailed workflows

### 9.1 WF-DLV-01 — Member Work Priority

**User goal:** “Các task nào của tôi cần ưu tiên hôm nay?”

**Preconditions**

- Active Company and Product Delivery Agent Workspace membership.
- Member view resolved from current group participation.
- Task records are bound to the authorized sources.

**Execution**

```text
authorize
-> resolve member task scope
-> Delivery Task Intelligence Agent
   -> list active tasks
   -> classify blocked/overdue/due-soon/unowned
   -> resolve dependency flags if needed
   -> produce WorkAssessment
-> deterministic priority ordering
-> Supervisor response
```

**Priority policy**

1. Explicit critical blocker assigned to the actor.
2. Overdue non-terminal item.
3. Due-soon item on an affected milestone or dependency path.
4. In-progress item.
5. Pending item.

The LLM may explain the order but cannot invent priority fields or deadlines.

**Result states:** `COMPLETED`, `PARTIAL_DATA`, `DENIED`, `FAILED_WORK_READ`.

### 9.2 WF-DLV-02 — Daily Delivery Health

**Primary user:** Lead.

```text
authorize workspace view
-> create parent workflow
-> parallel:
   - WorkAssessment
   - PlanningForecastAssessment
   - RiskDependencyAssessment
-> EvidenceKnowledgeAssessment for critical/pending claims
-> validate provenance and freshness
-> deterministic get_delivery_portfolio_health
-> build Delivery Brief
-> Supervisor synthesis
```

**Output**

- authoritative portfolio health;
- blocked/overdue work;
- milestone/release status;
- critical dependencies and risks;
- decisions needed;
- data gaps and stale sources;
- next actions with owners only when sources identify them.

**Partial failure policy**

- Work failure: no portfolio conclusion; return insufficient data.
- Risk failure: preserve work/planning facts, mark risk assessment unavailable.
- Decision evidence failure: do not treat chat evidence as official.
- LLM synthesis failure: return deterministic brief.

### 9.3 WF-DLV-03 — Blocker Resolution

**User goal:** understand and resolve a specific blocker.

```text
Work Agent: confirm task/blocker/age/owner
-> Risk Agent: dependency chain, blast radius, risk severity
-> Planning Agent: milestone/release impact
-> Capacity Agent: assignment candidates [only after activation]
-> Supervisor: mitigation alternatives
-> optional ActionProposal
-> Lead approval
-> reauthorization and optimistic-concurrency execution
```

**Possible proposals**

- dependency status transition;
- decision record transition;
- task owner or due-date change after those action types are implemented;
- escalation notification after communication policy is implemented.

The workflow must never silently reassign a task or change a date.

### 9.4 WF-DLV-04 — Milestone Health

```text
Planning Agent: baseline, current status, scope diff
|| Work Agent: completion and blocker state
|| Risk Agent: critical path and external dependency
-> deterministic schedule/health calculation
-> Evidence Agent verifies pending constraints
-> Supervisor response
```

If historical data is insufficient, return current deterministic state and an explicit forecast data gap rather than an estimated date from the LLM.

### 9.5 WF-DLV-05 — Change Impact Assessment

**Triggers**

- task added to or removed from a release;
- milestone date/baseline changed;
- dependency becomes blocked/resolved;
- release build or version changes;
- a relevant decision is superseded.

**Execution**

```text
load previous version + current version
-> Planning Agent computes scope/schedule diff
-> Work Agent identifies affected items
-> Risk Agent recalculates dependency/risk impact
-> Capacity Agent calculates workload impact [when enabled]
-> invalidate stale prior assessments
-> Supervisor returns ChangeImpactAssessment
-> Lead approves any mutation proposal
```

### 9.6 WF-DLV-06 — Delivery Release Readiness

**Business goal:** decide whether the Delivery side is ready to submit a ReleaseCandidate to QA.

```text
Work Agent: completion/blocker assessment
|| Planning Agent: release identity, scope and milestone consistency
|| Risk Agent: unresolved critical risks/dependencies
|| Evidence Agent: pending/stale recorded decisions and evidence
-> deterministic Delivery readiness policy
-> Lead reviews source-backed result
-> create/submit ReleaseCandidate through HITL-authorized command
```

This workflow produces Delivery readiness only. It cannot declare QA readiness or final production approval.

## 10. Workflow and agent contracts

### 10.1 `DeliveryWorkflow`

```text
id
workflow_type
organization_workspace_id
agent_workspace_id
actor_user_id
actor_role_snapshot
subject_type
subject_id
subject_version
status
authorization_scope_hash
deadline_at
result_json
created_at
updated_at
completed_at
```

### 10.2 `SpecialistTask`

```text
id
workflow_id
parent_run_id
target_specialist
task_type
goal
subject_refs
allowed_resource_ids
authorization_scope_hash
input_schema_version
input_payload_hash
idempotency_key
deadline_at
tool_budget
token_budget
status
attempt
```

### 10.3 `SpecialistResult`

```text
id
workflow_id
specialist_task_id
specialist_profile
result_type
schema_version
status = SUCCESS | PARTIAL | ERROR
facts
inferences
recommendations
source_references
data_gaps
input_payload_hash
generated_at
expires_at
```

### 10.4 Result invariants

- Every fact ID must originate from an authorized tool result.
- Every high-impact fact must have a source.
- Inference and recommendation fields must be separate from facts.
- Results cannot contain a wider resource set than the delegated envelope.
- Expired results cannot contribute to a current health decision.
- A changed subject version invalidates previous results.
- Specialist output cannot contain action execution fields.

### 10.5 Agent Runtime Contract

Every Supervisor-to-specialist invocation must use a versioned runtime envelope. The Supervisor never invokes an arbitrary prompt or forwards its full conversation.

**Trusted invocation envelope**

```text
contract_version
trace_id
workflow_id
parent_run_id
child_run_id
organization_workspace_id
agent_workspace_id
actor_id
actor_role_snapshot
target_specialist
task_type
goal
subject_refs + subject_version
authorization_capability_ref
authorization_scope_hash
purpose
context_pack
prompt_version
model_policy
tool_allowlist_version
tool_budget
token_budget
max_steps
deadline_at
idempotency_key
issued_at
expires_at
request_signature
```

`context_pack` contains minimal structured facts and evidence references. Model-visible allowed IDs are hints for context minimization, not the security authority. `authorization_capability_ref` resolves server-side to the current capability and is revalidated by the Tool Gateway.

**Runtime validation order**

1. Verify service signature and contract version.
2. Verify the runtime is registered for the target specialist/workspace/profile.
3. Verify request expiry, deadline and idempotency.
4. Resolve the server-side authorization capability.
5. Verify subject version and current source bindings.
6. Load the specialist's prompt/model/tool policy from registries.
7. Execute within max steps, tool, token and time budgets.
8. Validate and sign the structured result.
9. Persist sanitized usage, status and lineage metadata.

**Runtime response envelope**

```text
contract_version
trace_id
workflow_id
parent_run_id
child_run_id
specialist
status
result_type
result_schema_version
result_payload
source_references
data_gaps
input_hash
result_hash
prompt_version
model_id
tool_allowlist_version
tool_calls_summary
usage
started_at
completed_at
retryability
error_code
response_signature
```

The response never contains chain of thought, system prompts, credentials or raw checkpoint state.

### 10.6 Agent-to-agent communication protocol

Specialists do not call each other directly in the initial architecture.

```text
Agent A
-> SpecialistResult
-> Orchestrator validation
-> Context Builder
-> minimal ContextPack
-> Agent B
```

The Context Builder may select validated facts, IDs and evidence references required by the next task. It cannot convert an inference into a fact or widen the original actor capability.

Direct peer-to-peer communication is prohibited until a separately reviewed use case proves it is required. This prevents hidden loops, unclear ownership and untraceable scope propagation.

### 10.7 Timeout, retry and loop policy

| Failure class | Retry | Required behavior |
|---|---:|---|
| Invalid authorization/scope | No | Deny and audit |
| Invalid contract/schema | At most one repair attempt | Then fail child run |
| LLM timeout/transient provider error | Bounded retry with backoff | Preserve deadline and budget |
| Tool timeout/transient source error | Bounded retry when tool is idempotent | Otherwise return partial/error |
| Stale subject/source version | No blind retry | Rebuild context and create a new child attempt |
| Deterministic policy rejection | No | Preserve authoritative rejection |
| Missing evidence | No automatic reasoning loop | Enter `WAITING_EVIDENCE` or return data gap |

Limits:

- maximum specialist child count per workflow;
- maximum fan-out depth of one in the initial release;
- no recursive specialist delegation;
- maximum two evidence/reassessment cycles;
- no retry beyond workflow deadline or token/cost budget;
- cancellation propagates to every pending child run.

## 11. Durable state model

Additive persistence target:

```text
delivery_agent_workflows
delivery_agent_runs
delivery_specialist_tasks
delivery_specialist_results
delivery_workflow_events
delivery_workflow_approvals
delivery_event_inbox
```

Shared generic `agent_*` tables may be used instead only if their contracts remain profile-safe and no cross-profile state is reused.

### 11.1 Workflow states

```text
CREATED
AUTHORIZING
PLANNING
DISPATCHING
WAITING_SPECIALISTS
VALIDATING_RESULTS
WAITING_EVIDENCE
DECISION_COMPUTED
WAITING_APPROVAL
COMPLETED
PARTIAL
FAILED
CANCELLED
EXPIRED
```

### 11.2 Child-run states

```text
PENDING
RUNNING
RETRY_SCHEDULED
SUCCEEDED
PARTIAL
FAILED
CANCELLED
TIMED_OUT
```

### 11.3 Event examples

```text
delivery.workflow.created
delivery.specialist.requested
delivery.specialist.completed
delivery.specialist.failed
delivery.evidence.requested
delivery.result.invalidated
delivery.approval.requested
delivery.approval.decided
delivery.workflow.completed
```

Outbox provides durable publication; inbox and unique idempotency keys prevent duplicate consumption.

## 12. LangGraph design

### 12.0 Hybrid entry flow

```text
request schema + input guardrail
-> identity/workspace/policy resolution
-> deterministic Request Router
   |-- DENY -> safe response, no model/tool
   |-- DIRECT_TOOL -> Tool Gateway -> deterministic response composer
   `-- SUPERVISOR_REASONING -> Supervisor graph
```

The direct path does not instantiate a Supervisor or specialist model call. The UI may still render the response under the Product Delivery Workspace Agent identity.

### 12.1 Supervisor graph

```text
validate_gateway_context
-> classify_business_goal
-> build_candidate_execution_plan
-> validate_plan_in_code
-> persist_workflow
-> dispatch_specialists
-> wait_results
-> validate_results
-> resolve_conflicts
-> compute_deterministic_state
-> maybe_create_action_proposal
-> maybe_interrupt_for_human
-> synthesize
-> output_guardrail
-> persist_and_complete
```

### 12.2 Specialist graph template

```text
validate_delegation
-> load_minimal_authorized_context
-> plan_domain_reads
-> call_domain_tools
-> evaluate_data_gaps
-> analyze_domain_result
-> validate_output_schema
-> validate_sources
-> return SpecialistResult
```

### 12.3 Persistence rule

LangGraph checkpointing supports execution, but PostgreSQL workflow records are the source of truth for cross-process status, idempotency, resume and audit. A process restart must not lose a workflow or grant stale authorization.

## 13. Memory policy

### 13.1 Supervisor thread memory

May store:

- user intent and clarified subject;
- workflow/result identifiers;
- published summaries;
- approval references.

Must not store an unrestricted copy of all specialist tool outputs.

### 13.2 Specialist working state

- scoped to one child run;
- contains only delegated input and bounded tool results;
- expires with the workflow retention policy;
- not reused as authority in another workflow.

### 13.3 Operational workspace memory

Only validated records may become operational memory:

- confirmed decision;
- approved plan;
- resolved risk;
- published Delivery assessment;
- source lineage.

Free-form LLM memory is never a source of truth for status, owner, deadline, risk or approval.

## 14. Security and authorization

Effective child capability:

```text
active actor
intersection company membership
intersection Delivery Agent Workspace membership
intersection Lead/Member resolved resources
intersection Supervisor task scope
intersection specialist tool allowlist
intersection purpose and consent
intersection current source binding
```

Mandatory controls:

- Server builds all role, profile and allowlist fields.
- Reauthorize before every child dispatch, resume and action execution.
- Child target must match the Product Delivery Workspace and specialist type.
- Tool queries include workspace and allowed-resource predicates before retrieval.
- Prompt injection inside chat/tool data cannot change the plan or policy.
- No raw JWT, OAuth token, system prompt or database credential enters model context.
- No child agent calls unrestricted SQL.
- Output source IDs are validated against the delegated capability.
- Cancellation or membership revocation invalidates pending child work.
- Logs contain metadata and hashes, not unnecessary raw content.

## 15. Human-in-the-loop action model

### 15.1 Existing actions retained

- `delivery_dependency_status`
- `delivery_decision_status`

### 15.2 Proposed actions, added only with domain APIs and tests

- `delivery_task_status`
- `delivery_task_assignment`
- `delivery_task_due_date`
- `delivery_milestone_date`
- `delivery_risk_acceptance`
- `delivery_release_candidate_submit`
- `delivery_workspace_notification`

### 15.3 Approval policy

| Action | Member proposes | Lead proposes | Required approver |
|---|---:|---:|---|
| Update own task status | Yes, when task policy permits | Yes | Actor confirmation or Lead by policy |
| Assign/reassign task | No by default | Yes | Delivery Lead |
| Change task due date | Proposal in own scope | Yes | Delivery Lead |
| Change milestone date | No | Yes | Delivery Lead |
| Resolve dependency | Proposal with evidence | Yes | Delivery Lead |
| Record decision outcome | Proposal | Yes | Delivery Lead |
| Accept delivery risk | No | Yes | Delivery Lead |
| Submit ReleaseCandidate | No | Yes | Delivery Lead |

Every proposal remains bound to payload hash, actor, authorization-scope hash, expiry, target row version and idempotency key.

## 16. API target

### 16.1 Logical agent boundary versus deployment boundary

An agent is defined by its instructions, tool allowlist, context builder, state, output schema, guardrails, model policy, budget and eval suite. It does not require a separate microservice.

Initial deployment:

```text
Product Delivery Runtime
  - Request Router adapter
  - Supervisor graph
  - Work specialist graph
  - Risk specialist graph
  - Planning specialist graph
  - Evidence specialist graph
```

The runtime contract is transport-neutral: an in-process adapter and a remote worker must accept the same signed envelope and return the same result contract. Split a specialist into a separate worker/container only when load, security, scaling or fault evidence justifies the operational cost.

### 16.2 Shared platform capabilities

All Product Delivery logical agents depend on shared, non-LLM platform controls:

```text
Identity and Workspace Resolver
Policy Engine
Request Router
Tool Gateway
Agent and Capability Registry
Prompt Registry
Model Gateway
Context Builder
Workflow Store
Outbox/Inbox
Audit and Trace
Observability
Evaluation Harness
Secrets
Rate Limit and Cost Control
Memory and Retention Policy
```

These controls are not duplicated inside each specialist prompt.

### 16.3 External API

```text
POST /api/v1/workspaces/{workspace_id}/agent-workspaces/{agent_workspace_id}/delivery/chat
GET  /api/v1/workspaces/{workspace_id}/agent-workspaces/{agent_workspace_id}/delivery/workflows/{workflow_id}
POST /api/v1/workspaces/{workspace_id}/agent-workspaces/{agent_workspace_id}/delivery/workflows/{workflow_id}/cancel
POST /api/v1/workspaces/{workspace_id}/agent-workspaces/{agent_workspace_id}/delivery/workflows/{workflow_id}/resume
GET  /api/v1/workspaces/{workspace_id}/agent-workspaces/{agent_workspace_id}/delivery/workflows/{workflow_id}/events
```

The client sends message and optional subject hints only. It cannot set specialist, role, allowed tools or authorized IDs.

### 16.4 Internal runtime surface

```text
POST /internal/v1/delivery-supervisor/runs
POST /internal/v1/delivery-specialists/{specialist}/runs
GET  /internal/v1/runs/{run_id}
POST /internal/v1/runs/{run_id}/cancel
```

The same surface may be implemented by an in-process adapter in phase 1. Separate containers are a later deployment decision based on load and failure evidence, not a requirement for logical multi-agent behavior.

## 17. UI requirements

The user sees one Product Delivery Workspace Agent.

Required states:

- understanding request;
- reading authorized Delivery data;
- analyzing work/planning/risk/evidence;
- waiting for a specialist;
- waiting for evidence;
- waiting for Lead approval;
- completed, partial, failed or cancelled.

The UI must show:

- final business status;
- workflow progress rather than synthetic agent-to-agent chat;
- facts and source links;
- freshness and data gaps;
- action proposal card;
- approval actor and outcome;
- retry/cancel controls when policy permits.

Internal specialist names may be shown as execution labels, but they are not navigable agent workspaces.

## 18. Failure and degradation policy

| Failure | Required behavior |
|---|---|
| One specialist timeout | Retry within budget; otherwise return partial result |
| Work read fails | Do not produce authoritative portfolio health |
| Risk specialist fails | Preserve other facts and mark risk analysis unavailable |
| LLM unavailable | Return deterministic tool/rule result where possible |
| Invalid specialist schema | Reject result; one bounded retry; then partial/failure |
| Stale subject version | Invalidate results and restart affected child tasks |
| Membership revoked while waiting | Cancel/deny resume |
| Duplicate event | Inbox deduplicates; no duplicate run/action |
| Delivery runtime down | Core and other workspaces remain available |
| Action target changed | Optimistic concurrency returns conflict and requires a new proposal |

No specialist may substitute for a failed specialist from another domain.

## 19. Observability

Record at minimum:

```text
trace_id
workflow_id
parent_run_id
child_run_id
actor_user_id
business_role
agent_workspace_id
specialist
intent
execution_mode
policy decision/reason
tool names and statuses
source IDs
data gaps
latency
retry count
token/tool budget and actual usage
model/prompt version
proposal and approval outcome
final workflow state
```

Dashboards:

- workflow success/partial/failure rate;
- p50/p95 latency by intent and specialist;
- direct-tool versus specialist-routing ratio;
- token and cost per successful workflow;
- data-gap frequency;
- source-validation failures;
- proposal acceptance rate;
- authorization denials;
- Supervisor candidate-plan rejection/fallback rate;
- child fan-out, depth and evidence-loop count;
- timeout/retry/dead-letter count.

## 20. Test and evaluation plan

### 20.1 Contract tests

- Reject extra auth/tool/profile fields.
- Reject result facts without authorized sources.
- Reject stale/expired result.
- Reject mismatched workflow/task hashes.
- Reject incorrect specialist/result type.
- Reject invalid signature, expired envelope and wrong runtime target.
- Reject prompt/model/tool-allowlist version mismatch.
- Verify in-process and remote adapters conform to the same runtime contract.

### 20.2 Router tests

- Simple lookup uses direct tool and no specialist LLM.
- Task analysis routes to Work only.
- Milestone health routes to Planning + Work + Risk.
- Capacity intent is denied/partial while feature gate is off.
- Client cannot force a specialist.
- Code fast path executes without Supervisor or specialist model calls.
- A Supervisor candidate plan outside the code allowlist is rejected or reduced.

### 20.3 Authorization tests

- Member sees only participating groups and allowed task IDs.
- Lead receives full bound Delivery source scope, not company-wide data.
- Revocation is effective before the next tool call/resume.
- Guessed task/group/person IDs fail closed.
- Specialist output cannot widen source scope.
- Model-visible allowed IDs cannot replace the server-side capability reference.
- Tool Gateway revalidates authorization for every read and action proposal.

### 20.4 Workflow tests

- Parallel child results are correlated to the same workflow.
- Out-of-order completion produces the same deterministic result.
- Duplicate events do not create duplicate child runs.
- Partial specialist failure produces an explicit partial response.
- Restart resumes from durable workflow state.
- Cancellation stops pending children.
- Subject version change invalidates stale results.
- Specialists cannot directly invoke another specialist.
- Maximum fan-out, depth and evidence-loop limits are enforced.
- Agent A transcript is not forwarded to Agent B; only validated context packs are used.

### 20.5 Business tests

- Blocked task yields correct risk and impact.
- Overdue dependency affects milestone assessment.
- Pending decision appears as a decision needed, not a decided fact.
- Message evidence cannot become an official decision without approval.
- Missing task history prevents unsupported forecast claims.
- Portfolio health remains identical with or without LLM synthesis.

### 20.6 Security tests

- Prompt injection requesting another workspace is denied.
- Tool output injection does not change routing/policy.
- Secret/system-prompt extraction is blocked.
- Action proposal replay is idempotent.
- A Member cannot approve a Lead action.
- Audit/log scan contains no secrets or unnecessary raw content.

### 20.7 Load and fault tests

- Per-workspace concurrency isolation.
- One slow specialist does not consume every worker.
- LLM provider timeout and quota exhaustion.
- Database restart during a waiting workflow.
- Worker crash after runtime completion but before result commit.
- Dead-letter replay with authorization revalidation.

## 21. Delivery phases and gates

### Phase 0 — Business validation and baseline

**Deliverables**

- Interview at least one Delivery Lead and two Members.
- Map current status, blocker and planning workflows.
- Measure baseline coordination time and blocker age.
- Freeze glossary, RACI and deterministic decision tables.
- Confirm the three MVP workflows are used in real operations.

**Gate:** no code rollout without named workflow owner, source of truth and measurable outcome.

### Phase 1 — Contracts and persistence

**Deliverables**

- Workflow, task and result contracts.
- Work, Planning, Risk and Evidence/Knowledge assessment schemas.
- Signed Agent Runtime Contract and server-side capability references.
- Deterministic Request Gateway and Tool Gateway interfaces.
- Additive migrations and repositories.
- Outbox dispatch and inbox deduplication.
- State-transition service with optimistic concurrency.

**Gate:** duplicate/restart/stale-version integration tests pass.

### Phase 2 — Supervisor foundation

**Deliverables**

- Code-first direct-read/single-specialist/multi-specialist routing.
- Supervisor LLM produces only a candidate plan; code validates agent set, dependencies, fan-out and budgets.
- Parent workflow and child run orchestration.
- Parallel dispatch, timeout, retry and cancellation.
- Runtime-contract adapter shared by in-process and future remote execution.
- Context Builder for structured result-to-context handoff; no transcript forwarding.
- Result validation and deterministic final-state computation.
- Existing Delivery synthesis and guardrails retained as final response layer.

**Gate:** simple reads use zero model calls; one complex request can create multiple bounded child runs, reject an invalid LLM plan and survive one child failure.

### Phase 3 — Specialist vertical slices

Implement in this order:

1. Delivery Task Intelligence.
2. Risk & Dependency.
3. Planning & Forecast.
4. Evidence & Knowledge.

Each slice requires:

- prompt and version;
- tool allowlist;
- state schema;
- output schema;
- guardrails;
- budget and timeout;
- unit/integration/eval cases;
- failure fallback.

**Gate:** no specialist is enabled by registry alone; its vertical slice must pass all gates.

### Phase 4 — MVP workflows

Implement:

1. Member Work Priority.
2. Daily Delivery Health.
3. Blocker Resolution.

**Gate:** source-backed UI and role/partial-failure E2E tests pass.

### Phase 5 — HITL expansion

- Retain dependency/decision transitions.
- Add task/milestone/release proposal types only with domain validators.
- Add proposal cards and approval history.
- Reauthorize and validate row version immediately before execution.

**Gate:** no side effect before valid approval; replay and stale proposal tests pass.

### Phase 6 — Advanced workflows

- Milestone Health.
- Change Impact Assessment.
- Delivery Release Readiness.
- Version invalidation and ReleaseCandidate integration.

**Gate:** old assessments become stale after scope/build/version changes.

### Phase 7 — Capacity data foundation

- Add work-transition history and capacity source model.
- Backfill only factual history; do not infer historical events.
- Implement flow/capacity tools and policy.
- Enable Capacity & Flow Agent in shadow mode.

**Gate:** metric reconciliation and fairness/privacy review pass.

### Phase 8 — Production rollout

- Shadow mode.
- Lead/Member pilot.
- Canary by Agent Workspace.
- Load/soak/fault tests.
- Runbook and incident rehearsal.
- KPI review and go/no-go.

## 22. Proposed PR sequence

```text
PD-MA-00  Current-state baseline, ADR and business decision tables
PD-MA-01  Workflow/specialist/result contracts
PD-MA-02  Workflow persistence, outbox dispatcher and inbox deduplication
PD-MA-03  Request Gateway, Tool Gateway and direct-read fast path
PD-MA-04  Supervisor planning plus durable child-run dispatch/wait/resume/cancel
PD-MA-05  Delivery Task Intelligence vertical slice
PD-MA-06  Risk & Dependency vertical slice
PD-MA-07  Planning & Forecast vertical slice
PD-MA-08  Evidence & Knowledge vertical slice
PD-MA-09  Member Work Priority workflow
PD-MA-10  Daily Delivery Health workflow
PD-MA-11  Blocker Resolution workflow
PD-MA-12  HITL action expansion
PD-MA-13  Unified workflow UI
PD-MA-14  Security, eval, load and fault gates
PD-MA-15  Milestone/Change Impact/Release Readiness workflows
PD-MA-16  Capacity data foundation and shadow specialist
PD-MA-17  Canary, operations and KPI review
```

PRs must be additive and keep the current Delivery dashboard and single-snapshot fallback operational behind feature flags.

## 23. File-level implementation map

Suggested new modules:

```text
src/agents/delivery_orchestration/
  request_router.py
  tool_gateway.py
  context_builder.py
  runtime_contracts.py
  runtime_adapter.py
  plan_validator.py

src/agents/delivery_supervisor/
  graph.py
  state.py
  router.py
  planner.py
  result_validator.py
  synthesis.py

src/agents/delivery_specialists/
  contracts.py
  work/
    graph.py
    state.py
    prompt.py
    tools.py
  risk_dependency/
    graph.py
    state.py
    prompt.py
    tools.py
  planning_forecast/
    graph.py
    state.py
    prompt.py
    tools.py
  evidence_knowledge/
    graph.py
    state.py
    prompt.py
    tools.py
  capacity_flow/
    graph.py
    state.py
    prompt.py
    tools.py

src/services/
  delivery_workflow_service.py
  delivery_specialist_dispatch_service.py
  delivery_workflow_event_service.py

src/api/
  delivery_workflow_routes.py

src/models/
  delivery_workflow_schemas.py

tests/test_agents/delivery_supervisor/
tests/test_agents/delivery_specialists/
tests/test_delivery_workflows.py
eval/datasets/product_delivery_multi_agent_v1.jsonl
```

Existing modules to extend carefully:

- `src/agents/tools/registry.py`
- `src/agents/contracts.py`
- `src/agents/schemas/delivery.py`
- `src/agents/profiles/workspace_delivery_graph.py`
- `src/agents/runtime/contracts.py`
- `src/agents/runtime/executor.py`
- `src/api/workspace_action_routes.py`
- `src/db/models.py`
- `src/services/workspace_outbox_service.py`
- Product Delivery Workspace UI page and API client.

Do not delete or replace the current graph until the Supervisor feature flag has passed canary and rollback tests.

## 24. Feature flags

```text
product_delivery_supervisor_enabled
product_delivery_hybrid_router_enabled
product_delivery_task_specialist_enabled
product_delivery_risk_specialist_enabled
product_delivery_planning_specialist_enabled
product_delivery_evidence_specialist_enabled
product_delivery_capacity_specialist_enabled
product_delivery_multi_specialist_workflows_enabled
```

Fallback behavior:

- Supervisor off: use the current Delivery snapshot/brief path.
- One specialist off: do not route to it; return explicit unsupported/partial behavior.
- Capacity off: never generate people/workload recommendations from incomplete data.
- Master Delivery flag off: fail closed for Delivery Agent invocation.

## 25. Definition of Done

The Product Delivery Workspace may be described as an operational multi-agent system only when all of the following are evidenced:

- Lead and Member communicate through one Product Delivery Workspace Agent.
- The code-based Request Gateway handles deterministic fast paths before any Supervisor LLM call.
- The Supervisor candidate plan is validated in code and selects the minimum sufficient specialist set.
- A multi-domain request creates one parent workflow and at least two independent child runs.
- Each specialist has a distinct prompt, allowlist, state, output schema and eval suite.
- Every child uses the signed Agent Runtime Contract and server-side authorization capability.
- Every tool call passes through Tool Gateway reauthorization; prompt fields are not treated as security.
- Child results use typed contracts and valid source references.
- Specialist-to-specialist context is rebuilt from structured results; no transcript or chain of thought is forwarded.
- Initial workflows contain no peer-to-peer or recursive agent calls.
- One child result can determine a later workflow branch.
- Workflow state survives process restart.
- Duplicate events do not duplicate work or actions.
- One specialist failure yields controlled partial behavior and does not fail another workspace.
- Lead/Member authorization is revalidated at dispatch, resume and action execution.
- Deterministic rules remain authoritative for health/risk/state transitions.
- The Supervisor recommends; the authorized human approves business-impacting decisions.
- No mutation occurs without an authorized Action Proposal lifecycle.
- The UI presents one coherent answer, progress, evidence and approval state.
- Pilot KPIs demonstrate real reduction in Delivery coordination cost.

## 26. Final implementation recommendation

Start with this minimum valuable configuration:

```text
1 deterministic Request Gateway + Tool Gateway
1 Product Delivery Workspace Supervisor
4 internal specialists:
  - Delivery Task Intelligence
  - Risk & Dependency
  - Planning & Forecast
  - Evidence & Knowledge

3 production workflows:
  - Member Work Priority
  - Daily Delivery Health
  - Blocker Resolution

1 shared deterministic rule layer
1 durable HITL proposal pipeline
1 versioned Agent Runtime Contract
```

Do not activate Capacity & Flow until the source model exists. Do not create one agent per primitive tool. If a tool later becomes a multi-step, independently evaluated capability, promote it through the agent criteria in section 4 and keep its data access deterministic underneath.
