import json
from pathlib import Path


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
