import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evo8 import user_setup


class UserSetup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.cfg, self.share = root / "config", root / "share"
        self.patches = [
            patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.cfg), "XDG_DATA_HOME": str(self.share)}),
            patch.object(user_setup, "SYSTEM_PIPEWIRE", (root / "usr-share-pipewire",)),
            patch.object(user_setup, "SYSTEM_UNITS", root / "usr-lib-systemd-user"),
            patch.object(user_setup, "_refresh"),
            patch.object(user_setup, "_systemctl"),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def test_fresh_install_then_up_to_date_then_remove(self):
        lines = user_setup.install()
        self.assertEqual(sum(line.split()[0] == "instalado" for line in lines), 6, lines)
        mezcla = self.cfg / "pipewire" / "evo8-mezcla.conf"
        self.assertEqual(mezcla.read_text(), (user_setup.DATA / "pipewire/evo8-mezcla.conf").read_text())
        service = (self.cfg / "systemd/user/evo8-restore.service").read_text()
        self.assertNotIn("%h/.local/bin", service)
        self.assertRegex(service, r"ExecStart=\S*evoctl restore")
        unit = (self.cfg / "systemd/user/evo8-mezcla.service").read_text()
        self.assertRegex(unit, r"ExecStart=\S*pipewire -c evo8-mezcla.conf")
        self.assertRegex(unit, r"ExecStartPost=-/\S*evoctl apply --wait")
        self.assertIn("WantedBy=pipewire.service", unit)
        # A fresh install never switches the Mezcla on.
        user_setup._systemctl.assert_not_called()
        desktop = (self.share / "applications/evo8-mixer.desktop").read_text()
        self.assertIn("Icon=evo8-mixer", desktop)
        self.assertTrue((self.share / "icons/hicolor/scalable/apps/evo8-mixer.svg").exists())

        self.assertTrue(all(line.strip().startswith("al día") for line in user_setup.install()))

        self.assertEqual(len(user_setup.remove()), 6)
        self.assertFalse(mezcla.exists())
        user_setup._systemctl.assert_called_once_with("disable", "--now", "evo8-mezcla.service")

    def test_replaces_the_always_on_dropin_and_keeps_it_on(self):
        old = self.cfg / "pipewire" / "pipewire.conf.d" / "20-mezcla.conf"
        old.parent.mkdir(parents=True)
        old.write_text("# 0.2\n")
        dry = user_setup.install(dry_run=True)
        self.assertTrue(old.exists())
        self.assertEqual(dry[0].split()[0], "quitar", dry)
        user_setup._systemctl.assert_not_called()
        lines = user_setup.install()
        self.assertFalse(old.exists())
        self.assertEqual(lines[0].split()[0], "quitado", lines)
        self.assertTrue((self.cfg / "pipewire" / "evo8-mezcla.conf").exists())
        user_setup._systemctl.assert_called_once_with("enable", "evo8-mezcla.service")

    def test_dry_run_writes_nothing(self):
        lines = user_setup.install(dry_run=True)
        self.assertTrue(all(line.split()[0] == "instalar" for line in lines), lines)
        self.assertFalse(self.cfg.exists())

    def test_leaves_packaged_and_dev_installs_alone(self):
        system = Path(self.tmp.name) / "usr-share-pipewire" / "evo8-mezcla.conf"
        system.parent.mkdir(parents=True)
        system.write_text("# packaged\n")
        unit = Path(self.tmp.name) / "usr-lib-systemd-user" / "evo8-mezcla.service"
        unit.parent.mkdir(parents=True)
        unit.write_text("# packaged\n")
        dev = self.cfg / "pipewire" / "pipewire-pulse.conf.d" / "20-bloquear-volumen-micro.conf"
        dev.parent.mkdir(parents=True)
        dev.symlink_to("/somewhere/else.conf")
        lines = user_setup.install()
        skipped = [line for line in lines if line.split()[0] == "omitido"]
        self.assertEqual(len(skipped), 3, lines)
        self.assertFalse((self.cfg / "pipewire" / "evo8-mezcla.conf").exists())
        self.assertFalse((self.cfg / "systemd" / "user" / "evo8-mezcla.service").exists())
        self.assertTrue(dev.is_symlink())
        user_setup.remove()
        self.assertTrue(dev.is_symlink())

    def test_udev_command_names_the_packaged_rule(self):
        cmd = user_setup.udev_command()
        self.assertIn(str(user_setup.UDEV_RULE), cmd)
        self.assertTrue(user_setup.UDEV_RULE.exists())


if __name__ == "__main__":
    unittest.main()
