# CS2-Crosshair-Converter

Converts a **pre-1.41.8.2** crosshair (CS:GO / old CS2 share code, or your old `cl_crosshair*` commands) into the
**pixel-based crosshair system** introduced in CS2 1.41.8.2 / 1.41.8.3 (the September 22–24, 2026 "Rush Hour" update).

It gives you:

- a **new share code** (version 4, the current format) you can import in game
- the **new console commands** (`cl_crosshair_length`, `cl_crosshair_gap`, …) for your console or `autoexec.cfg`
- an old → new comparison table, plus notes on anything that couldn't carry over exactly

Pure Python 3.9+, no dependencies.

## Quick start

```powershell
cd CS2-Crosshair-Converter
python -m cs2xhair                       # interactive: paste a code or commands
python -m cs2xhair CSGO-xxxxx-xxxxx-xxxxx-xxxxx-xxxxx
python -m cs2xhair "cl_crosshairsize 2; cl_crosshairgap -2; cl_crosshairstyle 4" --height 1080
python -m cs2xhair convert "C:\Program Files (x86)\Steam\...\cfg\autoexec.cfg" --format commands -o new_crosshair.cfg
```

Or install it so `cs2xhair` works from anywhere: `pip install -e .`

### Options (`convert`)

| Option | Meaning |
|---|---|
| `--height N` | Vertical **render** resolution you play at (default `1080`). Stretched 1280×960 → `960`. |
| `--style N` | Force a new style (0–8) instead of the automatic mapping. |
| `--outline off\|full\|half` | Force outline mode. Default keeps on/off from the old crosshair. |
| `--spread-limit N` | `cl_crosshair_dynamic_spread_limit` (default 255). |
| `--format all\|commands\|oneline\|code\|json` | What to print. |
| `-o FILE` | Also save the output to a file (e.g. a `.cfg`). |

### Other commands

- `python -m cs2xhair decode CODE` – show what's inside any share code (old or new).
- `python -m cs2xhair encode "cl_crosshair_length 5; ..."` – build a share code from commands.

## How the conversion works

### 1. Reading share codes

A share code is 18 bytes written as one big number in base 57
(alphabet `ABCDEFGHJKLMNOPQRSTUVWXYZabcdefhijkmnopqrstuvwxyz23456789`, least-significant digit first).
Byte 0 is a checksum (sum of the other bytes mod 256) and byte 1 is the format version:

| Version | CS2 build | Notes |
|---|---|---|
| 1 | < 1.41.8.2 (and all of CS:GO) | Sizes stored ×10 as "units", color presets, outline thickness |
| 3 | 1.41.8.2 | Sizes in whole **pixels** + the screen height they were made for |
| 4 | 1.41.8.3+ | v3 + outline mode (off / full / half) and Static Square style |

Full byte layouts are documented at the top of [`cs2xhair/codec.py`](cs2xhair/codec.py).

### 2. Old units → pixels

The old game scaled everything by `render height / 480`, except the gap:

```
scale      = height / 480                      (2.25 at 1080p, 2.0 at 960p)
length_px  = round(size × scale)               (round half to even)
thick_px   = max(1, round(thickness × scale))
space_px   = trunc(4 + gap)                    (gap was NOT resolution-scaled)
```

The new gap is measured from the crosshair center, so:

```
new gap = space_px + ceil(new thickness / 2)
```

Worked example at 1080p, `size 2, thickness 0.5, gap -2`:
length = round(4.5) = **4**, thickness = round(1.125) = **1**, gap = trunc(2) + ceil(0.5) = **3**.

The new code stores `screen_height`, so the game rescales it correctly if you later change resolution.

### 3. Everything else

| Old setting | New | Rule |
|---|---|---|
| `cl_crosshairstyle` | `cl_crosshairstyle` | 4 Classic Static → 4 Static Cross (exact). 2 → 2, 5 → 5 (suggested). 0, 1, 3 → nearest match (warned). |
| `cl_crosshaircolor` 0–4 | `cl_crosshaircolor_r/g/b` | Presets become RGB (red, green, yellow, blue, cyan). |
| `cl_crosshairalpha` + `cl_crosshairusealpha` | `cl_crosshaircolor_a` | Alpha if usealpha was on, else 255. |
| `cl_crosshair_drawoutline` + `outlinethickness` | `cl_crosshair_drawoutline` 0/1/2 | On → full. Thickness no longer exists (try `--outline half`). |
| dot, T, recoil, split settings | same names | Carried over; split values clamped to new ranges. |
| negative gap | – | New gap can't go below 0, so overlapping-bar crosshairs are clamped (warned). |
| `cl_fixedcrosshairgap`, `cl_crosshairgap_useweaponvalue` | removed | Dropped (noted). |

### Confidence

- **Verified:** Classic Static crosshairs at 1920×1080 and 1280×960 (on-screen pixel measurements).
- **Same math, less certain:** other resolutions and dynamic styles. The converter prints a warning; check it in game.

## Project layout

```
cs2xhair/
  sharecode.py   base-57 <-> bytes, checksum
  codec.py       decode/encode v1, v3, v4 share codes
  models.py      LegacyCrosshair / PixelCrosshair dataclasses, style + color tables
  commands.py    parse .cfg / console text, render new commands
  convert.py     old -> new conversion rules and notes
  inputs.py      auto-detect share code vs commands
  cli.py         command-line interface
tests/           unittest suite (python -m unittest discover -s tests)
```

`tests/vectors.json` holds 81 share codes generated with the reference JS library, so the codec is checked
byte-for-byte against an independent implementation.

## Sources / credits

- Share code layouts cross-checked against [csgo-sharecode](https://github.com/akiver/csgo-sharecode) by AkiVer (MIT).
- Pixel conversion rules: [CS2 Crosshair Restore – conversion method](https://crosshairrestore.com/conversion-method/).
- Cvar renames/ranges: [SyberiaK/csxhair#1](https://github.com/SyberiaK/csxhair/issues/1),
  [timesaver.gg](https://timesaver.gg/news/cs2-crosshair-settings-update-old-codes-not-working),
  [SkinsMonkey](https://skinsmonkey.com/blog/cs2-crosshair-update-september-2026).
