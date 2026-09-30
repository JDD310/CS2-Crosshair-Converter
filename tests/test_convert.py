import unittest

from cs2xhair import LegacyCrosshair, convert, decode, encode, load, parse_commands
from cs2xhair.convert import legacy_pixels


class PixelMath(unittest.TestCase):
    def test_1080p_static(self):
        # size 2 * 2.25 = 4.5 -> 4 (half to even); thickness 0.5 * 2.25 -> 1
        # space = trunc(4 + -2) = 2; gap = 2 + ceil(1/2) = 3
        new = convert(LegacyCrosshair(style=4, size=2, thickness=0.5, gap=-2), 1080).crosshair
        self.assertEqual((new.length, new.thickness, new.gap, new.style), (4, 1, 3, 4))

    def test_960p_scale(self):
        px = legacy_pixels(LegacyCrosshair(size=3, thickness=1, gap=-3), 960)
        self.assertEqual(px, {"length": 6, "thickness": 2, "space": 1})

    def test_fraction_gap_truncates(self):
        self.assertEqual(legacy_pixels(LegacyCrosshair(gap=-2.5), 1080)["space"], 1)
        self.assertEqual(legacy_pixels(LegacyCrosshair(gap=1.9), 1080)["space"], 5)

    def test_thickness_minimum(self):
        self.assertEqual(convert(LegacyCrosshair(thickness=0), 1080).crosshair.thickness, 1)

    def test_very_negative_gap_clamps(self):
        result = convert(LegacyCrosshair(gap=-10, thickness=1), 1080)
        self.assertEqual(result.crosshair.gap, 0)
        self.assertTrue(any(n.level == "warn" for n in result.notes))

    def test_huge_length_clamps(self):
        self.assertEqual(convert(LegacyCrosshair(size=500), 2160).crosshair.length, 255)


class Mapping(unittest.TestCase):
    def test_color_preset_and_alpha(self):
        new = convert(LegacyCrosshair(color=4, alpha=100, use_alpha=False), 1080).crosshair
        self.assertEqual((new.red, new.green, new.blue, new.alpha), (0, 255, 255, 255))

    def test_custom_color(self):
        new = convert(LegacyCrosshair(color=5, red=1, green=2, blue=3, alpha=77), 1080).crosshair
        self.assertEqual((new.red, new.green, new.blue, new.alpha), (1, 2, 3, 77))

    def test_style_override_and_outline(self):
        new = convert(LegacyCrosshair(style=2, draw_outline=True), 1080, style=7, outline=2).crosshair
        self.assertEqual((new.style, new.outline_mode), (7, 2))

    def test_output_is_valid_v4_code(self):
        new = convert(LegacyCrosshair(), 1080).crosshair
        again = decode(encode(new))
        self.assertEqual(again.to_dict(), new.to_dict())
        self.assertEqual(again.version, 4)


class Commands(unittest.TestCase):
    def test_parse_legacy_cfg(self):
        text = """
        // my crosshair
        cl_crosshairsize "2"; cl_crosshairgap "-2.5"
        cl_crosshairstyle 4
        bind "mouse1" "+attack"
        cl_crosshairdot 1 cl_crosshair_t 1
        """
        parsed = parse_commands(text)
        self.assertEqual(parsed.system, "legacy")
        x = parsed.crosshair
        self.assertEqual((x.size, x.gap, x.style, x.dot, x.t_style), (2.0, -2.5, 4, True, True))
        self.assertIn("bind", parsed.ignored)

    def test_detect_new_commands(self):
        loaded = load("cl_crosshair_length 5; cl_crosshair_gap 3; cl_crosshairstyle 4")
        self.assertFalse(loaded.is_legacy)
        self.assertEqual(loaded.crosshair.length, 5)

    def test_mixed_commands_rejected(self):
        with self.assertRaises(ValueError):
            load("cl_crosshairsize 2; cl_crosshair_length 5")

    def test_code_and_commands_agree(self):
        legacy = LegacyCrosshair(style=4, size=1.5, thickness=1, gap=-3, color=5, red=0, green=255, blue=255)
        from_code = load(encode(legacy)).crosshair
        self.assertEqual(convert(from_code, 1080).crosshair, convert(legacy, 1080).crosshair)


if __name__ == "__main__":
    unittest.main()
