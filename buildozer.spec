[app]
title = KeepIt
package.name = keepit
package.domain = org.keepit
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,json
version = 0.2

requirements = python3,kivy==2.3.0,plyer

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 31
android.ndk = 25b
android.ndk_api = 31
android.enable_androidx = True

android.permissions = CAMERA,READ_MEDIA_IMAGES,POST_NOTIFICATIONS,INTERNET
android.archs = arm64-v8a, armeabi-v7a
android.debug_symbols = 0

android.apptheme = @android:style/Theme.NoTitleBar

log_level = 2
warn_on_root = 1
