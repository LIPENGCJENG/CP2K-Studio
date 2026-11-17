
import re
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFontDatabase
from i18n.qt import QPlainTextEdit


class CP2KHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text):
        for pattern, color in [(r'^\s*&[A-Za-z_]+(?:\s+[A-Za-z_]+)?', '#54c5c3'),
                               (r'\b[-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?\b', '#e9ba78'),
                               (r'!.*$', '#8292a9')]:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class InputEditor(QPlainTextEdit):
    """Read-only preview intentionally stays derived from the unified model."""
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.highlighter = CP2KHighlighter(self.document())

    def show_text(self, text):
        if text == self.toPlainText():
            return
        scroll = self.verticalScrollBar().value()
        self.setPlainText(text)
        self.verticalScrollBar().setValue(scroll)
