# Codex CLI and IDE AI Log Hooks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make project-local Codex CLI and Codex IDE turns append normalized `tool=codex` entries to `.ai-log/session.jsonl` on Windows and POSIX systems.

**Architecture:** Both Codex surfaces load one project-local `.codex/hooks.json`. Platform-specific hook commands resolve the Git root, call a resilient Python launcher, and pipe the official hook JSON payload into the existing `scripts/log_hook.py` normalizer.

**Tech Stack:** Codex lifecycle hooks, JSON, Windows batch, Bash, Python 3.11+, pytest.

## Global Constraints

- Preserve the existing `.ai-log/session.jsonl` JSON Lines format.
- Preserve the 1,000-character prompt limit.
- Preserve existing Claude, Gemini, Cursor, Copilot, and Antigravity logging.
- Preserve pre-push submission and archive behavior.
- Do not bypass Codex hook trust; the developer must approve changed hooks with `/hooks`.
- Do not include unrelated backend changes in logging commits.

---

## File Map

- Create `tests/test_codex_ai_log_hooks.py`: contract and integration coverage for Codex hook configuration, Windows launcher behavior, and normalized log output.
- Modify `.codex/hooks.json`: schema-correct shared CLI/IDE lifecycle hooks with POSIX and Windows commands.
- Modify `scripts/_pyrun.cmd`: repository-relative, reliable Windows Python selection.
- Modify `scripts/_pyrun.sh`: repository-relative POSIX Python selection.
- Keep `scripts/log_hook.py` unchanged unless its characterization tests expose a compatibility defect.

### Task 1: Lock the Codex hook contract

**Files:**
- Create: `tests/test_codex_ai_log_hooks.py`
- Modify: `.codex/hooks.json`

**Interfaces:**
- Consumes: Codex `hooks.json` lifecycle schema.
- Produces: `UserPromptSubmit` and `Stop` command handlers with `type`, `command`, and `commandWindows`.

- [ ] **Step 1: Write the failing hook schema test**

```python
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_codex_hooks_define_cross_platform_command_handlers():
    config = json.loads((REPO_ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))

    for event in ("UserPromptSubmit", "Stop"):
        handler = config["hooks"][event][0]["hooks"][0]
        assert handler["type"] == "command"
        assert "git rev-parse --show-toplevel" in handler["command"]
        assert "git rev-parse --show-toplevel" in handler["commandWindows"]
        assert "--tool=codex" in handler["command"]
        assert "--tool=codex" in handler["commandWindows"]
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_codex_ai_log_hooks.py::test_codex_hooks_define_cross_platform_command_handlers -v
```

Expected: FAIL because the current handlers omit `type` and `commandWindows`.

- [ ] **Step 3: Implement the minimal schema-correct hook definitions**

Use the same handler shape for both events:

```json
{
  "type": "command",
  "command": "bash -lc 'repo=$(git rev-parse --show-toplevel) && bash \"$repo/scripts/_pyrun.sh\" \"$repo/scripts/log_hook.py\" --tool=codex'",
  "commandWindows": "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \"$repo = git rev-parse --show-toplevel; & (Join-Path $repo 'scripts\\_pyrun.cmd') (Join-Path $repo 'scripts\\log_hook.py') '--tool=codex'\"",
  "timeout": 10
}
```

- [ ] **Step 4: Run the targeted test and verify GREEN**

Run the Step 2 command again.

Expected: PASS.

- [ ] **Step 5: Commit the hook contract**

```powershell
git add tests/test_codex_ai_log_hooks.py .codex/hooks.json
git commit -m "fix: configure Codex AI log hooks"
```

### Task 2: Make the Windows launcher select a usable project Python

**Files:**
- Modify: `tests/test_codex_ai_log_hooks.py`
- Modify: `scripts/_pyrun.cmd`
- Modify: `scripts/_pyrun.sh`

**Interfaces:**
- Consumes: a Python script or normal Python CLI arguments in `%*` / `"$@"`.
- Produces: the selected Python process stdout and its exit code.

- [ ] **Step 1: Write the failing Windows launcher test**

```python
import os
import subprocess

import pytest


@pytest.mark.skipif(os.name != "nt", reason="Windows batch launcher test")
def test_windows_python_launcher_works_from_repo_subdirectory():
    launcher = REPO_ROOT / "scripts" / "_pyrun.cmd"
    command = subprocess.list2cmdline(
        [str(launcher), "-c", "print('PYRUN_OK')"]
    )

    completed = subprocess.run(
        command,
        cwd=REPO_ROOT / "Frontend",
        shell=True,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "PYRUN_OK"
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_codex_ai_log_hooks.py::test_windows_python_launcher_works_from_repo_subdirectory -v
```

Expected: FAIL with exit code `112` and `No installed Python found!` because `_pyrun.cmd` stops at the broken `py.exe` launcher.

- [ ] **Step 3: Implement repository-relative interpreter selection**

Update `_pyrun.cmd` to derive `REPO_ROOT` from `%~dp0..` and try, in order:

```bat
%REPO_ROOT%\.venv\Scripts\python.exe
%REPO_ROOT%\.ai-log\.venv\Scripts\python.exe
python
python3
py -3
```

Only use a PATH candidate after a zero-exit probe. Forward `%*`, return the child exit code, and exit `0` with a concise stderr message only when no candidate works.

Update `_pyrun.sh` to derive:

```bash
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
```

and probe virtual environments under `$REPO_ROOT` before PATH interpreters.

- [ ] **Step 4: Run the launcher test and verify GREEN**

Run the Step 2 command again.

Expected: PASS with stdout `PYRUN_OK`.

- [ ] **Step 5: Run both tests in the file**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_codex_ai_log_hooks.py -v
```

Expected: all current tests PASS.

- [ ] **Step 6: Commit launcher reliability**

```powershell
git add scripts/_pyrun.cmd scripts/_pyrun.sh tests/test_codex_ai_log_hooks.py
git commit -m "fix: make AI log Python launchers reliable"
```

### Task 3: Verify Codex payload normalization without changing existing formats

**Files:**
- Modify: `tests/test_codex_ai_log_hooks.py`
- Verify: `scripts/log_hook.py`

**Interfaces:**
- Consumes: Codex hook JSON on stdin and `--tool=codex`.
- Produces: one normalized line in `$AI_LOG_DIR/session.jsonl` and `{"status":"logged"}` on stdout.

- [ ] **Step 1: Add a characterization integration test**

```python
def test_codex_prompt_hook_appends_normalized_truncated_entry(tmp_path):
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "session-1",
        "turn_id": "turn-1",
        "transcript_path": "transcripts/session-1.jsonl",
        "prompt": "x" * 1200,
    }
    env = {**os.environ, "AI_LOG_DIR": str(tmp_path)}

    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "log_hook.py"),
            "--tool=codex",
        ],
        cwd=REPO_ROOT,
        env=env,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"status": "logged"}
    entries = [
        json.loads(line)
        for line in (tmp_path / "session.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(entries) == 1
    assert entries[0]["tool"] == "codex"
    assert entries[0]["event"] == "UserPromptSubmit"
    assert entries[0]["session_id"] == "session-1"
    assert entries[0]["turn_id"] == "turn-1"
    assert entries[0]["transcript_path"] == "transcripts/session-1.jsonl"
    assert entries[0]["prompt"] == "x" * 1000
```

- [ ] **Step 2: Run the characterization test**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_codex_ai_log_hooks.py::test_codex_prompt_hook_appends_normalized_truncated_entry -v
```

Expected: PASS, confirming `log_hook.py` already implements the required format.

- [ ] **Step 3: Run targeted logging verification**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_codex_ai_log_hooks.py -v
.\.venv\Scripts\python.exe -m ruff check tests\test_codex_ai_log_hooks.py scripts\log_hook.py
```

Expected: all tests PASS and Ruff reports `All checks passed!`.

- [ ] **Step 4: Run full regression verification**

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m ruff check src tests scripts
```

Expected: all tests PASS and Ruff reports no errors.

- [ ] **Step 5: Execute the Windows hook command against a temporary log directory**

Send representative `UserPromptSubmit` and `Stop` payloads through the exact `commandWindows` handler with `AI_LOG_DIR` set to a temporary directory. Confirm two entries with `tool=codex` and the correct event names.

- [ ] **Step 6: Commit integration coverage**

```powershell
git add tests/test_codex_ai_log_hooks.py
git commit -m "test: cover Codex AI log payloads"
```

### Task 4: Activate and verify in both Codex surfaces

**Files:**
- No repository changes expected.

**Interfaces:**
- Consumes: trusted project hook definitions.
- Produces: live CLI and IDE entries in `.ai-log/session.jsonl`.

- [ ] **Step 1: Restart Codex sessions after the configuration change**

Close and reopen the Codex CLI session and reload the IDE window for `F:\P-132`.

- [ ] **Step 2: Review and trust hooks**

Run `/hooks` in Codex CLI, review `log-prompt` and `log-stop`, and trust the exact definitions. Do not use `--dangerously-bypass-hook-trust`.

- [ ] **Step 3: Verify CLI logging**

Submit one identifiable test prompt from Codex CLI, end the turn, and confirm new `UserPromptSubmit` and `Stop` entries with `tool=codex`.

- [ ] **Step 4: Verify IDE logging**

Submit one identifiable test prompt from the Codex IDE extension, end the turn, and confirm the same two event types append to the same file.

- [ ] **Step 5: Confirm submission remains separate**

Verify local entries exist before `git push`. Preserve the existing pre-push submission behavior; local logging must not require `AI_LOG_SERVER` or `AI_LOG_API_KEY`.
