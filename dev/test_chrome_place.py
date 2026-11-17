#!/usr/bin/python3
import os
import unittest

os.environ.setdefault('GI_TYPELIB_PATH', '')

from lumen_app.overlay import bar_origin


class BarOriginTests(unittest.TestCase):
    def test_mode_capsule_sits_just_under_the_selection(self):
        # A selection near the top must not fall to the bottom of the screen.
        origin = bar_origin((40, 40, 300, 180), (220, 48), (2880, 1620))
        self.assertEqual(origin, (80, 226))

    def test_capsule_moves_above_when_the_bottom_is_blocked(self):
        origin = bar_origin((100, 540, 200, 50), (160, 44), (800, 600))
        self.assertEqual(origin, (120, 490))

    def test_fullscreen_tucks_inside_the_bottom_edge(self):
        origin = bar_origin((0, 0, 800, 600), (160, 44), (800, 600))
        self.assertEqual(origin, (320, 548))

    def test_annotation_bar_keeps_the_selection_right_edge(self):
        origin = bar_origin((100, 100, 400, 80), (180, 44), (800, 600), anchor='end')
        self.assertEqual(origin, (320, 186))

    def test_wide_capsule_stays_on_screen(self):
        origin = bar_origin((700, 100, 80, 40), (200, 44), (800, 600))
        self.assertEqual(origin, (592, 146))


if __name__ == '__main__':
    unittest.main()
