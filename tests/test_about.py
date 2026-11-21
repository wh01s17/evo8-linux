import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evo8 import about


def fake_usb(root: Path, name: str, vendor: str, product: str, bcd: str, speed: str = "480"):
    d = root / name
    d.mkdir()
    for f, v in (("idVendor", vendor), ("idProduct", product), ("bcdDevice", bcd), ("speed", speed)):
        (d / f).write_text(v + "\n")


class About(unittest.TestCase):
    def test_firmware_text(self):
        self.assertEqual(about.firmware_text("014c\n"), "1.4c")
        self.assertEqual(about.firmware_text("0210"), "2.10")
        self.assertEqual(about.firmware_text("weird"), "weird")

    def test_device_from_sysfs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(about.device(root)["connected"])
            fake_usb(root, "1-1", "046d", "0007", "0100")          # another vendor
            fake_usb(root, "1-4", "2708", "0007", "014c")
            self.assertEqual(about.device(root),
                             {"connected": True, "firmware": "1.4c", "tested": True, "speed": "480 Mbit/s"})
            (root / "1-4" / "bcdDevice").write_text("0150\n")
            self.assertFalse(about.device(root)["tested"])

    def test_missing_sysfs(self):
        self.assertFalse(about.device(Path("/nonexistent/usb"))["connected"])

    def test_report_hides_home(self):
        home = os.path.expanduser("~")
        self.assertEqual(about.tilde(home + "/x/y"), "~/x/y")
        self.assertEqual(about.tilde(home + "x"), home + "x")
        self.assertEqual(about.tilde("/usr/share"), "/usr/share")
        with patch.object(about, "device", return_value={"connected": False, "firmware": "",
                                                          "tested": False, "speed": ""}):
            text = about.report()
        self.assertIn(about.version(), text.splitlines()[0])
        self.assertIn("EVO 8: no conectada", text)
        self.assertNotIn(home + "/", text)


if __name__ == "__main__":
    unittest.main()
