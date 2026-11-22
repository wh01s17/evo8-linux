"""Hear the Mezcla, or single interface inputs, on the selected output.

The full monitor links the Mezcla source straight onto the selected output's
first two channels (FL/FR, or AUX0/AUX1 on a Pro Audio interface): a direct
port link adds no buffering of its own, so the delay is the graph quantum,
which is lowered while monitoring (not on a Bluetooth output, which cannot
take it). The Compartido listening loopback is muted
meanwhile, because the mix already carries it and it would be heard twice.

Each interface input can also be heard on its own: its capture port is linked
onto the same two output channels, without the Compartido music, which keeps
playing through its listening loopback. The inputs wanted on are kept in a
runtime file and the links are kept in step with it by every call (`status`
included), so they come back after PipeWire restarts and follow the selected
output. While the full monitor is on they are lifted, as the Mezcla already
carries inputs 1-2.

Links are made with pw-link, so they live in PipeWire rather than in this
process; they last until turned off or PipeWire restarts.
"""

from __future__ import annotations

import os

from . import mix, pw, state

SOURCE_PORT = f"{mix.MIX_SOURCE}:capture_MONO"
QUANTUM = int(os.environ.get("EVO8_MONITOR_QUANTUM", "128"))
INPUT_SOURCE = os.environ.get("EVO8_INPUT_SOURCE", "alsa_input.usb-Audient_EVO8-00.pro-input-0")

# Present while the full monitor is on. If its links vanish without `off`
# (PipeWire restarted, the output was recreated), `status` finds the mark and
# undoes the rest: the muted listening stream and the forced quantum.
MARKER = state.runtime_dir() / "evo8-monitor"
INPUTS_FILE = state.runtime_dir() / "evo8-monitor-inputs"

# The wh01s17 shell scripts kept the same state under other names; adopt it.
_LEGACY_MARKER = state.runtime_dir() / "wh01s17-mix-monitor"
_LEGACY_INPUTS = state.runtime_dir() / "wh01s17-mix-monitor-inputs"
for _old, _new in ((_LEGACY_MARKER, MARKER), (_LEGACY_INPUTS, INPUTS_FILE)):
    if _old.exists() and not _new.exists():
        try:
            _old.replace(_new)
        except OSError:
            pass


class MonitorError(RuntimeError):
    pass


# ---- full monitor ----

def available() -> bool:
    return SOURCE_PORT in pw.output_ports()


def _playback_links(port: str) -> list[str]:
    # Real sinks have playback_* inputs; Meet's own capture stream has input_*
    # ports and is left alone.
    return [t for t in pw.links_from(port) if ":playback_" in t]


def is_on() -> bool:
    return bool(_playback_links(SOURCE_PORT))


def _listen_inputs() -> list[pw.SinkInput]:
    return [s for s in pw.sink_inputs() if s.node_name == mix.LISTEN_NODE]


def _listen_muted() -> bool:
    return any(s.mute for s in _listen_inputs())


def _set_listen_mute(muted: bool) -> None:
    for s in _listen_inputs():
        pw.run("pactl", "set-sink-input-mute", str(s.index), "1" if muted else "0")


def status() -> str:
    """"on", "off" or "unavailable" (no Mezcla); heals stale state on the way."""
    if not available():
        result = "unavailable"
    elif is_on():
        result = "on"
    else:
        # Off, but left in a monitoring state by links that vanished on their own.
        if MARKER.exists() or _listen_muted():
            _undo_side_effects()
        result = "off"
    if INPUTS_FILE.exists():
        sync_inputs()
    # Also while the full monitor is on: the selected output may have become a
    # Bluetooth one, which must not keep the low quantum.
    if result == "on" or INPUTS_FILE.exists():
        update_quantum()
    return result


def _sync_port(port: str, want: set[str]) -> None:
    """Make `port`'s playback links exactly `want`, touching only what differs.

    Re-linking what is already linked is not harmless: every link change makes
    the selected output's node change, and a client that re-targets the monitor
    on such changes (follow) would loop, glitching the audio each time."""
    have = set(_playback_links(port))
    for t in have - want:
        pw.unlink(port, t)
    for t in want - have:
        pw.link(port, t)


def turn_on() -> None:
    if not available():
        raise MonitorError("unavailable")
    ports = pw.sink_ports()
    if not ports:
        raise MonitorError("the selected output has no playback ports")
    _sync_port(SOURCE_PORT, set(ports))
    if not all(s.mute for s in _listen_inputs()):
        _set_listen_mute(True)
    MARKER.touch()
    sync_inputs()
    update_quantum()


def _undo_side_effects() -> None:
    if _listen_muted():
        _set_listen_mute(False)
    MARKER.unlink(missing_ok=True)
    sync_inputs()
    update_quantum()


def turn_off() -> None:
    _sync_port(SOURCE_PORT, set())
    _undo_side_effects()


def toggle() -> None:
    turn_off() if is_on() else turn_on()


def follow() -> None:
    """Re-target whatever is monitored onto the selected output."""
    if is_on():
        turn_on()
    elif MARKER.exists() or _listen_muted():
        _undo_side_effects()
    else:
        sync_inputs()
        update_quantum()


# ---- single inputs ----

def interface_ports() -> list[str]:
    """Capture ports of the interface, in input order (AUX0 = input 1)."""
    prefix = f"{INPUT_SOURCE}:capture_"
    ports = [p for p in pw.output_ports() if p.startswith(prefix)]

    def order(p: str):
        tail = p[len(prefix):]
        digits = "".join(c for c in tail if c.isdigit())
        return (tail.rstrip("0123456789"), int(digits) if digits else 0)

    return sorted(ports, key=order)


def wanted_inputs() -> set[int]:
    try:
        text = INPUTS_FILE.read_text()
    except OSError:
        return set()
    return {int(l) for l in text.split() if l.isdigit()}


def _write_wanted(wanted: set[int]) -> None:
    if not wanted:
        INPUTS_FILE.unlink(missing_ok=True)
        return
    tmp = INPUTS_FILE.with_suffix(".tmp")
    tmp.write_text("".join(f"{n}\n" for n in sorted(wanted)))
    tmp.replace(INPUTS_FILE)


def sync_inputs() -> None:
    """Bring the input links in line with the wanted set: only missing links are
    made and stale ones removed, so a call that changes nothing makes no sound."""
    ports = interface_ports()
    if not ports:
        return
    targets = [] if is_on() else pw.sink_ports()
    wanted = wanted_inputs()
    for i, port in enumerate(ports, start=1):
        _sync_port(port, set(targets) if i in wanted else set())


def _any_input_linked() -> bool:
    return any(_playback_links(p) for p in interface_ports())


def low_quantum_ok(sink: str | None = None) -> bool:
    """Whether the selected output can take the low quantum.

    A forced quantum is global: every stream on the system runs at it, not only
    the monitor. A Bluetooth output needs far bigger buffers (WirePlumber gives
    it ~1024), so forcing 128 on one glitches everything that plays, and the
    radio link adds more delay than the quantum would save anyway."""
    sink = pw.default_sink() if sink is None else sink
    return not sink.startswith("bluez_output.")


def update_quantum() -> None:
    """Hold the low quantum while anything is monitored on an output that can
    take it. Only our own value is ever undone, never one something else forced."""
    current = pw.force_quantum()
    if (is_on() or _any_input_linked()) and low_quantum_ok():
        if current == 0:
            pw.set_force_quantum(QUANTUM)
    elif current == QUANTUM:
        pw.set_force_quantum(0)


def inputs() -> list[int]:
    """One 0/1 per interface input: whether it is monitored."""
    wanted = wanted_inputs()
    return [1 if i in wanted else 0 for i in range(1, len(interface_ports()) + 1)]


def set_input(n: int, on: bool | None) -> None:
    """Turn input n on, off, or toggle it (on=None)."""
    count = len(interface_ports())
    if not 1 <= n <= count:
        raise MonitorError(f"no input {n} on {INPUT_SOURCE}")
    wanted = wanted_inputs()
    if on is None:
        on = n not in wanted
    (wanted.add if on else wanted.discard)(n)
    _write_wanted(wanted)
    sync_inputs()
    update_quantum()
