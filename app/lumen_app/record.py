"""Region recording through GNOME's existing screencast service.

org.gnome.Shell.Screencast already records a rectangle with Mutter and
GStreamer (hardware H.264 when it can, WebM otherwise). Lumen only chooses
the rectangle and when to stop. That service records picture, not audio,
and it cannot pause.
"""
import os
import time

import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gio, GLib, Gtk  # noqa: E402

from . import SHELL_IFACE, SHELL_PATH  # noqa: E402
from .icons import glyph_button  # noqa: E402

BUS = 'org.gnome.Shell.Screencast'
PATH = '/org/gnome/Shell/Screencast'
IFACE = 'org.gnome.Shell.Screencast'


# Frame rate is the knob the system recorder actually honors. The hardware
# pipeline stays in place; a custom encoder string would turn that off.
QUALITIES = (('流畅', 24), ('标准', 30), ('清晰', 60))


def stage_area(sel, scale, stage=None):
    """Image-pixel selection to stage pixels for ScreencastArea."""
    x, y, w, h = sel
    scale = scale or 1
    x, y = int(round(x / scale)), int(round(y / scale))
    w, h = max(1, int(round(w / scale))), max(1, int(round(h / scale)))
    if stage:
        limit_w, limit_h = int(stage['width']), int(stage['height'])
        x = min(max(0, x), max(0, limit_w - 1))
        y = min(max(0, y), max(0, limit_h - 1))
        w = min(w, limit_w - x)
        h = min(h, limit_h - y)
    return (x, y, max(1, w), max(1, h))



def fit_controls(area, stage, bar=(460, 96)):
    """Keep the control capsule outside the recorded rectangle.

    Returns the area that will actually be recorded, and the capsule origin.
    If the selection covers the screen, a strip is left off the bottom.
    """
    sx, sy, sw, sh = area
    bw, bh = bar
    stage_w = int(stage['width']) if stage else sx + sw + bw + 40
    stage_h = int(stage['height']) if stage else sy + sh + bh + 40

    def clamp(x, y):
        return (max(8, min(int(x), stage_w - bw - 8)),
                max(8, min(int(y), stage_h - bh - 8)))

    def overlaps(x, y, rect):
        rx, ry, rw, rh = rect
        return not (x + bw <= rx or x >= rx + rw or y + bh <= ry or y >= ry + rh)

    candidates = (
        (sx + sw - bw, sy + sh + 28),
        (sx, sy + sh + 28),
        (sx + sw - bw, sy - bh - 28),
        (sx + sw + 28, sy),
        (sx - bw - 28, sy),
    )
    for raw in candidates:
        x, y = clamp(*raw)
        if not overlaps(x, y, area):
            return area, (x, y)
    cut = bh + 16
    if sh - cut >= 32:
        shrunk = (sx, sy, sw, sh - cut)
        x, y = clamp(sx + max(0, sw - bw), sy + sh - bh - 8)
        return shrunk, (x, y)
    return area, clamp(8, 8)


def _clock(seconds):
    seconds = max(0, int(seconds))
    return f'{seconds // 60:02d}:{seconds % 60:02d}'


class CountdownWindow(Gtk.Window):
    """Big 3-2-1 on the live desktop. Destroyed before recording starts."""

    def __init__(self, app, area, on_cancel):
        x, y, w, h = area
        cx = int(x + w / 2 - 110)
        cy = int(y + h / 2 - 80)
        super().__init__(application=app, resizable=False,
                         title=f'lumen-pin@{cx},{cy}')
        self.add_css_class('lumen-countdown')
        self.set_titlebar(Gtk.Box())
        self.label = Gtk.Label(label='3', css_classes=['lumen-count'])
        self.set_child(self.label)
        self.set_default_size(220, 160)
        keys = Gtk.EventControllerKey()
        keys.connect('key-pressed', lambda *_a: on_cancel() or True)
        self.add_controller(keys)
        self.connect('close-request', lambda *_a: on_cancel() or True)

    def set_number(self, number):
        self.label.set_label(str(number))


class RecordWindow(Gtk.Window):
    def __init__(self, recorder, origin):
        x, y = origin
        super().__init__(application=recorder.app, resizable=False,
                         title=f'lumen-pin@{int(x)},{int(y)}')
        self.recorder = recorder
        self.add_css_class('lumen-record')
        self.set_titlebar(Gtk.Box())
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=['lumen-bar'],
                      spacing=2)
        # The shell recorder has no audio or pause. The controls stay visible
        # so the capsule matches the design, and say so when pressed.
        for name, tip in (('mic', '系统区域录屏暂不收音'), ('speaker', '系统区域录屏暂不收录系统声音')):
            button = glyph_button(Gtk.Button, name, tip)
            button.connect('clicked', lambda *_b, text=tip: recorder.note(text))
            bar.append(button)
        bar.append(Gtk.Box(css_classes=['lumen-rec-dot']))
        self.time = Gtk.Label(label='00:00', css_classes=['lumen-time'])
        bar.append(self.time)
        pause = glyph_button(Gtk.Button, 'pause', '系统区域录屏不能暂停')
        pause.connect('clicked', lambda *_: recorder.note('不能暂停'))
        bar.append(pause)
        stop = glyph_button(Gtk.Button, 'stop', '停止    Esc', css=('primary',))
        stop.connect('clicked', lambda *_: recorder.stop())
        bar.append(stop)
        self.set_child(bar)

        keys = Gtk.EventControllerKey()
        keys.connect('key-pressed', self._key)
        self.add_controller(keys)
        self.connect('close-request', lambda *_: recorder.stop() or True)

    def _key(self, _ctrl, keyval, _code, _state):
        name = Gdk_key(keyval)
        if name == 'escape':
            self.recorder.stop()
            return True
        return False


def Gdk_key(keyval):
    from gi.repository import Gdk
    return (Gdk.keyval_name(Gdk.keyval_to_lower(keyval)) or '').lower()


class Recorder:
    def __init__(self, app, area, fps=30, stage=None):
        self.app = app
        self.area = area
        self.stage = stage
        self.fps = fps
        self.filename = None
        self.started_at = None
        self._starting = False
        self._stop_requested = False
        self._closed = False
        self._timer = 0
        self._count_id = 0
        self._count_left = 3
        self._signal = 0
        self._note_until = 0
        self._bus = None
        self.window = None
        self._count_win = None

    def start(self):
        self._count_win = CountdownWindow(self.app, self.area, self.cancel)
        self._count_win.present()
        self._count_id = GLib.timeout_add(900, self._count_step)

    def cancel(self):
        if self.filename or self._starting:
            self.stop()
            return
        self.close()

    def _count_step(self):
        if self._closed:
            return False
        self._count_left -= 1
        if self._count_left > 0:
            self._count_win.set_number(self._count_left)
            return True
        self._count_id = 0
        self._count_win.destroy()
        self._count_win = None
        # Leave a strip only when the selection covers the whole stage, so the
        # shell capsule can sit outside both the picture and the selection.
        self.area, origin = fit_controls(self.area, self.stage)
        # Title it like a pin: the running shell already moves lumen-pin
        # windows, and will not reload extension code until the next login.
        self.window = RecordWindow(self, origin)
        self.window.present()
        GLib.timeout_add(400, self._call_start)
        return False


    def _show_bar(self):
        x, y, w, h = self.area
        params = GLib.Variant('(iiii)', (int(x), int(y), int(w), int(h)))
        try:
            Gio.bus_get_sync(Gio.BusType.SESSION, None).call(
                'org.gnome.Shell', SHELL_PATH, SHELL_IFACE, 'ShowRecordBar',
                params, None, Gio.DBusCallFlags.NONE, 1000, None, None)
        except GLib.Error as error:
            print(f'lumen: record bar: {error}', flush=True)

    def _hide_bar(self):
        try:
            Gio.bus_get_sync(Gio.BusType.SESSION, None).call(
                'org.gnome.Shell', SHELL_PATH, SHELL_IFACE, 'HideRecordBar',
                None, None, Gio.DBusCallFlags.NONE, 1000, None, None)
        except GLib.Error:
            pass

    def note(self, text):
        if self.window is not None:
            self._note_until = time.monotonic() + 1.4
            self.window.time.set_text(text)

    def _call_start(self):
        if self._closed:
            return False
        videos = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS) or GLib.get_home_dir()
        os.makedirs(videos, exist_ok=True)
        template = os.path.join(videos, 'Lumen_%d_%t')
        options = GLib.VariantBuilder.new(GLib.VariantType.new('a{sv}'))
        options.add_value(GLib.Variant.new_dict_entry(
            GLib.Variant.new_string('draw-cursor'),
            GLib.Variant.new_variant(GLib.Variant.new_boolean(True))))
        options.add_value(GLib.Variant.new_dict_entry(
            GLib.Variant.new_string('framerate'),
            GLib.Variant.new_variant(GLib.Variant.new_int32(self.fps))))
        x, y, w, h = self.area
        params = GLib.Variant.new_tuple(
            GLib.Variant.new_int32(x), GLib.Variant.new_int32(y),
            GLib.Variant.new_int32(w), GLib.Variant.new_int32(h),
            GLib.Variant.new_string(template), options.end())
        self._starting = True
        self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self._signal = self._bus.signal_subscribe(
            BUS, IFACE, 'Error', PATH, None, Gio.DBusSignalFlags.NONE, self._on_error)
        self._bus.call(BUS, PATH, IFACE, 'ScreencastArea', params, GLib.VariantType('(bs)'),
                       Gio.DBusCallFlags.NONE, 20000, None, self._started)
        return False

    def _started(self, bus, result):
        self._starting = False
        if self._closed:
            return
        try:
            ok, path = bus.call_finish(result).unpack()
        except GLib.Error as error:
            self.fail(str(error))
            return
        if not ok:
            self.fail('无法开始录屏')
            return
        self.filename = path
        self.started_at = time.monotonic()
        self._timer = GLib.timeout_add(200, self._tick)
        if self._stop_requested:
            self._stop_requested = False
            self.stop()

    def _tick(self):
        if self._closed or self.started_at is None:
            return False
        if time.monotonic() >= self._note_until:
            self.window.time.set_text(_clock(time.monotonic() - self.started_at))
        return True

    def _on_error(self, *_args):
        if not self._closed:
            self.fail('录屏中断')

    def stop(self):
        if self._closed:
            return
        if self._starting:
            self._stop_requested = True
            return
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = 0
        if not self.filename:
            self.close()
            return
        self._bus.call(BUS, PATH, IFACE, 'StopScreencast', None, GLib.VariantType('(b)'),
                       Gio.DBusCallFlags.NONE, 10000, None, self._stopped)

    def _stopped(self, bus, result):
        path = self.filename
        try:
            bus.call_finish(result)
        except GLib.Error as error:
            self.fail(str(error))
            return
        self.close()
        if path:
            note = Gio.Notification.new('录屏已保存')
            note.set_body(os.path.basename(path))
            self.app.send_notification('lumen-saved', note)

    def fail(self, message):
        path = self.filename
        self.close()
        note = Gio.Notification.new('录屏失败')
        note.set_body(message)
        self.app.send_notification('lumen-record', note)
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = 0
        if self._count_id:
            GLib.source_remove(self._count_id)
            self._count_id = 0
        if self._count_win is not None:
            self._count_win.destroy()
            self._count_win = None
        if self._signal and self._bus is not None:
            self._bus.signal_unsubscribe(self._signal)
            self._signal = 0
        if self.window is not None:
            self.window.destroy()
            self.window = None
        if self.app.recorder is self:
            self.app.recorder = None
