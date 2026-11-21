"""Controls the kernel driver (snd-usb-audio) already exposes for the EVO 8.

"Mic Playback Volume" is the analog preamp gain per input (the same one the
interface's knob turns), raw 0..116 = -8..+50 dB in 0.5 dB steps. The EVO does
not keep these across a power cycle (it comes back at -8 dB), so every change
is saved and `restore_preamp()` puts them back.
"""

from __future__ import annotations

import os
import re

from . import pw, state

CARD = os.environ.get("EVO8_ALSA_CARD", "EVO8")
PREAMP_CONTROL = "Mic Playback Volume"


class AlsaError(RuntimeError):
    pass


def _control(name: str) -> dict:
    info = pw.run("amixer", "-c", CARD, "cget", f"name={name}")
    if not info:
        raise AlsaError(f"control '{name}' not found on card {CARD}")
    rng = re.search(r"min=(-?\d+),max=(-?\d+)", info)
    db = re.search(r"dBminmax-min=(-?[\d.]+)dB,max=(-?[\d.]+)dB", info)
    vals = re.search(r": values=([\d,-]+)", info)
    if not (rng and db and vals):
        raise AlsaError(f"could not parse '{name}' on card {CARD}")
    return {
        "raw_min": int(rng[1]), "raw_max": int(rng[2]),
        "db_min": float(db[1]), "db_max": float(db[2]),
        "values": [int(v) for v in vals[1].split(",")],
    }


def preamp() -> dict:
    """{"min", "max", "step", "gains"} in dB."""
    c = _control(PREAMP_CONTROL)
    step = (c["db_max"] - c["db_min"]) / (c["raw_max"] - c["raw_min"])
    gains = [round(c["db_min"] + (v - c["raw_min"]) * step, 2) for v in c["values"]]
    return {"min": c["db_min"], "max": c["db_max"], "step": round(step, 4), "gains": gains}


def set_preamp(n: int, db: float) -> None:
    c = _control(PREAMP_CONTROL)
    if not 1 <= n <= len(c["values"]):
        raise AlsaError(f"input must be 1-{len(c['values'])}")
    db = min(max(db, c["db_min"]), c["db_max"])
    raw = round(c["raw_min"] + (db - c["db_min"]) / (c["db_max"] - c["db_min"]) * (c["raw_max"] - c["raw_min"]))
    values = list(c["values"])
    values[n - 1] = raw
    pw.run("amixer", "-c", CARD, "cset", f"name={PREAMP_CONTROL}", ",".join(map(str, values)), check=True)
    applied = c["db_min"] + (raw - c["raw_min"]) * (c["db_max"] - c["db_min"]) / (c["raw_max"] - c["raw_min"])
    saved = state.load().get("preamp") or {}
    saved[str(n)] = round(applied, 2)
    state.save("preamp", saved)


def restore_preamp() -> None:
    saved = state.load().get("preamp") or {}
    try:
        c = _control(PREAMP_CONTROL)
    except AlsaError:
        return
    values = list(c["values"])
    for key, db in saved.items():
        n = int(key)
        if 1 <= n <= len(values) and isinstance(db, (int, float)):
            db = min(max(db, c["db_min"]), c["db_max"])
            values[n - 1] = round(c["raw_min"] + (db - c["db_min"]) / (c["db_max"] - c["db_min"])
                                  * (c["raw_max"] - c["raw_min"]))
    if values != c["values"]:
        pw.run("amixer", "-c", CARD, "cset", f"name={PREAMP_CONTROL}", ",".join(map(str, values)))
