"""User settings and source-checkout defaults, independent of the Tk UI."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys


def source_root() -> Path | None:
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "pyproject.toml").is_file() and (candidate / "src" / "git_repo_manager").is_dir():
        return candidate
    return None


def default_scan_root() -> Path:
    checkout = source_root()
    return checkout.parent if checkout is not None else Path.cwd()


def default_state_file() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return base / "GitRepoManager" / "state.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "GitRepoManager" / "state.json"
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "git-repo-manager" / "state.json"


def legacy_state_file() -> Path | None:
    checkout = source_root()
    return checkout / ".git-repo-manager.json" if checkout is not None else None


def load_state(path: Path, *, fallback: Path | None = None) -> dict:
    """Read known settings only; use the old portable file if no new state exists."""
    try:
        source = path if path.exists() or fallback is None else fallback
        state = json.loads(source.read_text(encoding="utf-8-sig"))
        if not isinstance(state, dict):
            return {}
        result = {}
        for key in ("root", "geometry"):
            if isinstance(state.get(key), str):
                result[key] = state[key]
        if isinstance(state.get("checked"), list):
            result["checked"] = [item for item in state["checked"] if isinstance(item, str)]
        result["skip_dependencies"] = state.get("skip_dependencies") is True
        return result
    except (OSError, ValueError):
        return {}


def save_state(path: Path, state: dict) -> None:
    """Replace a complete settings file, including on a fresh installation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
