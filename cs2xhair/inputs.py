"""Turn whatever the user pasted (share code or commands) into a crosshair object."""

from __future__ import annotations

from dataclasses import dataclass, field

from . import codec
from .commands import CommandParseError, parse_commands
from .models import LegacyCrosshair, PixelCrosshair
from .sharecode import looks_like_share_code


@dataclass
class LoadedInput:
    kind: str  # "code" or "commands"
    crosshair: LegacyCrosshair | PixelCrosshair
    ignored: list[str] = field(default_factory=list)

    @property
    def is_legacy(self) -> bool:
        return isinstance(self.crosshair, LegacyCrosshair)

    def describe(self) -> str:
        era = "old (pre-1.41.8.2)" if self.is_legacy else f"new (v{self.crosshair.version})"
        return f"{era} {'share code' if self.kind == 'code' else 'console commands'}"


def load(text: str) -> LoadedInput:
    text = text.strip()
    if not text:
        raise ValueError("nothing to convert - paste a share code or crosshair commands")
    if looks_like_share_code(text):
        return LoadedInput("code", codec.decode(text))
    if "cl_" not in text.lower():
        raise ValueError("input is neither a CSGO-XXXXX-... share code nor cl_crosshair commands")
    try:
        parsed = parse_commands(text)
    except CommandParseError as exc:
        raise ValueError(str(exc)) from None
    return LoadedInput("commands", parsed.crosshair, parsed.ignored)
