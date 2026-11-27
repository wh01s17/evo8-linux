<p align="center"><img src="https://raw.githubusercontent.com/wh01s17/evo8-linux/main/src/evo8/data/evo8-mixer.svg" width="112" alt="Logo de evo8-linux: un 8 en píxeles con los colores de un medidor de nivel"></p>

# evo8-linux

<p>
<a href="https://pypi.org/project/evo8-linux/"><img src="https://img.shields.io/pypi/v/evo8-linux?label=PyPI" alt="Versión en PyPI"></a>
<a href="https://github.com/wh01s17/evo8-linux/actions/workflows/ci.yml"><img src="https://github.com/wh01s17/evo8-linux/actions/workflows/ci.yml/badge.svg" alt="Estado del CI"></a>
<img src="https://img.shields.io/badge/licencia-MIT-blue" alt="Licencia MIT">
</p>

Control del **Audient EVO 8** en Linux: una ventana tipo consola y un CLI
para la interfaz y para el audio del sistema.

En Linux la EVO 8 funciona como interfaz de audio estándar, pero el kernel no
expone su mezcla de monitoreo interna, el ruteo del loop-back ni el phantom.
evo8-linux los controla hablando con la interfaz directamente por USB. Además
incluye un mezclador para PipeWire y, si lo necesitas, un micrófono virtual que
junta tus entradas con el audio de otras apps.

Son tres partes separadas, cada una con su pestaña en la ventana:

| Parte | Pestaña | Qué toca |
|---|---|---|
| [El hardware de la EVO 8](#el-hardware-de-la-evo-8) | EVO 8 | La interfaz misma, por USB |
| [El sonido del PC](#el-sonido-del-pc) | SONIDO DEL PC | Volúmenes y dispositivos del sistema (PipeWire) |
| [El micrófono virtual](#el-micrófono-virtual-opcional) | MICRÓFONO VIRTUAL | Un dispositivo virtual que se enciende y se apaga |

![La pestaña SONIDO DEL PC: las cuatro entradas de la EVO con preamp, volumen, medidor y monitor, las apps, la salida seleccionada por pares de canales y los perfiles de cada tarjeta](https://raw.githubusercontent.com/wh01s17/evo8-linux/main/docs/img/sonido.png)

## Índice

- [Qué hace](#qué-hace)
  - [El hardware de la EVO 8](#el-hardware-de-la-evo-8)
  - [El sonido del PC](#el-sonido-del-pc)
  - [El micrófono virtual (opcional)](#el-micrófono-virtual-opcional)
- [Instalación](#instalación)
  - [Arch Linux](#arch-linux)
  - [Otras distribuciones (pipx)](#otras-distribuciones-pipx)
  - [Desde el código](#desde-el-código)
  - [Después de actualizar o desinstalar](#después-de-actualizar-o-desinstalar)
  - [Primeros pasos](#primeros-pasos)
- [Uso](#uso)
  - [La ventana](#la-ventana)
  - [La línea de comandos](#la-línea-de-comandos)
  - [Si el audio se corta](#si-el-audio-se-corta)
- [Cómo funciona](#cómo-funciona)
- [El repositorio](#el-repositorio)
- [Advertencia](#advertencia)
- [Licencia](#licencia)

## Qué hace

### El hardware de la EVO 8

- **Mezcla de monitoreo interna**: lo que oyes directo en los audífonos, sin
  pasar por el PC y sin latencia. Es la matriz de 10 entradas (4 analógicas y
  6 del PC) × 4 salidas, con fader, paneo y silencio, y atajos como «Como de
  fábrica» u «Oír entradas 1 y 2».
- **Loop-back**: qué llega a los canales de captura 5-6. Puede ser el par de
  fábrica, todo lo que suena en el PC (salidas 1-2), las salidas 3-4 o las
  entradas 1-2 / 3-4.
- **Entradas**: ganancia del preamp en dB, phantom 48 V y silencio.
- **Al conectarla**: la EVO olvida esos ajustes cuando se apaga. Un servicio
  los restaura al conectarla. El phantom nunca se enciende solo.

### El sonido del PC

Un mezclador para el audio del sistema. Funciona igual con el micrófono
virtual encendido o apagado.

- **Entradas**: preamp, volumen en el sistema y medidor de cada entrada de la
  EVO.
- **Apps y salida**: volumen, silencio y medidores de lo que suena y de la
  salida seleccionada, por canal.
- **Monitor de entrada**: escuchar una entrada por la salida seleccionada, con
  latencia baja.
- **Perfiles de tarjeta**: elegir cómo usa el sistema cada tarjeta de sonido,
  con lo que hace cada opción.
- Los navegadores no pueden cambiar el volumen de los micrófonos por su
  cuenta (el control automático de ganancia de las videollamadas lo hacía).

### El micrófono virtual (opcional)

Un dispositivo virtual que **se enciende y se apaga** con un interruptor.
Apagado no existe: no aparece en las apps y el resto del sonido no cambia.

- **Mezcla**: un micrófono que suma las entradas 1-2 de la EVO y una salida
  virtual, **Compartido**. Lo que mandes a Compartido (música, un metrónomo,
  un backing track) lo escuchas tú y también sale por la Mezcla. Cualquier app
  puede usarla como micrófono: OBS, un DAW, Discord o el navegador.
- **Ganancia en vivo** por canal, y apps que se mandan a Compartido de a una.
- **Sincronía**: quien toca sobre la música la oye con retraso, y su
  instrumento llega con otro. *Calibrar* mide ese desfase mientras tocas sobre
  un click y lo compensa retrasando la música solo hacia la Mezcla.
- **Monitor de la Mezcla**: escuchar el micrófono completo, tal como lo
  reciben las apps.

![La pestaña MICRÓFONO VIRTUAL encendida: el interruptor arriba, cuánto entra de las entradas 1-2 y de Compartido, el retardo de sincronía con Calibrar, las apps que se pueden mandar a Compartido y la Mezcla con su monitor](https://raw.githubusercontent.com/wh01s17/evo8-linux/main/docs/img/mezcla.png)

## Instalación

Solo para la **Audient EVO 8** (no la EVO 4 ni la EVO 16). El control por USB
se probó con el firmware 1.4c.

Hay tres formas de instalarla. Elige una sola: si mezclas dos, los comandos
de una tapan a los de la otra. `evoctl --version` dice cuál versión tienes.

### Arch Linux

**Instalar**

```sh
git clone https://github.com/wh01s17/evo8-linux
cd evo8-linux/packaging/arch
makepkg -si
```

Instala todo en el sistema y trae las dependencias, incluida la fuente de los
íconos. Después, desconecta y vuelve a conectar la EVO una vez.

**Actualizar**

```sh
cd evo8-linux/packaging/arch
git pull
makepkg -si
```

El paquete se compila siempre desde lo último de GitHub. `git pull` trae el
PKGBUILD al día, por si cambió.

**Desinstalar**

```sh
evoctl mezcla off
sudo pacman -Rns evo8-linux-git
```

`evoctl mezcla off` va antes: desactiva el micrófono virtual en tu usuario.

### Otras distribuciones (pipx)

**Instalar**

```sh
pipx install "evo8-linux[gui,usb]"
evoctl setup
```

pip solo instala Python. `evoctl setup` copia a tu usuario la config de
PipeWire y el servicio del micrófono virtual, el servicio que restaura los
ajustes y la entrada del menú, y te da
el comando `sudo` exacto para la regla udev (control por USB sin root). También
avisa si falta algo del sistema: PipeWire, WirePlumber, `pactl`, `amixer` o la
fuente *JetBrainsMono Nerd Font*, y si el portal de escritorio quedó con 0 µs
de tiempo real (ver [Si el audio se corta](#si-el-audio-se-corta)).

**Actualizar**

```sh
pipx upgrade evo8-linux
evoctl setup
```

`evoctl setup` va después de cada actualización: deja al día los archivos que
copió a tu usuario.

**Desinstalar**

```sh
evoctl setup --remove
pipx uninstall evo8-linux
sudo rm /etc/udev/rules.d/70-audient-evo8.rules
```

`evoctl setup --remove` apaga el micrófono virtual y quita los archivos de
tu usuario. La regla udev la
pusiste con `sudo`, así que se quita igual.

### Desde el código

Requisitos: PipeWire + WirePlumber, `pactl`, `amixer`, Python ≥ 3.11,
`python-pyusb`, `pyside6`, `qt6-svg` y *JetBrainsMono Nerd Font*
(`ttf-jetbrains-mono-nerd`).

**Instalar**

```sh
git clone https://github.com/wh01s17/evo8-linux
cd evo8-linux
make install      # evoctl y evo8-mixer en ~/.local/bin, apuntando a esta carpeta
sudo make udev    # control por USB sin root
```

**Actualizar**

```sh
cd evo8-linux
git pull
make install
```

Los comandos y la config de PipeWire apuntan a la carpeta, así que `git pull`
basta para ellos. `make install` actualiza las copias: los servicios y la
entrada del menú.

**Desinstalar**

```sh
cd evo8-linux
make uninstall
sudo rm /etc/udev/rules.d/70-audient-evo8.rules
```

### Después de actualizar o desinstalar

- Si la actualización cambió el micrófono virtual y lo usas, apágalo y
  enciéndelo para cargarlo: `evoctl mezcla off && evoctl mezcla on`. No
  corta el resto del audio.
- **Si vienes de la versión 0.2 o anterior**, la Mezcla estaba dentro de
  PipeWire y no se podía apagar. Tras actualizar (y `evoctl setup` con pipx),
  reinicia PipeWire una vez (corta el audio un momento):
  `systemctl --user restart pipewire pipewire-pulse wireplumber`. Con pipx
  o desde el código queda encendida como antes; con el paquete de Arch,
  enciéndela con `evoctl mezcla on`.
- Reabre la ventana para usar la versión nueva.
- Desinstalar no borra tus ajustes guardados (ganancias, retardo, preamps y
  mezcla interna). Si no vas a volver a instalarla:
  `rm -r ~/.local/state/evo8`.

### Primeros pasos

1. Pon la EVO 8 en el perfil **Pro Audio**, desde la pestaña SONIDO DEL PC
   (columna PERFILES) o con
   `evoctl profiles set alsa_card.usb-Audient_EVO8-00 pro-audio`.
2. Si quieres el micrófono virtual, enciéndelo con el interruptor de la
   pestaña MICRÓFONO VIRTUAL o con `evoctl mezcla on`. Viene apagado.
3. En la app, elige **Mezcla** como micrófono. Si la app tiene supresión de
   ruido o control automático de ganancia, desactívalos: alteran la música
   que mandas por Compartido.

## Uso

### La ventana

`evo8-mixer`, o *Mezclador EVO 8* en el menú de aplicaciones.

- **SONIDO DEL PC**: una tira por canal: las entradas de la EVO (preamp,
  volumen, medidor y monitor), las apps, la salida seleccionada y los
  perfiles de cada tarjeta, con lo que hace cada uno.
- **MICRÓFONO VIRTUAL**: arriba, el interruptor que lo enciende y lo apaga.
  Encendido, cuánto entra de cada entrada y de Compartido, cuánto oyes
  Compartido, la sincronía con *Calibrar*, qué apps suenan por Compartido y
  la Mezcla con su monitor. El cuadrito verde junto al nombre de la pestaña
  indica que está encendido.
- **EVO 8**: la mezcla de monitoreo interna y el loop-back. Los cambios
  quedan en espera hasta que pulsas *Aplicar a la EVO*, porque cada envío por
  USB corta el audio un instante (ver [Cómo funciona](#cómo-funciona)).
- **ACERCA DE**: versión, firmware de la EVO, cómo está instalado y un botón
  que copia esos datos para reportar un problema.

![La pestaña EVO 8: phantom y silencio por entrada, y la mezcla de monitoreo de los audífonos 1 con faders y paneo](https://raw.githubusercontent.com/wh01s17/evo8-linux/main/docs/img/evo.png)

Cada control tiene 󰑐 para volver al valor estándar. `evo8-mixer --mezcla` y
`evo8-mixer --evo` abren directo en esas pestañas. Hay una sola ventana:
volver a lanzarla la trae al frente.

### La línea de comandos

```sh
# Micrófono virtual
evoctl mezcla on                  # encenderlo (queda así al reiniciar); off para apagarlo
evoctl mezcla status              # on, off, failed, missing o legacy
evoctl mix get                    # ganancias: [entrada 1, entrada 2, Compartido L, R]
evoctl mix set 1 0.8              # entrada 1 al 80 % (lineal, 0..4)
evoctl share list                 # apps que están en Compartido
evoctl share on <node-id>         # mandar una app a Compartido
evoctl delay set 40               # retrasar Compartido 40 ms hacia la Mezcla
evoctl calibrate --apply          # medir el desfase tocando sobre un click
evoctl apply                      # restaurar lo guardado tras reiniciar PipeWire

evoctl monitor toggle             # escuchar la Mezcla completa

# Sonido del PC
evoctl monitor input 1 on         # escuchar la entrada 1 en la salida
evoctl profiles list              # perfiles de cada tarjeta

# Hardware de la EVO (cada comando corta el audio ~0,1 s)
evoctl preamp set 2 24.5          # preamp de la entrada 2 en dB
evoctl hw input phantom 2 on      # 48 V en la entrada 2
evoctl hw input mute 3 on         # silenciar la entrada 3 en la EVO
evoctl hw loopback set pc12       # loop-back = lo que suena por las salidas 1-2
evoctl hw mix get                 # mezcla interna (dB)
evoctl hw mix set 1 1 -6          # entrada 1 → salida 1 a -6 dB
evoctl hw mix set 5 3 off         # PC 1 → salida 3 apagado

evoctl --help                     # todos los comandos
```

La salida es JSON o un valor por línea, para usarla en scripts o en una barra
de escritorio.

### Si el audio se corta

- **Se corta en todas las apps y los reproductores se cierran solos** (mpv
  muere y vuelve a abrir): suele ser el portal de escritorio. Si `rtkit` se
  instaló con la sesión ya abierta, el portal se queda informando 0 µs de
  tiempo real y el kernel mata cada programa de audio que pide tiempo real.
  `evoctl setup` lo detecta. Se arregla con
  `systemctl --user restart xdg-desktop-portal` (o cerrando sesión) y
  volviendo a abrir esos programas.
- **Con un monitor encendido** (de entrada o de la Mezcla): el monitor baja la latencia de *todo*
  PipeWire (quantum 128). En una salida Bluetooth no lo hace, porque esa
  salida necesita búferes grandes y se entrecortaría; ahí el monitor funciona
  igual, con la latencia propia del Bluetooth.

## Cómo funciona

![Diagrama: arriba, el audio. Las entradas 1-2 de la EVO y Compartido se suman en mezcla.suma, que aplica la sincronía y las ganancias y entrega el micrófono virtual Mezcla a cualquier app; Compartido también va a la salida para que lo escuches, y el monitor lleva la Mezcla a la salida. Abajo, el control. La ventana y evoctl usan la librería evo8, que ajusta PipeWire al instante y habla por USB con la EVO para la mezcla interna, el loop-back, los preamps, el phantom y el silencio.](https://raw.githubusercontent.com/wh01s17/evo8-linux/main/docs/img/como-funciona.svg)

El proyecto mueve dos cosas distintas:

- **El audio en el PC** (verde) lo hace PipeWire. El micrófono virtual es un
  proceso aparte de PipeWire, el servicio de usuario `evo8-mezcla.service`
  (`pipewire -c evo8-mezcla.conf`). Crea **Compartido** (una salida virtual),
  **mezcla.suma** (un *filter-chain* que retrasa Compartido y aplica una
  ganancia por canal) y la **Mezcla** (el micrófono virtual). Encenderlo es
  activar el servicio (`systemctl --user enable --now`); apagarlo, detenerlo.
  Como no vive dentro del daemon, ninguna de las dos cosas reinicia PipeWire.
  La ventana y `evoctl` cambian sus valores al instante, sin cortes.
- **El hardware de la EVO** (ámbar) no pasa por PipeWire. Se controla con
  peticiones USB estándar de audio (UAC2) que el kernel no expone. Linux no
  deja enviarlas mientras el driver de audio tiene la interfaz, así que
  evo8-linux suelta el driver, envía y lo devuelve. El audio se corta ~0,1 s,
  y por eso la ventana agrupa los cambios y espera a que pulses *Aplicar a la
  EVO*.

El protocolo USB y lo verificado en el dispositivo están en
[`docs/protocolo-usb.md`](https://github.com/wh01s17/evo8-linux/blob/main/docs/protocolo-usb.md).

## El repositorio

| Ruta | Qué hay |
|---|---|
| [`src/evo8/`](https://github.com/wh01s17/evo8-linux/tree/main/src/evo8) | La librería y `evoctl`. Sonido del PC: `pw.py`, `monitor.py`, `apps.py`, `profiles.py`, `alsa.py` (preamps). Micrófono virtual: `mix.py` (encendido, ganancias, sincronía) y `calibrate.py`. Hardware: `usb.py`, `hw.py`. `evoctl setup`: `user_setup.py` |
| [`src/evo8/gui/`](https://github.com/wh01s17/evo8-linux/tree/main/src/evo8/gui) | La ventana: PySide6 y QML (`SystemPage`, `MezclaPage`, `HardwarePage`, `AboutPage`) |
| [`src/evo8/data/`](https://github.com/wh01s17/evo8-linux/tree/main/src/evo8/data) | Config de PipeWire (`evo8-mezcla.conf`: el micrófono virtual), servicios de systemd, regla udev, entrada del menú e ícono |
| [`packaging/arch/`](https://github.com/wh01s17/evo8-linux/tree/main/packaging/arch) | El PKGBUILD |
| [`docs/protocolo-usb.md`](https://github.com/wh01s17/evo8-linux/blob/main/docs/protocolo-usb.md) | El protocolo USB de la EVO 8 |
| [`plan.md`](https://github.com/wh01s17/evo8-linux/blob/main/plan.md) | Arquitectura, estado y próximos pasos |
| [`CHANGELOG.md`](https://github.com/wh01s17/evo8-linux/blob/main/CHANGELOG.md) | Cambios de cada versión |
| [`PUBLISH.md`](https://github.com/wh01s17/evo8-linux/blob/main/PUBLISH.md) | Cómo publicar una versión |

Los tests corren con `make test`, sin necesidad de tener la EVO conectada.

## Advertencia

Proyecto independiente, sin relación con Audient. EVO es una marca de
Audient. El control por USB se basa en ingeniería inversa para
interoperabilidad y no incluye código ni binarios de Audient. Se probó en una
EVO 8 con firmware 1.4c. Úsalo bajo tu responsabilidad: si la interfaz deja de
responder, desconéctala y vuelve a conectarla.

## Licencia

MIT
