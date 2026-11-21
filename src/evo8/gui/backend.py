"""The object QML talks to (`mixer` in the QML context).

Everything slow (pactl, pw-cli, amixer, USB) runs on one worker thread, in
order, so the window never blocks and writes never overtake each other.

* Reads: a 1 s poll for PulseAudio state (devices, streams, volumes) and a 3 s
  poll for the rest (Mezcla gains, sync delay, preamps, monitor, profiles).
* Writes: sliders change the model at once (so the control does not jump) and
  queue a write; writes with the same key coalesce for 60 ms, so a drag costs a
  few commands, not one per pixel. Polled values for a key are ignored for a
  moment after writing it, until the system has caught up.
* Hardware (USB) settings drop the audio for a moment, so they are staged and
  applied together with one button.
"""

from __future__ import annotations

import queue
import threading
import time
import traceback

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from .. import about, alsa, calibrate, hw, mix, monitor, profiles, pw, state
from . import snapshot
from .meters import Meters

HOLD_S = 1.5
FAST_MS = 1000
SLOW_EVERY = 3
FLUSH_MS = 60
METER_MS = 50
METER_DECAY = 0.82


class Worker:
    """One thread running jobs in order; results come back through `done`."""

    def __init__(self, done: Signal):
        self._q: queue.Queue = queue.Queue()
        self._done = done
        threading.Thread(target=self._run, daemon=True).start()

    def submit(self, key: str, fn, *args) -> None:
        self._q.put((key, fn, args))

    def _run(self) -> None:
        while True:
            key, fn, args = self._q.get()
            try:
                result, error = fn(*args), None
            except Exception as e:  # reported to the window, never fatal
                result, error = None, str(e) or e.__class__.__name__
                traceback.print_exc()
            self._done.emit(key, result, error)


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _slow_read() -> dict:
    return {
        "gains": _safe(mix.gains),
        "delayMs": _safe(mix.delay_ms),
        "preamp": _safe(alsa.preamp),
        "monitor": _safe(monitor.status, "unavailable"),
        "inputMonitors": _safe(monitor.inputs, []),
        "cards": _safe(profiles.cards, []),
    }


class Backend(QObject):
    modelChanged = Signal()
    metersChanged = Signal()
    hwChanged = Signal()
    aboutChanged = Signal()
    _done = Signal(str, "QVariant", "QVariant")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model: dict = {
            "gains": None, "delayMs": None, "preamp": None, "monitor": "",
            "inputMonitors": [], "cards": [], "sink": None, "mezcla": None,
            "escucha": None, "streams": [], "message": "",
            "calibrating": False, "notice": "",
        }
        saved = state.load().get("hw") or {}
        self._hw: dict = {
            "mix": saved.get("mix"), "loopback": saved.get("loopback"),
            "readAt": saved.get("readAt"), "pending": {}, "pendingLoopback": None,
            "phantom": saved.get("phantom"), "mute": saved.get("mute"),
            "pendingPhantom": {}, "pendingMute": {},
            "busy": False, "message": "",
        }
        self._meters_view: dict = {}
        self._about: dict = {}
        self.refreshAbout()
        self._hold: dict[str, float] = {}
        self._before_mute: dict[int, float] = {}
        self._writes: dict[str, tuple] = {}
        self._inflight: set[str] = set()
        self._tick = 0

        self._done.connect(self._on_done)
        self._worker = Worker(self._done)

        self._flush_timer = QTimer(self, singleShot=True, interval=FLUSH_MS, timeout=self._flush)
        self._listen_save = QTimer(self, singleShot=True, interval=400,
                                   timeout=lambda: self._worker.submit("listen-save", mix.save_listen_level))
        self._poll_timer = QTimer(self, interval=FAST_MS, timeout=self._poll)
        self._poll_timer.start()
        self._poll()

        self._meters = Meters([
            ("suma", mix.SUM_NODE, 4, True),       # FL/FR inputs 1-2, RL/RR Compartido
            ("mezcla", mix.MIX_SOURCE, 1, False),
        ])
        self._meters.start()
        self._meter_timer = QTimer(self, interval=METER_MS, timeout=self._update_meters)
        self._meter_timer.start()

    # ---- properties ----
    def _get_model(self):
        return self._model

    def _get_meters(self):
        return self._meters_view

    def _get_hw(self):
        return self._hw

    model = Property("QVariant", _get_model, notify=modelChanged)
    meters = Property("QVariant", _get_meters, notify=metersChanged)
    hardware = Property("QVariant", _get_hw, notify=hwChanged)

    def _get_about(self):
        return self._about

    about = Property("QVariant", _get_about, notify=aboutChanged)

    # Files only (metadata, sysfs, config paths): cheap, no USB traffic.
    @Slot()
    def refreshAbout(self) -> None:
        import PySide6
        from PySide6.QtCore import qVersion
        self._about = about.info({"PySide6": PySide6.__version__, "Qt": qVersion()})
        self.aboutChanged.emit()

    @Slot()
    def copyAbout(self) -> None:
        from PySide6.QtGui import QGuiApplication
        QGuiApplication.clipboard().setText(about.report(self._about))

    def shutdown(self) -> None:
        self._meters.stop()

    # ---- polling ----
    def _poll(self) -> None:
        if "fast" not in self._inflight:
            self._inflight.add("fast")
            self._worker.submit("fast", snapshot.take)
        if self._tick % SLOW_EVERY == 0 and "slow" not in self._inflight:
            self._inflight.add("slow")
            self._worker.submit("slow", _slow_read)
        self._tick += 1

    def _held(self, key: str) -> bool:
        return self._hold.get(key, 0) > time.monotonic()

    def _hold_key(self, key: str) -> None:
        self._hold[key] = time.monotonic() + HOLD_S

    def _update(self, values: dict) -> None:
        changed = False
        for k, v in values.items():
            if self._held(k):
                continue
            if self._model.get(k) != v:
                self._model[k] = v
                changed = True
        if changed:
            self._model = dict(self._model)
            self.modelChanged.emit()

    def _on_done(self, key: str, result, error) -> None:
        self._inflight.discard(key)
        if key == "fast" and result:
            self._update(result)
        elif key == "slow" and result:
            self._update(result)
        elif key == "calibrated":
            if error:
                self._model = dict(self._model, calibrating=False, notice="", message="SINC · " + error)
            else:
                self._hold.pop("delayMs", None)
                self._model = dict(self._model, calibrating=False, delayMs=result["ms"],
                                   notice=f"SINC · {result['summary']} · aplicado {result['ms']} ms")
            self.modelChanged.emit()
        elif key == "hw-read":
            self._hw_done(result, error, "Leído de la EVO.")
        elif key == "hw-apply":
            self._hw_done(result, error, "Aplicado a la EVO.")
        elif error:
            self._set_message(error)

    def _set_message(self, text: str) -> None:
        self._model = dict(self._model, message=text)
        self.modelChanged.emit()

    # ---- writes ----
    def _queue(self, key: str, fn, *args) -> None:
        self._writes[key] = (fn, args)
        self._flush_timer.start()

    def _flush(self) -> None:
        writes, self._writes = self._writes, {}
        for key, (fn, args) in writes.items():
            self._worker.submit("write:" + key, fn, *args)

    def _local(self, key: str, value) -> None:
        self._hold_key(key)
        self._model = dict(self._model, **{key: value})
        self.modelChanged.emit()

    @Slot(int, float)
    def setGain(self, index: int, value: float) -> None:
        gains = list(self._model["gains"] or mix.DEFAULT_GAINS)
        gains[index] = round(max(0.0, min(mix.MAX_GAIN, value)), 4)
        self._local("gains", gains)
        self._queue(f"gain{index}", mix.set_gain, index + 1, gains[index])

    @Slot(int)
    def toggleGainMute(self, index: int) -> None:
        """Mute a Mezcla gain (0..3; 2 and 3 move together) and bring back the
        level it had."""
        gains = list(self._model["gains"] or mix.DEFAULT_GAINS)
        indices = [2, 3] if index in (2, 3) else [index]
        if gains[indices[0]] > 0:
            self._before_mute[index] = gains[indices[0]]
            value = 0.0
        else:
            value = self._before_mute.pop(index, mix.DEFAULT_GAINS[indices[0]])
        if len(indices) == 2:
            self.setSharedGain(value)
        else:
            self.setGain(index, value)

    @Slot(float)
    def setSharedGain(self, value: float) -> None:
        """Compartido L and R together."""
        gains = list(self._model["gains"] or mix.DEFAULT_GAINS)
        gains[2] = gains[3] = round(max(0.0, min(mix.MAX_GAIN, value)), 4)
        self._local("gains", gains)
        self._queue("gain2", mix.set_gain, 3, gains[2])
        self._queue("gain3", mix.set_gain, 4, gains[3])

    @Slot(int, float)
    def setPreamp(self, index: int, db: float) -> None:
        pre = self._model["preamp"]
        if not pre:
            return
        gains = list(pre["gains"])
        gains[index] = db
        self._local("preamp", dict(pre, gains=gains))
        self._queue(f"preamp{index}", alsa.set_preamp, index + 1, db)

    @Slot(float)
    def setDelay(self, ms: float) -> None:
        ms = round(max(0, min(mix.MAX_DELAY_MS, ms)))
        self._local("delayMs", ms)
        self._queue("delay", mix.set_delay_ms, ms)

    @Slot(float)
    def setListenVolume(self, value: float) -> None:
        esc = self._model["escucha"]
        if not esc:
            return
        self._local("escucha", dict(esc, volume=value))
        raw = snapshot.raw(value)
        self._queue("escucha", pw.run, "pactl", "set-sink-input-volume", str(esc["index"]), raw, raw)
        self._listen_save.start()

    @Slot(float)
    def setMezclaVolume(self, value: float) -> None:
        m = self._model["mezcla"]
        if not m:
            return
        self._local("mezcla", dict(m, volume=value))
        self._queue("mezcla", pw.run, "pactl", "set-source-volume", mix.MIX_SOURCE, snapshot.raw(value))

    @Slot()
    def toggleMezclaMute(self) -> None:
        m = self._model["mezcla"]
        if m:
            self._local("mezcla", dict(m, mute=not m["mute"]))
            self._queue("mezcla-mute", pw.run, "pactl", "set-source-mute", mix.MIX_SOURCE, "toggle")

    @Slot("QVariantList", float)
    def setSinkChannels(self, channels, value: float) -> None:
        sink = self._model["sink"]
        if not sink:
            return
        vols = list(sink["volumes"])
        for c in channels:
            if 0 <= int(c) < len(vols):
                vols[int(c)] = value
        self._local("sink", dict(sink, volumes=vols))
        self._queue("sink", pw.run, "pactl", "set-sink-volume", sink["name"], *map(snapshot.raw, vols))

    @Slot()
    def toggleSinkMute(self) -> None:
        sink = self._model["sink"]
        if sink:
            self._local("sink", dict(sink, mute=not sink["mute"]))
            self._queue("sink-mute", pw.run, "pactl", "set-sink-mute", sink["name"], "toggle")

    def _stream(self, index: int):
        return next((s for s in self._model["streams"] if s["index"] == index), None)

    def _local_stream(self, index: int, **changes) -> None:
        streams = [dict(s, **changes) if s["index"] == index else s for s in self._model["streams"]]
        self._local("streams", streams)

    @Slot(int, float)
    def setStreamVolume(self, index: int, value: float) -> None:
        s = self._stream(index)
        if not s:
            return
        self._local_stream(index, volume=value)
        raw = snapshot.raw(value)
        self._queue(f"stream{index}", pw.run, "pactl", "set-sink-input-volume", str(index),
                    *[raw] * s["channels"])

    @Slot(int)
    def toggleStreamMute(self, index: int) -> None:
        s = self._stream(index)
        if s:
            self._local_stream(index, mute=not s["mute"])
            self._queue(f"stream-mute{index}", pw.run, "pactl", "set-sink-input-mute", str(index), "toggle")

    @Slot(int)
    def toggleStreamShared(self, index: int) -> None:
        from .. import apps
        s = self._stream(index)
        if s and s["nodeId"]:
            self._local_stream(index, shared=not s["shared"])
            self._queue(f"share{index}", apps.share, s["nodeId"], not s["shared"])

    @Slot()
    def toggleMonitor(self) -> None:
        if self._model["monitor"] not in ("on", "off"):
            return
        on = self._model["monitor"] != "on"
        self._local("monitor", "on" if on else "off")
        self._queue("monitor", monitor.turn_on if on else monitor.turn_off)

    @Slot(int)
    def toggleInputMonitor(self, index: int) -> None:
        cur = list(self._model["inputMonitors"] or [])
        if index >= len(cur):
            return
        cur[index] = 0 if cur[index] else 1
        self._local("inputMonitors", cur)
        self._queue(f"input-monitor{index}", monitor.set_input, index + 1, bool(cur[index]))

    @Slot(str, str)
    def setCardProfile(self, card: str, profile: str) -> None:
        cards = [dict(c, active=profile, warning=profiles.warning(dict(c, active=profile)))
                 if c["name"] == card else c for c in self._model["cards"]]
        self._local("cards", cards)
        self._queue(f"profile:{card}", pw.run, "pactl", "set-card-profile", card, profile)

    # ---- sync calibration ----
    # Runs on its own thread: it takes ~15 s of playing, and the polls and
    # writes must keep going meanwhile.
    @Slot()
    def calibrate(self) -> None:
        if self._model["calibrating"]:
            return
        self._model = dict(self._model, calibrating=True,
                           notice="SINC · toca un golpe corto y seco en cada click (los primeros 4 son de cuenta)…")
        self.modelChanged.emit()

        def job():
            try:
                r = calibrate.run(apply=True, on_progress=lambda _m: None)
                self._done.emit("calibrated", {"ms": r.median_ms, "summary": r.summary}, None)
            except Exception as e:
                self._done.emit("calibrated", None, str(e))

        threading.Thread(target=job, daemon=True).start()

    # ---- hardware (USB) ----
    def _hw_set(self, **changes) -> None:
        self._hw = dict(self._hw, **changes)
        self.hwChanged.emit()

    @Slot()
    def hwRead(self) -> None:
        if self._hw["busy"]:
            return
        self._hw_set(busy=True, message="Leyendo de la EVO…")
        self._worker.submit("hw-read", hw.read_all)

    @Slot(int, int, float)
    def hwSetCell(self, inp: int, out: int, db: float) -> None:
        pending = dict(self._hw["pending"])
        key = f"{inp},{out}"
        current = (self._hw["mix"] or [[None] * 4] * 10)[inp][out]
        if current is not None and abs(current - db) < 0.5:
            pending.pop(key, None)
        else:
            pending[key] = round(db)
        self._hw_set(pending=pending)

    @Slot(str)
    def hwSetLoopback(self, name: str) -> None:
        self._hw_set(pendingLoopback=None if name == self._hw["loopback"] else name)

    def _hw_flag(self, kind: str, inp: int, on: bool) -> None:
        current = (self._hw.get(kind) or [None] * 4)[inp]
        pending = dict(self._hw["pending" + kind.capitalize()])
        if current is not None and bool(current) == on:
            pending.pop(str(inp), None)
        else:
            pending[str(inp)] = on
        self._hw_set(**{"pending" + kind.capitalize(): pending})

    @Slot(int, bool)
    def hwSetPhantom(self, inp: int, on: bool) -> None:
        self._hw_flag("phantom", inp, on)

    @Slot(int, bool)
    def hwSetMute(self, inp: int, on: bool) -> None:
        self._hw_flag("mute", inp, on)

    @Slot()
    def hwDiscard(self) -> None:
        self._hw_set(pending={}, pendingLoopback=None, pendingPhantom={}, pendingMute={}, message="")

    @Slot()
    def hwApply(self) -> None:
        if self._hw["busy"]:
            return
        changes = [(int(k.split(",")[0]), int(k.split(",")[1]), float(v)) for k, v in self._hw["pending"].items()]
        loop = self._hw["pendingLoopback"]
        phantom = {int(k): v for k, v in self._hw["pendingPhantom"].items()}
        mute = {int(k): v for k, v in self._hw["pendingMute"].items()}
        if not changes and loop is None and not phantom and not mute:
            return
        self._hw_set(busy=True, message="Aplicando a la EVO…")

        def job():
            hw.apply(changes, loop, phantom, mute)
            return hw.read_all()

        self._worker.submit("hw-apply", job)

    def _hw_done(self, result, error, ok_text: str) -> None:
        if error:
            self._hw_set(busy=False, message="Error: " + error)
            return
        read_at = time.strftime("%H:%M:%S")
        state.save("hw", {"mix": result["mix"], "loopback": result["loopback"], "readAt": read_at,
                          "phantom": result["phantom"], "mute": result["mute"]})
        self._hw_set(busy=False, mix=result["mix"], loopback=result["loopback"], readAt=read_at,
                     phantom=result["phantom"], mute=result["mute"],
                     pending={}, pendingLoopback=None, pendingPhantom={}, pendingMute={},
                     message=ok_text)

    # ---- meters ----
    def _update_meters(self) -> None:
        levels = self._meters.levels()
        view = dict(self._meters_view)
        for name, peaks in levels.items():
            prev = view.get(name) or [0.0] * len(peaks)
            view[name] = [round(max(p, q * METER_DECAY), 4) for p, q in zip(peaks, prev)]
        if view != self._meters_view:
            self._meters_view = view
            self.metersChanged.emit()
