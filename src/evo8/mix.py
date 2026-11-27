"""The Mezcla virtual microphone (evo8/data/pipewire/evo8-mezcla.conf).

It is optional and runs as a PipeWire client of its own, the user unit
evo8-mezcla.service: enabled means on (it starts with PipeWire), disabled
means none of its nodes exist. Switching it touches no other audio.

mezcla.suma is a filter-chain summing six channels into Mezcla:
  mix:Gain 1 = interface input 1, mix:Gain 2 = input 2,
  mix:Gain 3/4 = Compartido L/R, after compL/compR, which delay Compartido so
  it lines up with an instrument played along to it,
  mix:Gain 5 = input 3, mix:Gain 6 = input 4 (last, so 1-4 kept their meaning).
All four inputs are always wired. Which of them are "in the Mezcla" is a
saved list; the rest run at gain 0, so adding or removing one is a gain
change: instant, and the Mezcla never goes away while apps use it.
These are live Props params, but PipeWire resets them to the config's values
whenever it restarts, so every change is also saved and `apply` puts the saved
values back. The Compartido listening level (mezcla.compartido.escucha) is
saved too: that stream opts out of WirePlumber's own restore so a mute the
monitor left behind never comes back.
"""

from __future__ import annotations

import time

from . import pw, state

SUM_NODE = "mezcla.suma"
LISTEN_NODE = "mezcla.compartido.escucha"
SHARED_SINK = "Compartido"
MIX_SOURCE = "Mezcla"
# Standard level of each mix:Gain (an input's when it is in the Mezcla).
DEFAULT_GAINS = [1.0, 1.0, 0.5, 0.5, 1.0, 1.0]
GAIN_COUNT = len(DEFAULT_GAINS)
INPUTS = 4
DEFAULT_INPUTS = [1, 2]
MAX_GAIN = 4.0
MAX_DELAY_MS = 500
SERVICE = "evo8-mezcla.service"
LEGACY_TEXT = ("la Mezcla de una instalación anterior sigue cargada dentro de PipeWire y no se "
               "puede apagar: si instalaste con pipx corre «evoctl setup»; después reinicia "
               "PipeWire (systemctl --user restart pipewire pipewire-pulse wireplumber)")


class MixError(RuntimeError):
    pass


def _sum_id() -> int:
    nid = pw.node_id(SUM_NODE)
    if nid is None:
        raise MixError("la Mezcla está apagada (evoctl mezcla on)"
                       if service_status() == "off" else f"node {SUM_NODE} not found")
    return nid


# ---- on / off ----

def _unit() -> dict[str, str]:
    out = pw.run("systemctl", "--user", "show", SERVICE, "-p", "LoadState", "-p", "ActiveState",
                 timeout=3)
    return dict(line.split("=", 1) for line in out.splitlines() if "=" in line)


def service_status() -> str:
    """"on", "off", "failed", "missing" (no unit installed) or "legacy" (the
    Mezcla runs inside PipeWire from an old drop-in, so it cannot be switched)."""
    unit = _unit()
    if unit.get("ActiveState") in ("active", "activating", "reloading"):
        return "on"
    if pw.node_id(SUM_NODE) is not None:
        return "legacy"
    if unit.get("LoadState") != "loaded":
        return "missing"
    return "failed" if unit.get("ActiveState") == "failed" else "off"


def set_enabled(on: bool) -> None:
    """Turn the Mezcla on (and keep it on across restarts) or off."""
    status = service_status()
    if status == "legacy":
        raise MixError(LEGACY_TEXT)
    if status == "missing":
        raise MixError(f"falta {SERVICE}: corre «evoctl setup»")
    if not on:
        from . import monitor
        if monitor.is_on():         # undo its mute and quantum before the nodes go
            monitor.turn_off()
    # The unit's ExecStartPost restores the saved values before this returns.
    pw.run("systemctl", "--user", "enable" if on else "disable", "--now", SERVICE,
           timeout=15, check=True)


def wait_ready(timeout: float = 10) -> bool:
    """Wait for the sum node to appear (the unit was just started)."""
    end = time.monotonic() + timeout
    while pw.node_id(SUM_NODE) is None:
        if time.monotonic() > end:
            return False
        time.sleep(0.2)
    return True


def _graph_params(nid: int) -> dict[str, float]:
    """The filter-graph's own Props entry (the one carrying "mix:Gain 1")."""
    for entry in pw.props_params(nid):
        params = entry.get("params")
        if isinstance(params, list) and "mix:Gain 1" in params:
            return {params[i]: params[i + 1] for i in range(0, len(params) - 1, 2)}
    return {}


def gains() -> list[float]:
    """mix:Gain 1-6: inputs 1-2, Compartido L/R, inputs 3-4."""
    p = _graph_params(_sum_id())
    return [float(p.get(f"mix:Gain {n}", DEFAULT_GAINS[n - 1])) for n in range(1, GAIN_COUNT + 1)]


def set_gain(n: int, gain: float) -> None:
    if not 1 <= n <= GAIN_COUNT:
        raise MixError(f"gain number must be 1-{GAIN_COUNT}")
    if not 0 <= gain <= MAX_GAIN:
        raise MixError(f"gain must be between 0 and {MAX_GAIN:g}")
    pw.set_graph_param(_sum_id(), f"mix:Gain {n}", gain)
    state.save(str(n), gain)


# ---- which inputs are in the Mezcla ----

def gain_number(inp: int) -> int:
    """The mix:Gain that carries interface input `inp` (1-4)."""
    return inp if inp <= 2 else inp + 2


def inputs() -> list[int]:
    saved = state.load().get("inputs")
    if not isinstance(saved, list):
        return list(DEFAULT_INPUTS)
    return sorted({n for n in saved if isinstance(n, int) and 1 <= n <= INPUTS})


def _input_gain(inp: int) -> float:
    """The level an input comes back at: its saved gain, else the standard."""
    g = state.load().get(str(gain_number(inp)))
    if isinstance(g, (int, float)) and 0 < g <= MAX_GAIN:
        return float(g)
    return DEFAULT_GAINS[gain_number(inp) - 1]


def set_input(inp: int, on: bool) -> None:
    """Add an interface input to the Mezcla, or take it out (gain 0; its
    level is kept for when it comes back). Saved even while the Mezcla is
    off; applied live when it is on."""
    if not 1 <= inp <= INPUTS:
        raise MixError(f"input must be 1-{INPUTS}")
    current = inputs()
    wanted = sorted(set(current) | {inp}) if on else [n for n in current if n != inp]
    state.save("inputs", wanted)
    nid = pw.node_id(SUM_NODE)
    if nid is not None:
        pw.set_graph_param(nid, f"mix:Gain {gain_number(inp)}", _input_gain(inp) if on else 0.0)


def delay_ms() -> int:
    p = _graph_params(_sum_id())
    if "compL:Delay (s)" not in p:
        raise MixError(f"no sync delay in {SUM_NODE} (evo8-mezcla.conf without compL/compR?)")
    return round(float(p["compL:Delay (s)"]) * 1000)


def _set_delay_live(nid: int, ms: float) -> None:
    s = ms / 1000
    pw.set_graph_param(nid, "compL:Delay (s)", s)
    pw.set_graph_param(nid, "compR:Delay (s)", s)


def set_delay_ms(ms: float) -> None:
    if not 0 <= ms <= MAX_DELAY_MS:
        raise MixError(f"delay must be between 0 and {MAX_DELAY_MS} ms")
    _set_delay_live(_sum_id(), ms)
    state.save("delay_ms", ms)


def save_listen_level() -> None:
    nid = pw.node_id(LISTEN_NODE)
    if nid is None:
        raise MixError(f"node {LISTEN_NODE} not found")
    for entry in pw.props_params(nid):
        vols = entry.get("channelVolumes")
        if isinstance(vols, list) and vols:
            state.save("escucha", vols)
            return


def apply() -> None:
    """Restore everything saved."""
    saved = state.load()
    if not saved:
        return
    nid = pw.node_id(SUM_NODE)
    if nid is not None:
        members = inputs()
        for n in range(1, GAIN_COUNT + 1):
            g = saved.get(str(n))
            if isinstance(g, (int, float)) and 0 <= g <= MAX_GAIN:
                pw.set_graph_param(nid, f"mix:Gain {n}", float(g))
        for inp in range(1, INPUTS + 1):      # membership wins over a saved level
            on = inp in members
            if not on or str(gain_number(inp)) not in saved:
                pw.set_graph_param(nid, f"mix:Gain {gain_number(inp)}", _input_gain(inp) if on else 0.0)
        ms = saved.get("delay_ms")
        if isinstance(ms, (int, float)) and 0 <= ms <= MAX_DELAY_MS:
            _set_delay_live(nid, float(ms))
    lid = pw.node_id(LISTEN_NODE)
    vols = saved.get("escucha")
    if lid is not None and isinstance(vols, list) and vols:
        pw.set_props(lid, "{ channelVolumes = [ " + " ".join(f"{float(v):.6g}" for v in vols) + " ] }")
