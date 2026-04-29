"""
ThemeManager — light / dark mode + note colour palette.
Matches the index.html colour tokens exactly.
"""

from kivy.event import EventDispatcher
from kivy.properties import StringProperty, BooleanProperty

THEMES = {
    'light': {
        'bg':             [0.973, 0.973, 0.973, 1],   # #f8f9fa
        'surface':        [1,     1,     1,     1],
        'card_bg':        [1,     1,     1,     1],
        'card_border':    [0.855, 0.855, 0.855, 1],   # #dadce0
        'text_primary':   [0.125, 0.125, 0.125, 1],   # #202124
        'text_secondary': [0.373, 0.373, 0.373, 1],   # #5f6368
        'text_muted':     [0.502, 0.502, 0.502, 1],   # #80868b
        'accent':         [0.102, 0.451, 0.910, 1],   # #1a73e8
        'fab_bg':         [1,     1,     1,     1],
        'topbar_bg':      [1,     1,     1,     1],
        'topbar_text':    [0.125, 0.125, 0.125, 1],
        'icon_color':     [0.373, 0.373, 0.373, 1],
        'pinned_label':   [0.502, 0.502, 0.502, 1],
        'selected_bg':    [0.820, 0.898, 1.000, 1],
        'selected_border':[0.102, 0.451, 0.910, 1],
        'divider':        [0.910, 0.910, 0.910, 1],
        'popup_bg':       [1,     1,     1,     1],
        'input_bg':       [0.973, 0.973, 0.973, 1],
        'mode_name':      'Light',
        'search_bg':      [0.937, 0.937, 0.937, 1],
    },
    'dark': {
        'bg':             [0.125, 0.125, 0.125, 1],   # #202124
        'surface':        [0.176, 0.180, 0.188, 1],   # #2d2e30
        'card_bg':        [0.176, 0.180, 0.188, 1],
        'card_border':    [0.235, 0.251, 0.263, 1],   # #3c4043
        'text_primary':   [0.910, 0.918, 0.929, 1],   # #e8eaed
        'text_secondary': [0.604, 0.627, 0.647, 1],   # #9aa0a6
        'text_muted':     [0.502, 0.525, 0.545, 1],   # #80868b
        'accent':         [0.541, 0.706, 0.973, 1],   # #8ab4f8
        'fab_bg':         [0.235, 0.251, 0.263, 1],
        'topbar_bg':      [0.125, 0.125, 0.125, 1],
        'topbar_text':    [0.910, 0.918, 0.929, 1],
        'icon_color':     [0.604, 0.627, 0.647, 1],
        'pinned_label':   [0.604, 0.627, 0.647, 1],
        'selected_bg':    [0.125, 0.220, 0.345, 1],
        'selected_border':[0.541, 0.706, 0.973, 1],
        'divider':        [0.235, 0.251, 0.263, 1],
        'popup_bg':       [0.176, 0.180, 0.188, 1],
        'input_bg':       [0.176, 0.180, 0.188, 1],
        'mode_name':      'Dark',
        'search_bg':      [0.176, 0.180, 0.188, 1],
    },
}

# 12-colour palette — matches index.html swatches
# Index 0 = Default (theme-aware), 1-11 = fixed colours
NOTE_COLORS_LIGHT = [
    [1.000, 1.000, 1.000, 1],   # 0 Default white
    [1.000, 0.871, 0.835, 1],   # 1 Flamingo  #fdd8d8→reddish
    [0.992, 0.729, 0.376, 1],   # 2 Tangerine #feba61
    [1.000, 0.976, 0.729, 1],   # 3 Banana    #fffab8
    [0.851, 0.965, 0.843, 1],   # 4 Sage      #d9f6d7
    [0.820, 0.961, 0.929, 1],   # 5 Teal      #d1f5ed  (was mint)
    [0.820, 0.902, 0.965, 1],   # 6 Denim     #d1e6f6
    [0.875, 0.820, 0.965, 1],   # 7 Lavender  #dfd1f6
    [0.965, 0.820, 0.929, 1],   # 8 Grape     #f6d1ed
    [0.965, 0.855, 0.820, 1],   # 9 Graphite  #f6dad1
    [0.922, 0.929, 0.937, 1],   #10 Gray      #ebeef0
    [0.776, 0.890, 0.878, 1],   #11 Eucalyptus
]

NOTE_COLORS_DARK = [
    [0.176, 0.180, 0.188, 1],   # 0 Default dark surface
    [0.290, 0.149, 0.145, 1],   # 1 Flamingo dark
    [0.302, 0.208, 0.094, 1],   # 2 Tangerine dark
    [0.302, 0.286, 0.098, 1],   # 3 Banana dark
    [0.141, 0.259, 0.141, 1],   # 4 Sage dark
    [0.125, 0.255, 0.239, 1],   # 5 Teal dark
    [0.125, 0.204, 0.282, 1],   # 6 Denim dark
    [0.200, 0.153, 0.302, 1],   # 7 Lavender dark
    [0.290, 0.149, 0.247, 1],   # 8 Grape dark
    [0.290, 0.196, 0.149, 1],   # 9 Graphite dark
    [0.220, 0.227, 0.235, 1],   #10 Gray dark
    [0.141, 0.243, 0.231, 1],   #11 Eucalyptus dark
]

# Human-readable names for the colour picker
COLOR_NAMES = [
    'Default', 'Flamingo', 'Tangerine', 'Banana',
    'Sage', 'Teal', 'Denim', 'Lavender',
    'Grape', 'Graphite', 'Gray', 'Eucalyptus',
]


class ThemeManager(EventDispatcher):
    mode    = StringProperty('dark')
    is_dark = BooleanProperty(True)

    def __init__(self, **kwargs):
        self.register_event_type('on_theme_change')
        super().__init__(**kwargs)

    def toggle(self):
        self.mode   = 'light' if self.mode == 'dark' else 'dark'
        self.is_dark = (self.mode == 'dark')
        self.dispatch('on_theme_change', self.mode)

    def get(self, key):
        return list(THEMES[self.mode].get(key, [0, 0, 0, 1]))

    def note_color(self, index):
        palette = NOTE_COLORS_DARK if self.mode == 'dark' else NOTE_COLORS_LIGHT
        return list(palette[max(0, min(index, len(palette) - 1))])

    def note_colors(self):
        return (NOTE_COLORS_DARK if self.mode == 'dark'
                else NOTE_COLORS_LIGHT)

    def on_theme_change(self, mode):
        pass
