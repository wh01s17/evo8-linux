"""Measure the Mezcla sync delay by playing along to a click.

Whoever plays along to music on Compartido hears it after the output latency,
and their instrument reaches the Mezcla after the input latency, so in the sum
the instrument trails the music by both. This measures that gap the only way
that includes the converters, USB and the player: a click track goes out
through Compartido exactly as the music does, the player hits a short note on
every click, and the onsets are compared in one 4-channel recording of
mezcla.suma (inputs 1-2 on FL/FR, Compartido on RL/RR), taken *before* the
sync delay so it measures the raw gap.
"""

from __future__ import annotations

import array
import math
import signal
import statistics
import subprocess
import tempfile
import time
import wave
from dataclasses import dataclass
from pathlib import Path

from . import mix, monitor, pw

RATE = 48000
BPM = 100
BEATS = 20          # the first 4 count in and are not measured
LEAD_IN = 1.0       # seconds of silence before the first click
COUNT_IN = 4
MIN_HITS = 6


class CalibrationError(RuntimeError):
    pass


@dataclass
class Result:
    clicks: int
    hits: int
    median_ms: int
    spread_ms: float | None

    @property
    def summary(self) -> str:
        spread = f" · dispersión {self.spread_ms:g} ms" if self.spread_ms is not None else ""
        return f"Golpes medidos: {self.hits} de {self.clicks} · retardo mediano {self.median_ms} ms{spread}"


def click_track(path: Path, bpm: float = BPM, beats: int = BEATS, lead: float = LEAD_IN) -> None:
    period = 60.0 / bpm
    total = int(RATE * (lead + beats * period + 1.0))
    data = array.array("h", [0] * total * 2)
    length = int(RATE * 0.015)
    for b in range(beats):
        start = int(RATE * (lead + b * period))
        freq = 2000.0 if b % 4 == 0 else 1500.0
        for i in range(length):
            v = int(22000 * math.sin(2 * math.pi * freq * i / RATE) * (1 - i / length))
            data[2 * (start + i)] = v
            data[2 * (start + i) + 1] = v
    with wave.open(str(path), "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())


def _envelope(data: array.array, channels: int, picked: list[int], win: int) -> list[int]:
    frames = len(data) // channels
    env = []
    for f in range(0, frames - win, win):
        m = 0
        for c in picked:
            seg = data[f * channels + c:(f + win) * channels + c:channels]
            if seg:
                m = max(m, max(abs(x) for x in seg))
        env.append(m)
    return env


def _onsets(env: list[int], refractory: int) -> list[int]:
    if not env:
        return []
    floor = statistics.median(env)
    top = max(env)
    if top <= floor * 4 or top < 300:
        return []
    thr = floor + 0.3 * (top - floor)
    out, last = [], -10 ** 9
    for i in range(1, len(env)):
        if env[i] >= thr and env[i - 1] < thr and i - last > refractory:
            out.append(i)
            last = i
    return out


def analyse(recording: Path, bpm: float = BPM) -> Result:
    """Onsets on 1 ms envelope frames: clicks on RL/RR, hits on FL/FR."""
    with wave.open(str(recording)) as w:
        rate, ch = w.getframerate(), w.getnchannels()
        data = array.array("h", w.readframes(w.getnframes()))
    win = rate // 1000
    clicks = _onsets(_envelope(data, ch, [2, 3], win), int(60000 / bpm * 0.6))[COUNT_IN:]
    hits = _onsets(_envelope(data, ch, [0, 1], win), 120)
    lags = []
    for c in clicks:
        near = [h - c for h in hits if -60 <= h - c <= 400]
        if near:
            lags.append(min(near, key=abs) if min(near) < 0 else near[0])
    if len(clicks) < MIN_HITS:
        raise CalibrationError("No se detectaron los clicks en Compartido (¿la escucha está en silencio?).")
    if len(lags) < MIN_HITS:
        raise CalibrationError(f"Solo se detectaron {len(lags)} golpes sobre {len(clicks)} clicks. "
                               "Toca más fuerte y seco, uno por click, y repite.")
    spread = None
    if len(lags) >= 4:
        q = statistics.quantiles(lags, n=4)
        spread = q[2] - q[0]
    return Result(len(clicks), len(lags), max(0, round(statistics.median(lags))), spread)


def run(apply: bool = False, on_progress=print) -> Result:
    if pw.node_id(mix.SUM_NODE) is None:
        raise CalibrationError("No se encontró la Mezcla (mezcla.suma).")
    if pw.node_id(mix.SHARED_SINK) is None:
        raise CalibrationError("No se encontró Compartido.")

    # The click must reach the ears the way the music does: through the
    # Compartido listening path, so the full monitor (which mutes that path) is
    # turned off for the measurement and restored afterwards.
    was_on = monitor.status() == "on"
    if was_on:
        monitor.turn_off()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            click, rec = Path(tmp) / "click.wav", Path(tmp) / "rec.wav"
            click_track(click)
            on_progress("Calibrando: toca un golpe corto y seco en cada click (los primeros 4 son de cuenta).")
            recorder = subprocess.Popen(
                ["pw-record", "--target", mix.SUM_NODE, "-P", "stream.capture.sink=true",
                 "--channels", "4", "--format", "s16", str(rec)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.3)
            subprocess.run(["pw-play", "--target", mix.SHARED_SINK, str(click)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.5)
            recorder.send_signal(signal.SIGINT)
            recorder.wait(timeout=5)
            result = analyse(rec)
    finally:
        if was_on:
            monitor.turn_on()
    if apply:
        mix.set_delay_ms(result.median_ms)
    return result
