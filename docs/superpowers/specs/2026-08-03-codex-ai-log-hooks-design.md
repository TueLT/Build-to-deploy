# Codex CLI and IDE AI Log Hooks — Design

## Objective

Make Codex CLI and the Codex IDE extension automatically append AI usage entries to
`.ai-log/session.jsonl` for this repository, while preserving the existing log format,
prompt limit, submission workflow, and integrations for other AI tools.

## Scope

This change covers project-local Codex lifecycle hooks on Windows and POSIX systems.
It does not change the grading server, submission API, archive behavior, or the log
formats used by Claude, Gemini, Cursor, Copilot, and Antigravity.

## Selected Approach

Use the project-local `.codex/hooks.json` as the single hook source for both Codex CLI
and the Codex IDE extension. Both surfaces use the same active project configuration,
so maintaining separate CLI and IDE logging configurations would add duplication and
drift without adding capability.

Global hooks under the user's home directory are intentionally not used because they
would affect unrelated repositories and would not be shared with other team members.

## Hook Events and Data

Two Codex lifecycle events are logged:

- `UserPromptSubmit`: records the submitted prompt, limited to 1,000 characters.
- `Stop`: records the end of a Codex turn as a lifecycle event.

Entries continue to use the normalized JSON Lines format produced by
`scripts/log_hook.py`, including the timestamp, tool, event, session, model, repository,
branch, commit, student email, prompt, turn ID, and transcript path when Codex supplies
those values.

The logger appends entries to one file:

```text
.ai-log/session.jsonl
```

It does not create one JSON file per session. The existing pre-push submission flow may
move submitted entries into `.ai-log/archive/YYYY-MM-DD.jsonl`; that behavior remains
unchanged.

## Components

### `.codex/hooks.json`

The hook definitions will follow the current Codex schema:

- Each handler declares `type: "command"`.
- `command` provides the POSIX launcher.
- `commandWindows` provides the Windows launcher.
- Commands resolve the repository root before invoking project scripts so hooks still
  work when Codex starts from a repository subdirectory.
- Existing `UserPromptSubmit` and `Stop` event coverage is retained.

### `scripts/_pyrun.cmd`

The Windows launcher will resolve the repository root from its own location and select
Python in this order:

1. `<repo>\.venv\Scripts\python.exe`
2. `<repo>\.ai-log\.venv\Scripts\python.exe`
3. `python` on `PATH`
4. `python3` on `PATH`
5. `py -3` only when the launcher can actually execute it

The current behavior of stopping after finding a broken `py.exe` launcher will be
removed. The launcher will return the child Python process exit code and will remain
non-blocking only when no usable interpreter exists.

### `scripts/_pyrun.sh`

The POSIX launcher will resolve the repository root from its own file location instead
of assuming the session working directory is the repository root. Its existing Python
fallback behavior will otherwise remain intact.

### `scripts/log_hook.py`

No format redesign is required. The existing Codex normalization already accepts the
official hook payload fields and limits prompts to 1,000 characters. Changes to this
file will be made only if a failing regression test reveals a compatibility issue.

## Runtime Flow

```text
Codex CLI or IDE
  -> UserPromptSubmit / Stop
  -> project .codex/hooks.json
  -> platform-specific Python launcher
  -> scripts/log_hook.py --tool=codex
  -> append normalized entry to .ai-log/session.jsonl
  -> existing git pre-push submission and archive flow
```

## Trust and Security

Codex requires users to review and trust non-managed project hooks by their exact
definition hash. The implementation will not bypass this protection. After the hook
definition changes, each developer must open Codex in the repository, run `/hooks`,
review the two handlers, and trust them once.

The project itself must also remain trusted. Prompt content is stored locally using the
existing 1,000-character limit. No additional transcript content is read, and no log is
submitted merely because a hook fires.

## Error Handling

- Hook commands must return valid JSON produced by `log_hook.py` when logging succeeds.
- Invalid or empty stdin remains a no-op, matching current behavior.
- A missing repository origin remains a no-op because entries cannot be attributed to a
  team repository.
- A missing Python interpreter must not block Codex, but the launcher should emit a
  concise diagnostic to stderr.
- Submission configuration errors remain isolated from local logging.

## Testing Strategy

Implementation follows a red-green-refactor cycle.

1. Add a config regression test asserting that both Codex events contain command
   handlers with `type`, `command`, and `commandWindows`.
2. Add a Windows launcher regression test that executes `_pyrun.cmd` and proves it uses
   a working project interpreter instead of stopping at a broken `py.exe` launcher.
3. Add a logger integration test that sends a representative Codex
   `UserPromptSubmit` payload into `log_hook.py`, writes to a temporary log directory,
   and validates the normalized entry.
4. Verify the existing 1,000-character prompt limit.
5. Run the targeted logging tests, the full backend test suite, and Ruff.
6. Execute both platform command strings manually with a temporary log directory on the
   available Windows environment.

The IDE and CLI use the same project hook definition, so the automated contract test
validates the shared configuration. Final interactive verification requires accepting
the hooks with `/hooks`, then submitting one prompt from CLI and one from the IDE and
checking that two new `tool=codex` entries appear.

## Acceptance Criteria

- Codex CLI appends `UserPromptSubmit` and `Stop` entries on Windows.
- Codex IDE uses the same hook configuration and appends entries in the same format.
- Logged prompts remain limited to 1,000 characters.
- Existing non-Codex logging configuration is unchanged.
- Hooks work when the session starts at the repository root or a subdirectory.
- A broken `py.exe` launcher no longer prevents fallback to a valid project Python.
- All automated tests and Ruff checks pass.
- The user-facing setup step is limited to reviewing and trusting the hooks with
  `/hooks` after opening a new Codex session.
