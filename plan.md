# evo8-linux — plan del proyecto

Documento de traspaso: con esto cualquier agente (o persona) puede retomar el
proyecto sin el historial de la conversación. Mantenerlo al día al cerrar cada
etapa.

---

## 1. Objetivo

Reemplazar en Linux lo que hace **EVO Control** (la app oficial de Audient para
Windows/macOS) para la interfaz **Audient EVO 8**, y sumar lo que hace falta
para **dar clases de guitarra por videollamada** (Google Meet en Chrome):

1. Un micrófono virtual (**Mezcla**) con guitarra + voz + audio compartido
   (YouTube, metrónomo, backing tracks), con ganancias ajustables en vivo.
2. Escucharse sin latencia (monitor por hardware o por software).
3. Sincronía entre la música compartida y lo que se toca encima.
4. Control del hardware de la EVO: mezcla de monitoreo interna, loop-back,
   preamps, y lo que falte de EVO Control.
5. Una ventana de mezclador (estilo consola) y un CLI (`evoctl`).

Prioridad del usuario: **mantener las funciones del driver original** de la
forma más mantenible. Por eso todo vive en una librería Python; la interfaz es
un cliente delgado.

---

## 2. Contexto del usuario y del equipo

- Arch Linux, PipeWire + WirePlumber, Hyprland, shell propio en Quickshell
  ("wh01s17", dotfiles en `~/dotfiles`, gestionados con stow).
- Audient **EVO 8** (USB 2708:0007, firmware bcdDevice 1.4c), perfil de tarjeta
  **Pro Audio** (obligatorio: expone las entradas por separado).
- Entrada 1: pedal Mooer GE150 (guitarra, directo a la interfaz).
  Entrada 2: micrófono SE X1A (48 V). Audífonos M50x en la salida de
  audífonos 1 (sigue a las salidas 1-2).
- El usuario habla español. **Toda la interfaz y los mensajes van en español.**

### Reglas de producto que pidió el usuario (respetarlas)

- Nombres **directos y simples** de lo que hace cada cosa; nada de nombres o
  descripciones "de clases" (no "Alumno", "Clase", etc.).
- Las entradas se rotulan **solo por número** ("Entrada 1", "IN 1"), nunca
  "Guitarra"/"Micro": los puertos pueden cambiar.
- El monitor siempre suena por la **salida seleccionada** (la por defecto).
- Cada control de la ventana tiene un botón **󰑐 restablecer** a su valor
  estándar.
- Los archivos Python no deben pasar de **1000 líneas** (dividir en módulos).

---

## 3. Arquitectura

```
                ┌──────────────── evo8 (librería Python) ────────────────┐
 evoctl (CLI) ──┤ pw.py       pw-dump / pw-cli / pw-link / pactl wrappers   │
 ventana (Qt) ──┤ mix.py      ganancias, sincronía y escucha de la Mezcla   │
 shell/barra  ──┤ monitor.py  monitor general y por entrada (enlaces)       │
                │ alsa.py     controles que ya expone el kernel (preamps)   │
                │ apps.py     apps → Compartido, perfiles de tarjeta        │
                │ calibrate.py medición de sincronía (click + onsets)       │
                │ usb.py      transporte UAC2 (suelta/devuelve el driver)   │
                │ hw.py       loop-back y mezcla interna (unidades 51, 60)  │
                │ profiles.py perfiles de tarjeta curados                   │
                │ gui/        ventana PySide6: backend.py (QObject + worker │
                │             thread), snapshot.py (pactl JSON → modelo),   │
                │             meters.py (pw-record --raw), qml/             │
                │ state.py    estado persistente (~/.local/state/evo8)      │
                └───────────────────────────────────────────────────────────┘
 config/pipewire/  grafo de la Mezcla (filter-chain + loopbacks)
 udev/             acceso USB sin root (TAG+="uaccess")
```

### 3.1 Grafo de audio (config/pipewire/pipewire.conf.d/20-mezcla.conf)

```
EVO capture AUX0/AUX1 ─► mezcla.entradas (loopback) ─► mezcla.suma FL/FR
Apps ─► "Compartido" (sink virtual) ─► mezcla.compartido.escucha ─► salida por defecto
                                   └► mezcla.compartido (loopback) ─► mezcla.suma RL/RR
mezcla.suma = filter-chain: compL/compR (delay) ─► mix (Gain 1-4) ─► "Mezcla" (fuente mono)
```

- `mix:Gain 1/2` = entradas 1/2; `mix:Gain 3/4` = Compartido L/R (0.5 = -6 dB).
- `compL/compR:Delay (s)` = compensación de sincronía (solo hacia la suma).
- Las posiciones del sink deben ser estándar (FL FR RL RR): con AUX0/AUX1 el
  filter-chain entregaba silencio.
- Los puentes con destino fijo usan `node.dont-fallback` + `node.linger` (esperan
  a que vuelva el destino) y `state.restore-props = false` (WirePlumber no debe
  restaurar silencios/volúmenes viejos).
- `pipewire-pulse.conf.d/20-bloquear-volumen-micro.conf`: quirk
  `block-source-volume` para chrome/chromium/firefox (el AGC de Meet bajaba el
  micrófono).
- Los parámetros del filter-chain se pierden al reiniciar PipeWire →
  `evoctl apply` los restaura desde `~/.local/state/evo8/state.json`.

### 3.2 Monitor (monitor.py)

- General: `pw-link Mezcla:capture_MONO` → primeros 2 puertos `playback_*` de la
  salida por defecto; silencia `mezcla.compartido.escucha` (ya va en la mezcla) y
  fuerza `clock.force-quantum` = 128 (`EVO8_MONITOR_QUANTUM`).
- Por entrada: enlaza `…pro-input-0:capture_AUXn` a la salida; las entradas
  pedidas se guardan en `$XDG_RUNTIME_DIR/evo8-monitor-inputs`; mientras el
  general está encendido se suspenden.
- **Regla crítica**: los enlaces se sincronizan tocando solo lo que difiere
  (`_sync_port`). Re-enlazar lo ya enlazado dispara cambios en el nodo de salida;
  el shell llama a `follow` en esos cambios y se formaba un **bucle** que
  re-enlazaba varias veces por segundo (probable causa de xruns en una clase).
- `pw-link --wait` al enlazar, para que la lectura siguiente vea el enlace.
- `status` se auto-repara (marcador en `$XDG_RUNTIME_DIR/evo8-monitor`).

### 3.3 Ventana (src/evo8/gui)

- `backend.Backend` es el objeto `mixer` en QML: propiedades `model`,
  `meters`, `hardware` (QVariant) y slots de escritura.
- Todo lo lento corre en un único hilo de trabajo, en orden. Sondeo: 1 s para
  pactl (dispositivos, streams, volúmenes), 3 s para ganancias, retardo,
  preamps, monitor y perfiles. Las escrituras se aplican al modelo al instante,
  se agrupan 60 ms por clave y el valor sondeado de esa clave se ignora 1,5 s.
- Volúmenes en la escala de PulseAudio (raw/65536), como pavucontrol.
- Medidores: un `pw-record --raw` por fuente (mezcla.suma 4 canales,
  Mezcla 1 canal), pasivos y con `node.name = evo8.meter.*`.
- Hardware: cambios en espera; "Aplicar a la EVO" hace una sola sesión USB y
  relee. El último estado leído se guarda en `state.json` (`hw`).
- QML sin dependencias del shell: `Theme.qml` (singleton), `PixelSlider`,
  `Toggle`, `GlyphButton`, `VMeter`, `Strip`, `ConsolePage`, `HardwarePage`.

### 3.4 Control del hardware por USB (usb.py, hw.py)

Detalle completo en `docs/protocolo-usb.md`. Resumen:

- EVO Control usa **peticiones UAC2 de clase estándar** a la interfaz 0:
  `bmRequestType 0x21/0xA1`, `bRequest` CUR(1)/RANGE(2),
  `wValue = (selector<<8)|canal`, `wIndex = (unidad<<8)|0`.
- Linux bloquea peticiones de clase a la interfaz 0 mientras `snd-usb-audio` la
  tiene (`EBUSY`). `usb.session()` suelta el driver de las interfaces 0-2,
  reclama la 0, envía, y reengancha la 0 (el driver vuelve a tomar 1-2).
  Retención medida: **~0,12 s**; la tarjeta y la Mezcla vuelven solas.
- **NUNCA** enviar peticiones de clase a la interfaz 3 (DFU): colgó el firmware
  y la EVO cayó del bus; solo se recuperó desconectando el USB.

| Unidad | Qué es | Estado |
|--------|--------|--------|
| 51, selector 6 | Ruteo de captura (1 byte/canal 0-5). Fuentes 0-5 = entradas, 6-11 = PC 1-6. Fábrica `[0,1,2,3,10,11]` | **Confirmado con audio** |
| 60, selector 1 | Mezcla de monitoreo 10×4, canal = `entrada*4+salida`, s16 dB×256, -128 = off | **Lectura/escritura confirmadas**; orden de entradas por confirmar con audio |
| 58 | `UacXUAudientInputControl` (por entrada: ¿phantom, mute, smart gain, monitor?) | Pendiente |
| 59 | `UacXUAudientOutputControl` (ALSA "Extension Unit Switch" = off) | Pendiente |
| 11 / 10 | FU: preamp ("Mic Playback Volume") / volumen de salida | Ya en ALSA |
| 50, 57 | XU sin mapear (50 alimenta al Mixer Unit) | Pendiente |

Los selectores de los envoltorios de EVO.exe (0x6589e0…0x658f10) están
listados en `docs/protocolo-usb.md`; los de 0x485xxx-0x486xxx pertenecen al
MonitorController del EVO 16 (no aplica al EVO 8).

---

## 4. Estado actual

### Hecho

- Paquete `evo8` + CLI `evoctl` (equivalente probado de los scripts bash que
  había en los dotfiles; salidas JSON idénticas).
- Monitor general y por entrada, con el bug del bucle corregido.
- Calibración de sincronía (análisis probado con señal sintética: 85 ms → 85 ms).
- Transporte USB y `evoctl hw loopback get|set`, `evoctl hw mix get|set`.
- Tests (`make test`): parseo de pw-link/amixer, preamp, calibración,
  snapshot de la ventana y perfiles.
- Repo público: https://github.com/wh01s17/evo8-linux
- Preamps guardados: la EVO vuelve a -8 dB tras un corte de energía;
  `evoctl apply` los restaura.
- **Ventana del mezclador** (`evo8-mixer`, PySide6 + QML en
  `src/evo8/gui/`): pestaña CONSOLA (ENTRADAS con PRE/fader/MONITOR,
  COMPARTIDO con OÍR/SINC, APPS con compartir/mute, MEZCLA con MONITOR, SALIDA
  por pares, PERFILES) y pestaña EVO 8 (loop-back y mezcla interna 10×4 con
  cambios en espera y "Aplicar a la EVO"). `evo8-mixer --evo` abre en la
  pestaña de hardware. App id Wayland: `evo8-mixer`.

### En los dotfiles (`~/dotfiles`)

Migración hecha (commits 9e3a02b, 942f1bf, 2dd4ed4): el panel de audio de la
barra muestra "Abrir mezclador" solo si `evo8-mixer` está instalado, lo lanza
(una sola ventana; la enfoca con `hyprctl dispatch 'hl.dsp.focus(...)'`) y
llama a `evoctl apply; evoctl monitor follow` cuando reaparece `mezcla.suma`
y a `evoctl monitor follow` cuando cambia la salida. Se borraron los scripts
`wh01s17-audio-*` de la Mezcla, el plugin Quickshell `wh01s17.mixer` y la
copia de `20-mezcla.conf`. Hyprland: regla `class ^evo8-mixer$` flotante
1640×640. En `shell.json` quedan cambios ajenos del usuario: no commitearlos.

---

## 5. Próximos pasos (en orden)

1. **Confirmar el monitoreo de la guitarra**: con la mezcla interna en 0 dB
   (estado tras reconectar), preguntar al usuario si oye la entrada 1 directa.
   Si no, investigar unidades 58/59 (posible mute/monitor por entrada o bypass
   de salida).
2. **Mapear unidades 58 y 59** desde EVO.exe: leer los llamadores de
   `InputControlModel` (0x47c0a0…) y `OutputControlModel` (0x47ebc0…) y los
   envoltorios `FUN_00658cb0`, `0x658c80`, `0x658d00`, `0x658b40`. Probar
   primero con GET, después SET reversibles a volumen bajo.
3. **Comandos de alto nivel** en `hw.py`: presets de mezcla interna
   ("entradas 1-2 a los audífonos", "sin monitoreo directo"), loop-back por
   nombre, y persistir/restaurar la configuración de hardware al conectar la
   EVO (regla udev o servicio de usuario).
4. **Ventana**: hecha. Pendiente: botón Calibrar en la tira COMP (corre
   `calibrate.run` en el worker y muestra el resultado), atajos de teclado,
   tema leído desde el shell wh01s17 si existe, y presets para la mezcla
   interna ("entradas a audífonos", "sin monitoreo directo").
5. **Migrar los dotfiles**: hecho (ver §4).
6. **Ruta sin cortes (opcional, a futuro)**: que `snd-usb-audio` exponga el
   Mixer Unit 60 como controles ALSA. Los descriptores son válidos; averiguar
   por qué el kernel no crea los controles (recargar el módulo con
   `dyndbg` y mirar `dmesg`; requiere sudo y corta el audio). Posible parche o
   quirk upstream.
7. Calibrar la sincronía con el usuario tocando (`evoctl calibrate --apply`).
8. Commit inicial y, si el usuario quiere, publicar el repo.

---

## 6. Cómo trabajar

```
make test                          # tests sin hardware
PYTHONPATH=src python3 -m evo8.cli <comando>   # sin instalar
make install                       # evoctl en ~/.local/bin (apunta a este checkout)
sudo make udev                     # acceso USB (ya instalado en la máquina del usuario)
```

### Reglas de seguridad con el hardware

- Antes de escribir algo nuevo: leer (GET) y anotar el valor original.
- Probar escrituras reversibles, a volumen bajo (tonos ≤ -30 dBFS), y
  restaurar al terminar. Avisar al usuario cuando algo suene.
- Agrupar escrituras en una sola `session()`: cada sesión corta el audio.
- Nunca durante una clase/llamada; nunca reiniciar PipeWire ni el shell si el
  usuario está en llamada.
- Si la EVO deja de responder (`-71` en `journalctl -k`), pedir al usuario que
  la desconecte y reconecte; no insistir con resets.

### Ingeniería inversa (para seguir mapeando)

- Instalador: `~/Downloads/EVO-v4.4.0a.exe` (NSIS) → `7z x` → `EVO/EVO.exe`
  (PE32, JUCE, SHA-256 `d49e1189…c0ce15`).
- Descompilación completa: REA (`npx -y rea-agents@6.9.0 decompile-all EVO.exe
  --output <dir> --provider ghidra`, con `GHIDRA_INSTALL_DIR=/opt/ghidra`);
  ~17 000 funciones, ~15 min.
- Vtables y llamadores: `tools/ghidra/DumpUacVtables.java` con
  `/opt/ghidra/support/analyzeHeadless <proj> evo -import EVO.exe
  -scriptPath tools/ghidra -postScript DumpUacVtables.java <salida.txt>`.
- Claves: `FUN_00658570(req, selector, canal, datos, largo)` = petición a una
  XU; `FUN_00658f10` = cruce del Mixer Unit; `FUN_00658ed0` = volumen de FU;
  constructores de modelos con el id de unidad (`FUN_00656310(…, 0x3a)` etc.).

### Convenciones de código

- Python ≥ 3.11, sin dependencias obligatorias (pyusb y PySide6 opcionales).
- Comentarios y docstrings en inglés; textos para el usuario en español.
- Salida del CLI apta para máquinas (JSON o un valor por línea); mensajes de
  error a stderr.
- Máximo 1000 líneas por archivo Python.
- Commits: Conventional Commits; el usuario decide cuándo commitear/pushear.
