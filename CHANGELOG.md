# Cambios

Todos los cambios relevantes de evo8-linux. El formato sigue
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y las versiones,
[Semantic Versioning](https://semver.org/lang/es/).

Cómo publicar una versión: [`PUBLISH.md`](https://github.com/wh01s17/evo8-linux/blob/main/PUBLISH.md).

## [Sin publicar]

### Documentación

- README reorganizado, con capturas de la ventana y un diagrama de cómo viaja
  el audio y quién controla cada parte.

## [0.1.0] - 2026-11-21

Primera versión publicada.

### Hardware de la EVO 8 (por USB)

- Mezcla de monitoreo interna (10 entradas × 4 salidas) con faders, paneo y
  silencio, como en EVO Control; atajos: de fábrica, sin monitoreo directo,
  solo la entrada 1, entradas 1 y 2.
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

[Sin publicar]: https://github.com/wh01s17/evo8-linux/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/wh01s17/evo8-linux/releases/tag/v0.1.0
