"""Convert a legacy (pre-1.41.8.2) crosshair into the pixel-based system.

How the old game drew a crosshair (at render height H):
    scale      = H / 480
    bar length = round(size * scale)                 (round half to even)
    thickness  = max(1, round(thickness * scale))
    bar space  = trunc(4 + gap)   <- NOT resolution scaled

The new system measures in whole pixels at ``cl_crosshair_screen_height``
and its gap runs from the centre of the crosshair to the start of a bar, so
    new gap = old bar space + ceil(new thickness / 2)

These rules come from on-screen pixel measurements of Classic Static
crosshairs at 1920x1080 and 1280x960 (see README for sources). Other styles
and resolutions use the same math but are less certain; the converter
flags that in its notes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .models import LEGACY_COLOR_PRESETS, LEGACY_STYLES, OUTLINE_MODES, PIXEL_STYLES, LegacyCrosshair, PixelCrosshair

VERIFIED_HEIGHTS = {1080, 960}

# old style -> (new style, confidence)
STYLE_MAP = {
    0: (0, "approx"),     # Default          -> Dynamic Cross
    1: (4, "approx"),     # Default Static   -> Static Cross
    2: (2, "suggested"),  # Classic          -> Dynamic Cross (Legacy)
    3: (0, "approx"),     # Classic Dynamic  -> Dynamic Cross
    4: (4, "exact"),      # Classic Static   -> Static Cross
    5: (5, "suggested"),  # Legacy           -> Static Cross (Shot Feedback)
}

LIMITS = {"length": (0, 255), "thickness": (1, 31), "gap": (0, 128)}


@dataclass
class Note:
    level: str  # "info" or "warn"
    message: str

    def __str__(self) -> str:
        return f"[{self.level.upper()}] {self.message}"


@dataclass
class ConversionResult:
    source: LegacyCrosshair
    crosshair: PixelCrosshair
    notes: list[Note] = field(default_factory=list)


def legacy_pixels(x: LegacyCrosshair, screen_height: int) -> dict:
    """How many pixels the old game drew, before clamping to the new ranges."""
    scale = screen_height / 480
    length = round(x.size * scale)  # Python's round() is round-half-to-even
    thickness = max(1, round(x.thickness * scale))
    space = math.trunc(4 + x.gap)   # fractions dropped, gap is not scaled
    return {"length": length, "thickness": thickness, "space": space}


def _clamp(name: str, value: int, notes: list[Note]) -> int:
    lo, hi = LIMITS[name]
    if value < lo or value > hi:
        clamped = max(lo, min(hi, value))
        notes.append(Note("warn", f"{name} {value}px is outside the new range {lo}-{hi}; using {clamped}."))
        return clamped
    return value


def _clamp_float(name: str, value: float, lo: float, hi: float, notes: list[Note]) -> float:
    if value < lo or value > hi:
        clamped = max(lo, min(hi, value))
        notes.append(Note("info", f"{name} {value:g} is outside the new range {lo:g}-{hi:g}; using {clamped:g}."))
        return clamped
    return value


def convert(
    legacy: LegacyCrosshair,
    screen_height: int = 1080,
    style: int | None = None,
    outline: int | None = None,
    spread_limit: int = 255,
) -> ConversionResult:
    """Convert ``legacy`` to a v4 pixel crosshair for the given render height."""
    if screen_height <= 0:
        raise ValueError("screen height must be positive")
    notes: list[Note] = []

    if screen_height not in VERIFIED_HEIGHTS:
        notes.append(Note(
            "warn",
            f"Sizes have only been pixel-verified at 1080p and 960p (4:3). "
            f"{screen_height}p uses the same height/480 scaling but check it in game.",
        ))

    # --- style
    old_name = LEGACY_STYLES.get(legacy.style, f"#{legacy.style}")
    if style is not None:
        new_style = style
        notes.append(Note("info", f"Style forced to {style} ({PIXEL_STYLES.get(style, '?')})."))
    elif legacy.style in STYLE_MAP:
        new_style, confidence = STYLE_MAP[legacy.style]
        if confidence != "exact":
            notes.append(Note(
                "warn" if confidence == "approx" else "info",
                f"Old style {legacy.style} ({old_name}) has no exact match; mapped to "
                f"{new_style} ({PIXEL_STYLES[new_style]}). Use --style to pick another.",
            ))
    else:
        new_style = 4
        notes.append(Note("warn", f"Unknown old style {legacy.style}; defaulting to 4 (Static Cross)."))

    if new_style in (0, 1, 2, 7):  # dynamic styles
        notes.append(Note("info", "Gap math is verified for static crosshairs; dynamic styles may look slightly different at rest."))

    # --- sizes
    px = legacy_pixels(legacy, screen_height)
    length = _clamp("length", px["length"], notes)
    thickness = _clamp("thickness", px["thickness"], notes)
    raw_gap = px["space"] + math.ceil(thickness / 2)
    if raw_gap < 0:
        notes.append(Note("warn", f"Gap {legacy.gap:g} made the bars overlap the centre; the new gap can't go below 0."))
        gap = 0
    else:
        gap = _clamp("gap", raw_gap, notes)

    # --- color / alpha
    red, green, blue = legacy.effective_rgb()
    if legacy.color in LEGACY_COLOR_PRESETS:
        notes.append(Note("info", f"Color preset {legacy.color} converted to RGB {red},{green},{blue}."))
    alpha = legacy.effective_alpha()
    if not legacy.use_alpha:
        notes.append(Note("info", "cl_crosshairusealpha was off, so alpha is 255 (fully opaque)."))

    # --- outline
    if outline is not None:
        outline_mode = outline
    else:
        outline_mode = 1 if legacy.draw_outline else 0
    if legacy.draw_outline and legacy.outline_thickness != 1:
        notes.append(Note(
            "info",
            f"Outline thickness {legacy.outline_thickness:g} no longer exists; outline is now "
            f"{OUTLINE_MODES[outline_mode]} (use --outline half for a thinner look).",
        ))

    # --- removed settings
    if legacy.gap_use_weapon_value:
        notes.append(Note("info", "cl_crosshairgap_useweaponvalue was removed; try cl_crosshair_dynamic_spread_limit instead."))

    result = PixelCrosshair(
        version=4,
        style=new_style,
        length=length,
        thickness=thickness,
        gap=gap,
        red=red,
        green=green,
        blue=blue,
        alpha=alpha,
        outline_mode=outline_mode,
        dot=legacy.dot,
        t_style=legacy.t_style,
        follow_recoil=legacy.follow_recoil,
        dynamic_spread_limit=max(0, min(255, spread_limit)),
        split_distance=max(0, min(127, legacy.split_distance)),
        inner_split_alpha=round(_clamp_float("inner split alpha", legacy.inner_split_alpha, 0, 1, notes) * 20) / 20,
        outer_split_alpha=round(_clamp_float("outer split alpha", legacy.outer_split_alpha, 0.3, 1, notes) * 20) / 20,
        split_size_ratio=round(_clamp_float("split size ratio", legacy.split_size_ratio, 0, 1, notes) * 100) / 100,
        screen_height=screen_height,
    )
    return ConversionResult(source=legacy, crosshair=result, notes=notes)
