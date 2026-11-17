"""Small, non-interactive help marker using Qt's native tooltip handling."""
from i18n.messages import i18n_msg, i18n_join, i18n_render
from html import escape
from i18n.language_manager import language_manager

from PySide6.QtCore import Qt
from i18n.qt import QLabel, QHBoxLayout
from ui.theme import COLORS


def attach_field_help(control, text):
    """Add help beside an existing AdaptiveGrid label, keeping its input gap."""
    layout = control.parentWidget().layout()
    label = layout.takeAt(0).widget()
    label.setWordWrap(False)
    label.ensurePolished()
    icon = HelpIcon(text)
    row = QHBoxLayout()
    row.setSpacing(6)
    row.addWidget(label, 0, Qt.AlignmentFlag.AlignVCenter)
    row.addWidget(icon, 0, Qt.AlignmentFlag.AlignVCenter)
    row.addStretch()
    extra = max(0, icon.height() - label.sizeHint().height())
    layout.setSpacing(max(0, layout.spacing() - extra))
    layout.insertLayout(0, row)
    return label, icon


class HelpIcon(QLabel):
    def __init__(self, text, parent=None):
        super().__init__('ⓘ', parent)
        self.setObjectName('helpIcon')
        self.setFixedSize(16, 16)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAccessibleName(i18n_msg('Description', code='studio.4262c45dc797bb0c'))
        self.setStyleSheet(
            i18n_msg('QLabel#helpIcon {{ color:{p0}; font-size:16px; }}QToolTip {{ background:{p1}; color:{p2}; border:1px solid {p3}; border-radius:6px; padding:8px; max-width:360px; }}', p0=COLORS["muted"], p1=COLORS["card"], p2=COLORS["foreground"], p3=COLORS["border"]))
        self.set_help_text(text)

    def set_help_text(self, text):
        self._help_message = text
        language_manager().callback(self, 'help', lambda icon: icon._render_help())
        self._render_help()

    def _render_help(self):
        text = i18n_render(self._help_message)
        self.setAccessibleDescription(text)
        # Qt rich text supports table widths and wraps long paragraphs reliably.
        paragraphs = i18n_join('<br><br>', (escape(part).replace('\n', '<br>') for part in text.split('\n\n')))
        self.setToolTip('<qt><table width="340" cellspacing="0" cellpadding="0"><tr><td>' + paragraphs + '</td></tr></table></qt>')
