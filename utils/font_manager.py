"""
font_manager.py — identical logic to original, kept for compatibility.
"""

import os
from kivy.core.text import LabelBase
from kivy.utils import platform

_UTILS_DIR = os.path.dirname(__file__)
_PROJ_ROOT = os.path.dirname(_UTILS_DIR)
_FONT_DIR  = os.path.join(_PROJ_ROOT, 'assets', 'fonts')

APP_FONT = 'AppFont'

_ANDROID_REGULAR = ['/system/fonts/NotoSans-Regular.ttf', '/system/fonts/Roboto-Regular.ttf']
_ANDROID_BOLD    = ['/system/fonts/NotoSans-Bold.ttf',    '/system/fonts/Roboto-Bold.ttf']

_DESKTOP_REGULAR = [
    '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf',
    '/usr/share/fonts/noto/NotoSans-Regular.ttf',
    '/usr/share/fonts/TTF/NotoSans-Regular.ttf',
    '/usr/share/fonts/google-noto/NotoSans-Regular.ttf',
]
_DESKTOP_BOLD = [
    '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf',
    '/usr/share/fonts/noto/NotoSans-Bold.ttf',
    '/usr/share/fonts/TTF/NotoSans-Bold.ttf',
    '/usr/share/fonts/google-noto/NotoSans-Bold.ttf',
]

_registered = False


def _register_android():
    r = next((p for p in _ANDROID_REGULAR if os.path.exists(p)), None)
    b = next((p for p in _ANDROID_BOLD    if os.path.exists(p)), None)
    if r:
        LabelBase.register(APP_FONT, fn_regular=r, fn_bold=b or None)


def _register_desktop():
    r = next((p for p in _DESKTOP_REGULAR if os.path.exists(p)), None)
    b = next((p for p in _DESKTOP_BOLD    if os.path.exists(p)), None)
    if r:
        try:
            LabelBase.register(APP_FONT, fn_regular=r, fn_bold=b or None)
            return
        except Exception:
            pass
    # Kivy bundled Roboto fallback
    try:
        import kivy as _k
        _kf  = os.path.join(os.path.dirname(_k.__file__), 'data', 'fonts')
        rr   = os.path.join(_kf, 'Roboto-Regular.ttf')
        rb   = os.path.join(_kf, 'Roboto-Bold.ttf')
        if os.path.exists(rr):
            LabelBase.register(APP_FONT,
                               fn_regular=rr,
                               fn_bold=rb if os.path.exists(rb) else None)
    except Exception:
        pass


def register_all():
    global _registered
    if _registered:
        return
    _registered = True
    if platform == 'android':
        _register_android()
    else:
        _register_desktop()


def get_emoji_font():
    return ''


def emoji_btn_kwargs(font_size_dp=18):
    return {'font_size': font_size_dp}
