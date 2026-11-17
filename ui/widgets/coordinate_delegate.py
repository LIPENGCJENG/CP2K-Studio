"""Format coordinates for painting while retaining full-precision edit data."""
import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QStyledItemDelegate


class CoordinateDelegate(QStyledItemDelegate):
    def displayText(self, value, locale):
        try:
            number = float(value)
            if math.isfinite(number):
                return f'{number:.4f}'
        except (TypeError, ValueError, OverflowError):
            pass
        # Invalid drafts stay visible for the existing validation workflow.
        return str(value)

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setFrame(False)
        editor.setAlignment(Qt.AlignmentFlag.AlignRight)
        return editor

    def setEditorData(self, editor, index):
        editor.setText(str(index.data(Qt.ItemDataRole.EditRole)))
        editor.selectAll()

    def setModelData(self, editor, model, index):
        text = editor.text()
        if text != str(index.data(Qt.ItemDataRole.EditRole)):
            model.setData(index, text, Qt.ItemDataRole.EditRole)
