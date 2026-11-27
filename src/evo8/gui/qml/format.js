.pragma library
// Formatting helpers for the mixer window (mirrors tests in tests/test_gui.py).

function signedDb(db) {
    var d = Math.round(Number(db) * 10) / 10
    if (!isFinite(d)) return "—"
    return (d > 0 ? "+" : "") + d.toFixed(1) + " dB"
}

// A value typed by hand ("24,5", "+12 dB", "-3") -> a number within
// [min, max] on the control's step grid; null when it is not a number.
function parseTyped(text, min, max, step) {
    var s = String(text).replace(/db/i, "").replace(",", ".").trim()
    if (!/^[+-]?(\d+\.?\d*|\.\d+)$/.test(s)) return null
    var v = Math.min(Number(max), Math.max(Number(min), Number(s)))
    var st = Number(step)
    if (st > 0) v = Number(min) + Math.round((v - Number(min)) / st) * st
    return Math.round(Math.min(Number(max), v) * 1e6) / 1e6
}

// Linear gain as decibels.
function gainDb(gain) {
    var g = Number(gain)
    if (!(g > 0)) return "-∞ dB"
    var r = Math.round(20 * Math.log(g) / Math.LN10 * 10) / 10
    if (r === 0) return "0.0 dB"
    return (r > 0 ? "+" : "") + r.toFixed(1) + " dB"
}

function percent(v) { return Math.round(Number(v || 0) * 100) + "%" }

function delayText(ms) { var v = Number(ms); return isFinite(v) ? Math.round(v) + " ms" : "—" }

// Peak 0..1 linear -> 0..1 on a -60..0 dBFS scale.
function meterLevel(peak) {
    var p = Number(peak)
    if (!(p > 0)) return 0
    var db = 20 * Math.log(p) / Math.LN10
    if (db <= -60) return 0
    return Math.min(1, (db + 60) / 60)
}

// "hot" above -3 dBFS, "loud" from -12 dBFS.
function meterZone(pos) {
    if (pos > 57 / 60) return "hot"
    if (pos > 48 / 60) return "loud"
    return "normal"
}

// At the standard value, within half a step.
function atDefault(value, standard, step) {
    if (standard === undefined || standard === null || isNaN(standard)) return true
    return Math.abs(Number(value) - Number(standard)) <= Math.max(1e-6, Math.abs(Number(step) || 0) / 2)
}

// Hardware mix cell: -128 = off.
function hwDb(db) {
    if (db === undefined || db === null) return "?"
    if (db <= -127.5) return "off"
    return Math.round(db) + ""
}

// ---- EVO internal mix: level + pan <-> the left/right cells of one output pair ----
// Pan law of a balance control: centred, both sides sit at the level (as the
// EVO's factory mix, all at 0 dB); panning attenuates the other side by
// 20·log10(1 - |pan|), reaching off at the edge. Levels below `floor` are off.
var HW_OFF = -128

function hwToLinear(db) { return db <= -127.5 ? 0 : Math.pow(10, db / 20) }

// {level, pan, muted} from a left and right cell (dB, -128 = off).
function hwLevelPan(l, r) {
    if (l === null || r === null || l === undefined || r === undefined) return null
    var gl = hwToLinear(l), gr = hwToLinear(r)
    if (gl === 0 && gr === 0) return { level: HW_OFF, pan: 0, muted: true }
    var level = Math.max(l, r)
    var pan = 0
    if (gl > gr) pan = -(1 - gr / gl)
    else if (gr > gl) pan = 1 - gl / gr
    return { level: level, pan: Math.round(pan * 100) / 100, muted: false }
}

// [left dB, right dB] for a level and pan; `floor` and below means off.
function hwCells(level, pan, floor) {
    if (level <= floor) return [HW_OFF, HW_OFF]
    var p = Math.max(-1, Math.min(1, Number(pan) || 0))
    function side(att) {
        var k = 1 - att
        if (k <= 0.001) return HW_OFF
        return Math.max(floor, level + 20 * Math.log(k) / Math.LN10)
    }
    return [side(Math.max(0, p)), side(Math.max(0, -p))]
}

function panText(p) {
    var v = Math.round(Number(p) * 100)
    if (v === 0) return "C"
    return (v < 0 ? "L " : "R ") + Math.abs(v)
}
