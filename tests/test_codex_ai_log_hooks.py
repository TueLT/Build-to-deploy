import json
import os
from pathlib import Path
import subprocess

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
