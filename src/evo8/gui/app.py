"""evo8-mixer: the mixer window."""

from __future__ import annotations

import os
import signal
import sys
from pathlib import Path

QML_DIR = Path(__file__).with_name("qml")


def main(argv: list[str] | None = None) -> int:
    try:
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtQuickControls2 import QQuickStyle
    except ImportError:
        print("falta PySide6 (pacman -S pyside6)", file=sys.stderr)
        return 1

    from PySide6.QtNetwork import QLocalServer, QLocalSocket

    from .backend import Backend

    QGuiApplication.setApplicationName("evo8-mixer")
    QGuiApplication.setDesktopFileName("evo8-mixer")   # Wayland app id
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(argv if argv is not None else sys.argv)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # One window at a time: a second launch asks the running one to come to
    # the front and exits.
    name = f"evo8-mixer-{os.getuid()}"
    probe = QLocalSocket()
    probe.connectToServer(name)
    if probe.waitForConnected(300):
        probe.write(b"raise\n")
        probe.waitForBytesWritten(300)
        return 0
    QLocalServer.removeServer(name)
    server = QLocalServer()
    server.listen(name)

    backend = Backend()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("mixer", backend)
    args = argv if argv is not None else sys.argv
    engine.setInitialProperties({"page": 1 if "--evo" in args else 0})
    engine.load(str(QML_DIR / "Main.qml"))
    if not engine.rootObjects():
        backend.shutdown()
        return 1
    window = engine.rootObjects()[0]

    def raise_window():
        sock = server.nextPendingConnection()
        if sock:
            sock.close()
        window.show()
        window.raise_()
        window.requestActivate()

    server.newConnection.connect(raise_window)
    code = app.exec()
    backend.shutdown()
    return code


if __name__ == "__main__":
    sys.exit(main())
