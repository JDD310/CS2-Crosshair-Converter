"""Command-line interface.

    cs2xhair convert CSGO-xxxxx-xxxxx-xxxxx-xxxxx-xxxxx --height 1080
    cs2xhair convert "cl_crosshairsize 2; cl_crosshairgap -2; cl_crosshairstyle 4"
    cs2xhair convert path/to/autoexec.cfg --format commands -o crosshair.cfg
    cs2xhair decode CSGO-xxxxx-...
    cs2xhair encode "cl_crosshair_length 5; cl_crosshair_gap 3; ..."
    cs2xhair            (no arguments: interactive prompt)
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__, codec
from .commands import legacy_to_commands, pixel_to_commands, render
from .convert import ConversionResult, convert
from .inputs import LoadedInput, load
from .models import LEGACY_STYLES, OUTLINE_MODES, PIXEL_STYLES, LegacyCrosshair, PixelCrosshair

OUTLINE_CHOICES = {name: value for value, name in OUTLINE_MODES.items()}
FORMATS = ("all", "commands", "oneline", "code", "json")


# --------------------------------------------------------------------------- input


def read_input(parts: list[str]) -> str:
    if not parts:
        return _prompt()
    if parts == ["-"]:
        return sys.stdin.read()
    if len(parts) == 1 and os.path.isfile(parts[0]):
        with open(parts[0], encoding="utf-8", errors="replace") as fh:
            return fh.read()
    return " ".join(parts)


def _prompt() -> str:
    print("Paste an old share code or your crosshair commands, then press Enter on an empty line:")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line.strip():
            if lines:
                break
            continue
        lines.append(line)
        if len(lines) == 1 and line.strip().startswith("CSGO-"):
            break
    return "\n".join(lines)


# --------------------------------------------------------------------------- output


def _onoff(value: bool) -> str:
    return "on" if value else "off"


def comparison_table(result: ConversionResult) -> str:
    old, new = result.source, result.crosshair
    r, g, b = old.effective_rgb()
    color_old = f"{r},{g},{b}" + (f" (preset {old.color})" if old.color < 5 else "")
    rows = [
        ("Style", f"{old.style} {LEGACY_STYLES.get(old.style, '?')}", f"{new.style} {new.style_name}"),
        ("Length", f"size {old.size:g}", f"{new.length} px"),
        ("Thickness", f"{old.thickness:g}", f"{new.thickness} px"),
        ("Gap", f"{old.gap:g}", f"{new.gap} px"),
        ("Color (RGB)", color_old, f"{new.red},{new.green},{new.blue}"),
        ("Alpha", f"{old.alpha} (usealpha {_onoff(old.use_alpha)})", str(new.alpha)),
        ("Outline", f"{_onoff(old.draw_outline)} ({old.outline_thickness:g})", OUTLINE_MODES[new.outline_mode]),
        ("Dot / T / Recoil", f"{_onoff(old.dot)} / {_onoff(old.t_style)} / {_onoff(old.follow_recoil)}",
         f"{_onoff(new.dot)} / {_onoff(new.t_style)} / {_onoff(new.follow_recoil)}"),
    ]
    w1 = max(len(r[0]) for r in rows) + 2
    w2 = max(len(r[1]) for r in rows) + 2
    lines = [f"{'Setting':<{w1}}{'Old':<{w2}}New", "-" * (w1 + w2 + 24)]
    lines += [f"{a:<{w1}}{b:<{w2}}{c}" for a, b, c in rows]
    return "\n".join(lines)


def pixel_summary(x: PixelCrosshair) -> str:
    return (
        f"Style {x.style} ({x.style_name}), length {x.length}px, thickness {x.thickness}px, gap {x.gap}px, "
        f"RGBA {x.red},{x.green},{x.blue},{x.alpha}, outline {OUTLINE_MODES.get(x.outline_mode, '?')}, "
        f"dot {_onoff(x.dot)}, T {_onoff(x.t_style)}, made for {x.screen_height}p"
    )


def render_conversion(result: ConversionResult, loaded: LoadedInput, fmt: str) -> str:
    new = result.crosshair
    code = codec.encode(new)
    commands = pixel_to_commands(new)
    if fmt == "code":
        return code
    if fmt == "commands":
        return render(commands)
    if fmt == "oneline":
        return render(commands, one_line=True)
    if fmt == "json":
        return json.dumps(
            {
                "input": loaded.describe(),
                "old": result.source.to_dict(),
                "new": new.to_dict(),
                "share_code": code,
                "commands": dict(commands),
                "notes": [{"level": n.level, "message": n.message} for n in result.notes],
            },
            indent=2,
        )

    out = [
        f"Input : {loaded.describe()}",
        f"Target: {new.screen_height}p render height",
        "",
        comparison_table(result),
        "",
        f"New share code: {code}",
        "",
        "Console commands (paste into the console or autoexec.cfg):",
        render(commands),
        "",
        "One line:",
        render(commands, one_line=True),
    ]
    if loaded.ignored:
        out += ["", f"Ignored {len(loaded.ignored)} non-crosshair command(s): {', '.join(sorted(set(loaded.ignored)))}"]
    if result.notes:
        out += ["", "Notes:"] + [f"  {n}" for n in result.notes]
    return "\n".join(out)


def render_pixel(x: PixelCrosshair, fmt: str, header: str) -> str:
    """For input that is already in the new format."""
    upgraded = PixelCrosshair(**{**x.to_dict(), "version": 4})
    code = codec.encode(upgraded)
    commands = pixel_to_commands(upgraded)
    if fmt == "code":
        return code
    if fmt == "commands":
        return render(commands)
    if fmt == "oneline":
        return render(commands, one_line=True)
    if fmt == "json":
        return json.dumps({"new": upgraded.to_dict(), "share_code": code, "commands": dict(commands)}, indent=2)
    return "\n".join([header, pixel_summary(x), "", f"Share code: {code}", "", render(commands)])


# --------------------------------------------------------------------------- commands


def cmd_convert(args) -> str:
    loaded = load(read_input(args.input))
    if not loaded.is_legacy:
        return render_pixel(loaded.crosshair, args.format, "This crosshair is already in the new format - nothing to convert.")
    result = convert(
        loaded.crosshair,
        screen_height=args.height,
        style=args.style,
        outline=None if args.outline is None else OUTLINE_CHOICES[args.outline],
        spread_limit=args.spread_limit,
    )
    return render_conversion(result, loaded, args.format)


def cmd_decode(args) -> str:
    xhair = codec.decode(" ".join(args.code))
    if args.json:
        return json.dumps({"version": getattr(xhair, "version", 1), **xhair.to_dict()}, indent=2)
    if isinstance(xhair, LegacyCrosshair):
        return "Old (version 1) crosshair code. Original commands:\n\n" + render(legacy_to_commands(xhair))
    return f"New (version {xhair.version}) crosshair code.\n{pixel_summary(xhair)}\n\n" + render(pixel_to_commands(xhair))


def cmd_encode(args) -> str:
    loaded = load(read_input(args.input))
    if loaded.kind == "code":
        return codec.encode(loaded.crosshair)
    if isinstance(loaded.crosshair, PixelCrosshair):
        loaded.crosshair.version = 4
    return codec.encode(loaded.crosshair)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cs2xhair",
        description="Convert pre-1.41.8.2 CS2/CS:GO crosshairs (share codes or commands) to the new pixel-based system.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("convert", help="convert an old share code / commands / .cfg file")
    p.add_argument("input", nargs="*", help="share code, commands, a .cfg path, or - for stdin (blank = prompt)")
    p.add_argument("--height", type=int, default=1080,
                   help="vertical render resolution you play at, e.g. 1080 or 960 for 1280x960 (default 1080)")
    p.add_argument("--style", type=int, choices=sorted(PIXEL_STYLES), help="force a new crosshair style")
    p.add_argument("--outline", choices=list(OUTLINE_CHOICES), help="force outline mode (default: keep on/off)")
    p.add_argument("--spread-limit", type=int, default=255, help="cl_crosshair_dynamic_spread_limit (default 255)")
    p.add_argument("--format", choices=FORMATS, default="all", help="what to print (default all)")
    p.add_argument("-o", "--output", help="also write the result to this file")
    p.set_defaults(func=cmd_convert)

    p = sub.add_parser("decode", help="show what's inside any crosshair share code")
    p.add_argument("code", nargs="+")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_decode, output=None)

    p = sub.add_parser("encode", help="build a share code from crosshair commands")
    p.add_argument("input", nargs="*")
    p.set_defaults(func=cmd_encode, output=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    if not argv:
        argv = ["convert"]  # double-click / bare run: interactive prompt
    elif argv[0] not in ("convert", "decode", "encode", "-h", "--help", "--version"):
        argv = ["convert", *argv]  # `cs2xhair CSGO-...` works as a shortcut
    args = parser.parse_args(argv)

    try:
        text = args.func(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(text)
    if getattr(args, "output", None):
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"\nSaved to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
