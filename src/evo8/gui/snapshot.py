"""One read of everything the mixer window shows that lives in PulseAudio terms.

`take()` runs three `pactl -f json` calls (sinks, sources, sink inputs) and
`build()` turns them into plain dicts the QML side can bind to. Volumes are
PulseAudio's 0..1 scale (raw / 65536), the same one pavucontrol and wpctl show.
`build()` is pure so it can be tested with recorded JSON.
"""

from __future__ import annotations

import json

from .. import mix, monitor, pw

NORM = 65536
# Our own plumbing and helpers never show up as "apps".
HIDDEN_PREFIXES = ("mezcla.", "evo8.", "wh01s17_speaker_tuning")


def _json(*args: str) -> list[dict]:
    try:
        data = json.loads(pw.run("pactl", "-f", "json", *args) or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def take() -> dict:
    return build(
        sinks=_json("list", "sinks"),
        sources=_json("list", "sources"),
        inputs=_json("list", "sink-inputs"),
        default_sink=pw.default_sink(),
    )


def _volumes(entry: dict) -> list[float]:
    vol = entry.get("volume") or {}
    return [round(ch.get("value", 0) / NORM, 4) for ch in vol.values() if isinstance(ch, dict)]


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _label(props: dict) -> str:
    return str(props.get("application.name") or props.get("media.name")
               or props.get("node.description") or props.get("node.name") or "App")


def build(sinks: list[dict], sources: list[dict], inputs: list[dict], default_sink: str) -> dict:
    sink = next((s for s in sinks if s.get("name") == default_sink), None)
    shared = next((s for s in sinks if s.get("name") == mix.SHARED_SINK), None)
    mezcla = next((s for s in sources if s.get("name") == mix.MIX_SOURCE), None)
    source = next((s for s in sources if s.get("name") == monitor.INPUT_SOURCE), None)

    out = {
        "sink": None,
        "source": None,
        "mezcla": None,
        "escucha": None,
        "streams": [],
    }
    if sink:
        props = sink.get("properties") or {}
        vols = _volumes(sink)
        out["sink"] = {
            "name": sink["name"],
            "label": str(props.get("device.nick") or props.get("device.description")
                         or sink.get("description") or sink["name"]),
            "isPro": "pro-output" in sink["name"],
            "volumes": vols,
            "mute": bool(sink.get("mute")),
        }
    if source:
        out["source"] = {"name": source["name"], "volumes": _volumes(source),
                         "mute": bool(source.get("mute"))}
    if mezcla:
        out["mezcla"] = {"volume": _avg(_volumes(mezcla)), "mute": bool(mezcla.get("mute"))}

    for si in inputs:
        props = si.get("properties") or {}
        name = str(props.get("node.name") or "")
        vols = _volumes(si)
        if name == mix.LISTEN_NODE:
            out["escucha"] = {"index": si["index"], "volume": _avg(vols), "mute": bool(si.get("mute"))}
            continue
        if name.startswith(HIDDEN_PREFIXES):
            continue
        out["streams"].append({
            "index": si["index"],
            "nodeId": str(props.get("object.id", "")),
            "label": _label(props),
            "volume": _avg(vols),
            "channels": len(vols) or 2,
            "mute": bool(si.get("mute")),
            "shared": bool(shared) and si.get("sink") == shared.get("index"),
        })
    return out


def raw(volume: float) -> str:
    return str(max(0, round(volume * NORM)))
