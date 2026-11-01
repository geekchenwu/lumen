import math

import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk  # noqa: E402

from . import theme  # noqa: E402
from .icons import glyph_button  # noqa: E402
from .record import QUALITIES, stage_area  # noqa: E402

TOOLS = [
    ('rect', '矩形', 'R'),
    ('ellipse', '椭圆', 'E'),
    ('arrow', '箭头', 'A'),
    ('line', '直线', 'L'),
    ('pen', '画笔', 'P'),
    ('marker', '荧光笔', 'M'),
    ('text', '文字', 'T'),
    ('mosaic', '马赛克', 'X'),
    ('step', '序号', 'N'),
]
TOOL_KEYS = {key.lower(): name for name, _label, key in TOOLS}


def size_family(tool):
    return {'marker': 'marker', 'text': 'text', 'mosaic': 'mosaic', 'step': 'step'}.get(tool, 'stroke')


def _sep():
    sep = Gtk.Box(css_classes=['sep'])
    return sep



class _Swatch(Gtk.DrawingArea):
    def __init__(self, button, color):
        super().__init__(content_width=18, content_height=18, can_target=False)
        self.button = button
        self.color = color
        self.set_draw_func(self._draw)

    def _draw(self, _a, cr, w, h):
        r, g, b = theme.hex_to_rgb(self.color)
        cx, cy = w / 2, h / 2
        if self.button.get_active():
            cr.arc(cx, cy, 8, 0, 2 * math.pi)
            cr.set_source_rgba(0.957, 0.937, 0.902, 0.95)
            cr.set_line_width(1.4)
            cr.stroke()
        cr.arc(cx, cy, 5.4, 0, 2 * math.pi)
        cr.set_source_rgb(r, g, b)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.22)
        cr.set_line_width(1)
        cr.stroke()


class _SizeDot(Gtk.DrawingArea):
    def __init__(self, radius):
        super().__init__(content_width=18, content_height=18, can_target=False)
        self.radius = radius
        self.set_draw_func(self._draw)

    def _draw(self, _a, cr, w, h):
        color = self.get_color()
        cr.arc(w / 2, h / 2, self.radius, 0, 2 * math.pi)
        cr.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        cr.fill()


class Toolbar(Gtk.Box):
    """Tools, stroke and colour on one bar. Cinnabar is only the confirm button."""

    def __init__(self, session):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, css_classes=['lumen-bar'],
                         halign=Gtk.Align.START, valign=Gtk.Align.START, visible=False)
        self.session = session
        self._syncing = False
        self.tool_buttons = {}
        for name, label, key in TOOLS:
            button = glyph_button(Gtk.ToggleButton, name, f'{label}    {key}')
            button.connect('toggled', self._on_tool_toggled, name)
            self.tool_buttons[name] = button
            self.append(button)

        self.prop_sep = _sep()
        self.append(self.prop_sep)
        self.size_buttons = []
        for i, (radius, label) in enumerate(zip((2.5, 4.2, 6.2), ('细', '中', '粗'))):
            button = Gtk.ToggleButton(tooltip_text=label, focus_on_click=False, can_focus=False)
            button.add_css_class('swatch')
            dot = _SizeDot(radius)
            button.set_child(dot)
            button.connect('state-flags-changed', lambda *_a, d=dot: d.queue_draw())
            button.connect('toggled', self._on_size, i)
            self.size_buttons.append(button)
            self.append(button)
        self.color_sep = _sep()
        self.append(self.color_sep)
        self.color_buttons = {}
        for color, name in zip(theme.PALETTE, theme.COLOR_NAMES):
            button = Gtk.ToggleButton(tooltip_text=name, focus_on_click=False, can_focus=False)
            button.add_css_class('swatch')
            swatch = _Swatch(button, color)
            button.set_child(swatch)
            button.connect('toggled', self._on_color, color)
            button.connect('state-flags-changed', lambda *_a, s=swatch: s.queue_draw())
            self.color_buttons[color] = button
            self.append(button)

        self.append(_sep())
        self.undo = self._action('undo', '撤销    Ctrl+Z', session.undo)
        self.redo = self._action('redo', '重做    Ctrl+Y', session.redo)
        self.append(_sep())
        self._action('pin', '贴到屏幕    Ctrl+T', lambda: session.finish('pin'))
        self._action('save', '保存    Ctrl+S', lambda: session.finish('save'))
        self._action('close', '退出    Esc', session.cancel, css=('danger',))
        self._action('check', '复制到剪贴板    Enter', lambda: session.finish('copy'), css=('primary',))

    def _action(self, glyph, tooltip, callback, css=()):
        button = glyph_button(Gtk.Button, glyph, tooltip, css)
        button.connect('clicked', lambda *_: callback())
        self.append(button)
        return button

    def _on_tool_toggled(self, button, name):
        if self._syncing:
            return
        self.session.set_tool(name if button.get_active() else None)

    def _on_size(self, button, index):
        if self._syncing:
            return
        if button.get_active():
            self.session.set_size_index(index)
        self.session.sync_chrome()

    def _on_color(self, button, color):
        if self._syncing:
            return
        if button.get_active():
            self.session.set_color(color)
        self.session.sync_chrome()

    def sync(self):
        self._syncing = True
        for name, button in self.tool_buttons.items():
            button.set_active(self.session.tool == name)
        index = self.session.size_index()
        for i, button in enumerate(self.size_buttons):
            button.set_active(i == index)
        for color, button in self.color_buttons.items():
            button.set_active(color == self.session.color)
            button.get_child().queue_draw()
        show = self.session.tool is not None
        mosaic = self.session.tool == 'mosaic'
        self.prop_sep.set_visible(show)
        for button in self.size_buttons:
            button.set_visible(show)
        self.color_sep.set_visible(show and not mosaic)
        for button in self.color_buttons.values():
            button.set_visible(show and not mosaic)
        self._syncing = False
        self.undo.set_sensitive(bool(self.session.anns))
        self.redo.set_sensitive(bool(self.session.redo_stack))


class ModeBar(Gtk.Box):
    """Shown once a region exists: still or record, then one cinnabar action."""

    def __init__(self, session):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, css_classes=['lumen-bar'],
                         halign=Gtk.Align.START, valign=Gtk.Align.START, visible=False)
        self.session = session
        self._syncing = False
        self.still = Gtk.ToggleButton(label='截图', focus_on_click=False, can_focus=False)
        self.record = Gtk.ToggleButton(label='录屏', focus_on_click=False, can_focus=False)
        self.still.add_css_class('mode')
        self.record.add_css_class('mode')
        self.still.connect('toggled', self._on_still)
        self.record.connect('toggled', self._on_record)
        self.append(self.still)
        self.append(self.record)
        self.append(_sep())
        self.size = Gtk.Label(css_classes=['lumen-time'])
        self.append(self.size)
        self.quality = Gtk.Button(focus_on_click=False, can_focus=False,
                                  tooltip_text='画质，点击切换')
        self.quality.add_css_class('mode')
        self.quality.connect('clicked', self._cycle_quality)
        self.append(self.quality)
        self.action_sep = _sep()
        self.append(self.action_sep)
        self.check = glyph_button(Gtk.Button, 'check', '进入标注    Enter', css=('primary',))
        self.dot = glyph_button(Gtk.Button, 'record', '开始录屏    Enter', css=('primary',))
        self.check.connect('clicked', lambda *_: session.confirm_mode())
        self.dot.connect('clicked', lambda *_: session.confirm_mode())
        self.append(self.check)
        self.append(self.dot)

    def _on_still(self, button):
        if self._syncing:
            return
        if button.get_active():
            self.session.capture_kind = 'still'
        self.sync()

    def _on_record(self, button):
        if self._syncing:
            return
        if button.get_active():
            self.session.capture_kind = 'record'
        self.sync()

    def _cycle_quality(self, *_args):
        self.session.record_quality = (self.session.record_quality + 1) % len(QUALITIES)
        self.sync()

    def sync(self):
        self._syncing = True
        still = self.session.capture_kind != 'record'
        self.still.set_active(still)
        self.record.set_active(not still)
        self.check.set_visible(still)
        self.dot.set_visible(not still)
        self.dot.set_sensitive(self.session.sel is not None and self.session.phase != 'count')
        recording = not still
        self.size.set_visible(recording and self.session.sel is not None)
        self.quality.set_visible(recording)
        self.action_sep.set_visible(True)
        if recording and self.session.sel is not None:
            x, y, w, h = stage_area(self.session.sel, self.session.f)
            self.size.set_text(f'{w} × {h}')
        name, _fps = QUALITIES[self.session.record_quality]
        self.quality.set_label(name)
        self._syncing = False
