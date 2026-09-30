"""Share code decode/encode, checked against vectors generated with the
reference JS implementation (csgo-sharecode 6.0.0) - see tests/vectors.json."""

import json
import unittest
from pathlib import Path

from cs2xhair import InvalidShareCode, LegacyCrosshair, PixelCrosshair, decode, encode

VECTORS = json.loads((Path(__file__).parent / "vectors.json").read_text())

V1_FIELDS = {
    "gap": "gap", "outline": "outline_thickness", "red": "red", "green": "green", "blue": "blue",
    "alpha": "alpha", "splitDistance": "split_distance", "followRecoil": "follow_recoil",
    "fixedCrosshairGap": "fixed_gap", "color": "color", "outlineEnabled": "draw_outline",
    "innerSplitAlpha": "inner_split_alpha", "outerSplitAlpha": "outer_split_alpha",
    "splitSizeRatio": "split_size_ratio", "thickness": "thickness", "centerDotEnabled": "dot",
    "deployedWeaponGapEnabled": "gap_use_weapon_value", "alphaEnabled": "use_alpha",
    "tStyleEnabled": "t_style", "style": "style", "length": "size",
}
PIXEL_FIELDS = {
    "style": "style", "followRecoil": "follow_recoil", "centerDotEnabled": "dot",
    "tStyleEnabled": "t_style", "red": "red", "green": "green", "blue": "blue", "alpha": "alpha",
    "gap": "gap", "length": "length", "dynamicSpreadLimit": "dynamic_spread_limit",
    "splitDistance": "split_distance", "innerSplitAlpha": "inner_split_alpha",
    "outerSplitAlpha": "outer_split_alpha", "splitSizeRatio": "split_size_ratio",
    "thickness": "thickness", "screenHeight": "screen_height", "outlineMode": "outline_mode",
    "outlineEnabled": "outline_mode",
}


class ReferenceVectors(unittest.TestCase):
    def test_decode_matches_reference(self):
        for vec in VECTORS:
            expected = vec["decoded"]
            xhair = decode(vec["code"])
            fields = V1_FIELDS if expected["version"] == 1 else PIXEL_FIELDS
            self.assertIsInstance(xhair, LegacyCrosshair if expected["version"] == 1 else PixelCrosshair)
            for key, value in expected.items():
                if key == "version":
                    continue
                with self.subTest(code=vec["code"], field=key):
                    self.assertAlmostEqual(float(getattr(xhair, fields[key])), float(value))

    def test_encode_round_trips(self):
        for vec in VECTORS:
            with self.subTest(code=vec["code"]):
                self.assertEqual(encode(decode(vec["code"])), vec["code"])


class Errors(unittest.TestCase):
    def test_bad_checksum(self):
        code = VECTORS[0]["code"]
        broken = code[:-1] + ("A" if code[-1] != "A" else "B")
        with self.assertRaises(InvalidShareCode):
            decode(broken)

    def test_garbage(self):
        for bad in ["", "hello", "CSGO-00000-00000-00000-00000-00000", "CSGO-abc"]:
            with self.subTest(bad=bad), self.assertRaises(InvalidShareCode):
                decode(bad)


if __name__ == "__main__":
    unittest.main()
