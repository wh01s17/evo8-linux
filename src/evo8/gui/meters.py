"""Peak meters: each reader is one `pw-record --raw` of float samples on stdout.

Readers run in threads and keep only the latest peak per channel; the window
polls `levels()` on a timer, so audio never waits for the UI and vice versa.
The capture streams carry an `evo8.` node name so the app list hides them.
Those on the Mezcla are passive (they never keep it running) and never fall
back to another device while it is off. The interface's inputs are read
directly and not passively, so their meters move whenever the window is open,
like any mixer's; that reader may fall back, because WirePlumber drops a
non-falling-back stream on an ALSA source while it reconfigures.
"""

from __future__ import annotations

import array
import subprocess
import threading

RATE = 48000
CHUNK_FRAMES = 480          # 10 ms
# A sample at or above this is clipping: 0 dBFS within float rounding
# (-0.01 dBFS). Float paths (a source volume above 100 %, the Mezcla's
# gains) can go past 1.0, which clips wherever the audio becomes integers.
CLIP_PEAK = 0.999
# A clip light stays on this long after the last clipping sample, so a single
# peak is still seen; then it goes out by itself.
CLIP_HOLD_S = 2.0


def clip_lights(until: dict[str, list[float]], levels: dict[str, list[float]], now: float,
                hold: float = CLIP_HOLD_S) -> tuple[dict[str, list[float]], dict[str, list[bool]]]:
    """One read of peaks -> (until, lit). `until` holds, per meter and
    channel, the time its light stays on to; a channel reaching CLIP_PEAK
    pushes it to now + hold."""
    new = {name: list(times) for name, times in until.items()}
    for name, peaks in levels.items():
        times = new.get(name) or []
        times += [0.0] * (len(peaks) - len(times))
        for i, p in enumerate(peaks):
            if p >= CLIP_PEAK:
                times[i] = now + hold
        new[name] = times
    return new, {name: [t > now for t in times] for name, times in new.items()}


class Reader:
    def __init__(self, name: str, target: str, channels: int, capture_sink: bool,
                 passive: bool = True, channel_map: str = ""):
        self.name, self.target, self.channels = name, target, channels
        self.capture_sink, self.passive, self.channel_map = capture_sink, passive, channel_map
        self.peaks = [0.0] * channels
        self._proc: subprocess.Popen | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()

    def take(self) -> list[float]:
        """Peaks since the last call."""
        p, self.peaks = self.peaks, [0.0] * self.channels
        return p

    def _cmd(self) -> list[str]:
        flag = lambda v: "true" if v else "false"   # noqa: E731
        props = (f"{{ node.name = evo8.meter.{self.name} node.passive = {flag(self.passive)} "
                 f"node.dont-fallback = {flag(self.passive)} stream.dont-remix = true "
                 f"stream.capture.sink = {flag(self.capture_sink)} }}")
        cmd = ["pw-record", "--raw", "--target", self.target, "--channels", str(self.channels),
               "--rate", str(RATE), "--format", "f32", "--latency", "20ms", "-P", props]
        if self.channel_map:
            cmd += ["--channel-map", self.channel_map]
        return cmd + ["-"]

    def _run(self) -> None:
        size = CHUNK_FRAMES * self.channels * 4
        while not self._stop.is_set():
            try:
                self._proc = subprocess.Popen(self._cmd(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            except OSError:
                return
            stream = self._proc.stdout
            while not self._stop.is_set():
                data = stream.read(size)
                if not data:
                    break
                samples = array.array("f")
                samples.frombytes(data[: len(data) - len(data) % (4 * self.channels)])
                peaks = self.peaks[:]
                for c in range(self.channels):
                    m = max((abs(x) for x in samples[c::self.channels]), default=0.0)
                    if m > peaks[c]:
                        peaks[c] = m
                self.peaks = peaks
            if self._proc.poll() is None:
                self._proc.terminate()
            # The target can vanish (PipeWire restart, card reprobe): retry.
            self._stop.wait(1.0)


class Meters:
    def __init__(self, specs: list[tuple]):
        """Each spec is Reader's arguments, name first."""
        self.readers = {spec[0]: Reader(*spec) for spec in specs}

    def start(self) -> None:
        for r in self.readers.values():
            r.start()

    def stop(self) -> None:
        for r in self.readers.values():
            r.stop()

    def levels(self) -> dict[str, list[float]]:
        return {name: r.take() for name, r in self.readers.items()}
