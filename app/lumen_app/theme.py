"""Hermès orange draws. Cinnabar confirms."""
import os

import gi

gi.require_version('Gdk', '4.0')
gi.require_version('Gtk', '4.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gdk, Gtk, PangoCairo  # noqa: E402

ACCENT = '#F37021'
ACCENT_HOVER = '#FF8A3D'
# Editor confirm and the single selection corner. Deeper than the annotation red.
CINNABAR = '#C44536'
CINNABAR_HOVER = '#D35445'
INK = '#0E0F11'
PAPER = '#F4EFE6'
GLASS = (0.071, 0.075, 0.086, 0.92)
# Must match DIM in extension.js so the frozen frame hands off seamlessly.
DIM = (8 / 255, 9 / 255, 12 / 255, 0.5)

PALETTE = ['#FF3D2E', ACCENT, '#D7FF3C', '#2EE6D6', '#3D7BFF', '#FFFFFF', '#16171A']
COLOR_NAMES = ['朱红', '爱马仕橙', '青柠', '湖青', '钴蓝', '纯白', '墨黑']

# Logical pixels per size step, keyed by the tool family.
SIZES = {
    'stroke': (2.0, 4.0, 7.0),
    'marker': (12.0, 18.0, 28.0),
    'text': (16.0, 24.0, 36.0),
    'mosaic': (8.0, 14.0, 24.0),
    'step': (11.0, 15.0, 20.0),
}

MONO = 'JetBrains Mono'
SANS = 'Space Grotesk'
TEXT_FAMILY = 'Space Grotesk, Noto Sans CJK SC, sans-serif'

_HERE = os.path.dirname(os.path.abspath(__file__))


def rgba(spec, alpha=None):
    color = Gdk.RGBA()
    if isinstance(spec, tuple):
        color.red, color.green, color.blue = spec[:3]
        color.alpha = spec[3] if len(spec) > 3 else 1.0
    else:
        color.parse(spec)
    if alpha is not None:
        color.alpha = alpha
    return color


def hex_to_rgb(spec):
    spec = spec.lstrip('#')
    return tuple(int(spec[i:i + 2], 16) / 255 for i in (0, 2, 4))


def luminance(spec):
    r, g, b = hex_to_rgb(spec)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def load_fonts():
    fontmap = PangoCairo.FontMap.get_default()
    for root in (os.path.join(_HERE, '..', 'fonts'), os.path.join(_HERE, '..', '..', 'fonts')):
        root = os.path.normpath(root)
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            if name.endswith('.ttf'):
                fontmap.add_font_file(os.path.join(root, name))
        return


CSS = f"""
window.lumen-overlay {{ background: black; }}
/* The shell paints the frozen frame under these (Session.backdrop). */
window.lumen-overlay.shell-backdrop {{ background: transparent; }}

.lumen-bar {{
  background: rgba(18, 19, 22, 0.94);
  border-radius: 14px;
  padding: 5px;
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.42), 0 2px 6px rgba(0, 0, 0, 0.3),
              inset 0 0 0 1px rgba(255, 255, 255, 0.07);
}}
.lumen-bar button {{
  min-width: 34px; min-height: 34px; padding: 0; margin: 0 1px;
  border-radius: 9px; border: none; box-shadow: none; outline: none;
  background: transparent; color: #E8EAED;
  transition: background 120ms ease, color 120ms ease;
}}
.lumen-bar button:hover {{ background: rgba(255, 255, 255, 0.09); }}
.lumen-bar button:active {{ background: rgba(255, 255, 255, 0.14); }}
.lumen-bar button:checked {{ background: rgba(243, 112, 33, 0.22); color: {PAPER}; }}
.lumen-bar button.swatch {{ min-width: 28px; min-height: 28px; margin: 3px 0; border-radius: 8px; }}
.lumen-bar button.mode {{ min-width: 58px; padding: 0 12px; font-size: 13px; }}
.lumen-bar button.primary {{ background: {CINNABAR}; color: {PAPER}; min-width: 40px; }}
.lumen-time {{
  color: {PAPER}; font-family: "{MONO}"; font-size: 13px;
  font-weight: 600; padding: 0 8px 0 4px;
}}
.lumen-rec-dot {{
  background: {CINNABAR}; border-radius: 99px;
  min-width: 8px; min-height: 8px; margin: 0 0 0 8px;
}}
.lumen-bar button.primary:hover {{ background: {CINNABAR_HOVER}; }}
.lumen-bar button.danger:hover {{ background: rgba(196, 69, 54, 0.22); color: #F0B2A8; }}
.lumen-bar button:disabled {{ color: rgba(244, 239, 230, 0.28); }}
.lumen-bar .sep {{ min-width: 1px; background: rgba(244, 239, 230, 0.12); margin: 8px 5px; }}

.lumen-text-editor {{
  border: 1px dashed rgba(243, 112, 33, 0.85);
  border-radius: 4px;
  padding: 2px 4px;
  background: rgba(0, 0, 0, 0.0);
}}
.lumen-text-editor textview, .lumen-text-editor textview text {{
  background: transparent;
  caret-color: {ACCENT};
}}

tooltip.background {{
  background: rgba(18, 19, 22, 0.96);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: none;
}}
tooltip label {{ color: #E8EAED; font-family: "{SANS}", "Noto Sans CJK SC"; font-size: 12px; }}

window.lumen-pin {{ background: transparent; }}
window.lumen-record {{ background: transparent; }}
window.lumen-countdown {{ background: transparent; }}
window.lumen-countdown > .titlebar {{
  min-height: 0; min-width: 0; padding: 0; margin: 0;
  border: none; background: none; box-shadow: none;
}}
.lumen-count {{
  color: #C44536;
  background: rgba(14, 15, 17, 0.94);
  border: 3px solid #F37021;
  border-radius: 36px;
  padding: 4px 28px 16px;
  font-family: "{MONO}", monospace;
  font-size: 120px;
  font-weight: 700;
}}
window.lumen-record > .titlebar {{
  min-height: 0; min-width: 0; padding: 0; margin: 0;
  border: none; background: none; box-shadow: none;
}}
window.lumen-pin > .titlebar {{
  min-height: 0; min-width: 0; padding: 0; margin: 0;
  border: none; background: none; box-shadow: none;
}}
window.lumen-pin.csd {{
  border-radius: 6px;
  box-shadow: 0 0 0 1px {rgba(ACCENT, 0.95).to_string()}, 0 14px 34px rgba(0, 0, 0, 0.42);
}}
window.lumen-pin.csd:backdrop {{
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.22), 0 8px 22px rgba(0, 0, 0, 0.32);
}}
.lumen-osd {{
  background: rgba(18, 19, 22, 0.88);
  color: {ACCENT};
  border-radius: 999px;
  padding: 3px 10px;
  margin: 10px;
  font-family: "{MONO}";
  font-size: 12px;
  font-weight: 600;
}}
popover.lumen-menu contents {{
  background: rgba(18, 19, 22, 0.97);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}}
popover.lumen-menu modelbutton {{ color: #E8EAED; border-radius: 7px; min-height: 30px; }}
popover.lumen-menu modelbutton:hover {{ background: rgba(255, 255, 255, 0.09); }}
popover.lumen-menu accelerator {{ color: rgba(232, 234, 237, 0.45); font-family: "{MONO}"; }}
"""


def install_css():
    provider = Gtk.CssProvider()
    provider.load_from_string(CSS)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
