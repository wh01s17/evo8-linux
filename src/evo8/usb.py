"""USB Audio Class requests to the EVO 8's control units.

What EVO Control (Windows/macOS) does, recovered from EVO.exe (UacLib): every
setting is a standard UAC2 class request on the audio control interface (0):

    SET: bmRequestType 0x21, GET: 0xA1
    bRequest  CUR (0x01) or RANGE (0x02)
    wValue    (control selector << 8) | channel / mixer control number
    wIndex    (unit id << 8) | 0

Linux only lets a process send class requests to an interface it has claimed,
and snd-usb-audio holds interface 0 while the card exists. So a batch of
requests runs inside `session()`: the audio interfaces are detached from
snd-usb-audio, the requests go out, and the driver is reattached, which brings
the card back. Audio stops for that moment (about a second), so writes are
batched and meant for setup, not for live faders.
"""

from __future__ import annotations

import contextlib
import struct
import time

VENDOR_ID = 0x2708
PRODUCT_ID = 0x0007          # EVO 8
CONTROL_IFACE = 0
AUDIO_IFACES = (0, 1, 2)     # control + playback + capture streaming

REQ_CUR = 0x01
REQ_RANGE = 0x02
TYPE_SET = 0x21              # class | interface, host to device
TYPE_GET = 0xA1              # class | interface, device to host
TIMEOUT_MS = 1000


class UsbError(RuntimeError):
    pass


def _usb():
    try:
        import usb.core
        import usb.util
    except ImportError as e:  # pragma: no cover - depends on the host
        raise UsbError("falta pyusb (pacman -S python-pyusb)") from e
    return usb


def find_device():
    usb = _usb()
    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if dev is None:
        raise UsbError("no se encontró la EVO 8 (2708:0007)")
    return dev


class Session:
    """Requests on a device whose audio interfaces we hold."""

    def __init__(self, dev):
        self.dev = dev

    def get(self, unit: int, selector: int, channel: int, length: int, request: int = REQ_CUR) -> bytes:
        data = self.dev.ctrl_transfer(TYPE_GET, request, (selector << 8) | (channel & 0xFF),
                                      (unit << 8) | CONTROL_IFACE, length, TIMEOUT_MS)
        return bytes(data)

    def set(self, unit: int, selector: int, channel: int, data: bytes, request: int = REQ_CUR) -> None:
        n = self.dev.ctrl_transfer(TYPE_SET, request, (selector << 8) | (channel & 0xFF),
                                   (unit << 8) | CONTROL_IFACE, data, TIMEOUT_MS)
        if n != len(data):
            raise UsbError(f"short write to unit {unit} selector {selector}: {n}/{len(data)}")

    # Common payloads: UAC2 volumes are signed 16-bit in 1/256 dB.
    def get_s16(self, unit: int, selector: int, channel: int) -> int:
        return struct.unpack("<h", self.get(unit, selector, channel, 2))[0]

    def set_s16(self, unit: int, selector: int, channel: int, value: int) -> None:
        self.set(unit, selector, channel, struct.pack("<h", value))

    def range_s16(self, unit: int, selector: int, channel: int) -> list[tuple[int, int, int]]:
        """RANGE answer: wNumSubRanges then (min, max, res) triples."""
        head = self.get(unit, selector, channel, 2, REQ_RANGE)
        count = struct.unpack("<H", head)[0]
        raw = self.get(unit, selector, channel, 2 + 6 * count, REQ_RANGE)
        return [struct.unpack_from("<hhh", raw, 2 + 6 * i) for i in range(count)]


@contextlib.contextmanager
def session(settle: float = 0.0):
    """Detach snd-usb-audio, yield a Session, then give the card back.

    All audio interfaces are detached: if only the control interface went, the
    driver would keep the old card half-alive on the streaming ones and refuse
    to create a new one on reattach. Reattaching interface 0 is enough for it
    to claim the streaming interfaces again."""
    usb = _usb()
    dev = find_device()
    detached = []
    try:
        for i in AUDIO_IFACES:
            if dev.is_kernel_driver_active(i):
                dev.detach_kernel_driver(i)
                detached.append(i)
        usb.util.claim_interface(dev, CONTROL_IFACE)
        yield Session(dev)
    finally:
        with contextlib.suppress(Exception):
            usb.util.release_interface(dev, CONTROL_IFACE)
        with contextlib.suppress(Exception):
            usb.util.dispose_resources(dev)
        if settle:
            time.sleep(settle)
        if detached:
            # The driver claims the streaming interfaces itself when it binds
            # the control interface, so only that one is handed back.
            try:
                dev.attach_kernel_driver(CONTROL_IFACE)
            except Exception as e:
                raise UsbError(f"no se pudo devolver la EVO al driver de audio: {e}; "
                               "desconecta y conecta el USB") from e
