import array
import json
import math
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

from evo8 import alsa, calibrate, mix, monitor, pw, state

PW_LINK_L = """\
Mezcla:capture_MONO
  |-> alsa_output.usb-Audient_EVO8-00.pro-output-0:playback_AUX0
  |-> alsa_output.usb-Audient_EVO8-00.pro-output-0:playback_AUX1
  |-> Meet:input_MONO
mezcla.entradas:input_AUX0
  |<- alsa_input.usb-Audient_EVO8-00.pro-input-0:capture_AUX0
alsa_input.usb-Audient_EVO8-00.pro-input-0:capture_AUX0
  |-> mezcla.entradas:input_AUX0
"""

AMIXER_PREAMP = """\
numid=3,iface=MIXER,name='Mic Playback Volume'
  ; type=INTEGER,access=rw---R--,values=4,min=0,max=116,step=0
  : values=9,65,0,0
  | dBminmax-min=-8.00dB,max=50.00dB
"""


class PwParsing(unittest.TestCase):
    def test_links_from_reads_only_that_port(self):
        with mock.patch.object(pw, "run", return_value=PW_LINK_L):
            self.assertEqual(pw.links_from("Mezcla:capture_MONO"), [
                "alsa_output.usb-Audient_EVO8-00.pro-output-0:playback_AUX0",
                "alsa_output.usb-Audient_EVO8-00.pro-output-0:playback_AUX1",
                "Meet:input_MONO",
            ])
            self.assertEqual(pw.links_from("alsa_input.usb-Audient_EVO8-00.pro-input-0:capture_AUX0"),
                             ["mezcla.entradas:input_AUX0"])
            self.assertEqual(pw.links_from("nope"), [])

    def test_props_come_from_the_full_dump(self):
        graph = {"params": ["mix:Gain 1", 2.0, "compL:Delay (s)", 0.04]}
        full = json.dumps([{"id": 7, "info": {"params": {"Props": [{"volume": 1.0}]}}},
                           {"id": 44, "info": {"params": {"Props": [{"volume": 1.0}, graph]}}}])
        with mock.patch.object(pw, "run", return_value=full) as run:
            self.assertEqual(pw.props_params(44)[1], graph)
            self.assertEqual(run.call_args.args, ("pw-dump",))
            self.assertEqual(pw.props_params(99), [])

    def test_force_quantum(self):
        out = "Found \"settings\" metadata 35\nupdate: id:0 key:'clock.force-quantum' value:'128' type:''\n"
        with mock.patch.object(pw, "run", return_value=out):
            self.assertEqual(pw.force_quantum(), 128)


class MezclaSwitch(unittest.TestCase):
    def status(self, unit_text: str, node: int | None = None) -> str:
        with mock.patch.object(pw, "run", return_value=unit_text), \
                mock.patch.object(pw, "node_id", return_value=node):
            return mix.service_status()

    def test_status(self):
        self.assertEqual(self.status("LoadState=loaded\nActiveState=active\n", 52), "on")
        self.assertEqual(self.status("LoadState=loaded\nActiveState=inactive\n"), "off")
        self.assertEqual(self.status("LoadState=loaded\nActiveState=failed\n"), "failed")
        self.assertEqual(self.status("LoadState=not-found\nActiveState=inactive\n"), "missing")
        # Running, but not from the unit: an old always-on drop-in.
        self.assertEqual(self.status("LoadState=loaded\nActiveState=inactive\n", 52), "legacy")
        self.assertEqual(self.status("", 52), "legacy")         # no systemd at all

    def test_switch(self):
        calls = []
        with mock.patch.object(pw, "run", side_effect=lambda *a, **k: calls.append(a) or ""), \
                mock.patch.object(mix, "service_status", return_value="on"), \
                mock.patch.object(monitor, "is_on", return_value=True), \
                mock.patch.object(monitor, "turn_off") as monitor_off:
            mix.set_enabled(False)
            monitor_off.assert_called_once()
            mix.set_enabled(True)
        self.assertEqual(calls, [("systemctl", "--user", "disable", "--now", "evo8-mezcla.service"),
                                 ("systemctl", "--user", "enable", "--now", "evo8-mezcla.service")])

    def test_cannot_switch_an_old_install(self):
        for status in ("legacy", "missing"):
            with mock.patch.object(mix, "service_status", return_value=status), \
                    mock.patch.object(pw, "run") as run:
                with self.assertRaises(mix.MixError):
                    mix.set_enabled(False)
                run.assert_not_called()

    def test_off_explains_itself(self):
        with mock.patch.object(pw, "node_id", return_value=None), \
                mock.patch.object(mix, "service_status", return_value="off"):
            with self.assertRaisesRegex(mix.MixError, "evoctl mezcla on"):
                mix.gains()


class MezclaInputs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        mock.patch.object(state, "STATE", Path(self.tmp.name) / "state.json").start()
        mock.patch.object(state, "LEGACY", Path(self.tmp.name) / "none.json").start()
        self.set = mock.patch.object(pw, "set_graph_param").start()
        mock.patch.object(pw, "node_id", return_value=44).start()
        self.addCleanup(mock.patch.stopall)

    def live(self) -> dict:
        return {c.args[1]: c.args[2] for c in self.set.call_args_list}

    def test_inputs_3_4_ride_on_gains_5_6(self):
        self.assertEqual([mix.gain_number(n) for n in (1, 2, 3, 4)], [1, 2, 5, 6])

    def test_starts_with_inputs_1_2(self):
        self.assertEqual(mix.inputs(), [1, 2])

    def test_add_and_remove(self):
        mix.set_input(3, True)
        self.assertEqual(mix.inputs(), [1, 2, 3])
        self.assertEqual(self.live(), {"mix:Gain 5": 1.0})
        state.save("5", 1.6)                  # its fader moved
        mix.set_input(3, False)
        self.assertEqual(mix.inputs(), [1, 2])
        self.assertEqual(self.live()["mix:Gain 5"], 0.0)
        mix.set_input(3, True)                # back at its own level
        self.assertEqual(self.live()["mix:Gain 5"], 1.6)
        mix.set_input(1, False)
        self.assertEqual(mix.inputs(), [2, 3])
        with self.assertRaises(mix.MixError):
            mix.set_input(5, True)

    def test_apply_keeps_removed_inputs_silent(self):
        state.save("1", 2.0)
        state.save("inputs", [2, 4])
        with mock.patch.object(pw, "props_params", return_value=[]):
            mix.apply()
        live = self.live()
        self.assertEqual(live["mix:Gain 1"], 0.0)     # saved 2.0, but out of the Mezcla
        self.assertEqual(live["mix:Gain 2"], 1.0)
        self.assertEqual(live["mix:Gain 5"], 0.0)
        self.assertEqual(live["mix:Gain 6"], 1.0)


class Preamp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(state, "STATE", Path(self.tmp.name) / "state.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        mock.patch.object(state, "LEGACY", Path(self.tmp.name) / "none.json").start()
        self.addCleanup(mock.patch.stopall)

    def test_get_in_db(self):
        with mock.patch.object(pw, "run", return_value=AMIXER_PREAMP):
            self.assertEqual(alsa.preamp(), {"min": -8.0, "max": 50.0, "step": 0.5,
                                             "gains": [-3.5, 24.5, -8.0, -8.0]})

    def test_set_rounds_and_clamps_one_input(self):
        calls = []

        def fake(*args, **kw):
            calls.append(args)
            return AMIXER_PREAMP

        with mock.patch.object(pw, "run", side_effect=fake):
            alsa.set_preamp(2, 20.3)     # 20.5 dB -> raw 57
            alsa.set_preamp(1, 99)       # clamped to +50 dB -> raw 116
        self.assertEqual(calls[1][-1], "9,57,0,0")
        self.assertEqual(calls[3][-1], "116,65,0,0")
        self.assertEqual(state.load()["preamp"], {"2": 20.5, "1": 50.0})
        with mock.patch.object(pw, "run", return_value=AMIXER_PREAMP):
            with self.assertRaises(alsa.AlsaError):
                alsa.set_preamp(5, 0)


def synthetic_recording(path: Path, lag_ms: float, hits: bool = True) -> None:
    """4-channel take: clicks on RL/RR, a hit `lag_ms` later on FL."""
    rate, bpm, beats, lead = 48000, calibrate.BPM, calibrate.BEATS, calibrate.LEAD_IN
    period = 60 / bpm
    total = int(rate * (lead + beats * period + 1))
    data = array.array("h", [0] * total * 4)
    burst = int(rate * 0.01)
    for b in range(beats):
        c = int(rate * (lead + b * period))
        h = c + int(rate * lag_ms / 1000)
        for i in range(burst):
            v = int(20000 * math.sin(2 * math.pi * 1500 * i / rate))
            data[4 * (c + i) + 2] = v
            data[4 * (c + i) + 3] = v
            if hits:
                data[4 * (h + i) + 0] = v
    with wave.open(str(path), "w") as w:
        w.setnchannels(4)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())


class Calibration(unittest.TestCase):
    def test_measures_the_lag(self):
        with tempfile.TemporaryDirectory() as tmp:
            rec = Path(tmp) / "rec.wav"
            synthetic_recording(rec, 85)
            r = calibrate.analyse(rec)
        self.assertEqual(r.clicks, calibrate.BEATS - calibrate.COUNT_IN)
        self.assertEqual(r.hits, r.clicks)
        self.assertAlmostEqual(r.median_ms, 85, delta=2)
        self.assertIn("Golpes medidos", r.summary)

    def test_no_playing_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            rec = Path(tmp) / "rec.wav"
            synthetic_recording(rec, 85, hits=False)
            with self.assertRaises(calibrate.CalibrationError):
                calibrate.analyse(rec)


if __name__ == "__main__":
    unittest.main()
