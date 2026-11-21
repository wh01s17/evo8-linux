import importlib.util
import os
import subprocess
import sys
import textwrap
import unittest


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "PySide6 not installed")
class MixerWindow(unittest.TestCase):
    def test_both_tabs_render_without_blocking_the_event_loop(self):
        # A Qt layout loop can block the GUI thread before a Qt timer fires.
        # Run in a subprocess so the test runner can enforce the timeout.
        script = textwrap.dedent("""\
            from unittest.mock import patch

            from PySide6.QtCore import Qt
            from PySide6.QtGui import QGuiApplication
            from PySide6.QtQml import QQmlApplicationEngine
            from PySide6.QtQuickControls2 import QQuickStyle

            from evo8.gui.app import QML_DIR
            from evo8.gui.backend import Backend, Meters

            QQuickStyle.setStyle("Basic")
            app = QGuiApplication([])
            with (
                patch.object(Backend, "_poll"),
                patch.object(Meters, "start"),
                patch("evo8.gui.backend.state.load", return_value={}),
            ):
                mixer = Backend()
            engine = QQmlApplicationEngine()
            engine.rootContext().setContextProperty("mixer", mixer)
            engine.load(str(QML_DIR / "Main.qml"))
            if not engine.rootObjects():
                raise SystemExit("No se pudo cargar la ventana")
            window = engine.rootObjects()[0]

            def next_frame():
                if window.property("page") == 0:
                    window.setProperty("page", 1)
                else:
                    app.quit()

            window.frameSwapped.connect(next_frame, Qt.ConnectionType.QueuedConnection)
            raise SystemExit(app.exec())
            """)
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
        env.pop("QT_QPA_PLATFORMTHEME", None)
        result = subprocess.run(
            [sys.executable, "-c", script], env=env, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
