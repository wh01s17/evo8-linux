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
    # EVO8_MIXER_INSTANCE gives a separate instance (tests, a second window).
    name = os.environ.get("EVO8_MIXER_INSTANCE") or f"evo8-mixer-{os.getuid()}"
    # The kernel accepts the connection even when the running window is hung,
    # so only a reply proves it is alive; otherwise take over the name.
    probe = QLocalSocket()
    probe.connectToServer(name)
    if probe.waitForConnected(300):
        probe.write(b"raise\n")
        probe.waitForBytesWritten(300)
        if probe.waitForReadyRead(1000) and probe.readAll().data().startswith(b"ok"):
            return 0
        print("la ventana anterior no responde; abriendo otra", file=sys.stderr)
    probe.abort()
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
        window.show()
        window.raise_()
        window.requestActivate()

    # Read the request before answering: closing a Unix socket with unread
    # data resets the peer, which would lose the reply. The caller closes.
    def on_connection():
        while (sock := server.nextPendingConnection()) is not None:
            def answer(sock=sock):
                sock.readAll()
                sock.write(b"ok\n")
                sock.flush()
                raise_window()
            sock.readyRead.connect(answer)
            sock.disconnected.connect(sock.deleteLater)
            if sock.bytesAvailable():
                answer()

    server.newConnection.connect(on_connection)
    code = app.exec()
    backend.shutdown()
    return code


if __name__ == "__main__":
    sys.exit(main())
