"""Low-level share code <-> bytes conversion.

Every CS:GO / CS2 crosshair share code (``CSGO-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX``)
is an 18-byte payload written as one big-endian integer in base 57, with the
least-significant digit first. Byte 0 is a checksum: the sum of bytes 1..17
modulo 256. Byte 1 is the format version (1 = legacy, 3/4 = pixel based).
"""

from __future__ import annotations

import re

DICTIONARY = "ABCDEFGHJKLMNOPQRSTUVWXYZabcdefhijkmnopqrstuvwxyz23456789"
BASE = len(DICTIONARY)  # 57
PAYLOAD_LENGTH = 18
CODE_CHARS = 25

_PATTERN = re.compile(r"^CSGO(-?[A-Za-z0-9]{5}){5}$")


class InvalidShareCode(ValueError):
    """Raised when a string is not a valid crosshair share code."""


def looks_like_share_code(text: str) -> bool:
    return bool(_PATTERN.match(text.strip()))


def checksum(payload: bytes | list[int]) -> int:
    return sum(payload[1:]) & 0xFF


def code_to_bytes(code: str) -> bytes:
    """Decode a share code into its 18-byte payload and verify the checksum."""
    code = code.strip()
    if not _PATTERN.match(code):
        raise InvalidShareCode(f"not a share code: {code!r}")

    value = 0
    for ch in reversed(code[4:].replace("-", "")):
        digit = DICTIONARY.find(ch)
        if digit < 0:
            raise InvalidShareCode(f"character {ch!r} can't appear in a share code")
        value = value * BASE + digit

    if value >= 1 << (8 * PAYLOAD_LENGTH):
        raise InvalidShareCode("share code value is too large")

    payload = value.to_bytes(PAYLOAD_LENGTH, "big")
    if payload[0] != checksum(payload):
        raise InvalidShareCode("checksum doesn't match (typo in the code?)")
    return payload


def bytes_to_code(payload: bytes | list[int]) -> str:
    """Encode an 18-byte payload as a share code. Byte 0 is recomputed."""
    data = bytearray(payload)
    if len(data) != PAYLOAD_LENGTH:
        raise ValueError(f"payload must be {PAYLOAD_LENGTH} bytes, got {len(data)}")
    if any(not 0 <= b <= 255 for b in data):
        raise ValueError("payload bytes must be in 0..255")
    data[0] = checksum(data)

    value = int.from_bytes(bytes(data), "big")
    chars = []
    for _ in range(CODE_CHARS):
        value, digit = divmod(value, BASE)
        chars.append(DICTIONARY[digit])
    s = "".join(chars)
    return "CSGO-" + "-".join(s[i : i + 5] for i in range(0, CODE_CHARS, 5))
