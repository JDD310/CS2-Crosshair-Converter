"""Data models for the two crosshair systems.

``LegacyCrosshair``  - CS:GO / CS2 before 1.41.8.2 (share code version 1).
                        Sizes are in "units" that CS scaled by screen_height / 480.
``PixelCrosshair``    - CS2 1.41.8.2+ (share code version 3 and 4).
                        Sizes are whole pixels at ``screen_height``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

# Old cl_crosshaircolor presets (5 = custom RGB from cl_crosshaircolor_r/g/b).
LEGACY_COLOR_PRESETS = {
    0: (255, 0, 0),      # red
    1: (0, 255, 0),      # green
    2: (255, 255, 0),    # yellow
    3: (0, 0, 255),      # blue
    4: (0, 255, 255),    # cyan
}

LEGACY_STYLES = {
    0: "Default",
    1: "Default Static",
    2: "Classic",
    3: "Classic Dynamic",
    4: "Classic Static",
    5: "Legacy",
}

PIXEL_STYLES = {
    0: "Dynamic Cross",
    1: "Dynamic Circle",
    2: "Dynamic Cross (Legacy)",
    3: "Static Circle",
    4: "Static Cross",
    5: "Static Cross (Shot Feedback)",
    6: "Dot Only",
    7: "Dynamic Quad",
    8: "Static Square",  # version 4 only
}

OUTLINE_MODES = {0: "off", 1: "full", 2: "half"}


@dataclass
class LegacyCrosshair:
    # Defaults follow the pre-update CS2 defaults, so a partial config
    # (only a few cvars set) still converts sensibly.
    style: int = 4
    size: float = 5.0                # cl_crosshairsize
    thickness: float = 0.5           # cl_crosshairthickness
    gap: float = 1.0                 # cl_crosshairgap (can be negative)
    color: int = 1                   # cl_crosshaircolor (0-4 preset, 5 custom)
    red: int = 50
    green: int = 250
    blue: int = 50
    alpha: int = 200
    use_alpha: bool = True           # cl_crosshairusealpha
    draw_outline: bool = True
    outline_thickness: float = 1.0   # cl_crosshair_outlinethickness
    dot: bool = False
    t_style: bool = False
    follow_recoil: bool = False
    split_distance: int = 7          # cl_crosshair_dynamic_splitdist
    inner_split_alpha: float = 1.0
    outer_split_alpha: float = 0.5
    split_size_ratio: float = 0.3
    fixed_gap: float = 3.0           # cl_fixedcrosshairgap
    gap_use_weapon_value: bool = False

    def effective_rgb(self) -> tuple[int, int, int]:
        """The color the game actually drew (presets override r/g/b)."""
        return LEGACY_COLOR_PRESETS.get(self.color, (self.red, self.green, self.blue))

    def effective_alpha(self) -> int:
        return self.alpha if self.use_alpha else 255

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PixelCrosshair:
    version: int = 4
    style: int = 4
    length: int = 8                  # cl_crosshair_length   0-255 px
    thickness: int = 1               # cl_crosshair_thickness 0-31 px
    gap: int = 4                     # cl_crosshair_gap      0-128 px
    red: int = 0
    green: int = 255
    blue: int = 0
    alpha: int = 255                 # cl_crosshaircolor_a
    outline_mode: int = 0            # 0 off, 1 full, 2 half (v3: 0/1 only)
    dot: bool = False
    t_style: bool = False
    follow_recoil: bool = False
    dynamic_spread_limit: int = 255
    split_distance: int = 7
    inner_split_alpha: float = 1.0   # steps of 0.05
    outer_split_alpha: float = 0.5   # steps of 0.05, min 0.3
    split_size_ratio: float = 0.3    # steps of 0.01
    screen_height: int = 1080        # cl_crosshair_screen_height

    @property
    def style_name(self) -> str:
        return PIXEL_STYLES.get(self.style, f"unknown ({self.style})")

    def to_dict(self) -> dict:
        return asdict(self)
