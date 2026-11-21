"""evoctl: command-line control of the Audient EVO 8 setup.

Output stays machine-friendly (JSON or one bare value per line) so the mixer
window and shell widgets can read it; messages for people go to stderr.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import alsa, apps, calibrate, mix, monitor


def _json(value) -> None:
    print(json.dumps(value, separators=(",", ":"), ensure_ascii=False))


def _on_off(word: str) -> bool | None:
    return {"on": True, "off": False, "toggle": None}[word]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="evoctl", description="Control del Audient EVO 8 y la Mezcla en Linux.")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("mix", help="ganancias de la Mezcla (1-2 entradas, 3-4 Compartido L/R)")
    ms = m.add_subparsers(dest="action", required=True)
    ms.add_parser("get", help="las cuatro ganancias, en JSON")
    s = ms.add_parser("set", help="una ganancia, lineal 0..4")
    s.add_argument("n", type=int, choices=range(1, 5))
    s.add_argument("gain", type=float)

    d = sub.add_parser("delay", help="compensación de sincronía de Compartido hacia la Mezcla")
    ds = d.add_subparsers(dest="action", required=True)
    ds.add_parser("get", help="retardo actual en ms")
    s = ds.add_parser("set", help="retardo en ms (0..500)")
    s.add_argument("ms", type=float)

    l = sub.add_parser("listen", help="nivel de escucha de Compartido")
    l.add_subparsers(dest="action", required=True).add_parser("save", help="guardar el nivel actual")

    sub.add_parser("apply", help="restaurar lo guardado: ganancias, retardo, escucha y preamps")

    mo = sub.add_parser("monitor", help="escuchar la Mezcla o entradas sueltas por la salida")
    mos = mo.add_subparsers(dest="action", required=True)
    for name in ("status", "on", "off", "toggle", "follow"):
        mos.add_parser(name)
    mos.add_parser("inputs", help="una marca 0/1 por entrada, en JSON")
    s = mos.add_parser("input", help="monitorear una entrada sola")
    s.add_argument("n", type=int)
    s.add_argument("state", choices=("on", "off", "toggle"))

    pr = sub.add_parser("preamp", help="ganancia de preamp por entrada (dB)")
    prs = pr.add_subparsers(dest="action", required=True)
    prs.add_parser("get")
    s = prs.add_parser("set")
    s.add_argument("n", type=int)
    s.add_argument("db", type=float)

    sh = sub.add_parser("share", help="enviar una app a Compartido o devolverla")
    shs = sh.add_subparsers(dest="action", required=True)
    shs.add_parser("list", help="node ids en Compartido, uno por línea")
    for name in ("on", "off"):
        shs.add_parser(name).add_argument("node_id")

    pf = sub.add_parser("profiles", help="perfiles de las tarjetas de sonido")
    pfs = pf.add_subparsers(dest="action", required=True)
    pfs.add_parser("list")
    s = pfs.add_parser("set")
    s.add_argument("card")
    s.add_argument("profile")

    hw = sub.add_parser("hw", help="ajustes del hardware por USB (corta el audio ~1 s)")
    hws = hw.add_subparsers(dest="area", required=True)
    lb = hws.add_parser("loopback", help="fuente de los canales 5-6 de captura")
    lbs = lb.add_subparsers(dest="action", required=True)
    lbs.add_parser("get")
    lbs.add_parser("set").add_argument("source", help="loopback | pc12 | pc34 | in12 | in34")
    hm = hws.add_parser("mix", help="mezcla de monitoreo interna (10 entradas × 4 salidas)")
    hms = hm.add_subparsers(dest="action", required=True)
    hms.add_parser("get", help="matriz en dB, JSON")
    s = hms.add_parser("set", help="un cruce: entrada (1-10) salida (1-4) dB u off")
    s.add_argument("input", type=int)
    s.add_argument("output", type=int)
    s.add_argument("db")

    c = sub.add_parser("calibrate", help="medir la sincronía tocando sobre un click")
    c.add_argument("--apply", action="store_true", help="aplicar el valor medido")
    c.add_argument("--recording", help="analizar una grabación de 4 canales existente")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _dispatch(args)
    except (mix.MixError, monitor.MonitorError, alsa.AlsaError, apps.AppsError,
            calibrate.CalibrationError, RuntimeError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1


def _dispatch(a) -> int:
    if a.cmd == "mix":
        if a.action == "get":
            _json(mix.gains())
        else:
            mix.set_gain(a.n, a.gain)
    elif a.cmd == "delay":
        if a.action == "get":
            print(mix.delay_ms())
        else:
            mix.set_delay_ms(a.ms)
    elif a.cmd == "listen":
        mix.save_listen_level()
    elif a.cmd == "apply":
        mix.apply()
        alsa.restore_preamp()
    elif a.cmd == "monitor":
        if a.action == "status":
            print(monitor.status())
        elif a.action == "on":
            monitor.turn_on()
        elif a.action == "off":
            monitor.turn_off()
        elif a.action == "toggle":
            monitor.toggle()
        elif a.action == "follow":
            monitor.follow()
        elif a.action == "inputs":
            _json(monitor.inputs())
        else:
            monitor.set_input(a.n, _on_off(a.state))
    elif a.cmd == "preamp":
        if a.action == "get":
            _json(alsa.preamp())
        else:
            alsa.set_preamp(a.n, a.db)
    elif a.cmd == "share":
        if a.action == "list":
            for nid in apps.shared_streams():
                print(nid)
        else:
            apps.share(a.node_id, a.action == "on")
    elif a.cmd == "profiles":
        if a.action == "list":
            _json(apps.card_profiles())
        else:
            apps.set_card_profile(a.card, a.profile)
    elif a.cmd == "hw":
        from . import hw
        if a.area == "loopback":
            if a.action == "get":
                _json(hw.loopback_get())
            else:
                hw.loopback_set(a.source)
        elif a.action == "get":
            _json(hw.mixer_get())
        else:
            db = hw.MIXER_OFF_DB if a.db == "off" else float(a.db)
            hw.mixer_set([(a.input - 1, a.output - 1, db)])
    elif a.cmd == "calibrate":
        if a.recording:
            from pathlib import Path
            result = calibrate.analyse(Path(a.recording))
            if a.apply:
                mix.set_delay_ms(result.median_ms)
        else:
            result = calibrate.run(apply=a.apply)
        print(result.summary)
        if a.apply:
            print(f"Compensación aplicada: {result.median_ms} ms.")
        print(f"RESULT {result.median_ms}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
