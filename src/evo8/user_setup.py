"""`evoctl setup`: put the files a pip/pipx install cannot place.

pip only installs Python code. The Mezcla needs a PipeWire drop-in, the
"Restaurar al conectar" service needs a user unit, and the menu entry needs a
.desktop file and an icon. All of those go under the user's home, so no root
is needed. The udev rule (USB access without root) is the one thing that does
need root: setup prints the exact command instead of running sudo itself.

It never restarts PipeWire: the user may be in a call.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).with_name("data")
UDEV_RULE = DATA / "udev" / "70-audient-evo8.rules"
UDEV_DEST = Path("/etc/udev/rules.d/70-audient-evo8.rules")
SYSTEM_PIPEWIRE = (Path("/usr/share/pipewire"), Path("/etc/pipewire"))
TOOLS = {
    "pactl": "pactl (libpulse / pulseaudio-utils)",
    "pw-cli": "PipeWire (pipewire)",
    "pw-dump": "PipeWire (pipewire)",
    "pw-link": "PipeWire (pipewire)",
    "pw-record": "PipeWire (pipewire)",
    "pw-play": "PipeWire (pipewire)",
    "pw-metadata": "PipeWire (pipewire)",
    "wpctl": "WirePlumber (wireplumber)",
    "amixer": "amixer (alsa-utils)",
}
FONT = "JetBrainsMono Nerd Font"


def _config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"))


def _data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"))


def bin_path(name: str) -> str:
    """Absolute path of one of our commands: next to the running Python first
    (a pipx or venv install), then PATH."""
    here = Path(sys.executable).parent / name
    if here.exists():
        return str(here)
    return shutil.which(name) or name


@dataclass
class Item:
    label: str
    dest: Path
    content: str
    note: str = ""          # why it is skipped, when it is


def _text(rel: str) -> str:
    return (DATA / rel).read_text()


def plan() -> list[Item]:
    cfg, share = _config_home(), _data_home()
    items: list[Item] = []
    for rel, label in (("pipewire/pipewire.conf.d/20-mezcla.conf", "PipeWire: la Mezcla"),
                       ("pipewire/pipewire-pulse.conf.d/20-bloquear-volumen-micro.conf",
                        "PipeWire: volumen fijo del micrófono en el navegador")):
        dest = cfg / rel
        item = Item(label, dest, _text(rel))
        # A drop-in in ~/.config shadows the system one with the same name:
        # never leave a stale copy over a packaged install.
        sub = Path(rel).relative_to("pipewire")
        system = next((d / sub for d in SYSTEM_PIPEWIRE if (d / sub).exists()), None)
        if system:
            item.note = f"ya lo instala el sistema ({system})"
        elif dest.is_symlink():
            item.note = f"enlace de una instalación de desarrollo ({os.readlink(dest)})"
        items.append(item)

    service = _text("systemd/evo8-restore.service").replace(
        "%h/.local/bin/evoctl", bin_path("evoctl"))
    items.append(Item("Servicio: restaurar ajustes al conectar la EVO",
                      cfg / "systemd" / "user" / "evo8-restore.service", service))

    desktop = _text("applications/evo8-mixer.desktop").replace(
        "Exec=evo8-mixer", "Exec=" + bin_path("evo8-mixer"))
    items.append(Item("Menú de aplicaciones", share / "applications" / "evo8-mixer.desktop", desktop))
    items.append(Item("Ícono", share / "icons" / "hicolor" / "scalable" / "apps" / "evo8-mixer.svg",
                      _text("evo8-mixer.svg")))
    return items


def checks() -> list[str]:
    """Problems setup cannot fix, in words the user can act on."""
    problems = []
    missing = sorted({pkg for tool, pkg in TOOLS.items() if not shutil.which(tool)})
    if missing:
        problems.append("Faltan programas del sistema: " + ", ".join(missing) + ".")
    for module, what in (("usb", "pyusb (control por USB)"), ("PySide6", "PySide6 (la ventana)")):
        try:
            __import__(module)
        except ImportError:
            problems.append(f"Falta {what}: pipx install --force 'evo8-linux[gui,usb]'.")
    if shutil.which("fc-list"):
        out = subprocess.run(["fc-list", FONT], capture_output=True, text=True).stdout
        if not out.strip():
            problems.append(f"Falta la fuente «{FONT}»: los íconos de la ventana se verán como cuadros.")
    from . import rt
    realtime = rt.problem()
    if realtime:
        problems.append(realtime)
    return problems


def udev_command() -> str:
    return (f"sudo install -Dm644 {UDEV_RULE} {UDEV_DEST} && "
            "sudo udevadm control --reload && sudo udevadm trigger --subsystem-match=usb")


def udev_installed() -> bool:
    return UDEV_DEST.exists() or Path("/usr/lib/udev/rules.d/70-audient-evo8.rules").exists()


def install(dry_run: bool = False) -> list[str]:
    lines = []
    for it in plan():
        if it.note:
            lines.append(f"  {'omitido':<11}{it.label}: {it.note}")
            continue
        current = it.dest.read_text() if it.dest.is_file() else None
        if current == it.content:
            lines.append(f"  {'al día':<11}{it.label}")
            continue
        verb = "instalar" if current is None else "actualizar"
        if not dry_run:
            it.dest.parent.mkdir(parents=True, exist_ok=True)
            it.dest.write_text(it.content)
            verb = "instalado" if current is None else "actualizado"
        lines.append(f"  {verb:<11}{it.label} → {it.dest}")
    if not dry_run:
        _refresh()
    return lines


def remove(dry_run: bool = False) -> list[str]:
    lines = []
    for it in plan():
        if it.note or not it.dest.is_file() or it.dest.is_symlink():
            continue
        if not dry_run:
            it.dest.unlink()
        lines.append(f"  {'quitar' if dry_run else 'quitado':<11}{it.label} ({it.dest})")
    if not dry_run:
        _refresh()
    return lines


def _refresh() -> None:
    """Let systemd and the menus see the new files; all optional."""
    for cmd in (["systemctl", "--user", "daemon-reload"],
                ["update-desktop-database", "-q", str(_data_home() / "applications")],
                ["gtk-update-icon-cache", "-q", "-t", str(_data_home() / "icons" / "hicolor")]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, capture_output=True)


def mezcla_loaded() -> bool | None:
    """Whether PipeWire already runs the Mezcla; None when it cannot tell."""
    if not shutil.which("pw-cli"):
        return None
    out = subprocess.run(["pw-cli", "ls", "Node"], capture_output=True, text=True).stdout
    return "mezcla.suma" in out


def evo_profile_ok() -> bool | None:
    """Whether the EVO 8 is on Pro Audio; None when it is not plugged in."""
    from . import apps, profiles
    try:
        cards = apps.card_profiles()
    except Exception:
        return None
    for card, wanted in profiles.REQUIRED.items():
        for c in cards:
            if c["name"] == card:
                return c["active"] == wanted
    return None


def run(remove_files: bool = False, dry_run: bool = False) -> int:
    if remove_files:
        lines = remove(dry_run)
        print("\n".join(lines) if lines else "Nada que quitar.")
        if udev_installed():
            print(f"\nLa regla udev queda; para quitarla: sudo rm {UDEV_DEST}")
        return 0

    print("Archivos de usuario:" + (" (simulación)" if dry_run else ""))
    lines = install(dry_run)
    print("\n".join(lines))
    pipewire_changed = any(line.split()[0] in ("instalado", "actualizado", "instalar", "actualizar")
                           and "PipeWire" in line for line in lines)
    steps = []
    if not udev_installed():
        steps.append("Permitir el control por USB sin root (pide tu contraseña):\n    " + udev_command())
    if pipewire_changed or mezcla_loaded() is False:
        steps.append("Reiniciar PipeWire para cargar la Mezcla (corta el audio un momento: no lo hagas mientras grabas o transmites):\n"
                     "    systemctl --user restart pipewire pipewire-pulse wireplumber")
    if evo_profile_ok() is False:
        steps.append("Poner la EVO 8 en el perfil Pro Audio:\n"
                     "    evoctl profiles set alsa_card.usb-Audient_EVO8-00 pro-audio")
    if steps:
        print("\nFalta:")
        for i, s in enumerate(steps, 1):
            print(f"  {i}. {s}")
    else:
        print("\nTodo listo. Abre el mezclador con evo8-mixer o desde el menú de aplicaciones.")
    problems = checks()
    if problems:
        print("\nRevisa:")
        for p in problems:
            print("  - " + p)
    return 1 if problems else 0
