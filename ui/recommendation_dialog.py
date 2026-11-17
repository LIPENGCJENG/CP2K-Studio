"""Persistent recommendation chooser; filtering never changes configuration."""
from i18n.messages import i18n_msg
from PySide6.QtCore import Qt, QSignalBlocker
from i18n.qt import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                              QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
                              QSplitter, QWidget, QScrollArea, QFrame, QSizePolicy)
from core.kind_recommender import recommend
from core.kind_validator import active_kinds, element_configuration_progress
from ui.theme import COLORS
from ui.widgets.section_card import SectionCard


class KindConfigurationView(QWidget):
    """Read-only, naturally sized text for one KIND; no fixed label heights."""
    def __init__(self, label, element, parent=None):
        super().__init__(parent)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(4)
        title = QLabel(i18n_msg('KIND {p0}', p0=label))
        title.setObjectName('cardTitle')
        title.setToolTip(i18n_msg('KIND {p0} / ELEMENT {p1}', p0=label, p1=element))
        box.addWidget(title)
        self.basis, self.potential = QLabel(), QLabel()
        for field in (self.basis, self.potential):
            field.setTextFormat(Qt.TextFormat.PlainText)
            field.setWordWrap(True)
            field.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            field.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse |
                                          Qt.TextInteractionFlag.TextSelectableByKeyboard)
            box.addWidget(field)

    def update_kind(self, kind):
        for field, prefix, value in [(self.basis, i18n_msg('Basis Set', code='studio.810ecb3582cd0af1'), kind.basis_set if kind else ''),
                                     (self.potential, i18n_msg('Pseudopotential', code='studio.e2a0fff9b04a6077'), kind.potential if kind else '')]:
            text = i18n_msg('{p0}: {p1}', p0=prefix, p1=value or i18n_msg('Not selected', code='studio.1182c5454f113db5'))
            if field.text() != text:
                field.setText(text)
                field.setToolTip(text)
                field.setStyleSheet(i18n_msg('color:{p0};', p0=COLORS["foreground" if value else "muted"]))


class RecommendationDialog(QDialog):
    def __init__(self, panel):
        super().__init__(panel)
        self.panel = panel
        self._signature = None
        self._column_widths_initialized = False
        self.setWindowTitle(i18n_msg('Recommend Basis Sets & Pseudopotentials', code='studio.eec62d383b87d4cd'))
        self.resize(1000, 500)
        layout = QVBoxLayout(self)
        note = QLabel(i18n_msg('Only existing conventional GPW/GTH entries with matching q/XC names are shown. UZH has no independently verified protocol here and is not recommended automatically.\nSelect a row and click Apply to update that KIND only. Recommendations do not guarantee accuracy or convergence.', code='studio.6a72d7d9c8263001'))
        note.setWordWrap(True)
        layout.addWidget(note)
        top = QHBoxLayout()
        label = QLabel(i18n_msg('Element Filter:', code='studio.d0cc3e65ececf2e6'))
        self.element_filter = QComboBox()
        self.element_filter.setMinimumWidth(140)
        label.setBuddy(self.element_filter)
        top.addWidget(label)
        top.addWidget(self.element_filter)
        top.addStretch()
        self.progress = QLabel()
        self.progress.setAccessibleName(i18n_msg('Element configuration progress', code='studio.a0fefa8b05953324'))
        top.addWidget(self.progress)
        layout.addLayout(top)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([i18n_msg('KIND / Element', code='studio.133344485a0218af'), i18n_msg('Basis Set', code='studio.810ecb3582cd0af1'), i18n_msg('Pseudopotential', code='studio.e2a0fff9b04a6077'), i18n_msg('Description', code='studio.4262c45dc797bb0c')])
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(72)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setMinimumWidth(420)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.splitter.setChildrenCollapsible(False)
        # The draggable handle doubles as a 16px gutter between outer borders.
        self.splitter.setHandleWidth(16)
        self.splitter.setStyleSheet('QSplitter::handle { background:transparent; }')
        self.splitter.addWidget(self.table)
        self.chosen_card = SectionCard(i18n_msg('Current Selections', code='studio.cf6da91a404d0589'))
        self.chosen_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.chosen_card.setMinimumWidth(180)
        self.chosen_card.setMaximumWidth(360)
        self.chosen_scroll = QScrollArea()
        self.chosen_scroll.setWidgetResizable(True)
        self.chosen_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chosen_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chosen_scroll.setStyleSheet('QScrollArea { background:transparent; border:0; } '
                                        'QScrollArea > QWidget > QWidget { background:transparent; }')
        self.chosen_content = QWidget()
        self.chosen_layout = QVBoxLayout(self.chosen_content)
        self.chosen_layout.setContentsMargins(0, 0, 0, 0)
        self.chosen_layout.setSpacing(12)
        self.chosen_views = {}
        self.chosen_scroll.setWidget(self.chosen_content)
        self.chosen_card.content.addWidget(self.chosen_scroll)
        self.splitter.addWidget(self.chosen_card)
        self.splitter.setSizes([730, 230])
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        layout.addWidget(self.splitter)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        self.apply_button = QPushButton(i18n_msg('Apply'))
        self.close_button = QPushButton(i18n_msg('Close'))
        for button in (self.apply_button, self.close_button):
            button.setAutoDefault(False)
        buttons.addWidget(self.apply_button)
        buttons.addStretch()
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)
        self.apply_button.clicked.connect(self.apply_selected)
        self.close_button.clicked.connect(self.reject)
        self.element_filter.currentIndexChanged.connect(self.filter_rows)
        panel.configuration_updated.connect(self.refresh_state)
        self.refresh_state(panel.current_project)

    def refresh_state(self, project):
        mapping = active_kinds(project)
        signature = (id(self.panel.catalog), tuple(sorted(mapping.items())), project.dft.xc_functional)
        if signature != self._signature:
            self._signature = signature
            self.populate(mapping, project.dft.xc_functional)
        completed, total = element_configuration_progress(project, self.panel.catalog)
        self.progress.setText(i18n_msg('Configured {p0}/{p1} elements', code='studio.7d2db2a6398bc21a', p0=completed, p1=total))
        color = 'muted' if not completed else 'success' if completed == total else 'accent'
        self.progress.setStyleSheet(i18n_msg('color:{p0};', p0=COLORS[color]))
        self.update_chosen_configuration(project, mapping)

    def update_chosen_configuration(self, project, mapping):
        labels = sorted(mapping)
        key = tuple(sorted(mapping.items()))
        if getattr(self, '_chosen_mapping', None) != key:
            self._chosen_mapping = key
            while self.chosen_layout.count():
                item = self.chosen_layout.takeAt(0)
                if item.widget():
                    item.widget().hide()
                    item.widget().deleteLater()
            self.chosen_views.clear()
            for index, label in enumerate(labels):
                if index:
                    line = QFrame()
                    line.setFixedHeight(1)
                    line.setStyleSheet(i18n_msg('background:{p0}; border:0;', p0=COLORS["border"]))
                    self.chosen_layout.addWidget(line)
                view = KindConfigurationView(label, mapping[label])
                self.chosen_views[label] = view
                self.chosen_layout.addWidget(view)
            self.chosen_layout.addStretch()
        for label in labels:
            self.chosen_views[label].update_kind(project.kinds.get(label))

    def populate(self, mapping, xc):
        current_filter = self.element_filter.currentData()
        selected = self.selected_option()
        scroll_x = self.table.horizontalScrollBar().value()
        scroll_y = self.table.verticalScrollBar().value()
        blocker = QSignalBlocker(self.element_filter)
        self.element_filter.clear()
        self.element_filter.addItem(i18n_msg('All Elements', code='studio.c267807c83aabf89'), None)
        for element in sorted(set(mapping.values())):
            self.element_filter.addItem(element, element)
        self.element_filter.setCurrentIndex(max(0, self.element_filter.findData(current_filter)))
        del blocker
        # Multiple KINDs of one element share the existing recommendation result.
        candidates = {element: recommend(self.panel.catalog, element, xc)
                      for element in set(mapping.values())}
        options = [(label, option) for label, element in sorted(mapping.items())
                   for option in candidates[element]]
        self.table.setUpdatesEnabled(False)
        try:
            self.table.clearSelection()
            self.table.setCurrentCell(-1, -1)
            self.table.setRowCount(0)
            self.table.setRowCount(len(options))
            for row, (label, option) in enumerate(options):
                element = mapping[label]
                values = [i18n_msg('{p0} / {p1}', p0=label, p1=element) if label != element else label,
                          option.basis.name, option.potential.name, option.note]
                for column, text in enumerate(values):
                    item = QTableWidgetItem(text)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item.setToolTip(text)
                    self.table.setItem(row, column, item)
                self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, (label, option))
                if selected and self.option_key(selected) == self.option_key((label, option)):
                    self.table.selectRow(row)
            if options and not self._column_widths_initialized:
                for column, cap in [(1, 280), (2, 260)]:
                    self.table.resizeColumnToContents(column)
                    self.table.setColumnWidth(column, max(150, min(cap, self.table.columnWidth(column))))
                self._column_widths_initialized = True
            self.filter_rows()
            self.table.horizontalScrollBar().setValue(scroll_x)
            self.table.verticalScrollBar().setValue(scroll_y)
        finally:
            self.table.setUpdatesEnabled(True)
        self.set_status('' if options else i18n_msg('No confirmed recommendation is available for this element/XC. Review actual candidates manually; no configuration is generated.', code='studio.aa7be42eb492ee8f'))

    @staticmethod
    def option_key(selected):
        label, option = selected
        return label, option.basis.key, option.potential.key

    def selected_option(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows or self.table.isRowHidden(rows[0].row()):
            return None
        return self.table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)

    def filter_rows(self, *_):
        element = self.element_filter.currentData()
        for row in range(self.table.rowCount()):
            _, option = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            self.table.setRowHidden(row, bool(element and option.basis.element != element))
        if self.table.currentRow() >= 0 and self.table.isRowHidden(self.table.currentRow()):
            self.table.clearSelection()
            self.table.setCurrentCell(-1, -1)

    def set_status(self, text, error=False):
        self.status.setText(text)
        self.status.setStyleSheet(i18n_msg('color:{p0};', p0=COLORS["error" if error else "muted"]))

    def apply_selected(self):
        selected = self.selected_option()
        if not selected:
            self.set_status(i18n_msg('Select a basis and pseudopotential combination first', code='studio.44d39f359c6c1821'), error=True)
            return
        label, option = selected
        try:
            self.panel.apply_recommendation(label, option)
        except Exception as exc:
            self.set_status(i18n_msg('Application failed: {p0}', code='studio.570e9d8af11fa767', p0=exc), error=True)
            return
        self.set_status(i18n_msg('Applied to KIND {p0}', code='studio.dbcdf7e62cdb8a56', p0=label))
