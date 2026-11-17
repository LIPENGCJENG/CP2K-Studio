
from PySide6.QtCore import Qt, QSize
from i18n.qt import QFrame, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QSizePolicy
from ui.theme import PAGE_MARGIN, CARD_SPACING, FIELD_SPACING
from ui.widgets.help_icon import HelpIcon


class SectionCard(QFrame):
    def __init__(self, title, description='', parent=None, *, help_text=''):
        super().__init__(parent)
        self.setObjectName('sectionCard')
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        box = QVBoxLayout(self)
        box.setContentsMargins(16, 16, 16, 16)
        box.setSpacing(12)
        self.title_label = QLabel(title)
        self.title_label.setObjectName('cardTitle')
        self.title_label.setWordWrap(True)
        if help_text:
            title_row = QHBoxLayout()
            title_row.setSpacing(6)
            title_row.addWidget(self.title_label, 0, Qt.AlignmentFlag.AlignVCenter)
            self.help_icon = HelpIcon(help_text, self)
            title_row.addWidget(self.help_icon, 0, Qt.AlignmentFlag.AlignVCenter)
            title_row.addStretch()
            box.addLayout(title_row)
        else:
            box.addWidget(self.title_label)
        if description:
            hint = QLabel(description)
            hint.setObjectName('muted')
            hint.setWordWrap(True)
            box.addWidget(hint)
        self.content = QVBoxLayout()
        self.content.setSpacing(FIELD_SPACING)
        box.addLayout(self.content)


def page_layout(widget):
    widget.setObjectName('page')
    box = QVBoxLayout(widget)
    box.setContentsMargins(PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN)
    box.setSpacing(CARD_SPACING)
    return box


class AdaptiveGrid(QWidget):
    """Label-over-control fields, two columns when there is room for both."""
    def __init__(self, columns=2, threshold=460, parent=None):
        super().__init__(parent)
        self.requested_columns = columns
        self.threshold = threshold
        self.columns = columns
        self.items = []
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(16)
        self.grid.setVerticalSpacing(12)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

    def add_field(self, label, control):
        container = QWidget()
        box = QVBoxLayout(container)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(6)
        if label is not None:
            text = QLabel(label)
            text.setObjectName('fieldLabel')
            text.setWordWrap(True)
            text.setBuddy(control)
            box.addWidget(text)
        box.addWidget(control, 0, Qt.AlignmentFlag.AlignLeft if control.maximumWidth() < 1000 else Qt.AlignmentFlag(0))
        self.items.append(container)
        self._arrange()
        return container

    def _arrange(self):
        while self.grid.count():
            self.grid.takeAt(0)
        for index, item in enumerate(self.items):
            self.grid.addWidget(item, index // self.columns, index % self.columns, Qt.AlignmentFlag.AlignTop)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1 if self.columns == 2 else 0)
        self.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        columns = self.requested_columns if self.width() >= self.threshold else 1
        if columns != self.columns:
            self.columns = columns
            self._arrange()

    def minimumSizeHint(self):
        # Let the parent scroll area shrink before the two-column grid reflows.
        width = max((item.minimumSizeHint().width() for item in self.items), default=0)
        return QSize(width, self.grid.minimumSize().height())
