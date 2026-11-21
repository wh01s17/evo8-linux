"""Card profiles a person would actually pick.

ALSA offers every channel layout it can probe (the EVO 8 lists 25), almost all
of them useless. Each card keeps:
  Pro Audio    -- every input and output as its own channel
  Estándar     -- the best regular profile (input + output if one exists)
  Solo salida  -- the best output-only one, when Estándar has inputs too
plus whatever is active now, so the current state is always visible.
Each one carries a short hint saying what picking it does.
"""

from __future__ import annotations

import re

from . import apps

# Profiles a card must be on for the Mezcla to work: its config reads the EVO 8
# inputs one by one, which only Pro Audio exposes.
REQUIRED = {"alsa_card.usb-Audient_EVO8-00": "pro-audio"}


def _profile_name(name: str) -> str:
    return "Pro Audio" if name == "pro-audio" else name


def friendly_label(text: str) -> str:
    label = str(text or "").strip()
    for pattern in (r"^sof-soundwire\s+", r"^built-?in audio\s+", r"\s+Output$", r"\s+Input$"):
        label = re.sub(pattern, "", label, flags=re.I)
    return label.replace("Microphones", "Microphone")


def card_label(name: str, description: str, profiles: list[dict]) -> str:
    desc = str(description or name or "")
    if re.search(r"built-?in", desc, re.I):
        return "Integrado"
    if profiles and all(p["name"] == "pro-audio" or re.search("hdmi", p["name"], re.I) for p in profiles):
        return "HDMI"
    return friendly_label(desc)


def hint(profile: dict, bluetooth: bool = False, required: bool = False) -> str:
    """What picking this profile does, in a few words."""
    if profile["name"] == "pro-audio":
        return "cada canal aparte" + (" · lo usa la Mezcla" if required else "")
    if profile["sinks"] and profile["sources"]:
        return "con micrófono, menor calidad" if bluetooth else "entrada y salida comunes"
    if profile["sinks"]:
        if bluetooth:
            return "solo sonido, alta calidad"
        return "solo sonido, sin entrada"
    if profile["sources"]:
        return "solo entrada"
    return ""


def curate(profiles: list[dict], active: str, bluetooth: bool = False,
           required: str = "") -> list[dict]:
    """Profiles come sorted by priority (apps.card_profiles)."""
    picked: list[dict] = []
    seen: set[str] = set()

    def add(p, label):
        if p and p["name"] not in seen:
            seen.add(p["name"])
            picked.append({"name": p["name"], "label": label,
                           "hint": hint(p, bluetooth, p["name"] == required)})

    pro = next((p for p in profiles if p["name"] == "pro-audio"), None)
    rest = [p for p in profiles if p["name"] != "pro-audio"]
    duplex = next((p for p in rest if p["sinks"] > 0 and p["sources"] > 0), None)
    output = next((p for p in rest if p["sinks"] > 0 and p["sources"] == 0), None)
    add(pro, "Pro Audio")
    if duplex:
        add(duplex, "Estándar")
        add(output, "Solo salida")
    else:
        add(output, "Estándar")
    for p in profiles:
        if p["name"] == active:
            add(p, p["description"])
    return picked


def warning(card: dict) -> str:
    """Non-empty when the card is off the profile the Mezcla needs."""
    required = card.get("required")
    if not required or card.get("active") == required:
        return ""
    return "Requiere " + _profile_name(required)


def cards(raw: list[dict] | None = None) -> list[dict]:
    """[{name, label, active, required, warning, profiles: [{name, label, hint}]}]"""
    result = []
    for c in apps.card_profiles() if raw is None else raw:
        required = REQUIRED.get(c["name"], "")
        curated = curate(c["profiles"], c["active"],
                         bluetooth=str(c["name"]).startswith("bluez_card."), required=required)
        if len(curated) < 2:
            continue
        card = {
            "name": c["name"],
            "label": card_label(c["name"], c["description"], c["profiles"]),
            "active": c["active"],
            "required": required,
            "profiles": curated,
        }
        card["warning"] = warning(card)
        result.append(card)
    return result
