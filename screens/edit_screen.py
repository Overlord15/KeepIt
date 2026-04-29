"""
EditScreen — full note editor with:
  · title / body TextInput
  · checklist rows (add / delete / check)
  · image strip with rounded thumbnails + file picker + camera
  · 12-colour dot picker
  · pin toggle
  · Android 12+ permission handling
  · image preview popup before adding
"""

import os
from kivy.uix.screenmanager import Screen, FallOutTransition
from kivy.uix.boxlayout     import BoxLayout
from kivy.uix.scrollview    import ScrollView
from kivy.uix.textinput     import TextInput
from kivy.uix.label         import Label
from kivy.uix.button        import Button
from kivy.uix.checkbox      import CheckBox
from kivy.uix.image         import Image as KivyImage
from kivy.uix.behaviors     import ButtonBehavior
from kivy.uix.popup         import Popup
from kivy.uix.filechooser   import FileChooserIconView
from kivy.uix.widget        import Widget
from kivy.uix.floatlayout   import FloatLayout
from kivy.graphics          import (Color, RoundedRectangle, Rectangle,
                                    StencilPush, StencilUse, StencilPop,
                                    StencilUnUse, Ellipse, Line)
from kivy.app               import App
from kivy.utils             import platform
from kivy.metrics           import dp
from kivy.core.window       import Window

from utils.font_manager import APP_FONT
from utils.storage      import make_note

# Import palette from grid_screen
from screens.grid_screen import (NOTE_COLORS_LIGHT, NOTE_COLORS_DARK,
                                  NOTE_COLORS_FIXED)

_ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icons')
def _icon(name): return os.path.join(_ICON_DIR, name)

COLOR_NAMES = [
    'Default', 'Flamingo', 'Tangerine', 'Banana',
    'Sage', 'Teal', 'Denim', 'Lavender',
    'Grape', 'Graphite', 'Gray', 'Eucalyptus',
]


def _card_color_for_mode(idx, dark):
    pal = NOTE_COLORS_DARK if dark else NOTE_COLORS_LIGHT
    return list(pal[max(0, min(idx, len(pal) - 1))])


def _luminance(rgba):
    r, g, b = rgba[:3]
    return 0.299 * r + 0.587 * g + 0.114 * b


def _text_color(rgba):
    return [0.08, 0.08, 0.08, 1] if _luminance(rgba) > 0.45 else [0.92, 0.92, 0.92, 1]


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
# ColorDot
# ─────────────────────────────────────────────────────────────────────────────
class ColorDot(Widget):
    def __init__(self, color_rgba, index, on_pick=None, **kwargs):
        super().__init__(size_hint=(1, 1), **kwargs)
        self.index     = index
        self._color    = list(color_rgba)
        self._selected = False
        self._on_pick  = on_pick
        self.bind(pos=lambda *a: self._draw(), size=lambda *a: self._draw())

    def _draw(self):
        side = min(self.width, self.height) * 0.68
        cx   = self.x + (self.width  - side) / 2
        cy   = self.y + (self.height - side) / 2
        r    = side / 2
        self.canvas.clear()
        with self.canvas:
            # Outer ring only when selected — clean blue ring
            if self._selected:
                Color(0.102, 0.451, 0.910, 1)
                Ellipse(pos=(cx - dp(2.5), cy - dp(2.5)),
                        size=(side + dp(5), side + dp(5)))
            else:
                # Subtle grey unselected ring
                Color(0.45, 0.45, 0.45, 0.35)
                Ellipse(pos=(cx - dp(1), cy - dp(1)),
                        size=(side + dp(2), side + dp(2)))
            # Dot itself
            Color(*self._color)
            Ellipse(pos=(cx, cy), size=(side, side))
            # White tick when selected
            if self._selected:
                Color(1, 1, 1, 1)
                hw = side * 0.20
                mx = cx + r
                my = cy + r
                Line(points=[mx - hw, my,
                              mx - hw * 0.25, my - hw * 0.65,
                              mx + hw * 0.85, my + hw * 0.65],
                     width=dp(1.6), cap='round', joint='round')

    def set_color(self, c):
        self._color = list(c); self._draw()

    def set_selected(self, v):
        self._selected = v; self._draw()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self._on_pick: self._on_pick(self.index)
            return True
        return super().on_touch_down(touch)


# ─────────────────────────────────────────────────────────────────────────────
# ChecklistRow
# ─────────────────────────────────────────────────────────────────────────────
class ChecklistRow(BoxLayout):
    def __init__(self, item, on_change=None, on_delete=None, dark=False, **kwargs):
        super().__init__(
            orientation='horizontal', size_hint_y=None, height=dp(42),
            spacing=dp(6), padding=[dp(2), dp(4), dp(2), dp(4)], **kwargs)
        self.item       = item
        self._on_change = on_change
        self._dark      = dark

        if dark:
            fc  = [0.88, 0.88, 0.88, 1]
            hc  = [0.58, 0.58, 0.58, 1]   # visible on dark bg
            cbc = [0.72, 0.82, 1.00, 1]   # blue-tinted checkbox, visible on dark
        else:
            fc  = [0.10, 0.10, 0.10, 1]
            hc  = [0.50, 0.50, 0.50, 1]
            cbc = [0.20, 0.20, 0.20, 1]

        wrap = BoxLayout(size_hint=(None, 1), width=dp(36), orientation='vertical')
        self.cb = CheckBox(
            active=item.get('checked', False),
            size_hint=(1, None), height=dp(30),
            color=cbc,
        )
        self.cb.bind(active=self._on_check)
        wrap.add_widget(Widget())
        wrap.add_widget(self.cb)
        wrap.add_widget(Widget())

        self.txt = TextInput(
            text=item.get('text', ''),
            font_name=APP_FONT, font_size=dp(14),
            multiline=True, size_hint=(1, None),
            background_color=[0, 0, 0, 0],
            foreground_color=fc,
            hint_text='List item',
            hint_text_color=hc,
            cursor_color=[0.102, 0.451, 0.910, 1],
            padding=[dp(4), dp(6), dp(4), dp(6)],
        )
        self.txt.height = dp(34)
        self.txt.bind(minimum_height=self._on_txt_h)
        self.txt.bind(text=self._on_text)

        class _XButton(ButtonBehavior, Label):
            pass
        del_btn = _XButton(
            text='X', font_name=APP_FONT, font_size=dp(14), bold=True,
            color=[0.60, 0.60, 0.60, 1],
            size_hint=(None, None), size=(dp(24), dp(24)),
        )
        del_btn.bind(on_press=lambda x: on_delete(self) if on_delete else None)
        del_wrap = BoxLayout(size_hint=(None, 1), width=dp(28), orientation='vertical')
        del_wrap.add_widget(Widget())
        del_wrap.add_widget(del_btn)
        del_wrap.add_widget(Widget())

        self.add_widget(wrap)
        self.add_widget(self.txt)
        self.add_widget(del_wrap)

    def _on_txt_h(self, inst, val):
        self.txt.height = val
        self.height     = max(dp(42), val + dp(12))

    def _on_check(self, cb, val):
        self.item['checked'] = val
        if self._on_change: self._on_change()

    def _on_text(self, inp, val):
        self.item['text'] = val
        if self._on_change: self._on_change()

    def get_item(self):
        return {'text': self.txt.text, 'checked': self.cb.active}


# ─────────────────────────────────────────────────────────────────────────────
# ImagePreviewPopup — shows selected image before confirming
# ─────────────────────────────────────────────────────────────────────────────
class ImagePreviewPopup(Popup):
    def __init__(self, path, on_confirm=None, **kwargs):
        content = BoxLayout(orientation='vertical', spacing=dp(8),
                            padding=[dp(8), dp(8), dp(8), dp(8)])
        img = KivyImage(source=path, allow_stretch=True, keep_ratio=True,
                        size_hint=(1, 1))
        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(12))
        ok  = Button(text='Add Image', font_name=APP_FONT, font_size=dp(14),
                     background_color=[0.102, 0.451, 0.910, 1])
        cancel = Button(text='Cancel', font_name=APP_FONT, font_size=dp(14),
                        background_color=[0.5, 0.5, 0.5, 1])
        btn_row.add_widget(ok)
        btn_row.add_widget(cancel)
        content.add_widget(img)
        content.add_widget(btn_row)

        super().__init__(
            title='Preview', content=content,
            size_hint=(0.92, 0.75), **kwargs)

        ok.bind(on_press=lambda x: self._confirm(path, on_confirm))
        cancel.bind(on_press=lambda x: self.dismiss())

    def _confirm(self, path, cb):
        self.dismiss()
        if cb: cb(path)


# ─────────────────────────────────────────────────────────────────────────────
# EditScreen
# ─────────────────────────────────────────────────────────────────────────────
class EditScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._note           = None
        self._checklist_rows = []
        self._images         = []
        self._color_index    = 0
        self._is_new         = True
        self._color_dots     = []
        self._pin_btn        = None

        app          = App.get_running_app()
        self.tm      = app.theme_manager
        self.storage = app.note_storage
        self._build_ui()
        self.tm.bind(on_theme_change=lambda *a: self._apply_theme())

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        tm   = self.tm
        dark = tm.mode == 'dark'

        with self.canvas.before:
            self._screen_bg_c = Color(*tm.get('bg'))
            self._screen_bg_r = Rectangle(pos=self.pos, size=self.size)
        self.bind(
            pos=lambda *a:  setattr(self._screen_bg_r, 'pos',  self.pos),
            size=lambda *a: setattr(self._screen_bg_r, 'size', self.size),
        )

        root = BoxLayout(orientation='vertical')

        # ── Topbar ────────────────────────────────────────────────────────────
        topbar = BoxLayout(
            orientation='horizontal', size_hint_y=None, height=dp(54),
            padding=[dp(6), dp(12), dp(6), dp(12)], spacing=dp(8))

        with topbar.canvas.before:
            self._tb_c = Color(*tm.get('topbar_bg'))
            self._tb_r = Rectangle(pos=topbar.pos, size=topbar.size)
        topbar.bind(
            pos=lambda *a:  setattr(self._tb_r, 'pos',  topbar.pos),
            size=lambda *a: setattr(self._tb_r, 'size', topbar.size),
        )

        # Left: pin, checklist, camera, gallery
        pin_btn,     _ = _img_btn('ic_pin.png',       24, self._toggle_pin)
        list_btn,    _ = _img_btn('ic_checklist.png', 24, self._add_checklist_item)
        camera_btn,  _ = _img_btn('ic_camera.png',    24, self._take_picture)
        gallery_btn, _ = _img_btn('ic_gallery.png',   24, self._pick_image)
        # Right: back/save
        back_btn,    _ = _img_btn('ic_back.png',      24, self._close_note)

        self._pin_btn    = pin_btn
        self.back_btn    = back_btn

        topbar.add_widget(pin_btn)
        topbar.add_widget(list_btn)
        topbar.add_widget(camera_btn)
        topbar.add_widget(gallery_btn)
        topbar.add_widget(Widget())
        topbar.add_widget(back_btn)

        # ── Scroll content ───────────────────────────────────────────────────
        scroll = ScrollView(do_scroll_x=False, size_hint=(1, 1))
        self.edit_area = BoxLayout(
            orientation='vertical', size_hint_y=None,
            padding=[dp(14), dp(12), dp(14), dp(32)], spacing=dp(10))
        self.edit_area.bind(minimum_height=self.edit_area.setter('height'))

        with self.edit_area.canvas.before:
            self._edit_bg_c = Color(*_card_color_for_mode(0, dark))
            self._edit_bg_r = Rectangle(
                pos=self.edit_area.pos, size=self.edit_area.size)
        self.edit_area.bind(
            pos=lambda *a:  setattr(self._edit_bg_r, 'pos',  self.edit_area.pos),
            size=lambda *a: setattr(self._edit_bg_r, 'size', self.edit_area.size),
        )

        tc = tm.get('text_primary')
        # hint colour: visible in both modes — slightly brighter than text_muted
        mc = [0.60, 0.60, 0.60, 1] if tm.mode == 'dark' else [0.55, 0.55, 0.55, 1]
        ac = tm.get('accent')

        self.title_input = TextInput(
            hint_text='Title', font_name=APP_FONT, font_size=dp(22),
            multiline=True, size_hint_y=None, height=dp(52),
            background_color=[0, 0, 0, 0],
            foreground_color=tc,
            hint_text_color=mc,
            cursor_color=ac,
            padding=[dp(2), dp(12), dp(2), dp(4)],
        )
        self.title_input.bind(minimum_height=self.title_input.setter('height'))

        self.body_input = TextInput(
            hint_text='Note…', font_name=APP_FONT, font_size=dp(15),
            multiline=True, size_hint_y=None, height=dp(120),
            background_color=[0, 0, 0, 0],
            foreground_color=tc,
            hint_text_color=mc,
            cursor_color=ac,
            padding=[dp(2), dp(8)],
        )
        self.body_input.bind(minimum_height=self.body_input.setter('height'))

        # Checklist container
        self.checklist_box = BoxLayout(
            orientation='vertical', size_hint_y=None, spacing=dp(2))
        self.checklist_box.bind(
            minimum_height=self.checklist_box.setter('height'))

        # Divider before colour picker
        div = Widget(size_hint_y=None, height=dp(1))
        with div.canvas:
            Color(*tm.get('divider'))
            self._div_r = Rectangle(pos=div.pos, size=div.size)
        div.bind(pos=lambda w, v: setattr(self._div_r, 'pos', v))
        div.bind(size=lambda w, v: setattr(self._div_r, 'size', v))

        # Colour dot row
        self._color_row = BoxLayout(
            orientation='horizontal', size_hint_y=None, height=dp(48),
            spacing=dp(2), padding=[dp(4), dp(4), dp(4), dp(4)])
        self._color_dots = []
        for i in range(len(NOTE_COLORS_LIGHT)):
            c   = _card_color_for_mode(i, dark)
            dot = ColorDot(c, i, on_pick=self._pick_color)
            self._color_row.add_widget(dot)
            self._color_dots.append(dot)
        if self._color_dots:
            self._color_dots[0].set_selected(True)

        # Image horizontal scroll
        self.images_box = BoxLayout(
            orientation='horizontal', size_hint=(None, None),
            height=0, spacing=dp(8), padding=[dp(4), dp(4)])
        self.images_box.bind(minimum_width=self.images_box.setter('width'))
        self.images_scroll = ScrollView(
            do_scroll_x=True, do_scroll_y=False,
            size_hint_y=None, height=0, bar_width=dp(3))
        self.images_scroll.add_widget(self.images_box)

        self.edit_area.add_widget(self.title_input)
        self.edit_area.add_widget(self.body_input)
        self.edit_area.add_widget(self.checklist_box)
        self.edit_area.add_widget(self.images_scroll)
        self.edit_area.add_widget(div)
        self.edit_area.add_widget(self._color_row)

        scroll.add_widget(self.edit_area)
        root.add_widget(topbar)
        root.add_widget(scroll)
        self.add_widget(root)

    # ── Load ─────────────────────────────────────────────────────────────────
    def load_note(self, note):
        if note is None:
            self._note   = make_note()
            self._is_new = True
        else:
            self._note   = dict(note)
            self._is_new = False

        self._color_index = self._note.get('color_index', 0)
        self._images      = list(self._note.get('images', []))

        self.title_input.text = self._note.get('title', '')
        self.body_input.text  = self._note.get('body', '')

        self.checklist_box.clear_widgets()
        self._checklist_rows.clear()
        for item in self._note.get('checklist', []):
            self._add_row(dict(item))

        self._apply_theme()
        self._rebuild_images()
        self._update_pin_btn()

    # ── Pin ──────────────────────────────────────────────────────────────────
    def _toggle_pin(self, *a):
        if self._note:
            self._note['pinned'] = not self._note.get('pinned', False)
        self._update_pin_btn()

    def _update_pin_btn(self):
        if not self._pin_btn: return
        pinned = self._note and self._note.get('pinned', False)
        self._pin_btn.source = _icon('ic_pin_active.png' if pinned else 'ic_pin.png')

    # ── Checklist ────────────────────────────────────────────────────────────
    def _add_checklist_item(self, *a):
        self._add_row({'text': '', 'checked': False})

    def _add_row(self, item):
        dark = self.tm.mode == 'dark'
        row  = ChecklistRow(item=item, on_change=None,
                            on_delete=self._remove_row, dark=dark)
        self.checklist_box.add_widget(row)
        self._checklist_rows.append(row)

    def _remove_row(self, row):
        self.checklist_box.remove_widget(row)
        if row in self._checklist_rows:
            self._checklist_rows.remove(row)

    # ── Colour picker ─────────────────────────────────────────────────────────
    def _pick_color(self, index):
        dark = self.tm.mode == 'dark'
        # Deselect ALL dots first — prevents multiple selected state
        for dot in self._color_dots:
            dot.set_selected(False)
        self._color_index = index
        if 0 <= index < len(self._color_dots):
            self._color_dots[index].set_selected(True)
        cc = _card_color_for_mode(index, dark)
        self._edit_bg_c.rgba = cc
        tc = _text_color(cc)
        self.title_input.foreground_color = tc
        self.body_input.foreground_color  = tc

    # ── Images ────────────────────────────────────────────────────────────────
    def _rebuild_images(self):
        self.images_box.clear_widgets()
        valid = [p for p in self._images if os.path.exists(p)]
        self._images = valid

        IMG_H  = dp(110)
        THUMB_W = dp(110)
        RADIUS  = dp(12)

        for path in valid:
            rl = FloatLayout(size_hint=(None, None), size=(THUMB_W, IMG_H))

            with rl.canvas.before:
                StencilPush()
                Color(1, 1, 1, 1)
                _sr = RoundedRectangle(pos=rl.pos, size=rl.size, radius=[RADIUS])
                StencilUse()

            with rl.canvas.after:
                StencilUnUse()
                Color(1, 1, 1, 1)
                RoundedRectangle(pos=rl.pos, size=rl.size, radius=[RADIUS])
                StencilPop()

            def _upd(inst, val, r=_sr):
                r.pos = inst.pos; r.size = inst.size
            rl.bind(pos=_upd, size=_upd)

            img = KivyImage(
                source=path, allow_stretch=True,
                size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
            try: img.fit_mode = 'cover'
            except Exception: img.keep_ratio = False

            rem_btn, _ = _img_btn(
                'ic_close.png', 22,
                lambda x, p=path: self._remove_image(p),
                fixed_size=True)
            rem_btn.pos_hint = {'right': 1.0, 'top': 1.0}

            rl.add_widget(img)
            rl.add_widget(rem_btn)
            self.images_box.add_widget(rl)

        h = IMG_H if valid else 0
        self.images_box.height    = h
        self.images_scroll.height = h

    def _remove_image(self, path):
        if path in self._images:
            self._images.remove(path)
        self._rebuild_images()

    # ── Camera ────────────────────────────────────────────────────────────────
    def _take_picture(self, *a):
        if platform == 'android':
            try:
                from plyer import camera
                import tempfile
                dest = os.path.join(tempfile.gettempdir(), 'keepit_photo.jpg')
                camera.take_picture(filename=dest, on_complete=self._on_photo_taken)
            except Exception as e:
                self._show_msg(f'Camera error: {e}')
        else:
            self._show_msg('Camera is only available on Android.')

    def _on_photo_taken(self, filename):
        if filename and os.path.exists(filename):
            self._images.append(filename)
            self._rebuild_images()

    # ── Gallery / File picker ─────────────────────────────────────────────────
    def _pick_image(self, *a):
        if platform == 'android':
            self._request_android_storage_then_pick()
        else:
            self._open_file_chooser()

    def _request_android_storage_then_pick(self):
        """Android 12+ (API 32+) uses READ_MEDIA_IMAGES; older uses READ_EXTERNAL_STORAGE."""
        try:
            from android.permissions import (request_permissions, check_permission,
                                             Permission)
            from jnius import autoclass
            VERSION = autoclass('android.os.Build$VERSION')
            sdk     = VERSION.SDK_INT

            if sdk >= 33:
                perm = 'android.permission.READ_MEDIA_IMAGES'
                granted = check_permission(perm)
            else:
                perm    = Permission.READ_EXTERNAL_STORAGE
                granted = check_permission(perm)

            if granted:
                self._launch_android_gallery()
            else:
                def _cb(perms, results):
                    if results and results[0]:
                        self._launch_android_gallery()
                    else:
                        self._show_msg(
                            'Storage permission denied.\n'
                            'Please grant it in Settings → Apps → KeepIt → Permissions.')
                request_permissions([perm], _cb)
        except Exception as e:
            print(f'[EditScreen] Permission check failed: {e}')
            self._open_file_chooser()

    def _launch_android_gallery(self):
        """Launch the system gallery picker via startActivityForResult."""
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent         = autoclass('android.content.Intent')
            intent = Intent(Intent.ACTION_PICK)
            intent.setType('image/*')
            try:
                from android.activity import bind as activity_bind
                activity_bind(on_activity_result=self._on_android_image_result)
            except Exception:
                pass
            PythonActivity.mActivity.startActivityForResult(intent, 1001)
        except Exception as e:
            print(f'[EditScreen] Gallery intent failed: {e}')
            if platform == 'android':
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: self._show_msg(
                    'Could not open gallery.\n'
                    'Please grant storage permission in Settings.'), 0)
            else:
                self._open_file_chooser()

    def _on_android_image_result(self, request_code, result_code, intent):
        """Activity result callback — may fire on a background thread.
        All Kivy UI work is deferred to the main thread via Clock.schedule_once."""
        from kivy.clock import Clock
        try:
            from jnius import autoclass
            Activity = autoclass('android.app.Activity')
            if result_code != Activity.RESULT_OK or not intent:
                return
            uri = intent.getData()
            if not uri:
                return

            # Try resolving content URI → real file path (works on older Android)
            resolved_path = None
            try:
                ctx    = autoclass('org.kivy.android.PythonActivity').mActivity
                cr     = ctx.getContentResolver()
                cols   = autoclass('android.provider.MediaStore$Images$Media')
                cursor = cr.query(uri, None, None, None, None)
                if cursor and cursor.moveToFirst():
                    idx = cursor.getColumnIndex(cols.DATA)
                    if idx >= 0:
                        p = cursor.getString(idx)
                        if p and os.path.exists(p):
                            resolved_path = p
                    cursor.close()
            except Exception:
                pass

            if resolved_path:
                # Known file path — safe to preview directly on main thread
                Clock.schedule_once(
                    lambda dt, p=resolved_path: self._preview_image(p), 0)
            else:
                # Content URI — copy bytes to cache file, then preview on main thread
                uri_str = str(uri.toString())
                self._copy_uri_to_cache(uri_str)
        except Exception as e:
            print(f'[EditScreen] Image result error: {e}')

    def _copy_uri_to_cache(self, uri_str):
        """Copy a content:// URI to a cache file entirely in the background thread,
        then schedule the Kivy preview on the main thread via Clock."""
        from kivy.clock import Clock
        try:
            from jnius import autoclass
            ctx = autoclass('org.kivy.android.PythonActivity').mActivity
            cr  = ctx.getContentResolver()
            Uri = autoclass('android.net.Uri')
            uri = Uri.parse(uri_str)

            cache_dir = ctx.getCacheDir().getAbsolutePath()
            tmp = os.path.join(cache_dir, 'keepit_img_preview.jpg')

            # Use Java Streams — no Kivy/graphics calls here
            InputStream  = autoclass('java.io.InputStream')
            FileOutputStream = autoclass('java.io.FileOutputStream')
            Arrays = autoclass('java.util.Arrays')

            stream = cr.openInputStream(uri)
            fos    = FileOutputStream(tmp)
            buf    = bytearray(8192)
            while True:
                chunk = stream.read()   # reads one byte as int (-1 = EOF)
                if chunk == -1:
                    break
                fos.write(chunk)
            fos.flush()
            fos.close()
            stream.close()

            if os.path.exists(tmp) and os.path.getsize(tmp) > 0:
                Clock.schedule_once(lambda dt, p=tmp: self._preview_image(p), 0)
            else:
                raise Exception('cache file empty or missing')
        except Exception as e:
            print(f'[EditScreen] URI copy failed: {e}')
            # Fallback: store the URI string directly and rebuild on main thread
            Clock.schedule_once(lambda dt: (
                self._images.append(uri_str) or self._rebuild_images()), 0)

    def _open_file_chooser(self):
        if platform == 'android':
            self._show_msg(
                'Please use the gallery button to pick an image.\n'
                'Direct file browsing is not available on Android.')
            return
        start = os.path.expanduser('~/Pictures')
        content  = BoxLayout(orientation='vertical', spacing=dp(6),
                             padding=[dp(4), dp(4)])
        fc       = FileChooserIconView(
            filters=['*.png', '*.jpg', '*.jpeg', '*.gif', '*.webp'],
            path=start)
        btn_row  = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        ok_btn   = Button(text='Preview & Add', font_name=APP_FONT,
                          font_size=dp(13),
                          background_color=[0.102, 0.451, 0.910, 1])
        can_btn  = Button(text='Cancel', font_name=APP_FONT,
                          font_size=dp(13),
                          background_color=[0.5, 0.5, 0.5, 1])
        btn_row.add_widget(ok_btn)
        btn_row.add_widget(can_btn)
        content.add_widget(fc)
        content.add_widget(btn_row)

        popup = Popup(title='Pick Image', content=content,
                      size_hint=(0.95, 0.88))

        ok_btn.bind(on_press=lambda x: self._preview_from_fc(fc.selection, popup))
        can_btn.bind(on_press=lambda x: popup.dismiss())
        popup.open()

    def _preview_from_fc(self, selection, parent_popup):
        if not selection:
            return
        path = selection[0]
        parent_popup.dismiss()
        self._preview_image(path)

    def _preview_image(self, path):
        """Show preview popup before adding image."""
        if not path:
            self._show_msg('No image path received.')
            return
        # Allow content:// URIs through (they won't pass os.path.exists)
        if not path.startswith('content://') and not os.path.exists(path):
            self._show_msg('Image file not found.')
            return
        prev = ImagePreviewPopup(path=path,
                                 on_confirm=self._add_confirmed_image)
        prev.open()

    def _add_confirmed_image(self, path):
        if path not in self._images:
            self._images.append(path)
        self._rebuild_images()

    # ── Save / Close ──────────────────────────────────────────────────────────
    def _collect_note(self):
        note = self._note
        note['title']       = self.title_input.text.strip()
        note['body']        = self.body_input.text.strip()
        note['checklist']   = [r.get_item() for r in self._checklist_rows]
        note['images']      = list(self._images)
        note['color_index'] = self._color_index
        return note

    def _close_note(self, *a):
        note = self._collect_note()
        has  = (note['title'] or note['body']
                or note['checklist'] or note['images'])
        if has:
            if self._is_new: self.storage.add(note)
            else:            self.storage.update(note)
        app = App.get_running_app()
        app.root.transition = FallOutTransition(duration=0.20)
        app.root.current    = 'grid'

    # ── Theme ─────────────────────────────────────────────────────────────────
    def _apply_theme(self, *a):
        tm   = self.tm
        dark = tm.mode == 'dark'
        self._screen_bg_c.rgba = tm.get('bg')
        self._tb_c.rgba        = tm.get('topbar_bg')
        cc = _card_color_for_mode(self._color_index, dark)
        self._edit_bg_c.rgba   = cc
        tc = _text_color(cc)
        mc = tm.get('text_muted')
        ac = tm.get('accent')
        self.title_input.foreground_color = tc
        self.body_input.foreground_color  = tc
        self.title_input.hint_text_color  = mc
        self.body_input.hint_text_color   = mc
        self.title_input.cursor_color     = ac
        self.body_input.cursor_color      = ac
        # Refresh colour dots — deselect ALL first then re-select current
        for i, dot in enumerate(self._color_dots):
            dot.set_color(_card_color_for_mode(i, dark))
            dot.set_selected(False)
        if 0 <= self._color_index < len(self._color_dots):
            self._color_dots[self._color_index].set_selected(True)

    def _show_msg(self, msg):
        popup = Popup(
            title='Info',
            content=Label(text=msg, font_name=APP_FONT,
                          text_size=(dp(260), None), halign='center'),
            size_hint=(0.82, None), height=dp(200))
        popup.open()
