# evo8-linux

Control del **Audient EVO 8** en Linux, más un micrófono virtual pensado para
tocar y enseñar en videollamadas.

Audient solo publica **EVO Control** para Windows y macOS. En Linux la EVO 8
funciona como interfaz de audio estándar (UAC2), pero el kernel no expone su
mezcla de monitoreo interna ni el ruteo del loop-back. Este proyecto los
recupera hablando con la interfaz por USB con el mismo protocolo que usa EVO
Control, obtenido por ingeniería inversa de la app oficial
([`docs/protocolo-usb.md`](docs/protocolo-usb.md)), y suma herramientas para
PipeWire.

> Estado: en desarrollo. Funcionan el CLI `evoctl` y la ventana `evo8-mixer`.
> Ver [`plan.md`](plan.md).

## Qué hace

**Hardware de la EVO 8 (por USB)**

- **Loop-back**: elegir qué llega a los canales de captura 5-6. Puede ser el
  par loop-back de fábrica, lo que suena por las salidas 1-2 (todo el audio del
  PC), las salidas 3-4 o las entradas 1-2 / 3-4.
- **Mezcla de monitoreo interna**: la matriz de 10 entradas (4 analógicas + 6
  del PC) × 4 salidas que EVO Control muestra como MASTER / ARTIST MIX, en dB.
- **Entradas**: ganancia del preamp en dB, phantom 48 V y silencio.
- **Al conectarla**: la EVO olvida preamps, mezcla interna y loop-back al
  apagarse; un servicio de usuario los restaura (el phantom no, por
  seguridad).

**Micrófono virtual para videollamadas (PipeWire)**

- **Mezcla**: una fuente que suma las entradas 1-2 de la EVO y una salida
  virtual **Compartido**. Lo que mandes a Compartido (YouTube, un metrónomo, un
  backing track) lo escuchas tú y también entra a la llamada.
- Ganancias en vivo por canal, y apps que se mandan a Compartido de a una.
- **Monitor**: escuchar la Mezcla completa, o una entrada sola, por la salida
  seleccionada, con latencia baja.
- **Sincronía**: quien toca encima de la música la oye con la latencia de
  salida, y su instrumento vuelve con la de entrada. `evoctl calibrate` mide ese
  desfase con un click y lo compensa retrasando la música solo hacia la Mezcla.
- Evita que el navegador (Meet, Zoom web) baje el volumen del micrófono por su
  cuenta.

## Instalación

Solo para la **Audient EVO 8** (no la EVO 4 ni la EVO 16). El control por USB
se probó con el firmware 1.4c.

### Arch Linux (paquete)

```sh
git clone https://github.com/wh01s17/evo8-linux
cd evo8-linux/packaging/arch
makepkg -si
systemctl --user restart pipewire pipewire-pulse wireplumber
```

Instala `evoctl` y `evo8-mixer` en `/usr/bin`, la config de PipeWire en
`/usr/share/pipewire`, la regla udev y el servicio que restaura los ajustes al
conectar la EVO (desconéctala y vuelve a conectarla una vez). Arrastra las
dependencias, incluida la fuente *JetBrainsMono Nerd Font* de los íconos.

### Desde el código (desarrollo)

Requisitos: PipeWire + WirePlumber, `pactl`, `amixer`, Python ≥ 3.11,
`python-pyusb` para el control por USB, `pyside6` para la ventana y
*JetBrainsMono Nerd Font* (`ttf-jetbrains-mono-nerd`) para los íconos.

```sh
git clone https://github.com/wh01s17/evo8-linux
cd evo8-linux
make install      # evoctl y evo8-mixer en ~/.local/bin (apuntan a esta carpeta), la config de PipeWire en ~/.config
sudo make udev    # permite al usuario hablar con la EVO por USB sin root
systemctl --user restart pipewire pipewire-pulse wireplumber
```

No mezcles las dos: con el paquete instalado, `make uninstall` quita los
lanzadores de `~/.local/bin`, que si no tendrían prioridad sobre los de `/usr/bin`.

La EVO 8 tiene que estar en el perfil **Pro Audio**
(`evoctl profiles set alsa_card.usb-Audient_EVO8-00 pro-audio`). En Meet, elige
**Mezcla** como micrófono y desactiva la cancelación de ruido.

## Uso

### Ventana

`evo8-mixer` abre el mezclador. Tiene tres pestañas:

- **CONSOLA**: una tira por canal (entradas, Compartido, apps, la Mezcla y la
  salida) con preamp, fader, medidores, compartir, silencio, sincronía, monitor
  y 󰑐 para volver al valor estándar. Al final, los perfiles
  de cada tarjeta (cómo la usa el sistema), con lo que hace cada uno.
  En la tira de Compartido, *Calibrar* mide el desfase mientras tocas sobre
  un click y ajusta la sincronía.
- **EVO 8**: el loop-back y la mezcla de monitoreo interna. Los cambios quedan
  en espera hasta que pulsas *Aplicar a la EVO*.
- **ACERCA DE**: versión, enlaces al repo y a los issues, el firmware de la EVO
  conectada y cómo está instalado. *Copiar para reportar un problema* deja esos
  datos en el portapapeles (con `~` en lugar de tu carpeta personal).

`evo8-mixer --evo` abre directo en la pestaña EVO 8. Hay una sola ventana: volver a
lanzar `evo8-mixer` la trae al frente (y abre otra si la anterior dejó de
responder).

### CLI

```sh
# Mezcla (micrófono virtual)
evoctl mix get                    # ganancias: [entrada 1, entrada 2, Compartido L, R]
evoctl mix set 1 0.8              # entrada 1 al 80 % (lineal, 0..4)
evoctl share list                 # apps que están en Compartido
evoctl share on <node-id>         # mandar una app a Compartido
evoctl delay set 40               # retrasar Compartido 40 ms hacia la Mezcla
evoctl calibrate --apply          # medir el desfase tocando sobre un click
evoctl apply                      # restaurar lo guardado tras reiniciar PipeWire

# Monitor
evoctl monitor toggle             # escuchar la Mezcla completa
evoctl monitor input 1 on         # escuchar solo la entrada 1

# Hardware de la EVO
evoctl preamp set 2 24.5          # preamp de la entrada 2 en dB
evoctl hw input phantom 2 on      # 48 V en la entrada 2
evoctl hw input mute 3 on         # silenciar la entrada 3 en la EVO
evoctl hw loopback set pc12       # loop-back = lo que suena por las salidas 1-2
evoctl hw mix get                 # mezcla interna (dB)
evoctl hw mix set 1 1 -6          # entrada 1 → salida 1 a -6 dB
evoctl hw mix set 5 3 off         # PC 1 → salida 3 apagado
```

Los comandos `hw` sueltan por un instante el driver de audio del kernel para
enviar la orden y lo devuelven de inmediato. El audio se corta ~0,1 s. Úsalos
para configurar, no durante una llamada.

## Cómo funciona

```
EVO entradas 1-2 ─► mezcla.entradas ─┐
                                     ├─► mezcla.suma (filter-chain: delay + ganancias) ─► Mezcla
Apps ─► Compartido ─┬─► mezcla.compartido ┘
                    └─► mezcla.compartido.escucha ─► salida seleccionada
```

- [`src/evo8/`](src/evo8): librería y CLI. `pw.py` (herramientas de PipeWire),
  `mix.py`, `monitor.py`, `calibrate.py`, `apps.py`, `alsa.py`, `usb.py`
  (transporte UAC2) y `hw.py` (loop-back y mezcla interna).
- [`config/pipewire/`](config/pipewire): el grafo de la Mezcla.
- [`docs/protocolo-usb.md`](docs/protocolo-usb.md): topología USB de la EVO 8,
  las peticiones que usa EVO Control y lo verificado en el dispositivo.
- [`plan.md`](plan.md): arquitectura, estado y próximos pasos.

## Advertencia

Proyecto independiente, sin relación con Audient. El control por USB se basa
en ingeniería inversa para interoperabilidad. Se probó en una EVO 8 con
firmware 1.4c. Úsalo bajo tu responsabilidad: si la interfaz deja de
responder, desconéctala y vuelve a conectarla. No incluye código ni binarios
de Audient.

## Licencia

MIT
