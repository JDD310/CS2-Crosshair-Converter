"""Decode / encode crosshair share codes (versions 1, 3 and 4).

Byte layouts (index = byte in the 18-byte payload):

Version 1 (CS:GO era, CS2 < 1.41.8.2)
    0  checksum                 9  cl_fixedcrosshairgap * 10 (signed)
    1  version = 1             10  bits 0-2 color, bit 3 outline, bits 4-7 inner split alpha * 10
    2  gap * 10 (signed)       11  bits 0-3 outer split alpha * 10, bits 4-7 split ratio * 10
    3  outline thickness * 2   12  thickness * 10
    4-6 red, green, blue       13  bits 1-3 style, bit 4 dot, bit 5 gap_useweaponvalue,
    7  alpha                        bit 6 usealpha, bit 7 T style
    8  bits 0-6 splitdist,     14  size * 10 (low 8 bits)
       bit 7 follow recoil     15  size * 10 (high 5 bits)

Version 3 / 4 (CS2 1.41.8.2 / 1.41.8.3+, pixel based)
    0  checksum                 7  gap (px)
    1  version                  8  length (px)
    2  bits 0-3 style,          9  dynamic spread limit
       bit 4 follow recoil,    10-13 packed 32-bit little-endian field:
       bit 5 outline (v3),           bits  0-6  split distance
       bit 6 dot, bit 7 T            bits  7-11 inner split alpha (/20)
    3-6 red, green, blue, alpha      bits 12-15 outer split alpha (/20, +0.3)
                                     bits 16-22 split size ratio (/100)
                                     bits 23-27 thickness (px)
                                     bits 28-29 outline mode (v4)
                               14-15 screen height (little-endian)

Layouts cross-checked against the MIT-licensed ``csgo-sharecode`` (AkiVer).
"""

from __future__ import annotations

from .models import LegacyCrosshair, PixelCrosshair
from .sharecode import InvalidShareCode, bytes_to_code, code_to_bytes

SPLIT_ALPHA_STEPS = 20
OUTER_SPLIT_ALPHA_MIN_STEPS = 6
SPLIT_RATIO_STEPS = 100


def _int8(b: int) -> int:
    return b - 256 if b > 127 else b


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def _tenths(value: float) -> int:
    return int(round(value * 10))


# --------------------------------------------------------------------------- decode


def decode(code: str) -> LegacyCrosshair | PixelCrosshair:
    """Decode any supported crosshair share code."""
    b = code_to_bytes(code)
    version = b[1]
    if version == 1:
        return _decode_v1(b)
    if version in (3, 4):
        return _decode_pixel(b, version)
    raise InvalidShareCode(f"unsupported crosshair code version {version}")


def _decode_v1(b: bytes) -> LegacyCrosshair:
    return LegacyCrosshair(
        gap=_int8(b[2]) / 10,
        outline_thickness=b[3] / 2,
        red=b[4],
        green=b[5],
        blue=b[6],
        alpha=b[7],
        split_distance=b[8] & 0x7F,
        follow_recoil=bool(b[8] & 0x80),
        fixed_gap=_int8(b[9]) / 10,
        color=b[10] & 0x07,
        draw_outline=bool(b[10] & 0x08),
        inner_split_alpha=(b[10] >> 4) / 10,
        outer_split_alpha=(b[11] & 0x0F) / 10,
        split_size_ratio=(b[11] >> 4) / 10,
        thickness=b[12] / 10,
        style=(b[13] & 0x0F) >> 1,
        dot=bool(b[13] & 0x10),
        gap_use_weapon_value=bool(b[13] & 0x20),
        use_alpha=bool(b[13] & 0x40),
        t_style=bool(b[13] & 0x80),
        size=(((b[15] & 0x1F) << 8) | b[14]) / 10,
    )


def _decode_pixel(b: bytes, version: int) -> PixelCrosshair:
    bits = int.from_bytes(b[10:14], "little")
    if version == 3:
        outline = 1 if b[2] & 0x20 else 0
    else:
        outline = (bits >> 28) & 0x03
    return PixelCrosshair(
        version=version,
        style=b[2] & 0x0F,
        follow_recoil=bool(b[2] & 0x10),
        dot=bool(b[2] & 0x40),
        t_style=bool(b[2] & 0x80),
        red=b[3],
        green=b[4],
        blue=b[5],
        alpha=b[6],
        gap=b[7],
        length=b[8],
        dynamic_spread_limit=b[9],
        split_distance=bits & 0x7F,
        inner_split_alpha=((bits >> 7) & 0x1F) / SPLIT_ALPHA_STEPS,
        outer_split_alpha=(((bits >> 12) & 0x0F) + OUTER_SPLIT_ALPHA_MIN_STEPS) / SPLIT_ALPHA_STEPS,
        split_size_ratio=((bits >> 16) & 0x7F) / SPLIT_RATIO_STEPS,
        thickness=(bits >> 23) & 0x1F,
        screen_height=b[14] | (b[15] << 8),
        outline_mode=outline,
    )


# --------------------------------------------------------------------------- encode


def encode(xhair: LegacyCrosshair | PixelCrosshair) -> str:
    """Encode a crosshair into a share code (version taken from the object)."""
    if isinstance(xhair, LegacyCrosshair):
        return bytes_to_code(_encode_v1(xhair))
    return bytes_to_code(_encode_pixel(xhair))


def _encode_v1(x: LegacyCrosshair) -> list[int]:
    size = _clamp(_tenths(x.size), 0, 0x1FFF)
    return [
        0,
        1,
        _clamp(_tenths(x.gap), -128, 127) & 0xFF,
        _clamp(int(round(x.outline_thickness * 2)), 0, 255),
        x.red & 0xFF,
        x.green & 0xFF,
        x.blue & 0xFF,
        x.alpha & 0xFF,
        (x.split_distance & 0x7F) | (int(x.follow_recoil) << 7),
        _clamp(_tenths(x.fixed_gap), -128, 127) & 0xFF,
        (x.color & 0x07) | (int(x.draw_outline) << 3) | (_clamp(_tenths(x.inner_split_alpha), 0, 15) << 4),
        _clamp(_tenths(x.outer_split_alpha), 0, 15) | (_clamp(_tenths(x.split_size_ratio), 0, 15) << 4),
        _clamp(_tenths(x.thickness), 0, 255),
        ((x.style & 0x07) << 1)
        | (int(x.dot) << 4)
        | (int(x.gap_use_weapon_value) << 5)
        | (int(x.use_alpha) << 6)
        | (int(x.t_style) << 7),
        size & 0xFF,
        size >> 8,
        0,
        0,
    ]


def _encode_pixel(x: PixelCrosshair) -> list[int]:
    if x.version not in (3, 4):
        raise ValueError("pixel crosshairs must be version 3 or 4")
    max_style = 7 if x.version == 3 else 8

    inner = int(round(_clamp(x.inner_split_alpha, 0, 1) * SPLIT_ALPHA_STEPS))
    outer = int(round(_clamp(x.outer_split_alpha, 0.3, 1) * SPLIT_ALPHA_STEPS)) - OUTER_SPLIT_ALPHA_MIN_STEPS
    ratio = int(round(_clamp(x.split_size_ratio, 0, 1) * SPLIT_RATIO_STEPS))
    bits = (
        _clamp(x.split_distance, 0, 127)
        | (inner << 7)
        | (outer << 12)
        | (ratio << 16)
        | (_clamp(x.thickness, 0, 31) << 23)
    )
    flags = _clamp(x.style, 0, max_style) | (int(x.follow_recoil) << 4) | (int(x.dot) << 6) | (int(x.t_style) << 7)
    if x.version == 3:
        flags |= int(x.outline_mode > 0) << 5
    else:
        bits |= _clamp(x.outline_mode, 0, 2) << 28

    height = _clamp(x.screen_height, 0, 65535)
    return [
        0,
        x.version,
        flags,
        _clamp(x.red, 0, 255),
        _clamp(x.green, 0, 255),
        _clamp(x.blue, 0, 255),
        _clamp(x.alpha, 0, 255),
        _clamp(x.gap, 0, 255),
        _clamp(x.length, 0, 255),
        _clamp(x.dynamic_spread_limit, 0, 255),
        *bits.to_bytes(4, "little"),
        height & 0xFF,
        height >> 8,
        0,
        0,
    ]
