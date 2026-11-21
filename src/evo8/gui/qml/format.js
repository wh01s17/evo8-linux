.pragma library
// Formatting helpers for the mixer window (mirrors tests in tests/test_gui.py).

function signedDb(db) {
    var d = Math.round(Number(db) * 10) / 10
    if (!isFinite(d)) return "—"
    return (d > 0 ? "+" : "") + d.toFixed(1) + " dB"
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
