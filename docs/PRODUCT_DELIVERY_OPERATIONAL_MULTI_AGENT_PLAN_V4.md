# Product Delivery operational multi-agent plan V4

## Business objective

The Workspace Agent is the single conversational entry point. It delegates only
when a request needs an independent business capability. The goal is not to
maximize the number of agents, but to reduce Lead reporting effort, make delivery
status reproducible, and help Members act on their own deadlines without exposing
workspace-wide data.

## Role workflows

### Delivery Lead

1. **Summarize tasks and checkpoint progress**
   - Workspace Agent routes to Delivery Task Intelligence for task facts.
   - Planning & Forecast receives the validated task result and deterministic
     checkpoint assessments.
   - The Workspace Agent synthesizes one answer and keeps source/agent lineage.
2. **Review plan completeness**
   - A Lead defines a checkpoint, deadline, and required tasks.
   - Rules compute completion percentage and time state.
   - When all required tasks are complete, the checkpoint remains
     `pending_lead_quality_review`; the agent cannot accept quality.
3. **Update operational state**
   - Task status/assignment/due-date changes are durable proposals.
   - Group updates and scheduled reminders are Lead-only proposals.
   - Every mutation is validated at proposal time and re-authorized at approval
     or send time, with idempotency, row version, expiry, and audit logging.
4. **Communicate to teams**
   - An approved immediate update is posted to the selected source group.
   - An approved one-shot reminder is persisted and delivered by the scheduler.
   - Messages are visibly labelled as Workspace Agent content approved by a Lead.

### Delivery Member

1. **My work**: Task Intelligence reads only tasks owned by the Member in groups
   they are currently allowed to access.
2. **My schedule**: deadline and checkpoint views use the same Member scope; they
   are not a workspace-wide completion claim.
3. **My task changes**: a Member may propose a status/due-date change only for
   their own task. A Lead still approves the proposal.
4. **Team reminders**: Members receive reminders through their authorized group;
   they cannot create Workspace Agent group broadcasts.

## Checkpoint rule contract

| Rule-owned field | Meaning |
|---|---|
| `completion_percent` | Completed required tasks / required tasks |
| `completed_on_time` | Every required task completed no later than the checkpoint deadline |
| `completed_late` | Every required task completed, but at least one completion was late |
| `overdue` | Deadline passed while required tasks remain incomplete |
| `at_risk` | Required tasks remain incomplete within three days of deadline |
| `on_track` | Required tasks remain incomplete but outside the risk window |
| `insufficient_data` | Missing deadline or required-task baseline |

The rule engine does not assess correctness, usefulness, acceptance criteria,
code quality, or release quality. Only the Lead can set `accepted` or `rejected`.
An objectively complete checkpoint therefore remains
`pending_lead_quality_review` until that human decision exists.

## Agent and tool selection

| User intent | Agent plan | Tools/capabilities |
|---|---|---|
| Greeting/help | Workspace Agent only | No business-data tool |
| Exact task lookup | Task Intelligence only | task details/search |
| My work / my schedule | Task Intelligence only | scoped tasks, checkpoint progress |
| Task summary + plan assessment | Delivery Task Intelligence -> Planning & Forecast | tasks, portfolio health, checkpoint progress, milestones |
| Checkpoint progress only | Planning & Forecast only | checkpoint progress, milestones, flow |
| Blocker/root impact | Task + Risk + Planning | tasks, dependencies, deterministic risks, schedule |
| Release readiness | Work + Planning + Risk + Evidence | work, plan, risks, decisions, source evidence |

`get_delivery_checkpoint_progress` remains a tool, not a separate agent, because
it is a deterministic data/rule capability. Planning & Forecast is the agent that
interprets that capability in the independent planning domain.

## Model policy

- Provider: OpenRouter.
- Model slug: `openai/gpt-5.6-luna` for Workspace synthesis, every Product
  Delivery specialist, QA Workspace synthesis, and verifier.
- Reasoning: `medium` for the current business-analysis baseline.
- Deterministic routing, RBAC, checkpoint labels, mutation validation, and
  approval gates do not depend on model output.

## Delivery phases and acceptance criteria

1. **Domain baseline**: durable checkpoint-task links, completion timestamps,
   human quality-review fields, migration and audit.
2. **Read path**: role-scoped checkpoint progress in Tool Gateway and specialist
   context; no cross-group or cross-member fallback.
3. **Adaptive orchestration**: one specialist for schedule/checkpoint-only turns;
   two specialists for task summary plus plan evaluation.
4. **Action path**: Lead-only group update/schedule proposals, approval,
   re-authorization, durable delivery, WebSocket notification.
5. **UI**: Lead controls for checkpoint definition, quality review, update and
   schedule; checkpoint status in chat results; Member schedule prompt.
6. **Verification**: rule unit tests, Lead/Member RBAC tests, action tests,
   migration test, complete backend regression, frontend production build, and
   an OpenRouter Luna smoke test without printing credentials.

## Explicit non-goals for this increment

- The agent does not autonomously judge quality.
- The scheduler is one-shot; recurring policies require a separate recurrence
  contract, cancellation UI, and escalation policy.
- External Google Calendar creation remains a Personal Agent capability unless
  a future team-calendar owner and consent model is approved.
- Natural-language mutations must produce a visible proposal, never an immediate
  side effect. The existing approval queue is the execution boundary..
