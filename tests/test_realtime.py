import unittest
from unittest import mock

from evo8 import pw, rt


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


if __name__ == "__main__":
    unittest.main()
