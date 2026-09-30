"""Parse console commands / .cfg text and render crosshairs back to commands."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field

from .models import LegacyCrosshair, PixelCrosshair

# cvar name -> (field, type)
LEGACY_CVARS = {
    "cl_crosshairstyle": ("style", int),
    "cl_crosshairsize": ("size", float),
    "cl_crosshairthickness": ("thickness", float),
    "cl_crosshairgap": ("gap", float),
    "cl_crosshaircolor": ("color", int),
    "cl_crosshaircolor_r": ("red", int),
    "cl_crosshaircolor_g": ("green", int),
    "cl_crosshaircolor_b": ("blue", int),
    "cl_crosshairalpha": ("alpha", int),
    "cl_crosshairusealpha": ("use_alpha", bool),
    "cl_crosshair_drawoutline": ("draw_outline", bool),
    "cl_crosshair_outlinethickness": ("outline_thickness", float),
    "cl_crosshairdot": ("dot", bool),
    "cl_crosshair_t": ("t_style", bool),
    "cl_crosshair_recoil": ("follow_recoil", bool),
    "cl_crosshair_dynamic_splitdist": ("split_distance", int),
    "cl_crosshair_dynamic_splitalpha_innermod": ("inner_split_alpha", float),
    "cl_crosshair_dynamic_splitalpha_outermod": ("outer_split_alpha", float),
    "cl_crosshair_dynamic_maxdist_splitratio": ("split_size_ratio", float),
    "cl_fixedcrosshairgap": ("fixed_gap", float),
    "cl_crosshairgap_useweaponvalue": ("gap_use_weapon_value", bool),
}

PIXEL_CVARS = {
    "cl_crosshairstyle": ("style", int),
    "cl_crosshair_style": ("style", int),
    "cl_crosshair_length": ("length", int),
    "cl_crosshair_thickness": ("thickness", int),
    "cl_crosshair_gap": ("gap", int),
    "cl_crosshaircolor_r": ("red", int),
    "cl_crosshaircolor_g": ("green", int),
    "cl_crosshaircolor_b": ("blue", int),
    "cl_crosshaircolor_a": ("alpha", int),
    "cl_crosshair_drawoutline": ("outline_mode", int),
    "cl_crosshairdot": ("dot", bool),
    "cl_crosshair_t": ("t_style", bool),
    "cl_crosshair_recoil": ("follow_recoil", bool),
    "cl_crosshair_dynamic_spread_limit": ("dynamic_spread_limit", int),
    "cl_crosshair_dynamic_splitdist": ("split_distance", int),
    "cl_crosshair_dynamic_splitalpha_innermod": ("inner_split_alpha", float),
    "cl_crosshair_dynamic_splitalpha_outermod": ("outer_split_alpha", float),
    "cl_crosshair_dynamic_maxdist_splitratio": ("split_size_ratio", float),
    "cl_crosshair_screen_height": ("screen_height", int),
}

# Names that only exist in one of the two systems - used to tell them apart.
LEGACY_ONLY = set(LEGACY_CVARS) - set(PIXEL_CVARS)
PIXEL_ONLY = set(PIXEL_CVARS) - set(LEGACY_CVARS)


class CommandParseError(ValueError):
    pass


@dataclass
class ParsedCommands:
    system: str                                   # "legacy" or "pixel"
    crosshair: LegacyCrosshair | PixelCrosshair
    applied: dict[str, str] = field(default_factory=dict)
    ignored: list[str] = field(default_factory=list)


def _coerce(raw: str, kind):
    text = raw.strip().lower()
    if kind is bool:
        if text in ("true", "yes", "on"):
            return True
        if text in ("false", "no", "off"):
            return False
        return float(text) != 0
    number = float(text)
    return int(round(number)) if kind is int else number


def tokenize(text: str) -> list[tuple[str, str]]:
    """Split cfg text into (cvar, value) pairs. Handles ;, newlines, quotes, // comments."""
    pairs = []
    for line in text.splitlines():
        line = re.sub(r"//.*", "", line)
        for statement in line.split(";"):
            statement = statement.strip()
            if not statement:
                continue
            try:
                parts = shlex.split(statement, posix=True)
            except ValueError:
                parts = statement.replace('"', " ").split()
            # "name value" - or several pairs run together: "a 1 b 2"
            i = 0
            while i < len(parts):
                name = parts[i].lower()
                has_value = i + 1 < len(parts) and not parts[i + 1].lower().startswith("cl_")
                pairs.append((name, parts[i + 1] if has_value else ""))
                i += 2 if has_value else 1
                if not name.startswith("cl_"):
                    break  # e.g. "bind x ..." - skip the rest of the statement
    return pairs


def looks_like_commands(text: str) -> bool:
    return any(name.startswith("cl_") for name, _ in tokenize(text))


def detect_system(names) -> str:
    names = set(names)
    legacy = names & LEGACY_ONLY
    pixel = names & PIXEL_ONLY
    if legacy and pixel:
        raise CommandParseError(
            "input mixes old and new crosshair commands "
            f"(old: {', '.join(sorted(legacy))}; new: {', '.join(sorted(pixel))})"
        )
    return "pixel" if pixel else "legacy"


def parse_commands(text: str, system: str | None = None) -> ParsedCommands:
    """Parse crosshair cvars. ``system`` is auto-detected unless given."""
    pairs = tokenize(text)
    if not pairs:
        raise CommandParseError("no commands found")
    system = system or detect_system(name for name, _ in pairs)
    table = LEGACY_CVARS if system == "legacy" else PIXEL_CVARS
    xhair = LegacyCrosshair() if system == "legacy" else PixelCrosshair()

    result = ParsedCommands(system=system, crosshair=xhair)
    for name, value in pairs:
        if name not in table:
            result.ignored.append(name)
            continue
        attr, kind = table[name]
        try:
            setattr(xhair, attr, _coerce(value, kind))
        except ValueError:
            raise CommandParseError(f"bad value for {name}: {value!r}") from None
        result.applied[name] = value

    if not result.applied:
        raise CommandParseError("none of the commands are crosshair settings")
    return result


def _fmt(value) -> str:
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, float):
        text = f"{value:.3f}".rstrip("0").rstrip(".")
        return text if text not in ("", "-0") else "0"
    return str(value)


def pixel_to_commands(x: PixelCrosshair) -> list[tuple[str, str]]:
    return [
        ("cl_crosshairstyle", _fmt(x.style)),
        ("cl_crosshair_length", _fmt(x.length)),
        ("cl_crosshair_thickness", _fmt(x.thickness)),
        ("cl_crosshair_gap", _fmt(x.gap)),
        ("cl_crosshair_drawoutline", _fmt(x.outline_mode)),
        ("cl_crosshairdot", _fmt(x.dot)),
        ("cl_crosshair_t", _fmt(x.t_style)),
        ("cl_crosshair_recoil", _fmt(x.follow_recoil)),
        ("cl_crosshaircolor_r", _fmt(x.red)),
        ("cl_crosshaircolor_g", _fmt(x.green)),
        ("cl_crosshaircolor_b", _fmt(x.blue)),
        ("cl_crosshaircolor_a", _fmt(x.alpha)),
        ("cl_crosshair_dynamic_spread_limit", _fmt(x.dynamic_spread_limit)),
        ("cl_crosshair_dynamic_splitdist", _fmt(x.split_distance)),
        ("cl_crosshair_dynamic_splitalpha_innermod", _fmt(x.inner_split_alpha)),
        ("cl_crosshair_dynamic_splitalpha_outermod", _fmt(x.outer_split_alpha)),
        ("cl_crosshair_dynamic_maxdist_splitratio", _fmt(x.split_size_ratio)),
        ("cl_crosshair_screen_height", _fmt(x.screen_height)),
    ]


def legacy_to_commands(x: LegacyCrosshair) -> list[tuple[str, str]]:
    reverse = {attr: name for name, (attr, _) in LEGACY_CVARS.items()}
    return [(reverse[k], _fmt(v)) for k, v in x.to_dict().items()]


def render(pairs: list[tuple[str, str]], one_line: bool = False) -> str:
    lines = [f'{name} "{value}"' for name, value in pairs]
    return "; ".join(lines) if one_line else "\n".join(lines)
