import unittest

from evo8 import profiles
from evo8.gui import snapshot


def vol(*values):
    return {f"ch{i}": {"value": v} for i, v in enumerate(values)}


SINKS = [
    {"index": 60, "name": "alsa_output.usb-Audient_EVO8-00.pro-output-0", "mute": False,
     "volume": vol(65536, 65536, 32768, 32768, 0, 0), "properties": {"device.nick": "EVO8"}},
    {"index": 46, "name": "Compartido", "mute": False, "volume": vol(65536, 65536), "properties": {}},
]
SOURCES = [{"name": "Mezcla", "mute": True, "volume": vol(52429), "properties": {}}]
INPUTS = [
    {"index": 7, "sink": 60, "mute": False, "volume": vol(65536, 65536),
     "properties": {"node.name": "mezcla.compartido.escucha", "object.id": "45"}},
    {"index": 9, "sink": 46, "mute": False, "volume": vol(62259, 62259),
     "properties": {"node.name": "Firefox", "application.name": "Firefox", "object.id": "140"}},
    {"index": 10, "sink": 60, "mute": True, "volume": vol(32768, 32768),
     "properties": {"node.name": "evo8.meter.suma", "object.id": "200"}},
]


class Snapshot(unittest.TestCase):
    def setUp(self):
        self.s = snapshot.build(SINKS, SOURCES, INPUTS, SINKS[0]["name"])

    def test_sink(self):
        self.assertEqual(self.s["sink"]["label"], "EVO8")
        self.assertTrue(self.s["sink"]["isPro"])
        self.assertEqual(self.s["sink"]["volumes"], [1.0, 1.0, 0.5, 0.5, 0.0, 0.0])

    def test_mezcla_and_listening(self):
        self.assertEqual(self.s["mezcla"], {"volume": 0.8, "mute": True})
        self.assertEqual(self.s["escucha"], {"index": 7, "volume": 1.0, "mute": False})

    def test_apps_hide_plumbing_and_know_sharing(self):
        self.assertEqual([a["label"] for a in self.s["streams"]], ["Firefox"])
        app = self.s["streams"][0]
        self.assertTrue(app["shared"])
        self.assertEqual(app["nodeId"], "140")
        self.assertAlmostEqual(app["volume"], 0.95, places=2)

    def test_raw(self):
        self.assertEqual(snapshot.raw(0.5), "32768")
        self.assertEqual(snapshot.raw(-1), "0")


def prof(name, desc, sinks, sources):
    return {"name": name, "description": desc, "sinks": sinks, "sources": sources}


class Profiles(unittest.TestCase):
    RAW = [{
        "name": "alsa_card.usb-Audient_EVO8-00", "description": "EVO8",
        "active": "output:analog-surround-21+input:analog-surround-41",
        "profiles": [
            prof("output:analog-surround-21+input:analog-surround-21", "2.1 + 2.1", 1, 1),
            prof("output:analog-surround-21+input:analog-surround-41", "2.1 + 4.1", 1, 1),
            prof("output:analog-surround-21", "2.1 out", 1, 0),
            prof("pro-audio", "Pro Audio", 1, 1),
        ],
    }, {
        "name": "alsa_card.pci-0000_01_00.1", "description": "GP106", "active": "output:hdmi-stereo",
        "profiles": [prof("output:hdmi-stereo", "HDMI", 1, 0), prof("pro-audio", "Pro Audio", 4, 0)],
    }]

    def test_curated_with_warning(self):
        cards = profiles.cards(self.RAW)
        evo = cards[0]
        self.assertEqual([p["label"] for p in evo["profiles"]],
                         ["Pro Audio", "Estándar", "Solo salida", "2.1 + 4.1"])
        self.assertEqual(evo["warning"], "Requiere Pro Audio")
        self.assertEqual(cards[1]["label"], "HDMI")
        self.assertEqual(cards[1]["warning"], "")


if __name__ == "__main__":
    unittest.main()
