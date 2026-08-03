import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_codex_hooks_define_cross_platform_command_handlers():
    config = json.loads((REPO_ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))

    for event_name in ("UserPromptSubmit", "Stop"):
        handler = config["hooks"][event_name][0]["hooks"][0]

        assert handler["type"] == "command"
        assert "git rev-parse --show-toplevel" in handler["command"]
        assert "git rev-parse --show-toplevel" in handler["commandWindows"]
        assert "--tool=codex" in handler["command"]
        assert "--tool=codex" in handler["commandWindows"]


@pytest.mark.skipif(os.name != "nt", reason="Windows launcher test")
def test_windows_python_launcher_uses_repository_venv_from_subdirectory(tmp_path):
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    (fake_bin / "py.cmd").write_text("@exit /b 112\n", encoding="utf-8")

    launcher = REPO_ROOT / "scripts" / "_pyrun.cmd"
    command = f'call "{launcher}" -c "print(\'PYRUN_OK\')"'
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"

    result = subprocess.run(
        command,
        cwd=REPO_ROOT / "Frontend",
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env=env,
        shell=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "PYRUN_OK"


def test_codex_prompt_is_normalized_and_appended_to_jsonl(tmp_path):
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "codex-session",
        "turn_id": "codex-turn",
        "transcript_path": "transcripts/codex.jsonl",
        "prompt": "x" * 1200,
    }
    env = os.environ.copy()
    env["AI_LOG_DIR"] = str(tmp_path)

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "log_hook.py"), "--tool=codex"],
        cwd=REPO_ROOT,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"status": "logged"}
    lines = (tmp_path / "session.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["tool"] == "codex"
    assert entry["event"] == "UserPromptSubmit"
    assert entry["session_id"] == "codex-session"
    assert entry["turn_id"] == "codex-turn"
    assert entry["transcript_path"] == "transcripts/codex.jsonl"
    assert entry["prompt"] == "x" * 1000


@pytest.mark.skipif(os.name != "nt", reason="Windows hook command test")
def test_windows_codex_hook_commands_log_prompt_and_stop_from_subdirectory(tmp_path):
    config = json.loads((REPO_ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    env = os.environ.copy()
    env["AI_LOG_DIR"] = str(tmp_path)

    payloads = {
        "UserPromptSubmit": {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "cli-session",
            "turn_id": "cli-turn",
            "transcript_path": "transcripts/cli.jsonl",
            "prompt": "Codex CLI prompt",
        },
        "Stop": {
            "hook_event_name": "Stop",
            "session_id": "ide-session",
            "turn_id": "ide-turn",
            "transcript_path": "transcripts/ide.jsonl",
        },
    }

    for event_name, payload in payloads.items():
        command = config["hooks"][event_name][0]["hooks"][0]["commandWindows"]
        result = subprocess.run(
            command,
            cwd=REPO_ROOT / "Frontend",
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            env=env,
            shell=True,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == {"status": "logged"}

    entries = [
        json.loads(line)
        for line in (tmp_path / "session.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [(entry["tool"], entry["event"]) for entry in entries] == [
        ("codex", "UserPromptSubmit"),
        ("codex", "Stop"),
    ]
