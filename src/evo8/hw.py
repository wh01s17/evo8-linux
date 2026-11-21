"""EVO 8 hardware settings over USB (see docs/protocolo-usb.md).

Confirmed on the device:
  * Routing matrix = unit 51, selector 6: one byte per capture channel (0-5)
    naming its source. Sources 0-5 are the analog inputs, 6-11 the computer's
    playback channels 1-6. Factory routing: inputs 1-4 on capture 1-4 and
    playback 5-6 ("loop-back") on capture 5-6.
  * Mixer unit 60, selector 1 (the hardware monitor mix): control number
    input * 4 + output, s16 in 1/256 dB, -128 dB = off. Readable and writable.
  * Input control unit 58 (4-byte values, channel = input - 1): selector 0 =
    phantom 48 V (verified against the front-panel button), 1 = preamp gain in
    1/256 dB (same as ALSA), 2 = mute (as EVO Control uses it).

Only selectors EVO Control itself uses may be touched: a GET to one it does
not use (unit 59, selector 3) went unanswered and hung the firmware until the
EVO was unplugged.

Each call is one usb.session(), which drops the audio card for a moment.
"""

from __future__ import annotations

from . import usb

ROUTE_UNIT = 51
ROUTE_SELECTOR = 6
LOOPBACK_CHANNELS = (4, 5)          # capture channels 5-6

MIXER_UNIT = 60
MIXER_SELECTOR = 1
MIXER_INPUTS = 10                   # inputs 1-4, then playback 1-6
MIXER_OUTPUTS = 4                   # outputs 1-4
MIXER_OFF_DB = -128.0

# Loop-back sources by name: (left, right) routing-matrix source indices.
LOOPBACK_SOURCES = {
    "loopback": (10, 11),           # playback 5-6, the factory setting
    "pc12": (6, 7),                 # whatever plays on outputs 1-2
    "pc34": (8, 9),
    "in12": (0, 1),
    "in34": (2, 3),
}


INPUT_UNIT = 58
INPUT_PHANTOM = 0
INPUT_MUTE = 2
INPUTS = 4


class HwError(RuntimeError):
    pass


def loopback_get() -> dict:
    with usb.session() as s:
        pair = tuple(s.get(ROUTE_UNIT, ROUTE_SELECTOR, c, 1)[0] for c in LOOPBACK_CHANNELS)
    name = next((n for n, p in LOOPBACK_SOURCES.items() if p == pair), None)
    return {"source": name, "raw": list(pair)}


def loopback_set(source: str) -> None:
    if source not in LOOPBACK_SOURCES:
        raise HwError(f"fuente desconocida: {source} (opciones: {', '.join(LOOPBACK_SOURCES)})")
    apply([], source)


def _mcn(inp: int, out: int) -> int:
    if not (0 <= inp < MIXER_INPUTS and 0 <= out < MIXER_OUTPUTS):
        raise HwError(f"entrada 1-{MIXER_INPUTS} y salida 1-{MIXER_OUTPUTS}")
    return inp * MIXER_OUTPUTS + out


def mixer_get() -> list[list[float]]:
    """Gain in dB of every input (rows) into every output (columns)."""
    with usb.session() as s:
        return [[s.get_s16(MIXER_UNIT, MIXER_SELECTOR, _mcn(i, o)) / 256 for o in range(MIXER_OUTPUTS)]
                for i in range(MIXER_INPUTS)]


def mixer_set(changes: list[tuple[int, int, float]]) -> None:
    """Apply (input, output, dB) changes, 0-based, in one session."""
    apply(changes, None)


def _flag(s, selector: int, inp: int) -> bool:
    return int.from_bytes(s.get(INPUT_UNIT, selector, inp, 4), "little", signed=True) != 0


def _set_flag(s, selector: int, inp: int, on: bool) -> None:
    s.set(INPUT_UNIT, selector, inp, (1 if on else 0).to_bytes(4, "little"))


def read_all() -> dict:
    """Everything in one session: {mix, loopback, loopbackRaw, phantom, mute}."""
    with usb.session() as s:
        matrix = [[s.get_s16(MIXER_UNIT, MIXER_SELECTOR, _mcn(i, o)) / 256 for o in range(MIXER_OUTPUTS)]
                  for i in range(MIXER_INPUTS)]
        pair = tuple(s.get(ROUTE_UNIT, ROUTE_SELECTOR, c, 1)[0] for c in LOOPBACK_CHANNELS)
        phantom = [_flag(s, INPUT_PHANTOM, i) for i in range(INPUTS)]
        mute = [_flag(s, INPUT_MUTE, i) for i in range(INPUTS)]
    name = next((n for n, p in LOOPBACK_SOURCES.items() if p == pair), None)
    return {"mix": matrix, "loopback": name, "loopbackRaw": list(pair), "phantom": phantom, "mute": mute}


def inputs_get() -> dict:
    with usb.session() as s:
        return {"phantom": [_flag(s, INPUT_PHANTOM, i) for i in range(INPUTS)],
                "mute": [_flag(s, INPUT_MUTE, i) for i in range(INPUTS)]}


def apply(changes: list[tuple[int, int, float]], loopback: str | None,
          phantom: dict[int, bool] | None = None, mute: dict[int, bool] | None = None) -> None:
    """Mixer changes (input, output, dB; 0-based), an optional loop-back
    source and per-input phantom/mute flags (0-based input -> on), all in one
    session so the audio drops only once."""
    if loopback is not None and loopback not in LOOPBACK_SOURCES:
        raise HwError(f"fuente desconocida: {loopback}")
    for flags in (phantom or {}, mute or {}):
        if any(not 0 <= i < INPUTS for i in flags):
            raise HwError(f"entrada 1-{INPUTS}")
    with usb.session() as s:
        for inp, on in (phantom or {}).items():
            _set_flag(s, INPUT_PHANTOM, inp, on)
        for inp, on in (mute or {}).items():
            _set_flag(s, INPUT_MUTE, inp, on)
        for inp, out, db in changes:
            db = max(MIXER_OFF_DB, min(0.0, db))
            s.set_s16(MIXER_UNIT, MIXER_SELECTOR, _mcn(inp, out), round(db * 256))
        if loopback is not None:
            for ch, src in zip(LOOPBACK_CHANNELS, LOOPBACK_SOURCES[loopback]):
                s.set(ROUTE_UNIT, ROUTE_SELECTOR, ch, bytes([src]))


def restore(saved: dict) -> bool:
    """Put back a saved {mix, loopback} (from state.json "hw") in one session.
    Phantom power is never restored: sending 48 V to whatever is plugged in
    now is not safe to assume. Returns whether anything was sent."""
    matrix = saved.get("mix")
    changes = []
    if isinstance(matrix, list) and len(matrix) == MIXER_INPUTS:
        changes = [(i, o, float(matrix[i][o])) for i in range(MIXER_INPUTS) for o in range(MIXER_OUTPUTS)]
    loopback = saved.get("loopback") if saved.get("loopback") in LOOPBACK_SOURCES else None
    if not changes and loopback is None:
        return False
    apply(changes, loopback)
    return True
