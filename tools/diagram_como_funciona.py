"""Draws docs/img/como-funciona.svg: python3 tools/diagram_como_funciona.py docs/img/como-funciona.svg"""
import sys
from xml.sax.saxutils import escape as esc

BG, PANEL, BOX, EDGE = "#12171a", "#161d21", "#1c2529", "#2f3c42"
FG, DIM, GREEN, AMBER, BLUE = "#d6dfd2", "#8a978d", "#84c959", "#e8b53f", "#7fb4d9"
FONT = "JetBrains Mono, DejaVu Sans Mono, Menlo, Consolas, monospace"
W, H = 980, 640
out = []
def add(s): out.append(s)

def text(x, y, s, size=13, color=FG, weight="normal", anchor="start"):
    add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{esc(s)}</text>')

def box(x, y, w, h, title, sub=(), accent=None, fill=BOX):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{accent or EDGE}" stroke-width="{2 if accent else 1.5}"/>')
    cy = y + 24
    text(x + 12, cy, title, 14, FG, "bold")
    for line in sub:
        cy += 18
        text(x + 12, cy, line, 11.5, DIM)

def arrow(points, color, label=None, lx=None, ly=None, dashed=False, anchor="middle"):
    d = "M " + " L ".join(f"{px} {py}" for px, py in points)
    dash = ' stroke-dasharray="6 5"' if dashed else ""
    mid = {GREEN: "g", AMBER: "a", BLUE: "b"}[color]
    add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"{dash} marker-end="url(#{mid})"/>')
    if label:
        text(lx, ly, label, 11, color, anchor=anchor)

add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">')
add(f'<title>Cómo funciona evo8-linux</title>')
add('<defs>' + "".join(
    f'<marker id="{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
    f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/></marker>' for k, c in (("g", GREEN), ("a", AMBER), ("b", BLUE))) + '</defs>')
add(f'<rect width="{W}" height="{H}" rx="14" fill="{BG}"/>')

# ---------- audio ----------
add(f'<rect x="16" y="16" width="{W-32}" height="352" rx="10" fill="{PANEL}" stroke="{EDGE}"/>')
text(32, 42, "AUDIO", 12, GREEN, "bold")
text(92, 42, "lo que sale por el micrófono virtual y lo que escuchas (PipeWire)", 12, DIM)

box(36, 70, 190, 62, "EVO 8 · IN 1-2", ("entradas de la interfaz",))
box(36, 226, 190, 62, "Apps", ("YouTube, metrónomo,", "backing tracks"))
box(276, 70, 190, 62, "Entradas", ("mezcla.entradas",))
box(276, 226, 190, 62, "Compartido", ("salida virtual:", "le mandas apps"))
add(f'<rect x="516" y="62" width="200" height="118" rx="6" fill="{BOX}" stroke="{GREEN}" stroke-width="2"/>')
text(528, 86, "Suma", 14, FG, "bold")
text(574, 86, "mezcla.suma", 11.5, DIM)
for i, (k, v) in enumerate((("SINC", "retrasa Compartido"), ("FADER", "ganancia por canal"))):
    y = 116 + i * 34
    add(f'<rect x="526" y="{y-16}" width="180" height="26" rx="4" fill="{BG}" stroke="{EDGE}"/>')
    text(534, y + 1, k, 10.5, GREEN, "bold")
    text(578, y + 1, v, 10.5, FG)
box(766, 70, 180, 62, "Mezcla", ("micrófono virtual",), accent=GREEN)
box(766, 226, 180, 62, "Salida", ("la seleccionada:", "audífonos o parlantes"))
add(f'<rect x="776" y="158" width="160" height="30" rx="15" fill="{BG}" stroke="{EDGE}"/>')
text(856, 178, "OBS · DAW · Meet …", 11.5, FG, anchor="middle")

arrow([(226, 101), (276, 101)], GREEN)
arrow([(466, 101), (516, 101)], GREEN)
arrow([(226, 257), (276, 257)], GREEN)
arrow([(466, 246), (616, 246), (616, 180)], GREEN, "a la Mezcla", 548, 238, anchor="middle")
arrow([(466, 272), (766, 272)], GREEN, "lo escuchas tú", 616, 290)
arrow([(716, 101), (766, 101)], GREEN)
arrow([(856, 132), (856, 158)], GREEN)
arrow([(946, 112), (958, 112), (958, 248), (946, 248)], GREEN, dashed=True)
text(952, 340, "MONITOR: te escuchas", 11, GREEN, anchor="end")
text(952, 356, "(Mezcla o una entrada → Salida)", 11, DIM, anchor="end")
text(36, 330, "SINC compensa la latencia: quien toca sobre la música la oye tarde,", 11.5, DIM)
text(36, 348, "así que la música se retrasa solo hacia la Mezcla (evoctl calibrate).", 11.5, DIM)

# ---------- control ----------
y0 = 392
add(f'<rect x="16" y="{y0}" width="{W-32}" height="{H-y0-16}" rx="10" fill="{PANEL}" stroke="{EDGE}"/>')
text(32, y0 + 26, "CONTROL", 12, AMBER, "bold")
text(110, y0 + 26, "quién mueve cada cosa", 12, DIM)

box(36, y0 + 58, 190, 62, "evo8-mixer", ("la ventana",))
box(36, y0 + 138, 190, 62, "evoctl", ("la línea de comandos",))
box(276, y0 + 92, 190, 72, "librería evo8", ("Python: un solo lugar", "para la lógica"))
box(516, y0 + 50, 200, 66, "PipeWire", ("pw-cli · pactl · pw-link", "al instante, sin cortes"), accent=BLUE)
box(516, y0 + 140, 200, 66, "USB · UAC2", ("suelta el driver ~0,1 s", "corta el audio un momento"), accent=AMBER)
box(766, y0 + 50, 180, 156, "EVO 8 hardware", ("mezcla interna 10×4", "  (monitoreo directo,", "   sin latencia)", "loop-back", "preamps · 48 V", "silencio por entrada"), accent=AMBER)

arrow([(226, y0 + 89), (251, y0 + 89), (251, y0 + 116), (276, y0 + 116)], AMBER)
arrow([(226, y0 + 169), (251, y0 + 169), (251, y0 + 140), (276, y0 + 140)], AMBER)
arrow([(466, y0 + 112), (491, y0 + 112), (491, y0 + 83), (516, y0 + 83)], BLUE)
arrow([(466, y0 + 144), (491, y0 + 144), (491, y0 + 173), (516, y0 + 173)], AMBER)
arrow([(716, y0 + 173), (766, y0 + 173)], AMBER)
arrow([(616, y0 + 50), (616, 368)], BLUE, dashed=True)
text(626, y0 + 14, "ganancias, retraso, monitor, apps", 11, BLUE)
add('</svg>')
open(sys.argv[1], "w").write("\n".join(out) + "\n")
