
from PySide6.QtCore import Qt, QSize
from i18n.qt import QLineEdit, QLabel


class NumericField(QLineEdit):
    """A regular scientific-notation text draft plus a noneditable unit label.

    Parsing/precision stays in FormPanel and Pydantic, exactly as before.
    Invalid intermediate input remains visible for actionable error feedback.
    """
    def __init__(self, unit='', parent=None):
        super().__init__(parent)
        self.setMinimumWidth(144)
        self.setMaximumWidth(240)
        self.unit = unit
        self.unit_label = QLabel(unit, self)
        self.unit_label.setObjectName('unitSuffix')
        self.unit_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.unit_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.unit_label.setVisible(bool(unit))
        self._position_unit()

    def sizeHint(self):
        return QSize(220, super().sizeHint().height())

    def _position_unit(self):
        width = self.unit_label.sizeHint().width() if self.unit else 0
        self.setTextMargins(0, 0, width + 12 if width else 0, 0)
        self.unit_label.setGeometry(max(0, self.width()-width-10), 1, width, max(1, self.height()-2))
        self.unit_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_unit()


def set_invalid(widget, invalid):
    if bool(widget.property('invalid')) != bool(invalid):
        widget.setProperty('invalid', bool(invalid))
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
