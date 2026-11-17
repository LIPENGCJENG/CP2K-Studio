"""Suppress hover help only on explicitly selected navigation surfaces."""
from PySide6.QtCore import QEvent, QObject


class HoverHelpBlocker(QObject):
    def eventFilter(self, watched, event):
        # QAction can regenerate a tool button's tooltip when its state changes.
        # Consume help events without interfering with hover or mouse events.
        if event.type() in (QEvent.Type.ToolTip, QEvent.Type.StatusTip):
            event.accept()
            return True
        return super().eventFilter(watched, event)

    def install_on(self, widget):
        widget.setToolTip('')
        widget.setStatusTip('')
        widget.installEventFilter(self)
