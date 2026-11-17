"""Keep the existing button geometry while fitting its full format caption."""
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QFontInfo, QFontMetricsF, QPalette
from i18n.qt import QPushButton, QStyleOptionButton, QStylePainter, QStyle, QSizePolicy


class StructureImportButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def minimumSizeHint(self):
        return QSize(0, super().minimumSizeHint().height())

    def caption_font(self, width):
        font = QFont(self.font())
        metrics = QFontMetricsF(font)
        extent = metrics.horizontalAdvance(self.text())
        size = QFontInfo(font).pixelSize()
        while extent > width and size > 1:
            size -= 1
            font.setPixelSize(size)
            extent = QFontMetricsF(font).horizontalAdvance(self.text())
        return font

    def paintEvent(self, event):
        option = QStyleOptionButton()
        self.initStyleOption(option)
        text, option.text = option.text, ''
        painter = QStylePainter(self)
        painter.drawControl(QStyle.ControlElement.CE_PushButton, option)
        contents = self.style().subElementRect(QStyle.SubElement.SE_PushButtonContents, option, self)
        painter.setFont(self.caption_font(contents.width()))
        self.style().drawItemText(painter, contents, Qt.AlignmentFlag.AlignCenter,
                                  option.palette, self.isEnabled(), text, QPalette.ColorRole.ButtonText)
