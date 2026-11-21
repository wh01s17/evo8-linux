"""Thin wrappers over the PipeWire / PulseAudio command-line tools.

Everything here shells out (pw-dump, pw-cli, pw-link, pw-metadata, pactl) so
the package needs no PipeWire bindings and behaves exactly like those tools.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field


class PwError(RuntimeError):
    pass


def run(*args: str, timeout: float = 5, check: bool = False) -> str:
    env = dict(os.environ, LC_ALL="C")
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
    except (OSError, subprocess.TimeoutExpired) as e:
        if check:
            raise PwError(f"{args[0]}: {e}") from e
        return ""
    if check and p.returncode != 0:
        raise PwError(p.stderr.strip() or f"{args[0]} failed ({p.returncode})")
    return p.stdout


# ---- nodes and params ----

def dump(object_id: int | None = None) -> list[dict]:
    out = run("pw-dump", *([str(object_id)] if object_id is not None else []))
    try:
        data = json.loads(out or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def node_id(name: str) -> int | None:
    for obj in dump():
        if obj.get("type") == "PipeWire:Interface:Node" and \
                obj.get("info", {}).get("props", {}).get("node.name") == name:
            return obj["id"]
    return None


def props_params(object_id: int) -> list[dict]:
    objs = dump(object_id)
    if not objs:
        return []
    return objs[0].get("info", {}).get("params", {}).get("Props", []) or []


def set_props(object_id: int, spa_pod: str) -> bool:
    """pw-cli set-param <id> Props <pod>; the pod is SPA-JSON text."""
    out = subprocess.run(["pw-cli", "set-param", str(object_id), "Props", spa_pod],
                         capture_output=True, text=True)
    return out.returncode == 0


def set_graph_param(object_id: int, param: str, value: float) -> bool:
    return set_props(object_id, f'{{ params = [ "{param}" {value:.6g} ] }}')


# ---- clock ----

def force_quantum() -> int:
    out = run("pw-metadata", "-n", "settings", "0", "clock.force-quantum")
    for line in out.splitlines():
        if "key:'clock.force-quantum'" in line and "value:'" in line:
            v = line.split("value:'", 1)[1].split("'", 1)[0]
            return int(v) if v.isdigit() else 0
    return 0


def set_force_quantum(value: int) -> None:
    run("pw-metadata", "-n", "settings", "0", "clock.force-quantum", str(value))


# ---- links ----

def output_ports() -> list[str]:
    return [l.strip() for l in run("pw-link", "-o").splitlines() if l.strip()]


def input_ports() -> list[str]:
    return [l.strip() for l in run("pw-link", "-i").splitlines() if l.strip()]


def links_from(port: str) -> list[str]:
    """Ports `port` (an output port) is linked to."""
    targets: list[str] = []
    current = None
    for line in run("pw-link", "-l").splitlines():
        if line and not line[0].isspace() and not line.startswith("|"):
            current = line.strip()
            continue
        s = line.strip()
        if current == port and s.startswith("|->"):
            targets.append(s[3:].strip())
    return targets


def link(src: str, dst: str) -> None:
    # --wait: return once the link exists, so a listing right after sees it.
    run("pw-link", "--wait", src, dst)


def unlink(src: str, dst: str) -> None:
    run("pw-link", "-d", src, dst)


# ---- pactl ----

def default_sink() -> str:
    return run("pactl", "get-default-sink").strip()


def sink_ports(sink: str | None = None, count: int = 2) -> list[str]:
    """First `count` playback ports of a sink (the selected output by default)."""
    sink = sink or default_sink()
    if not sink:
        return []
    prefix = f"{sink}:playback_"
    return [p for p in input_ports() if p.startswith(prefix)][:count]


@dataclass
class SinkInput:
    index: int
    sink: int
    props: dict = field(default_factory=dict)
    mute: bool = False

    @property
    def node_id(self) -> str:
        return str(self.props.get("object.id", ""))

    @property
    def node_name(self) -> str:
        return str(self.props.get("node.name", ""))


def sink_inputs() -> list[SinkInput]:
    out = run("pactl", "-f", "json", "list", "sink-inputs")
    try:
        data = json.loads(out or "[]")
    except json.JSONDecodeError:
        return []
    return [SinkInput(index=d.get("index", -1), sink=d.get("sink", -1),
                      props=d.get("properties", {}) or {}, mute=bool(d.get("mute")))
            for d in data]


def sink_index(name: str) -> int | None:
    for line in run("pactl", "list", "short", "sinks").splitlines():
        cols = line.split("\t")
        if len(cols) > 1 and cols[1] == name:
            return int(cols[0])
    return None
