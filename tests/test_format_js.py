"""Pan law and formatting helpers of the QML window (qml/format.js), run in node."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

FORMAT_JS = Path(__file__).parents[1] / "src/evo8/gui/qml/format.js"


def js(expr: str):
    code = FORMAT_JS.read_text().replace(".pragma library", "") + f"\nconsole.log(JSON.stringify({expr}))"
    out = subprocess.run(["node", "-e", code], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@unittest.skipUnless(shutil.which("node"), "node not installed")
class FormatJs(unittest.TestCase):
    def test_level_pan_round_trip(self):
        self.assertEqual(js("hwLevelPan(0, 0)"), {"level": 0, "pan": 0, "muted": False})
        self.assertEqual(js("hwLevelPan(-128, -128)"), {"level": -128, "pan": 0, "muted": True})
        l, r = js("hwCells(-6, -0.5, -61)")
        self.assertEqual(l, -6)
        self.assertAlmostEqual(r, -6 + -6.0206, places=2)
        self.assertEqual(js(f"hwLevelPan({l}, {r})"), {"level": -6, "pan": -0.5, "muted": False})

    def test_edges_and_off(self):
        self.assertEqual(js("hwCells(0, 1, -61)"), [-128, 0])     # hard right: left off
        self.assertEqual(js("hwCells(-61, 0, -61)"), [-128, -128])  # fader at the bottom
        self.assertEqual(js("panText(0)"), "C")
        self.assertEqual(js("panText(-0.3)"), "L 30")


if __name__ == "__main__":
    unittest.main()
