#!/usr/bin/env python3
"""Exercise the real entry point without starting a desktop session."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


LAUNCHER = Path(__file__).resolve().parents[1] / 'app' / 'lumen'


class LauncherTests(unittest.TestCase):
    def run_launcher(self, renderer=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'lumen').write_bytes(LAUNCHER.read_bytes())
            (root / 'lumen_app').mkdir()
            (root / 'lumen_app' / '__init__.py').write_text('')
            (root / 'lumen_app' / 'cli.py').write_text(
                'import os\ndef main(argv):\n print(os.environ.get("GSK_RENDERER", "")); return 0\n')
            env = os.environ.copy()
            env.pop('GSK_RENDERER', None)
            if renderer is not None:
                env['GSK_RENDERER'] = renderer
            return subprocess.check_output([sys.executable, str(root / 'lumen')],
                                           text=True, env=env).strip()

    def test_defaults_to_cairo(self):
        self.assertEqual(self.run_launcher(), 'cairo')

    def test_respects_explicit_renderer(self):
        self.assertEqual(self.run_launcher('gl'), 'gl')


if __name__ == '__main__':
    unittest.main()
