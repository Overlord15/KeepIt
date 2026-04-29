"""
KeepIt — Google Keep clone in Kivy
Android 12+ and Desktop compatible.
"""

import os
os.environ['KIVY_KEYBOARD'] = 'system'

from kivy.app               import App
from kivy.uix.screenmanager import ScreenManager, RiseInTransition
from kivy.core.window       import Window
from kivy.utils             import platform

from utils.font_manager import register_all
register_all()

# ── Android permissions ───────────────────────────────────────────────────────
if platform == 'android':
    from android.permissions import request_permissions, check_permission, Permission
    from jnius import autoclass

    def _perm_callback(permissions, results):
        if not all(results):
            print('[Permissions] Some permissions denied.')

    def request_android_permissions():
        from jnius import autoclass
        VERSION = autoclass('android.os.Build$VERSION')
        sdk     = VERSION.SDK_INT
        perms   = []
        if sdk >= 33:
            # Android 13+
            perms.append('android.permission.READ_MEDIA_IMAGES')
            perms.append('android.permission.POST_NOTIFICATIONS')
        else:
            perms.append(Permission.READ_EXTERNAL_STORAGE)
            if sdk < 29:
                perms.append(Permission.WRITE_EXTERNAL_STORAGE)
        request_permissions(perms, _perm_callback)

    def check_storage_permission():
        try:
            from jnius import autoclass
            VERSION = autoclass('android.os.Build$VERSION')
            if VERSION.SDK_INT >= 33:
                return check_permission('android.permission.READ_MEDIA_IMAGES')
            return check_permission(Permission.READ_EXTERNAL_STORAGE)
        except Exception:
            return False

else:
    def request_android_permissions(): pass
    def check_storage_permission():    return True


# ── Screens ───────────────────────────────────────────────────────────────────
from screens.grid_screen import GridScreen
from screens.edit_screen import EditScreen
from utils.storage       import NoteStorage
from utils.theme         import ThemeManager


class KeepApp(App):
    title = 'KeepIt'

    def build(self):
        if platform != 'android':
            Window.size = (400, 780)

        request_android_permissions()

        self.theme_manager = ThemeManager()
        self.note_storage  = NoteStorage()

        sm = ScreenManager()
        sm.add_widget(GridScreen(name='grid'))
        sm.add_widget(EditScreen(name='edit'))
        sm.current = 'grid'
        return sm


if __name__ == '__main__':
    KeepApp().run()
