"""Saved settings, restored by `evoctl apply` after PipeWire restarts.

One JSON object in $XDG_STATE_HOME/evo8/state.json. On first use it takes over
the file the wh01s17 shell scripts kept (wh01s17/mezcla-gains.json), so the
gains and sync delay already tuned carry over.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return Path(base) / "evo8"


def runtime_dir() -> Path:
    return Path(os.environ.get("XDG_RUNTIME_DIR") or "/tmp")


STATE = state_dir() / "state.json"
LEGACY = state_dir().parent / "wh01s17" / "mezcla-gains.json"


def load() -> dict:
    for path in (STATE, LEGACY):
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return data
    return {}


def save(key: str, value) -> None:
    data = load()
    data[key] = value
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, separators=(",", ":")))
    tmp.replace(STATE)
