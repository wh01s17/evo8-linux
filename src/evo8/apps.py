"""Per-app routing to Compartido, and card profiles.

Compartido plays on the selected output and also feeds the Mezcla, so moving
an app's stream there sends that app along with the mic. WirePlumber
remembers the choice per application, so its later streams go there too.
Streams are named by PipeWire node id; pactl numbers sink inputs differently,
so they are matched through each sink input's object.id.
"""

from __future__ import annotations

import json

from . import mix, pw


class AppsError(RuntimeError):
    pass


def shared_streams() -> list[str]:
    """Node ids of the app streams currently on Compartido."""
    shared = pw.sink_index(mix.SHARED_SINK)
    if shared is None:
        return []
    return [s.node_id for s in pw.sink_inputs() if s.sink == shared and s.node_id]


def share(node_id: str, on: bool) -> None:
    match = next((s for s in pw.sink_inputs() if s.node_id == str(node_id)), None)
    if match is None:
        raise AppsError(f"no playback stream for node {node_id}")
    if on:
        if pw.sink_index(mix.SHARED_SINK) is None:
            raise AppsError(f"sink {mix.SHARED_SINK} not found")
        target = mix.SHARED_SINK
    else:
        target = pw.default_sink()
    pw.run("pactl", "move-sink-input", str(match.index), target, check=True)


# ---- card profiles ----
# Only profiles that are available and not "off" are listed, highest priority
# first, and cards with nothing to switch between (a phone's audio gateway) are
# dropped, so every card listed has a real choice.

def card_profiles() -> list[dict]:
    out = pw.run("pactl", "-f", "json", "list", "cards", timeout=2)
    try:
        cards = json.loads(out or "[]")
    except json.JSONDecodeError:
        return []
    result = []
    for c in cards:
        profiles = [
            {"name": name, "description": p.get("description") or name,
             "sinks": p.get("sinks", 0), "sources": p.get("sources", 0),
             "_priority": p.get("priority", 0)}
            for name, p in (c.get("profiles") or {}).items()
            if name != "off" and p.get("available") is not False
        ]
        profiles.sort(key=lambda p: -p["_priority"])
        for p in profiles:
            del p["_priority"]
        if len(profiles) > 1:
            result.append({
                "name": c.get("name"),
                "description": (c.get("properties") or {}).get("device.description") or c.get("name"),
                "active": c.get("active_profile") or "",
                "profiles": profiles,
            })
    return result


def set_card_profile(card: str, profile: str) -> None:
    pw.run("pactl", "set-card-profile", card, profile, timeout=3, check=True)
