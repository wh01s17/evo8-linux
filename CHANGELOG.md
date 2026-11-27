# Cambios

Todos los cambios relevantes de evo8-linux. El formato sigue
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y las versiones,
[Semantic Versioning](https://semver.org/lang/es/).

Cómo publicar una versión: [`PUBLISH.md`](https://github.com/wh01s17/evo8-linux/blob/main/PUBLISH.md).

## [Sin publicar]

## [0.4.0] - 2026-11-27

### Cambiado

- Arriba de la ventana dice «Mezclador EVO 8» con la versión de la app, y
  las pestañas quedan en una línea propia, debajo.

### Agregado

- El micrófono virtual puede usar cualquiera de las 4 entradas de la EVO, no
  solo la 1 y la 2. En MICRÓFONO VIRTUAL, **+** agrega una entrada y ✕ la
  quita; también `evoctl mezcla add|remove N` y `evoctl mezcla inputs`. Es
  instantáneo y no corta el micrófono. Al volver, una entrada recupera su
  nivel. Empieza con las entradas 1 y 2, como antes.
- `evoctl mix get` devuelve 6 ganancias: las 4 de siempre y al final las de
  las entradas 3 y 4 (`mix set 5|6`).
- Tras actualizar, apaga y enciende la Mezcla una vez para cargar su config
  nueva: `evoctl mezcla off && evoctl mezcla on`.

### Documentación

- README: capturas nuevas de SONIDO DEL PC, MICRÓFONO VIRTUAL y EVO 8.

## [0.3.0] - 2026-11-27

### Cambiado

- La ventana separa las tres partes del proyecto en pestañas: **SONIDO DEL
  PC** (entradas, apps, salida y perfiles), **MICRÓFONO VIRTUAL** (la Mezcla,
  Compartido, la sincronía y qué apps van a Compartido) y **EVO 8** (el
  hardware). La pestaña CONSOLA ya no existe.
- En SONIDO DEL PC, el fader de cada entrada es su volumen en el sistema (lo
  que reciben todas las apps). La ganancia hacia la Mezcla está en
  MICRÓFONO VIRTUAL. Las entradas tienen medidor propio, las cuatro, aunque
  la Mezcla esté apagada.
- **El micrófono virtual se enciende y se apaga**: con el interruptor de la
  pestaña MICRÓFONO VIRTUAL o con `evoctl mezcla on|off|toggle|status`.
  Apagado, la Mezcla y Compartido no existen y las apps que estaban en
  Compartido vuelven a la salida. El estado se mantiene al reiniciar.
  Encenderlo o apagarlo no reinicia PipeWire ni corta el resto del audio:
  ahora la Mezcla corre como un servicio propio (`evo8-mezcla.service`) y no
  como parte de PipeWire.
- En una instalación nueva el micrófono virtual viene apagado.
  `evoctl setup` migra una instalación anterior: quita la config vieja y deja
  la Mezcla encendida. Hay que reiniciar PipeWire una vez.
- `evoctl apply --wait` espera a que aparezca la Mezcla antes de restaurar.
- `evo8-mixer --mezcla` abre directo en MICRÓFONO VIRTUAL.
- Se quitó la línea de leyenda bajo las pestañas. Lo que hace cada control
  se explica en un globo de ayuda al pasar el mouse (faders y PERFILES
  incluidos).

### Documentación

- README: un índice, y cómo instalar, actualizar y desinstalar con cada
  método (paquete de Arch, pipx y desde el código), y qué hacer después.

## [0.2.0] - 2026-11-22

### Agregado

- `evoctl setup` avisa cuando el portal de escritorio informa 0 µs de tiempo
  real mientras rtkit permite más. Pasa si rtkit se instala con la sesión
  abierta, y hace que el kernel mate los programas de audio (mpv, navegadores)
  y su sonido se corte. El aviso trae el comando que lo arregla.

### Corregido

- El monitor ya no fuerza el quantum bajo cuando la salida seleccionada es
  Bluetooth: era global y entrecortaba todo lo que sonaba. Si cambias a una
  salida Bluetooth con el monitor encendido, lo suelta en la siguiente
  revisión del estado.

## [0.1.1] - 2026-11-21

### Cambiado

- Los textos de la app y del paquete describen un uso general. En CONSOLA, el
  grupo de la Mezcla se llama «MICRÓFONO VIRTUAL», y la Mezcla se presenta
  como un micrófono para cualquier app.
- En PERFILES, la opción Bluetooth con micrófono dice «con micrófono, menor
  calidad».
- ACERCA DE: la nota de marca dice solo «EVO es una marca de Audient».

### Documentación

- README reorganizado, con capturas de la ventana y un diagrama de cómo viaja
  el audio y quién controla cada parte.
- `CHANGELOG.md` con los cambios de cada versión.

## [0.1.0] - 2026-11-21

Primera versión publicada.

### Hardware de la EVO 8 (por USB)

- Mezcla de monitoreo interna (10 entradas × 4 salidas) con faders, paneo y
  silencio; atajos: de fábrica, sin monitoreo directo, solo la entrada 1,
  entradas 1 y 2.
- Loop-back: elegir qué llega a los canales de captura 5-6.
- Phantom 48 V y silencio por entrada; ganancia de los preamps en dB.
- Los cambios van en una sola sesión USB al pulsar «Aplicar a la EVO».
- Al conectar la EVO, un servicio de usuario restaura preamps, mezcla interna
  y loop-back (el phantom nunca se enciende solo).

### Micrófono virtual para videollamadas (PipeWire)

- **Mezcla**: suma las entradas 1-2 y la salida virtual **Compartido**, con
  ganancia en vivo por canal.
- Monitor de la Mezcla o de una entrada suelta por la salida seleccionada, con
  latencia baja.
- Sincronía: `evoctl calibrate` y el botón *Calibrar* miden el desfase tocando
  sobre un click y retrasan Compartido solo hacia la Mezcla.
- El navegador (Meet, Zoom web) ya no baja el volumen del micrófono por su cuenta.

### Ventana `evo8-mixer`

- Pestañas CONSOLA (entradas, Compartido, apps, Mezcla, salida y perfiles de
  tarjeta), EVO 8 (hardware) y ACERCA DE (versión, firmware, instalación y un
  botón para copiar esos datos al reportar un problema).
- Cada control tiene un botón para volver a su valor estándar.
- Una sola ventana: volver a lanzarla la trae al frente, y abre otra si la
  anterior dejó de responder.
- Los perfiles de tarjeta explican qué hace cada uno.
- Cambio de pestaña en ~20 ms.
- Logo propio.

### CLI `evoctl`

- `mix`, `delay`, `listen`, `apply`, `restore`, `monitor`, `preamp`, `share`,
  `profiles`, `hw` y `calibrate`, con salida apta para scripts.
- `evoctl setup` instala en el usuario lo que pip no puede (config de PipeWire,
  servicio, menú e ícono) y dice qué falta; `--remove` lo deshace.
- `evoctl --version`.

### Instalación

- PyPI: `pipx install "evo8-linux[gui,usb]"` y luego `evoctl setup`.
- Arch Linux: `packaging/arch/PKGBUILD` (`evo8-linux-git`).
- CI en GitHub Actions: tests en Arch, paquete de Arch con `namcap` y el wheel
  instalado y probado en Ubuntu con Python 3.11 y 3.13.

[Sin publicar]: https://github.com/wh01s17/evo8-linux/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/wh01s17/evo8-linux/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/wh01s17/evo8-linux/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/wh01s17/evo8-linux/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/wh01s17/evo8-linux/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/wh01s17/evo8-linux/releases/tag/v0.1.0
