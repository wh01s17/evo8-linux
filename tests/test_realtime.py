import tempfile
import unittest
from pathlib import Path
from unittest import mock

from evo8 import monitor, pw, rt


def busctl(portal: str, rtkit: str):
    """A fake pw.run answering busctl for the portal and for rtkit."""
    def run(*args, **kwargs):
        if args[0] != "busctl":
            return ""
        return portal if args[1] == "--user" else rtkit
    return run


class Realtime(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(rt.shutil, "which", return_value="/usr/bin/busctl")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_portal_stuck_at_zero_is_a_problem(self):
        with mock.patch.object(pw, "run", busctl("x 0\n", "x 200000\n")):
            self.assertEqual(rt.limits(), (0, 200000))
            message = rt.problem()
        self.assertIn("200000", message)
        self.assertIn(rt.FIX, message)

    def test_portal_in_step_with_rtkit_is_fine(self):
        with mock.patch.object(pw, "run", busctl("x 200000\n", "x 200000\n")):
            self.assertEqual(rt.problem(), "")

    def test_zero_without_rtkit_kills_nothing(self):
        with mock.patch.object(pw, "run", busctl("x 0\n", "")):
            self.assertEqual(rt.limits(), (0, None))
            self.assertEqual(rt.problem(), "")

    def test_no_busctl_cannot_tell(self):
        with mock.patch.object(rt.shutil, "which", return_value=None):
            self.assertEqual(rt.limits(), (None, None))
            self.assertEqual(rt.problem(), "")


class MonitorQuantum(unittest.TestCase):
    def setUp(self):
        self.forced = 0
        self.sink = "alsa_output.usb-Audient_EVO8-00.pro-output-0"
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for target, attr, value in (
            (pw, "force_quantum", lambda: self.forced),
            (pw, "set_force_quantum", self._set),
            (pw, "default_sink", lambda: self.sink),
            (monitor, "is_on", lambda: True),
            (monitor, "available", lambda: True),
            (monitor, "MARKER", Path(tmp.name) / "marker"),
            (monitor, "INPUTS_FILE", Path(tmp.name) / "inputs"),
        ):
            patcher = mock.patch.object(target, attr, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _set(self, value):
        self.forced = value

    def test_wired_output_gets_the_low_quantum(self):
        monitor.update_quantum()
        self.assertEqual(self.forced, monitor.QUANTUM)

    def test_bluetooth_output_is_left_alone(self):
        self.sink = "bluez_output.B8_D5_0B_AF_50_23.1"
        monitor.update_quantum()
        self.assertEqual(self.forced, 0)

    def test_switching_to_bluetooth_while_on_releases_it(self):
        monitor.update_quantum()
        self.sink = "bluez_output.B8_D5_0B_AF_50_23.1"
        self.assertEqual(monitor.status(), "on")
        self.assertEqual(self.forced, 0)

    def test_never_undoes_a_quantum_someone_else_forced(self):
        self.forced = 256
        self.sink = "bluez_output.B8_D5_0B_AF_50_23.1"
        monitor.update_quantum()
        self.assertEqual(self.forced, 256)


if __name__ == "__main__":
    unittest.main()
