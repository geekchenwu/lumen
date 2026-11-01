#!/usr/bin/python3
import os
import unittest

os.environ.setdefault('GI_TYPELIB_PATH', '')

from lumen_app.record import fit_controls, stage_area, _clock


class RecordAreaTests(unittest.TestCase):
    def test_stage_pixels_follow_scale(self):
        self.assertEqual(stage_area((200, 100, 400, 300), 2), (100, 50, 200, 150))

    def test_zero_scale_does_not_divide(self):
        self.assertEqual(stage_area((10, 10, 20, 20), 0), (10, 10, 20, 20))


    def test_capsule_sits_below_a_partial_selection(self):
        area = (100, 100, 400, 300)
        stage = {'width': 2880, 'height': 1620}
        recorded, origin = fit_controls(area, stage)
        self.assertEqual(recorded, area)
        self.assertEqual(origin, (40, 428))

    def test_fullscreen_keeps_a_bottom_strip_out_of_the_recording(self):
        stage = {'width': 2880, 'height': 1620}
        recorded, origin = fit_controls((0, 0, 2880, 1620), stage)
        self.assertEqual(recorded, (0, 0, 2880, 1508))
        self.assertEqual(origin, (2412, 1516))
        # The capsule must not overlap the recorded rectangle.
        x, y = origin
        rx, ry, rw, rh = recorded
        self.assertTrue(y >= ry + rh or y + 96 <= ry or x >= rx + rw or x + 460 <= rx)

    def test_clock(self):
        self.assertEqual(_clock(0), '00:00')
        self.assertEqual(_clock(75), '01:15')


if __name__ == '__main__':
    unittest.main()
