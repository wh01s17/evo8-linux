"""Peak meters: each reader is one `pw-record --raw` of float samples on stdout.

Readers run in threads and keep only the latest peak per channel; the window
polls `levels()` on a timer, so audio never waits for the UI and vice versa.
The capture streams are passive (they never keep a device awake) and carry an
`evo8.` node name so the app list hides them.
"""

from __future__ import annotations

import array
import subprocess
import threading

RATE = 48000
CHUNK_FRAMES = 480          # 10 ms


class Reader:
    def __init__(self, name: str, target: str, channels: int, capture_sink: bool):
        self.name, self.target, self.channels = name, target, channels
        self.capture_sink = capture_sink
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
        props = (f"{{ node.name = evo8.meter.{self.name} node.passive = true "
                 f"stream.capture.sink = {'true' if self.capture_sink else 'false'} }}")
        return ["pw-record", "--raw", "--target", self.target, "--channels", str(self.channels),
                "--rate", str(RATE), "--format", "f32", "--latency", "20ms", "-P", props, "-"]

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
    def __init__(self, specs: list[tuple[str, str, int, bool]]):
        self.readers = {name: Reader(name, target, ch, cap) for name, target, ch, cap in specs}

    def start(self) -> None:
        for r in self.readers.values():
            r.start()

    def stop(self) -> None:
        for r in self.readers.values():
            r.stop()

    def levels(self) -> dict[str, list[float]]:
        return {name: r.take() for name, r in self.readers.items()}
