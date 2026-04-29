"""
GridScreen — improved masonry grid with search bar, theme toggle,
multi-select, and true staggered two-column layout.
"""

import os
from kivy.uix.screenmanager import Screen, RiseInTransition
from kivy.uix.scrollview    import ScrollView
from kivy.uix.boxlayout     import BoxLayout
from kivy.uix.floatlayout   import FloatLayout
from kivy.uix.label         import Label
from kivy.uix.textinput     import TextInput
from kivy.uix.widget        import Widget
from kivy.uix.image         import Image as KivyImage
from kivy.uix.behaviors     import ButtonBehavior
from kivy.uix.checkbox      import CheckBox
from kivy.graphics          import (Color, RoundedRectangle, Rectangle,
                                    StencilPush, StencilUse, StencilUnUse,
                                    StencilPop, Line)
from kivy.app               import App
from kivy.clock             import Clock
from kivy.metrics           import dp
from kivy.core.window       import Window

from utils.font_manager import APP_FONT
from utils.storage      import make_note

LONG_PRESS_DURATION = 0.45

_ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icons')
def _icon(name): return os.path.join(_ICON_DIR, name)

# 12-colour palette identical to theme.py NOTE_COLORS_LIGHT/DARK
NOTE_COLORS_LIGHT = [
    [1.000, 1.000, 1.000, 1],
    [1.000, 0.871, 0.835, 1],
    [0.992, 0.729, 0.376, 1],
    [1.000, 0.976, 0.729, 1],
    [0.851, 0.965, 0.843, 1],
    [0.820, 0.961, 0.929, 1],
    [0.820, 0.902, 0.965, 1],
    [0.875, 0.820, 0.965, 1],
    [0.965, 0.820, 0.929, 1],
    [0.965, 0.855, 0.820, 1],
    [0.922, 0.929, 0.937, 1],
    [0.776, 0.890, 0.878, 1],
]
NOTE_COLORS_DARK = [
    [0.176, 0.180, 0.188, 1],
    [0.290, 0.149, 0.145, 1],
    [0.302, 0.208, 0.094, 1],
    [0.302, 0.286, 0.098, 1],
    [0.141, 0.259, 0.141, 1],
    [0.125, 0.255, 0.239, 1],
    [0.125, 0.204, 0.282, 1],
    [0.200, 0.153, 0.302, 1],
    [0.290, 0.149, 0.247, 1],
    [0.290, 0.196, 0.149, 1],
    [0.220, 0.227, 0.235, 1],
    [0.141, 0.243, 0.231, 1],
]

# Always export so edit_screen can import
NOTE_COLORS_FIXED = NOTE_COLORS_LIGHT


def _card_color(idx, dark=False):
    pal = NOTE_COLORS_DARK if dark else NOTE_COLORS_LIGHT
    return list(pal[max(0, min(idx, len(pal) - 1))])


def _luminance(rgba):
    r, g, b = rgba[:3]
    return 0.299 * r + 0.587 * g + 0.114 * b


def _text_color(rgba):
    return [0.08, 0.08, 0.08, 1] if _luminance(rgba) > 0.45 else [0.92, 0.92, 0.92, 1]


def _secondary_color(rgba):
    return [0.30, 0.30, 0.30, 1] if _luminance(rgba) > 0.45 else [0.68, 0.68, 0.68, 1]


# ─────────────────────────────────────────────────────────────────────────────
# IconButton
# ─────────────────────────────────────────────────────────────────────────────
class IconButton(ButtonBehavior, KivyImage):
    def __init__(self, source, size_dp, on_press_cb=None, fixed_size=False, **kwargs):
        super().__init__(**kwargs)
        self.source = source
        self._cb    = on_press_cb
        if fixed_size:
            self.size_hint = (None, None)
            self.size      = (dp(size_dp), dp(size_dp))
        else:
            self.size_hint = (None, 1)
            self.width     = dp(size_dp)
        try: self.fit_mode = 'contain'
        except Exception: pass

    def on_press(self):
        if self._cb: self._cb(self)


def _img_btn(icon_name, size_dp, on_press, fixed_size=False):
    b = IconButton(source=_icon(icon_name), size_dp=size_dp,
                   on_press_cb=on_press, fixed_size=fixed_size)
    return b, b


# ─────────────────────────────────────────────────────────────────────────────
# RoundedImageView — stencil-clipped hero image
# ─────────────────────────────────────────────────────────────────────────────
class RoundedImageView(BoxLayout):
    def __init__(self, source, radius=dp(8), **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            StencilPush()
            Color(1, 1, 1, 1)
            self._sr = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
            StencilUse()
        with self.canvas.after:
            StencilUnUse()
            Color(1, 1, 1, 1)
            self._sr2 = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
            StencilPop()
        self.bind(pos=self._upd, size=self._upd)
        img = KivyImage(source=source, size_hint=(1, 1), allow_stretch=True)
        try: img.fit_mode = 'cover'
        except Exception: img.keep_ratio = False
        self.add_widget(img)

    def _upd(self, *a):
        self._sr.pos = self._sr2.pos = self.pos
        self._sr.size = self._sr2.size = self.size


# ─────────────────────────────────────────────────────────────────────────────
# FAB button
# ─────────────────────────────────────────────────────────────────────────────
class FABButton(ButtonBehavior, Widget):
    def __init__(self, on_press_cb=None, **kwargs):
        super().__init__(**kwargs)
        self._cb       = on_press_cb
        self.size_hint = (None, None)
        self.size      = (dp(56), dp(56))
        with self.canvas:
            self._shadow_color = Color(0, 0, 0, 0.18)
            self._shadow       = RoundedRectangle(
                pos=(self.x + dp(2), self.y - dp(2)),
                size=(dp(56), dp(56)), radius=[dp(16)])
            self._bg_color = Color(0.102, 0.451, 0.910, 1)
            self._bg       = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[self.width/2])
        self.bind(pos=self._upd, size=self._upd)

        # + label
        self._icon = KivyImage(
            source=_icon('quill.png'),   # ← use sun icon here
            size_hint=(None, None),
            size=(dp(26), dp(26)),
        )
        self.add_widget(self._icon)

        # center it
        self.bind(pos=lambda *a: setattr(self._icon, 'pos', (
            self.x + self.width/2 - self._icon.width/2,
            self.y + self.height/2 - self._icon.height/2
        )))

    def _upd(self, *a):
        self._bg.pos    = self.pos
        self._bg.size   = self.size
        self._shadow.pos = (self.x + dp(2), self.y - dp(2))
        self._shadow.size = self.size

    def set_color(self, rgba):
        self._bg_color.rgba = rgba

    def on_press(self):
        if self._cb: self._cb(self)


# ─────────────────────────────────────────────────────────────────────────────
# _make_label
# ─────────────────────────────────────────────────────────────────────────────
def _make_label(text, font_size, color, max_lines, bold=False, shorten=False):
    lbl = Label(
        text=text, font_name=APP_FONT, font_size=font_size,
        bold=bold, color=color,
        size_hint_y=None, halign='left', valign='top',
        text_size=(None, None),
        max_lines=max_lines, shorten=shorten, shorten_from='right',
    )
    lbl.bind(width=lambda w, v: setattr(w, 'text_size', (v, None)))
    lbl.bind(texture_size=lambda w, v: setattr(w, 'height', v[1]))
    return lbl


# ─────────────────────────────────────────────────────────────────────────────
# NoteCard
# ─────────────────────────────────────────────────────────────────────────────
class NoteCard(BoxLayout):
    def __init__(self, note, on_tap=None, on_long_press=None, dark=False, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.note           = note
        self._on_tap        = on_tap
        self._on_long_press = on_long_press
        self._lp_event      = None
        self.selected       = False
        self._dark          = dark
        self.size_hint_y    = None
        self.padding        = [dp(10), dp(10), dp(10), dp(10)]
        self.spacing        = dp(5)
        self._build()

    def _build(self):
        note  = self.note
        cidx  = note.get('color_index', 0)
        cc    = _card_color(cidx, self._dark)
        tc    = _text_color(cc)
        sc    = _secondary_color(cc)

        with self.canvas.before:
            self._bg_c = Color(*cc)
            self._bg_r = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(10)])
            # Border: more visible in dark, subtle in light
            if self._dark:
                self._bd_c = Color(1, 1, 1, 0.10)   # faint white pop
            else:
                self._bd_c = Color(0, 0, 0, 0.08)
            self._bd_l = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height,
                                   dp(10)), width=dp(1.0))
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        if note.get('title'):
            self.add_widget(_make_label(note['title'], dp(13.5), tc, 3, bold=True))

        has_body = bool(note.get('body', '').strip())
        has_cl   = bool(note.get('checklist'))

        if has_body:
            lines = 3 if not has_cl and not note.get('title') else 1
            self.add_widget(_make_label(
                note['body'], dp(12), sc, lines, shorten=(lines == 1)))

        if has_cl:
            MAX = 5
            for item in note['checklist'][:MAX]:
                row = BoxLayout(size_hint_y=None, height=dp(20), spacing=dp(4))
                cb  = CheckBox(
                    active=item.get('checked', False),
                    size_hint=(None, None), size=(dp(16), dp(16)),
                    color=tc, disabled=True,
                )
                txt = Label(
                    text=item.get('text', ''), font_name=APP_FONT,
                    font_size=dp(11.5), color=sc,
                    size_hint_y=None, height=dp(20),
                    halign='left', valign='middle', max_lines=1,
                    shorten=True, shorten_from='right',
                    text_size=(None, dp(20)),
                )
                txt.bind(width=lambda w, v: setattr(w, 'text_size', (v, dp(20))))
                row.add_widget(cb)
                row.add_widget(txt)
                self.add_widget(row)
            rem = len(note['checklist']) - MAX
            if rem > 0:
                more = Label(
                    text=f'+ {rem} more', font_name=APP_FONT,
                    font_size=dp(10.5), color=sc,
                    size_hint_y=None, height=dp(15), halign='left',
                )
                more.bind(size=lambda w, v: setattr(w, 'text_size', v))
                self.add_widget(more)

        if note.get('images'):
            p = note['images'][0]
            if os.path.exists(p):
                self.add_widget(RoundedImageView(
                    source=p, radius=dp(8),
                    size_hint=(1, None), height=dp(90)))

        # selection ring (hidden by default)
        with self.canvas.after:
            self._sel_c = Color(0.102, 0.451, 0.910, 0)
            self._sel_l = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height,
                                   dp(10)), width=dp(2))

        for c in self.children:
            c.bind(height=self._recompute)
        self._recompute()

    def _recompute(self, *a):
        n     = len(self.children)
        total = (self.padding[1] + self.padding[3]
                 + sum(c.height for c in self.children)
                 + self.spacing * max(0, n - 1))
        self.height = max(total, dp(52))

    def _upd_bg(self, *a):
        self._bg_r.pos  = self.pos
        self._bg_r.size = self.size
        self._bd_l.rounded_rectangle = (
            self.x, self.y, self.width, self.height, dp(10))
        self._sel_l.rounded_rectangle = (
            self.x, self.y, self.width, self.height, dp(10))

    def refresh_colors(self, dark):
        self._dark = dark
        cidx = self.note.get('color_index', 0)
        cc   = _card_color(cidx, dark)
        self._bg_c.rgba = cc

    def set_selected(self, sel):
        self.selected = sel
        if sel:
            self._sel_c.a = 1.0
            self._bg_c.rgba = [0.82, 0.898, 1.0, 1] if not self._dark \
                               else [0.125, 0.220, 0.345, 1]
        else:
            self._sel_c.a = 0.0
            cidx = self.note.get('color_index', 0)
            self._bg_c.rgba = _card_color(cidx, self._dark)

    # Touch
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._lp_event = Clock.schedule_once(
                self._fire_lp, LONG_PRESS_DURATION)
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self._lp_event:
            self._lp_event.cancel()
            self._lp_event = None
            if self.collide_point(*touch.pos) and self._on_tap:
                self._on_tap(self.note)
        return super().on_touch_up(touch)

    def on_touch_move(self, touch):
        if self._lp_event and not self.collide_point(*touch.pos):
            self._lp_event.cancel()
            self._lp_event = None
        return super().on_touch_move(touch)

    def _fire_lp(self, dt):
        self._lp_event = None
        if self._on_long_press:
            self._on_long_press(self.note, self)


# ─────────────────────────────────────────────────────────────────────────────
# StaggeredGrid — true masonry
# ─────────────────────────────────────────────────────────────────────────────
class StaggeredGrid(BoxLayout):
    _GAP = dp(8)

    def __init__(self, notes, on_tap, on_long_press, card_registry,
                 dark=False, **kwargs):
        super().__init__(
            orientation='horizontal', size_hint_y=None,
            spacing=dp(8),
            padding=[dp(10), dp(4), dp(10), dp(4)],
            **kwargs)
        self._dark = dark

        self._col_l = BoxLayout(
            orientation='vertical', size_hint=(1, None), spacing=self._GAP)
        self._col_l.bind(minimum_height=self._col_l.setter('height'))
        self._col_r = BoxLayout(
            orientation='vertical', size_hint=(1, None), spacing=self._GAP)
        self._col_r.bind(minimum_height=self._col_r.setter('height'))

        self.add_widget(self._col_l)
        self.add_widget(self._col_r)

        self._lh = self._rh = 0.0
        self._build(notes, on_tap, on_long_press, card_registry)
        self._col_l.bind(height=self._sync)
        self._col_r.bind(height=self._sync)
        self._sync()

    def _sync(self, *_):
        self.height = max(self._col_l.height, self._col_r.height, dp(48))

    def _build(self, notes, on_tap, on_long_press, reg):
        for note in notes:
            card = NoteCard(note=note, on_tap=on_tap,
                            on_long_press=on_long_press, dark=self._dark)
            reg[note['id']] = card
            if self._lh <= self._rh:
                self._col_l.add_widget(card)
                self._lh += card.height + self._GAP
                card.bind(height=lambda w, h, side='l': self._recalc(side))
            else:
                self._col_r.add_widget(card)
                self._rh += card.height + self._GAP
                card.bind(height=lambda w, h, side='r': self._recalc(side))

    def _recalc(self, side):
        col  = self._col_l if side == 'l' else self._col_r
        kids = col.children
        tot  = sum(c.height for c in kids) + self._GAP * max(0, len(kids) - 1)
        if side == 'l': self._lh = tot
        else:           self._rh = tot
        self._sync()


# ─────────────────────────────────────────────────────────────────────────────
# SectionLabel
# ─────────────────────────────────────────────────────────────────────────────
class SectionLabel(BoxLayout):
    def __init__(self, text, **kwargs):
        super().__init__(
            orientation='horizontal', size_hint_y=None, height=dp(30),
            padding=[dp(14), 0, dp(14), 0], **kwargs)
        app = App.get_running_app()
        self.tm = app.theme_manager
        self.lbl = Label(
            text=text.upper(), font_name=APP_FONT,
            font_size=dp(11), bold=True,
            color=self.tm.get('pinned_label'),
            halign='left', valign='middle',
        )
        self.lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))
        self.add_widget(self.lbl)
        self.tm.bind(on_theme_change=lambda *a: setattr(
            self.lbl, 'color', self.tm.get('pinned_label')))


# ─────────────────────────────────────────────────────────────────────────────
# SelectionBar
# ─────────────────────────────────────────────────────────────────────────────
class SelectionBar(BoxLayout):
    def __init__(self, on_delete=None, on_pin=None, on_cancel=None, **kwargs):
        super().__init__(
            orientation='horizontal', size_hint_y=None, height=dp(52),
            padding=[dp(8), dp(6)], spacing=dp(8), **kwargs)
        app = App.get_running_app()
        self.tm = app.theme_manager
        with self.canvas.before:
            self._bg_c = Color(*self.tm.get('topbar_bg'))
            self._bg_r = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)
        self.tm.bind(on_theme_change=lambda *a: self._apply_theme())

        self.cancel_btn, _ = _img_btn('ic_close.png',  34, lambda x: on_cancel()  if on_cancel  else None)
        self.pin_btn,    _ = _img_btn('ic_pin.png',    34, lambda x: on_pin()     if on_pin     else None)
        self.del_btn,    _ = _img_btn('ic_delete.png', 34, lambda x: on_delete()  if on_delete  else None)
        self.count_lbl = Label(
            text='0 selected', font_name=APP_FONT, font_size=dp(15),
            color=self.tm.get('topbar_text'), halign='left',
        )
        self.count_lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))
        self.add_widget(self.cancel_btn)
        self.add_widget(self.count_lbl)
        self.add_widget(Widget())
        self.add_widget(self.pin_btn)
        self.add_widget(self.del_btn)

    def _upd(self, *a):
        self._bg_r.pos = self.pos; self._bg_r.size = self.size

    def _apply_theme(self):
        self._bg_c.rgba     = self.tm.get('topbar_bg')
        self.count_lbl.color = self.tm.get('topbar_text')

    def set_count(self, n):
        self.count_lbl.text = f'{n} selected'


# ─────────────────────────────────────────────────────────────────────────────
# AppTopBar  — title + search + theme toggle
# ─────────────────────────────────────────────────────────────────────────────
class AppTopBar(BoxLayout):
    def __init__(self, on_theme_toggle=None, on_search=None, **kwargs):
        super().__init__(
            orientation='vertical', size_hint_y=None, height=dp(108),
            **kwargs)
        app = App.get_running_app()
        self.tm = app.theme_manager
        self._on_search = on_search

        with self.canvas.before:
            self._bg_c = Color(*self.tm.get('topbar_bg'))
            self._bg_r = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)
        self.tm.bind(on_theme_change=lambda *a: self._apply_theme())

        # ── Row 1: title + theme btn ─────────────────────────────────────────
        row1 = BoxLayout(
            orientation='horizontal', size_hint_y=None, height=dp(52),
            padding=[dp(16), 0, dp(12), 0], spacing=dp(8))

        self.title_lbl = Label(
            text='KeepIt', font_name=APP_FONT,
            font_size=dp(22), bold=True,
            color=self.tm.get('topbar_text'),
            halign='left', valign='middle',
        )
        self.title_lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))

        self._on_toggle = on_theme_toggle
        icon = 'ic_sun.png' if self.tm.mode == 'dark' else 'ic_moon.png'
        self.theme_btn, self.theme_img = _img_btn(icon, 30, self._do_toggle)

        row1.add_widget(self.title_lbl)
        row1.add_widget(self.theme_btn)

        # ── Row 2: search bar (V3 — Label overlay over TextInput) ───────────
        # A Label is stacked above the TextInput in a FloatLayout. It shows
        # the hint text and is perfectly centered. On focus or any typing it
        # becomes invisible. The TextInput itself has no hint_text at all.

        row2 = BoxLayout(
            orientation='horizontal', size_hint_y=None, height=dp(48),
            padding=[dp(12), dp(6), dp(12), dp(6)],
        )

        self._search_bg_box = FloatLayout(size_hint=(1, 1))
        with self._search_bg_box.canvas.before:
            self._srch_bg_c = Color(*self.tm.get('search_bg'))
            self._srch_bg_r = RoundedRectangle(
                pos=self._search_bg_box.pos,
                size=self._search_bg_box.size,
                radius=[dp(22)])
        self._search_bg_box.bind(pos=self._upd_srch, size=self._upd_srch)

        # Real TextInput — no hint, transparent bg, fixed height, centered
        self.search_input = TextInput(
            hint_text='',
            font_name=APP_FONT, font_size=dp(14),
            multiline=False,
            size_hint=(1, None), height=dp(36),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            background_color=[0, 0, 0, 0],
            foreground_color=self.tm.get('text_primary'),
            cursor_color=self.tm.get('accent'),
            padding=[dp(14), dp(10), dp(14), dp(10)],
        )
        self.search_input.bind(text=self._on_text)
        self.search_input.bind(focus=self._on_srch_focus)
        self.search_input.bind(text=self._on_srch_text)

        # Label overlay — perfectly centered, pointer ignored
        self._hint_overlay = Label(
            text='Search your notes',
            font_name=APP_FONT, font_size=dp(14),
            color=self.tm.get('text_muted'),
            size_hint=(1, None), height=dp(36),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='left', valign='middle',
        )
        self._hint_overlay.bind(
            size=lambda w, v: setattr(w, 'text_size', (v[0] - dp(28), v[1])))

        self._search_bg_box.add_widget(self.search_input)
        self._search_bg_box.add_widget(self._hint_overlay)
        row2.add_widget(self._search_bg_box)

        self.add_widget(row1)
        self.add_widget(row2)

    def _upd(self, *a):
        self._bg_r.pos = self.pos; self._bg_r.size = self.size

    def _upd_srch(self, *a):
        self._srch_bg_r.pos  = self._search_bg_box.pos
        self._srch_bg_r.size = self._search_bg_box.size

    def _on_srch_focus(self, inp, focused):
        if focused:
            self._hint_overlay.opacity = 0
        elif not inp.text:
            self._hint_overlay.opacity = 1

    def _on_srch_text(self, inp, val):
        self._hint_overlay.opacity = 0 if val else 1

    def _on_text(self, inp, val):
        if self._on_search: self._on_search(val)

    def _do_toggle(self, *a):
        if self._on_toggle: self._on_toggle()

    def _apply_theme(self):
        tm = self.tm
        self._bg_c.rgba                    = tm.get('topbar_bg')
        self._srch_bg_c.rgba               = tm.get('search_bg')
        self.title_lbl.color               = tm.get('topbar_text')
        self.search_input.foreground_color = tm.get('text_primary')
        self._hint_overlay.color           = tm.get('text_muted')
        icon = 'ic_sun.png' if tm.mode == 'dark' else 'ic_moon.png'
        self.theme_img.source = _icon(icon)


# ─────────────────────────────────────────────────────────────────────────────
# GridScreen
# ─────────────────────────────────────────────────────────────────────────────
class GridScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_ids       = set()
        self.card_widgets       = {}
        self._multi_select      = False
        self._search_query      = ''

        app          = App.get_running_app()
        self.tm      = app.theme_manager
        self.storage = app.note_storage
        self._build_ui()
        self.tm.bind(on_theme_change=lambda *a: self._apply_theme())
        self.bind(size=self._upd_bg, pos=self._upd_bg)

    def _build_ui(self):
        tm = self.tm
        with self.canvas.before:
            self._bg_c = Color(*tm.get('bg'))
            self._bg_r = Rectangle(pos=self.pos, size=self.size)

        fl = FloatLayout()

        root = BoxLayout(
            orientation='vertical',
            size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})

        self.top_bar = AppTopBar(
            on_theme_toggle=self._toggle_theme,
            on_search=self._on_search,
        )
        self.action_bar = SelectionBar(
            on_delete=self._delete_selected,
            on_pin=self._pin_selected,
            on_cancel=self._cancel_selection,
        )
        self.action_bar.opacity  = 0
        self.action_bar.disabled = True
        self.action_bar.height   = 0

        self.scroll = ScrollView(do_scroll_x=False, size_hint=(1, 1))
        self.content = BoxLayout(
            orientation='vertical', size_hint_y=None,
            spacing=0, padding=[0, dp(4), 0, dp(96)])
        self.content.bind(minimum_height=self.content.setter('height'))
        self.scroll.add_widget(self.content)

        root.add_widget(self.top_bar)
        root.add_widget(self.action_bar)
        root.add_widget(self.scroll)

        # FAB
        self.fab = FABButton(on_press_cb=self._new_note)
        self.fab.pos_hint = {'right': 0.94, 'y': 0.03}

        fl.add_widget(root)
        fl.add_widget(self.fab)
        self.add_widget(fl)
        self._load_notes()

    # ── Notes ─────────────────────────────────────────────────────────────────
    def on_enter(self, *a):
        self._load_notes()

    def _on_search(self, query):
        self._search_query = query.strip()
        self._load_notes()

    def _load_notes(self):
        self.content.clear_widgets()
        self.card_widgets.clear()
        dark = self.tm.mode == 'dark'

        if self._search_query:
            results = self.storage.search(self._search_query)
            if results:
                self.content.add_widget(
                    SectionLabel(text=f'Results ({len(results)})'))
                self.content.add_widget(Widget(size_hint_y=None, height=dp(2)))
                self.content.add_widget(StaggeredGrid(
                    results, self._on_card_tap, self._on_card_lp,
                    self.card_widgets, dark=dark))
            else:
                self.content.add_widget(Widget(size_hint_y=None, height=dp(80)))
                lbl = Label(
                    text='No notes found', font_name=APP_FONT,
                    font_size=dp(16), color=self.tm.get('text_muted'),
                    size_hint_y=None, height=dp(40))
                self.content.add_widget(lbl)
            return

        pinned = self.storage.pinned()
        others = self.storage.others()

        self.content.add_widget(Widget(size_hint_y=None, height=dp(4)))

        if pinned:
            self.content.add_widget(SectionLabel(text='Pinned'))
            self.content.add_widget(Widget(size_hint_y=None, height=dp(2)))
            self.content.add_widget(StaggeredGrid(
                pinned, self._on_card_tap, self._on_card_lp,
                self.card_widgets, dark=dark))

        if others:
            if pinned:
                self.content.add_widget(Widget(size_hint_y=None, height=dp(14)))
            lbl = 'Others' if pinned else 'Notes'
            self.content.add_widget(SectionLabel(text=lbl))
            self.content.add_widget(Widget(size_hint_y=None, height=dp(2)))
            self.content.add_widget(StaggeredGrid(
                others, self._on_card_tap, self._on_card_lp,
                self.card_widgets, dark=dark))

        if not pinned and not others:
            self.content.add_widget(Widget(size_hint_y=None, height=dp(100)))
            lbl = Label(
                text='No notes yet.\nTap + to create one.',
                font_name=APP_FONT, font_size=dp(16),
                color=self.tm.get('text_muted'),
                halign='center', size_hint_y=None, height=dp(60))
            lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))
            self.content.add_widget(lbl)

    # ── Card callbacks ────────────────────────────────────────────────────────
    def _on_card_tap(self, note):
        if self._multi_select:
            self._toggle_select(note['id'])
        else:
            self._open_note(note)

    def _on_card_lp(self, note, card):
        self._enter_multi_select()
        self._toggle_select(note['id'])

    def _open_note(self, note):
        app = App.get_running_app()
        app.root.get_screen('edit').load_note(note)
        app.root.transition = RiseInTransition(duration=0.22)
        app.root.current    = 'edit'

    def _new_note(self, *a):
        app = App.get_running_app()
        app.root.get_screen('edit').load_note(None)
        app.root.transition = RiseInTransition(duration=0.22)
        app.root.current    = 'edit'

    # ── Multi-select ──────────────────────────────────────────────────────────
    def _enter_multi_select(self):
        self._multi_select       = True
        self.action_bar.opacity  = 1
        self.action_bar.disabled = False
        self.action_bar.height   = dp(52)
        self.top_bar.opacity     = 0
        self.top_bar.disabled    = True
        self.top_bar.height      = 0

    def _cancel_selection(self):
        self._multi_select       = False
        self.selected_ids.clear()
        for card in self.card_widgets.values():
            card.set_selected(False)
        self.action_bar.opacity  = 0
        self.action_bar.disabled = True
        self.action_bar.height   = 0
        self.top_bar.opacity     = 1
        self.top_bar.disabled    = False
        self.top_bar.height      = dp(108)

    def _toggle_select(self, nid):
        if nid in self.selected_ids:
            self.selected_ids.discard(nid)
            if nid in self.card_widgets:
                self.card_widgets[nid].set_selected(False)
        else:
            self.selected_ids.add(nid)
            if nid in self.card_widgets:
                self.card_widgets[nid].set_selected(True)
        self.action_bar.set_count(len(self.selected_ids))
        if not self.selected_ids:
            self._cancel_selection()

    def _delete_selected(self):
        if not self.selected_ids: return
        self.storage.delete_many(list(self.selected_ids))
        self._cancel_selection()
        self._load_notes()

    def _pin_selected(self):
        for nid in list(self.selected_ids):
            self.storage.toggle_pin(nid)
        self._cancel_selection()
        self._load_notes()

    # ── Theme ─────────────────────────────────────────────────────────────────
    def _toggle_theme(self):
        self.tm.toggle()

    def _apply_theme(self, *a):
        self._bg_c.rgba = self.tm.get('bg')
        self._load_notes()

    def _upd_bg(self, *a):
        self._bg_r.pos  = self.pos
        self._bg_r.size = self.size
