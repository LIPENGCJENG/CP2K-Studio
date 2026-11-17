"""Lightweight badge painting shared by table and navigation delegates."""

from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QColor
from i18n.qt import QStyledItemDelegate, QStyle, QStyleOptionViewItem
from ui.theme import COLORS

STATUS_ROLE = int(Qt.ItemDataRole.UserRole) + 8
COLORS_BY_STATE = {'ready': COLORS['success'], 'warning': COLORS['warning'],
                   'error': COLORS['error'], 'na': COLORS['muted'], 'unchecked': COLORS['muted']}
SYMBOLS = {'ready': '✓', 'warning': '!', 'error': '×', 'na': '–', 'unchecked': '○'}


class StatusBadgeDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        text = opt.text
        opt.text = ''
        option.widget.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, option.widget)
        state = index.data(STATUS_ROLE) or 'unchecked'
        color = QColor(COLORS_BY_STATE[state])
        painter.save()
        rect = QRectF(option.rect.adjusted(5, 7, -5, -7))
        tint = QColor(color); tint.setAlpha(24)
        painter.setBrush(tint)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 4, 4)
        painter.setPen(color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()


class StepIndicatorDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        text = opt.text
        opt.text = ''
        option.widget.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, option.widget)
        painter.save()
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        painter.setPen(QColor(COLORS['accent'] if selected else COLORS['foreground']))
        painter.drawText(option.rect.adjusted(10, 0, -28, 0), Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap, text)
        state = index.data(STATUS_ROLE) or 'unchecked'
        painter.setPen(QColor(COLORS_BY_STATE[state]))
        painter.drawText(option.rect.adjusted(option.rect.width()-22, 0, -5, 0), Qt.AlignmentFlag.AlignCenter, SYMBOLS[state])
        painter.restore()

    def sizeHint(self, option, index):
        width = max(100, option.widget.viewport().width()-38) if option.widget else 140
        rect = option.fontMetrics.boundingRect(0, 0, width, 1000, Qt.TextFlag.TextWordWrap, index.data() or '')
        return QSize(160, max(44, rect.height()+20))
