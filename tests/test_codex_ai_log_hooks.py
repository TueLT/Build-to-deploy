import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _config() -> dict:
    return json.loads(
        (REPO_ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8")
    )


def test_codex_hook_config_uses_supported_schema():
    config = _config()

    assert set(config) <= {"description", "hooks"}
    for event_name in ("UserPromptSubmit", "Stop"):
        handler = config["hooks"][event_name][0]["hooks"][0]
        assert handler["type"] == "command"
        assert "git rev-parse --show-toplevel" in handler["command"]
        assert "--tool=codex" in handler["command"]
        assert "--tool=codex" in handler["commandWindows"]
        assert handler["commandWindows"].startswith("scripts\\_pyrun.cmd")


def test_codex_prompt_is_normalized_and_appended_to_jsonl(tmp_path):
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "codex-session",
        "turn_id": "codex-turn",
        "transcript_path": "transcripts/codex.jsonl",
        "prompt": "Codex prompt",
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
    assert json.loads(result.stdout) == {"continue": True, "suppressOutput": True}
    entries = [
        json.loads(line)
        for line in (tmp_path / "session.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(entries) == 1
    assert entries[0]["tool"] == "codex"
    assert entries[0]["event"] == "UserPromptSubmit"
    assert entries[0]["prompt"] == "Codex prompt"
    expected_branch = subprocess.check_output(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
    ).strip()
    assert entries[0]["branch"] == expected_branch


@pytest.mark.skipif(os.name != "nt", reason="Windows hook command test")
def test_windows_codex_hook_command_runs_from_repo_root(tmp_path):
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "windows-session",
        "turn_id": "windows-turn",
        "transcript_path": "transcripts/windows.jsonl",
        "prompt": "Windows Codex prompt",
    }
    env = os.environ.copy()
    env["AI_LOG_DIR"] = str(tmp_path)
    command = _config()["hooks"]["UserPromptSubmit"][0]["hooks"][0][
        "commandWindows"
    ]

    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env=env,
        shell=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"continue": True, "suppressOutput": True}
    entry = json.loads(
        (tmp_path / "session.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert entry["tool"] == "codex"
    assert entry["prompt"] == "Windows Codex prompt"


@pytest.mark.skipif(os.name != "nt", reason="Windows hook installer test")
def test_windows_hook_installer_writes_executable_shebang_without_bom(tmp_path):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_ROOT / "scripts" / "setup_hooks.ps1"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    hook_bytes = (tmp_path / ".git" / "hooks" / "pre-push").read_bytes()
    assert hook_bytes.startswith(b"#!/usr/bin/env bash\n")
    assert not hook_bytes.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in hook_bytes
