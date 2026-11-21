"""What the "Acerca de" tab and `evoctl --version` show.

Everything here is read from files (package metadata, sysfs, config paths):
nothing talks to the EVO over USB, so it is safe to call at any time.
"""

from __future__ import annotations

import os
import platform
from pathlib import Path

from . import __version__, state

NAME = "evo8-linux"
APP = "Mezclador EVO 8"
DESCRIPTION = ("Control del Audient EVO 8 en Linux: mezcla de monitoreo interna, "
               "loop-back y preamps, un mezclador para PipeWire y un micrófono "
               "virtual que junta tus entradas con el audio de otras apps.")
AUTHOR = "wh01s17"
LICENSE = "MIT"
REPO = "https://github.com/wh01s17/evo8-linux"
ISSUES = REPO + "/issues"
DISCLAIMER = "Proyecto no oficial, sin relación con Audient."
TESTED_FIRMWARE = "1.4c"

VENDOR_ID, PRODUCT_ID = "2708", "0007"
SYSFS_USB = Path("/sys/bus/usb/devices")

_CONFIG_DIRS = (
    ("usuario", Path(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")) / "pipewire"),
    ("sistema", Path("/etc/pipewire")),
    ("paquete", Path("/usr/share/pipewire")),
)
_UDEV_RULES = (Path("/etc/udev/rules.d/70-audient-evo8.rules"),
               Path("/usr/lib/udev/rules.d/70-audient-evo8.rules"))


def tilde(path) -> str:
    """The path with the home folder as "~", so reports don't carry the user name."""
    text, home = str(path), os.path.expanduser("~")
    return "~" + text[len(home):] if home not in ("", "/") and (text == home or text.startswith(home + "/")) else text


def version() -> str:
    try:
        from importlib.metadata import PackageNotFoundError, version as dist_version
        return dist_version(NAME)
    except (ImportError, PackageNotFoundError):
        return __version__


def firmware_text(bcd: str) -> str:
    """bcdDevice as sysfs prints it ("014c") → "1.4c"."""
    bcd = bcd.strip().lower()
    if len(bcd) != 4:
        return bcd
    return f"{int(bcd[:2], 16)}.{bcd[2:]}"


def device(root: Path = SYSFS_USB) -> dict:
    """{connected, firmware, tested, speed} from sysfs, without any USB traffic."""
    try:
        entries = sorted(root.iterdir())
    except OSError:
        entries = []
    for d in entries:
        try:
            if (d / "idVendor").read_text().strip() != VENDOR_ID:
                continue
            if (d / "idProduct").read_text().strip() != PRODUCT_ID:
                continue
            fw = firmware_text((d / "bcdDevice").read_text())
            speed = (d / "speed").read_text().strip() if (d / "speed").exists() else ""
        except OSError:
            continue
        return {"connected": True, "firmware": fw, "tested": fw == TESTED_FIRMWARE,
                "speed": f"{speed} Mbit/s" if speed else ""}
    return {"connected": False, "firmware": "", "tested": False, "speed": ""}


def install_kind(module_file: str = __file__) -> str:
    path = Path(module_file).resolve()
    if (path.parents[2] / ".git").exists():
        return f"desarrollo ({tilde(path.parents[2])})"
    if str(path).startswith("/usr/"):
        return "paquete del sistema"
    return "pip"


def pipewire_config() -> str:
    """Where the Mezcla config PipeWire loads comes from (first one wins)."""
    for label, base in _CONFIG_DIRS:
        f = base / "pipewire.conf.d" / "20-mezcla.conf"
        if f.exists():
            return f"{tilde(f)} ({label})"
    return ""


def udev_rule() -> str:
    return next((str(p) for p in _UDEV_RULES if p.exists()), "")


def info(extra_versions: dict | None = None) -> dict:
    return {
        "name": NAME, "app": APP, "version": version(), "description": DESCRIPTION,
        "author": AUTHOR, "license": LICENSE, "repo": REPO, "issues": ISSUES,
        "disclaimer": DISCLAIMER, "testedFirmware": TESTED_FIRMWARE,
        "device": device(),
        "install": install_kind(),
        "pipewireConfig": pipewire_config(),
        "udevRule": udev_rule(),
        "stateFile": tilde(state.STATE),
        "versions": {"Python": platform.python_version(), **(extra_versions or {})},
        "platform": f"{platform.system()} {platform.release()}",
    }


def report(data: dict | None = None) -> str:
    """Plain text to paste into a bug report."""
    d = data or info()
    dev = d["device"]
    lines = [
        f"{d['name']} {d['version']}",
        f"EVO 8: {'conectada, firmware ' + dev['firmware'] if dev['connected'] else 'no conectada'}",
        f"Instalación: {d['install']}",
        f"Config de PipeWire: {d['pipewireConfig'] or 'no encontrada'}",
        f"Regla udev: {d['udevRule'] or 'no instalada'}",
        f"Sistema: {d['platform']}",
    ]
    lines += [f"{k}: {v}" for k, v in d["versions"].items()]
    return "\n".join(lines)
