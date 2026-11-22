"""Whether audio programs can get real-time scheduling without being killed.

PipeWire clients (mpv, browsers, WirePlumber) ask for a real-time audio thread
through the desktop portal, which hands the request to rtkit. Before that,
PipeWire sets the process's RLIMIT_RTTIME to the portal's RTTimeUSecMax. The
portal reads that value from rtkit once, when it starts: if rtkit was not
installed or running then (installed with the session already open), the
portal reports 0 for as long as it runs, and still grants real time through
rtkit afterwards. A real-time thread with a 0 µs limit is sent SIGKILL by the
kernel the first time a timer tick finds it running, so the program dies at
random every few seconds or minutes and its audio cuts out.

Restarting the portal makes it read rtkit again.
"""

from __future__ import annotations

import shutil

from . import pw

PORTAL = ("--user", "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop",
          "org.freedesktop.portal.Realtime")
RTKIT = ("--system", "org.freedesktop.RealtimeKit1", "/org/freedesktop/RealtimeKit1",
         "org.freedesktop.RealtimeKit1")
FIX = "systemctl --user restart xdg-desktop-portal"


def _rttime(bus: str, service: str, path: str, interface: str) -> int | None:
    """RTTimeUSecMax as busctl prints it ("x 200000"); None when it cannot ask."""
    out = pw.run("busctl", bus, "get-property", service, path, interface, "RTTimeUSecMax",
                 timeout=3).split()
    if len(out) == 2 and out[1].lstrip("-").isdigit():
        return int(out[1])
    return None


def limits() -> tuple[int | None, int | None]:
    """(portal, rtkit) maximum real-time run time in µs; None for either one
    that is not there or does not answer."""
    if not shutil.which("busctl"):
        return None, None
    return _rttime(*PORTAL), _rttime(*RTKIT)


def problem() -> str:
    """Non-empty when the portal would get audio programs killed."""
    portal, rtkit = limits()
    # Without rtkit the portal grants no real time at all, so its 0 kills nothing.
    if portal == 0 and rtkit:
        return ("El portal de escritorio informa 0 µs de tiempo real (rtkit permite "
                f"{rtkit} µs): los programas de audio que piden tiempo real (mpv, navegadores) "
                "mueren al azar y su audio se corta. Pasa cuando rtkit se instala con la sesión "
                f"abierta. Arreglo: {FIX} (o cerrar sesión) y volver a abrir esos programas.")
    return ""
