"""Shared, device-independent dark theme for windows, dialogs and popups."""
from core.resources import resource_path
from PySide6.QtGui import QColor, QPalette, QFontDatabase
from PySide6.QtWidgets import QApplication

COLORS = dict(background='#172333', card='#1d2d40', input='#111e2e', border='#33485f',
              foreground='#dce7f3', muted='#99abc1', accent='#76d4cf',
              success='#83d9c1', warning='#e8bf79', error='#efa39b')
PAGE_MARGIN = 20
CARD_SPACING = 16
FIELD_SPACING = 12


def stylesheet():
    source = resource_path('ui', 'styles.qss').read_text(encoding='utf-8')
    for key, value in COLORS.items():
        source = source.replace('@' + key + '@', value)
    return source.replace('@assets@', resource_path('ui', 'assets').as_posix())


def apply_theme():
    app = QApplication.instance()
    if app is None:
        return
    source = stylesheet()
    if app.styleSheet() == source:
        return
    if app.style().objectName().lower() != 'fusion':
        app.setStyle('Fusion')
    palette = QPalette()
    for role, color in [(QPalette.ColorRole.Window, 'background'), (QPalette.ColorRole.Base, 'input'),
                        (QPalette.ColorRole.AlternateBase, 'card'), (QPalette.ColorRole.Text, 'foreground'),
                        (QPalette.ColorRole.WindowText, 'foreground'), (QPalette.ColorRole.Button, 'card'),
                        (QPalette.ColorRole.ButtonText, 'foreground'), (QPalette.ColorRole.Highlight, 'border'),
                        (QPalette.ColorRole.HighlightedText, 'accent'), (QPalette.ColorRole.ToolTipBase, 'card'),
                        (QPalette.ColorRole.ToolTipText, 'foreground')]:
        palette.setColor(role, QColor(COLORS[color]))
    app.setPalette(palette)
    app.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
    app.setStyleSheet(source)
