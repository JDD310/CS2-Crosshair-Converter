import io
import unittest
from contextlib import redirect_stdout

from cs2xhair import decode
from cs2xhair.cli import main


def run(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(list(argv))
    return code, buf.getvalue().strip()


class CLI(unittest.TestCase):
    def test_code_format(self):
        status, out = run("convert", "cl_crosshairsize 2; cl_crosshairgap -2", "--format", "code")
        self.assertEqual(status, 0)
        self.assertEqual(decode(out).gap, 3)

    def test_shortcut_without_subcommand(self):
        status, out = run("cl_crosshairsize", "3", "--format", "commands")
        self.assertEqual(status, 0)
        self.assertIn('cl_crosshair_length "7"', out)  # 3 * 2.25 = 6.75 -> 7

    def test_new_format_input_passthrough(self):
        status, out = run("CSGO-sP6xU-TSyN9-sZcO5-2D48M-UppkP")
        self.assertIn("already in the new format", out)

    def test_bad_input(self):
        status, _ = run("convert", "hello world")
        self.assertEqual(status, 1)


if __name__ == "__main__":
    unittest.main()
