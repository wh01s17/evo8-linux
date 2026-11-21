# Protocolo USB del EVO 8

Notas de ingeniería inversa de **EVO Control v4.4.0a** (Windows,
`EVO-v4.4.0a.exe`, `EVO.exe` SHA-256 `d49e1189…c0ce15`), hechas con Ghidra 12.2
a través de REA. EVO.exe es una app JUCE; habla con el dispositivo mediante el
driver Thesycon (`tusbaudioapi.dll`), a través de una librería propia `UacLib`.

## Transporte

Todas las funciones del dispositivo son **peticiones UAC2 de clase estándar** a
la interfaz de control de audio (0). `UacLib` las arma así
(`FUN_00658570` → `FUN_00655920`):

| Campo           | Valor                                         |
|-----------------|-----------------------------------------------|
| bmRequestType   | `0x21` (SET) / `0xA1` (GET): clase, interfaz  |
| bRequest        | `0x01` CUR, `0x02` RANGE                      |
| wValue          | `(selector << 8) \| canal`                    |
| wIndex          | `(id de unidad << 8) \| 0`                    |

No hay peticiones vendor para el control normal (la API vendor de Thesycon se
importa, pero el camino de las unidades usa la de clase).

### Consecuencia en Linux

`usbfs` solo deja enviar peticiones de clase a una interfaz reclamada por el
proceso, y `snd-usb-audio` tiene la interfaz 0 mientras existe la tarjeta:

- `GET` a la interfaz 0 con el driver cargado → `EBUSY`.
- Dirigida a la interfaz DFU libre (3) con el id de unidad en el byte alto →
  el dispositivo no responde (`ETIMEDOUT`) y **el firmware queda colgado**:
  minutos después el kernel recibe `-71` en todo y la EVO cae del bus; solo se
  recupera desconectándola. **No enviar peticiones de clase a la interfaz 3.**

Por eso `evo8.usb.session()` suelta el driver de las interfaces 0-2, envía las
peticiones y lo devuelve (la tarjeta reaparece; el audio se corta ~1 s).

## Topología (descriptor de control)

```
IT 1  (micrófonos, 6 canales) ─► FU 11 (ganancia preamp, "Mic Playback Volume")
IT 2  (USB, 6 canales)        ─► FU 10 (volumen de salida, "EVO8  Playback Volume")
FU 11 + FU 10 ─► XU 50 (10 canales) ─► MU 60 (mezclador 10 × 4) ─► XU 59 ─► OT 20 (salidas)
                                                                └─► OT 22 (captura USB)
FU 11 + FU 10 ─► XU 51 (6 canales)
IT 1 ─► XU 58 (4 canales)      IT 2 ─► XU 57
Reloj: CS 41 ─► CX 40
```

El Mixer Unit 60 (10 entradas × 4 salidas, bmMixerControls `ff ff ff ff ff`)
es la mezcla de monitoreo por hardware. `snd-usb-audio` no crea controles para
él (`/proc/asound/EVO8/usbmixer` solo lista las unidades 10, 11, 41 y 59).

## Unidades de Audient (clases de UacLib)

| Clase UacLib                     | Unidad | Modelo en EVO.exe       |
|----------------------------------|--------|-------------------------|
| `UacXUAudientInputControl`       | 0x3a = 58 | `InputControlModel`  |
| `UacXUAudientOutputControl`      | 0x3b = 59 | `OutputControlModel` |
| `UacXUAudientBlendMixer`         | 0x38 = 56 | `BlendMixerModel` (EVO 4) |
| `UacXUAudientMonitorController`  | 0x36 = 54 | `MonitorControllerModel` (EVO 16) |
| `UacXUAudientRoutingMatrix`      | 51     | `SystemModel` (loop-back) |
| `UacMixerUnit`                   | 60     | `MixerModel`            |

### Peticiones conocidas (SET CUR, selector, canal, bytes)

Envoltorios de `FUN_00658570(req, selector, canal, datos, largo)`; la clase a la
que pertenece cada uno se completa con el volcado de vtables.

| Función     | Selector | Canal      | Bytes |
|-------------|----------|------------|-------|
| 0x658d60    | 6        | parámetro  | 1     | (RoutingMatrix: fuente por canal) |
| 0x658c80    | 1        | n          | 1     |
| 0x658ed0    | 2        | n          | 2     |
| 0x658f10    | 1        | base + n   | 2     |
| 0x658d00    | 0x0d     | n          | 1     |
| 0x658b40    | 0x0b     | n          | 2     |
| 0x658ab0    | 0x10     | parámetro  | 2     |
| 0x658bb0    | 0x17     | parámetro  | 2     |
| 0x658a70    | 6        | 0          | 2     |
| 0x6589e0    | 4        | 0          | 1     |
| 0x658a40    | 5        | 0          | 1     |
| 0x658d30    | 3        | 0          | 1     |
| 0x658e70    | 7        | 0          | 1     |
| 0x658ea0    | 8        | 0          | 1     |
| 0x658b80    | 0x0c     | 0          | 1     |
| 0x658c20    | 0        | 0          | 1     |
| 0x658c50    | 1        | 0          | 1     |
| 0x658e10    | 0x15     | 0          | 1     |
| 0x658ae0    | 0x19     | 0          | 1     |
| 0x658b10    | 0        | 0          | 4     |
| 0x658bf0    | 1        | 0          | 4     |
| 0x658e40    | 0x18     | 0          | 4     |

## Confirmado en el dispositivo (firmware bcdDevice 1.4c)

`usb.session()` retiene la interfaz ~0,12 s; la tarjeta vuelve sola.

### Ruteo de captura (unidad 51, selector 6, 1 byte por canal 0-5)

| Valor | Fuente                         |
|-------|--------------------------------|
| 0-5   | entradas analógicas 1-6        |
| 6-11  | reproducción del PC 1-6        |

Fábrica: `[0, 1, 2, 3, 10, 11]` → captura 1-4 = entradas 1-4, captura 5-6 =
reproducción 5-6 (el par "loop-back"). Verificado: con `[…, 8, 9]` un tono a
-30 dBFS en reproducción 3-4 aparece a -30 dBFS en captura 5-6.

### Mezcla de monitoreo (Mixer Unit 60, selector 1)

Número de control = `entrada × 4 + salida` (base 0), s16 en 1/256 dB, rango
RANGE `[-32512, 0, 256]` (-127..0 dB, paso 1 dB); EVO Control escribe
-128 dB para silenciar. GET devuelve lo escrito (verificado). Tras conectar la
EVO, los 40 cruces leen 0 dB. Entradas: 1-4 analógicas, 5-10 reproducción 1-6
(orden de las fuentes de la XU 50: FU 11 y luego FU 10; pendiente de verificar
con audio).

### Controles de entrada (unidad 58) y salida (unidad 59)

Mapeado desde `EvoSystemComponent::createInputControls` (orden de los
botones: Gain, Phantom, Mute, SG Arm, Link) y sus handlers (`FUN_004cfe20`,
`FUN_004cff80`, `FUN_004d0030`, `FUN_004d0170`, `FUN_004d0240`), todos vía
`FUN_00658cb0` (4 bytes):

| Unidad | CS | Canal | Valor | Uso |
|--------|----|-------|-------|-----|
| 58 | 0 | entrada-1 | 0/1 | phantom 48 V |
| 58 | 1 | entrada-1 | dB×256 | ganancia (verificado: -3,5 / +24,5 dB) |
| 58 | 2 | entrada-1 | 0/1 | mute |
| 58 | 3 | entrada-1 (par) | 0/1 | link estéreo |
| 58 | 4 | entrada-1 | bitmask | bit 0: Smart Gain armado |
| 59 | 0 | 0 | dB×256 | volumen de salida (`FUN_004cfd30`) |
| 59 | 1 | 0 | 0/1 | mute de salida (`FUN_004d00d0`) |

**Advertencia**: un GET a la unidad 59, CS 3 quedó sin respuesta y colgó el
control del firmware (hubo que desconectar la EVO). No sondear selectores que
la app no usa.
