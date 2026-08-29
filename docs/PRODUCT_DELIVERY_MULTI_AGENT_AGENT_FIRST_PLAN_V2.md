# Product Delivery Agent-first Multi-Agent Plan v2

> Status: canonical implementation amendment  
> Date: 2026-08-27  
> Supersedes: every chatbot `direct_tool` path and every statement that a specialist is only a label around a pre-rendered response  
> Retains: RBAC, source consent, deterministic policy gates, durable workflow records, HITL and workspace isolation
>
> Amended by `PRODUCT_DELIVERY_ADAPTIVE_ORCHESTRATION_PLAN_V3.md`: only business-data requests require specialists; conversational turns use the Workspace Agent boundary without business reads.

## 1. Product decision

The Product Delivery chatbot has one user-facing agent: **Product Delivery Workspace Agent**. Every authorized **business-data request** must create an agent workflow and invoke at least one LLM-backed specialist. Conversational turns are governed by the v3 adaptive amendment and do not create specialist workflows. A primitive tool result is never presented as an agent answer.

Tools remain deterministic data/action capabilities. An agent owns a coherent business capability, selects from its allowlist, interprets results and returns a typed result to the Workspace Agent. The Workspace Agent is the only component that answers the user and owns final accountability.

Direct deterministic reads remain valid for dashboards, selectors, health checks and explicit non-chat REST resources. They must not appear as `Workspace Agent` chat responses.

## 2. Target architecture

```text
User
  -> Product Delivery Workspace Agent (Supervisor)
       -> policy + authorization envelope
       -> intent/plan
       -> ChildTask -> Specialist Agent
            -> allowlisted deterministic tools
            -> LLM interpretation
            -> SpecialistResult
       -> validate result identity, scope, sources and hashes
       -> optionally pass selected validated result facts to the next specialist
       -> final synthesis/response
  -> User
```

Agent-to-agent communication is mediated by the Supervisor. Specialists do not freely chat with each other and cannot delegate recursively.

## 3. Agent catalogue and tool ownership

### 3.1 Product Delivery Workspace Agent

Responsibilities:

- receive the user request and own the response;
- plan only within trusted routing/policy constraints;
- issue bounded `ChildTask` envelopes;
- validate every `SpecialistResult`;
- construct minimal downstream context from validated upstream outputs;
- synthesize multiple results and expose uncertainty/data gaps;
- create action proposals but never bypass HITL.

It does not query the database directly from model code and does not execute business mutations.

### 3.2 Delivery Task Intelligence Agent

Independent business capability: retrieve, filter, aggregate, prioritize and explain tasks/work items at
exact-task, actor, authorized-group and authorized-workspace scope.

Tools:

- `get_delivery_task_details`;
- `search_delivery_tasks`;
- `get_delivery_tasks`;
- `get_delivery_checkpoint_progress` for schedule-aware task views;
- `get_delivery_portfolio_health` for authorized aggregate views;
- `get_delivery_task_status_history` when the event source exists;
- read-only assignee/deadline/source projections.

Outputs `TaskAssessment` containing facts, aggregate metrics, priority/reason codes, sources, gaps and
recommendations, with no mutation fields. It handles exact lookup, Member My Work and group/workspace task
summaries. Exact lookup therefore uses one specialist LLM rather than the former zero-LLM fast path.

### 3.3 Consolidation decision

The former Work Intelligence split is retired. Its portfolio/workstream task aggregation belongs to Delivery
Task Intelligence because it uses the same task source, authorization boundary and core reasoning context.
No new workflow dispatches `work_intelligence`; legacy stored values normalize to `task_intelligence` when read.

### 3.4 Risk & Dependency Agent

Tools: `get_delivery_risks`, `get_delivery_dependencies`, `get_delivery_portfolio_health`. It may consume a validated `TaskAssessment` or `WorkAssessment` supplied by the Supervisor. It cannot treat upstream recommendations as facts.

### 3.5 Planning & Forecast Agent

Tools: `get_delivery_milestones`, `get_delivery_release_status`, `get_delivery_flow_metrics`. It may consume validated work/risk metrics. Missing history or baseline remains an explicit gap; it cannot invent ETA or probability.

### 3.6 Evidence & Knowledge Agent

Tools: `get_delivery_decisions`, `search_delivery_messages`. It validates evidence, provenance, freshness and conflicts. Chat evidence never becomes a formal decision automatically.

### 3.7 Capacity & Flow Agent

Remains data-gated until assignment history, availability inputs, fairness policy and flow-event history meet the existing activation criteria.

## 4. Routing decisions

| Intent | Required workflow | Agent sequence |
|---|---|---|
| Exact task lookup | `single_specialist` | Task -> Workspace response |
| Member work priority | `single_specialist` | Task -> Workspace response |
| Portfolio/work health | single or multi | Work -> optional Workspace synthesis |
| Blocker analysis | `multi_specialist` | Task/Work -> Risk + Planning -> Workspace synthesis |
| Dependency analysis | `multi_specialist` | Work -> Risk -> Planning -> Workspace synthesis |
| Milestone health | `multi_specialist` | Work + Planning -> Risk -> Workspace synthesis |
| Change impact | `multi_specialist` | Work -> Planning -> Risk -> optional Evidence -> Workspace synthesis |
| Release readiness | `multi_specialist` | Work -> Planning + Risk -> Evidence -> Workspace synthesis |
| Decision status | `single_specialist` | Evidence -> Workspace response |
| Daily Delivery health | `multi_specialist` | Work + Planning + Risk -> conditional Evidence -> Workspace synthesis |
| Capacity analysis | feature-gated | Task/Work -> Capacity only after activation |

Rules:

- no accepted business-data route may have zero specialists; workspace-only conversational routes are defined by the v3 amendment;
- one specialist is sufficient when one business capability can answer;
- the Workspace Agent may forward a validated single result through its response boundary without a second synthesis call;
- multi-specialist responses require Workspace Agent synthesis;
- deterministic routing may identify an unambiguous intent, but it is a policy component, not an agent response.

## 5. Agent communication contracts

### 5.1 `ChildTask`

```text
workflow_id
run_id
specialist
goal
subject_refs
allowed_tools
max_tool_calls
authorization_capability_ref
authorization_scope_hash
base_context_hash
upstream_result_hashes
deadline_at
```

### 5.2 `SpecialistResult`

```text
workflow_id
run_id
specialist
status
facts
inferences
recommendations
metrics
sources
data_gaps
input_hash
upstream_result_hashes
output_hash
prompt_version
model_provider
model_name
usage
attempt_count
generated_at
```

### 5.3 Result chaining rules

1. The Supervisor validates workflow/run/specialist identity.
2. Returned source IDs must be a subset of delegated sources.
3. The Supervisor records the upstream result hash.
4. Only selected facts, metrics, gaps and source references enter downstream context.
5. Inferences and recommendations remain labelled and cannot be promoted to facts.
6. Downstream agents receive no raw prompt, hidden state, token or complete conversation.
7. Every downstream result records the exact upstream hashes it consumed.

## 6. Specialist tool execution model

The end state uses a signed server Tool Gateway capability. The runtime supplies workflow/run ID, tool name and bounded arguments; the server revalidates current membership, role, source binding, consent and subject version for every call.

The production-MVP transition uses a delegated tool-result pack built by the same server gateway. The specialist must execute an allowlisted runtime tool selection over that pack before LLM explanation. This creates observable tool calls and prevents a specialist from reading keys outside its tool policy while the remote signed callback is introduced separately.

No model receives database credentials, bearer tokens or arbitrary query capability.

## 7. Supervisor DAG behaviour

### 7.1 Single specialist

```text
authorize -> plan -> dispatch specialist -> validate result -> respond
```

There is always at least one specialist LLM attempt. Provider failure produces a deterministic specialist fallback with an explicit reason; it never silently becomes a direct-tool chatbot answer.

### 7.2 Multi specialist

```text
authorize
-> stage 1 foundation agents
-> validate results
-> stage 2 dependent agents with upstream hashes
-> optional evidence stage
-> Workspace Agent synthesis
-> output guardrail
-> persist answer and lineage
```

Independent agents may run in parallel. A dependent agent cannot start until declared upstream results are terminal or the Supervisor records why it continued without them.

## 8. Authorization and business roles

- Member sees only authorized groups and member-scoped work where required.
- Lead sees source groups bound to that Product Delivery agent workspace.
- Neither role may use the agent to access another agent workspace.
- Source scope is revalidated before workflow creation and for every future remote tool call.
- Agent results never grant additional authority.
- Mutations remain proposals. Task assignment stays Lead-only; status/due-date proposals retain ownership and optimistic-version rules.

## 9. Persistence and observability

Persist workflow plan/version, actor role snapshot, authorization scope hash, supervisor/specialist runs, dependency hashes, prompt/model/tool policy versions, sanitized tool-call summaries, per-run usage/attempt/fallback/latency/error, structured results, sources, gaps, output hashes, synthesis and workflow events.

UI must show the actual sequence rather than only a flat list: agent, status, model, token usage, upstream dependencies and fallback reason.

## 10. Implementation backlog

### AF-MA-01 — Plan/contracts

- adopt this amendment as canonical;
- add Task Intelligence and upstream lineage fields;
- keep direct reads outside chatbot routes.

### AF-MA-02 — Agent-first routing

- route `TASK_LOOKUP` and `MY_WORK_PRIORITY` to Task Intelligence;
- assert every business-data chat route includes at least one enabled specialist;
- remove the chatbot direct-response branch.

### AF-MA-03 — Task Intelligence vertical slice

- task-specific minimal context and exact-subject filtering;
- deterministic task analysis plus LLM explanation;
- independent prompt/model/tool policy and structured result.

### AF-MA-04 — Delegated tool execution

- add runtime delegated tool-result executor;
- enforce specialist allowlist at call time;
- record tool call summary;
- retain the server gateway as authorization authority.

### AF-MA-05 — Supervisor DAG/result chaining

- execute foundation and dependent stages;
- construct minimal upstream packs;
- record and validate upstream hashes;
- retain conditional Evidence.

### AF-MA-06 — Persistence/API/UI

- persist upstream hashes/tool summaries/model usage;
- expose the workflow sequence in API;
- display Task Intelligence and lineage in UI.

### AF-MA-07 — Tests and rollout gates

- exact task chat proves at least one specialist LLM call and workflow ID;
- multi workflow proves dependent result hashes;
- no specialist reads a disallowed context key/tool;
- Member/Lead/outsider scope tests;
- provider timeout/output rejection fallback tests;
- migration, regression, Docker and UI build;
- load/canary remain explicit production operations gates.

## 11. Definition of Done

- Every Product Delivery response is owned by the Workspace Agent; every business-data response is backed by at least one specialist run, while v3 workspace-only turns are explicitly non-data conversational responses.
- Exact task lookup is not `direct_tool` and never returns `llm_calls=0` while presented as an agent answer.
- Task Intelligence is independently prompted, evaluated and observable.
- Multi-agent workflows exchange only typed, validated results through the Supervisor.
- Downstream lineage proves which upstream result hashes were consumed.
- Tools remain deterministic and authorization remains server-side.
- UI/telemetry do not mislabel single-agent tool calling as multi-agent.
- Full regression and live single/multi-agent E2E pass.
- Capacity, async crash-resume, remote callback Tool Gateway, load and canary are not falsely marked complete before their gates exist.
