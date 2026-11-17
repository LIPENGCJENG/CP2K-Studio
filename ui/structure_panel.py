from i18n.messages import i18n_msg, i18n_str, i18n_join
from i18n.language_manager import language_manager
from pathlib import Path
import numpy as np
from PySide6.QtCore import Signal, Qt, QEvent, QSize, QItemSelection, QItemSelectionModel
from i18n.qt import (QWidget, QLabel, QPushButton, QComboBox,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QHBoxLayout, QVBoxLayout, QBoxLayout, QLayout,
                              QAbstractItemView, QDialog, QApplication,
                              QSizePolicy, QAbstractButton, QMessageBox,
                              QLineEdit, QAbstractSpinBox, QPlainTextEdit, QTextEdit,
                              QAbstractSlider, QSplitterHandle, QTabBar, QMenuBar)
from ui.structure_view import StructureView
from ui.coordinate_range_dialog import CoordinateRangeDialog
from ui.widgets.coordinate_delegate import CoordinateDelegate
from core.models import Structure
from core.atom_constraints import COMPONENTS, set_fixed_atoms
from ui.simulation_box_dialog import SimulationBoxDialog
from core.structure import SUPPORTED_STRUCTURE_EXTENSIONS
from ui.widgets.structure_import_button import StructureImportButton

ATOM_ID_ROLE = Qt.ItemDataRole.UserRole
KIND_COLUMN = 4  # hidden backing field retained for existing KIND editing code
FIXED_COLUMN = 5


class CoordinateItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
            return float(self.text()) < float(other.text())
        except ValueError:
            return super().__lt__(other)


class AtomActionsBar(QWidget):
    """Two action rows; narrow panes wrap groups instead of scrolling."""
    def __init__(self, controls):
        super().__init__()
        self.setObjectName('atomActionsBar')
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.setStyleSheet('QWidget#atomActionsBar, QWidget#atomActionGroup '
                          '{ background:transparent; border:0; }')
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(0, 0, 0, 0)
        self.box.setSpacing(8)
        self.box.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        height = max(control.sizeHint().height() for control in controls)
        for control in controls:
            control.setFixedHeight(height)
        self.direction_group = self._group(controls[:2])
        self.fixed_group = self._group(controls[2:4])
        self.groups = [(self.direction_group, self.fixed_group), tuple(controls[4:])]
        self.rows = []
        for widgets in self.groups:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            for widget in widgets:
                row.addWidget(widget, 0, Qt.AlignmentFlag.AlignLeft)
            row.addStretch()
            self.box.addLayout(row)
            self.rows.append(row)
        language_manager().callback(self, 'action_rows', lambda bar: bar.reflow())

    def _group(self, controls):
        group = QWidget(self)
        group.setObjectName('atomActionGroup')
        group.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        row = QHBoxLayout(group)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        for control in controls:
            row.addWidget(control)
        return group

    def minimumSizeHint(self):
        width = max(widget.minimumSizeHint().width() for widgets in self.groups for widget in widgets)
        return QSize(width, self.box.minimumSize().height())

    def reflow(self):
        for row, widgets in zip(self.rows, self.groups):
            needed = sum(widget.sizeHint().width() for widget in widgets) + row.spacing() * (len(widgets)-1)
            direction = (QBoxLayout.Direction.LeftToRight if self.width() >= needed
                         else QBoxLayout.Direction.TopToBottom)
            if row.direction() != direction:
                row.setDirection(direction)
        self.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reflow()


class StructurePanel(QWidget):
    changed = Signal()
    constraints_changed = Signal()
    import_requested = Signal()
    box_generated = Signal()
    boundary_confirmed = Signal()

    def __init__(self):
        super().__init__()
        from ui.widgets.section_card import SectionCard, page_layout
        layout = page_layout(self)
        heading = QLabel(i18n_msg('01 · Structure & Cell', code='studio.32d69f2433650d2c'))
        heading.setObjectName('heading')
        layout.addWidget(heading)
        card = SectionCard(i18n_msg('Structure Import', code='studio.c77dc73ab554bf6c'))
        self.import_button = StructureImportButton(i18n_msg('Import Structure （{formats}）',
            code='structure.import_button', formats=' / '.join(SUPPORTED_STRUCTURE_EXTENSIONS)))
        self.import_button.clicked.connect(lambda *_: self.import_requested.emit())
        card.content.addWidget(self.import_button)
        self.summary = QLabel(i18n_msg('No structure imported', code='studio.3b2ba961a7fc56f5'))
        self.summary.setWordWrap(True)
        card.content.addWidget(self.summary)
        self.import_notice = QLabel()
        self.import_notice.setWordWrap(True)
        self.import_notice.setObjectName('muted')
        self.import_notice.hide()
        card.content.addWidget(self.import_notice)
        self.box_button = QPushButton(i18n_msg('Generate Simulation Box…', code='xsd.box_button'))
        self.box_button.hide()
        self.box_button.clicked.connect(self.generate_box)
        card.content.addWidget(self.box_button)
        self._import_notices = []
        layout.addWidget(card)
        card = SectionCard(i18n_msg('Cell & Periodicity', code='studio.5261b980378d173d'), help_text=i18n_msg('PERIODIC · Keep CELL and POISSON consistent', code='studio.d08a29082f7ac8a5'))
        self.periodic = QComboBox()
        self.periodic.setAccessibleName('PERIODIC')
        self.periodic.addItems(['NONE', 'X', 'Y', 'Z', 'XY', 'XZ', 'YZ', 'XYZ'])
        self.periodic.currentIndexChanged.connect(self._periodic_changed)
        card.content.addWidget(self.periodic)
        self.confirm_molecule_button = QPushButton(i18n_msg('Confirm Isolated Molecule…', code='periodicity.confirm_button'))
        self.confirm_molecule_button.clicked.connect(self.confirm_isolated_molecule)
        self.confirm_molecule_button.hide()
        confirm_row = QHBoxLayout()
        confirm_row.addWidget(self.confirm_molecule_button)
        confirm_row.addStretch()
        card.content.addLayout(confirm_row)
        self.cell = QTableWidget(3, 3)
        self.cell.setItemDelegate(CoordinateDelegate(self.cell))
        self.cell.setHorizontalHeaderLabels(['x', 'y', 'z'])
        self.cell.setVerticalHeaderLabels(['A', 'B', 'C'])
        self.cell.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.cell.setFixedHeight(132)
        self.cell.cellChanged.connect(lambda *_: self.changed.emit())
        card.content.addWidget(self.cell)
        layout.addWidget(card)
        # Mounted once in MainWindow's persistent right pane. Keep the same
        # instance here for structure, selection and constraint synchronization.
        self.view = StructureView()
        self.view.atom_clicked.connect(self._view_atom_clicked)
        card = SectionCard(i18n_msg('Atomic Coordinates', code='studio.6dc715068235b1cd'), help_text=(
            i18n_msg('Range selection uses true Cartesian XYZ coordinates (Å); selection does not fix atoms.\nCP2K 2026.1 FIXED_ATOMS fixes fractional components, which differ from Cartesian XYZ in nonorthogonal cells.\nCtrl/Cmd for multiple selection, Shift for a range. Row numbers follow the final INP order; sorting only changes the display.', code='studio.410e84884db83b24')))
        self.fix_button = QPushButton(i18n_msg('Fix Selected', code='studio.22de130a828addda'))
        self.unfix_button = QPushButton(i18n_msg('Unfix Selected', code='studio.fa7dd269ce190eb7'))
        self.components = QComboBox()
        self.components.addItems(COMPONENTS)
        self.components.setAccessibleName(i18n_msg('Fixed components (fractional coordinates)', code='studio.c6e9bf994796e74d'))
        self.components.setToolTip(i18n_msg('CP2K fixes fractional components; these are independent of the Cartesian range-selection axis', code='studio.60cfdbf4c58a0226'))
        self.direction_label = QLabel(i18n_msg('Fix components:', code='studio.989ef351d02d4727'))
        self.direction_label.setObjectName('fieldLabel')
        self.direction_label.setBuddy(self.components)
        self.direction_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.range_button = QPushButton(i18n_msg('Select by Coordinate Range…', code='studio.96a1eac2d8ebb65a'))
        self.clear_fixed_button = QPushButton(i18n_msg('Clear All Fixed', code='studio.410a52677fd2675f'))
        self.actions_bar = AtomActionsBar([self.direction_label, self.components, self.fix_button, self.unfix_button,
                                          self.range_button, self.clear_fixed_button])
        card.content.addWidget(self.actions_bar)
        self.fixed_count = QLabel(i18n_msg('Fixed: 0 atoms · Selected: 0 atoms', code='studio.95e94df25073aa21'))
        self.fixed_count.setWordWrap(True)
        card.content.addWidget(self.fixed_count)
        # Operation results/errors only; selection counts live in fixed_count.
        self.action_status = QLabel()
        self.action_status.setWordWrap(True)
        self.action_status.hide()
        card.content.addWidget(self.action_status)
        self.coords = QTableWidget(0, 6)
        coordinate_delegate = CoordinateDelegate(self.coords)
        for column in range(1, 4):
            self.coords.setItemDelegateForColumn(column, coordinate_delegate)
        self.coords.setHorizontalHeaderLabels([i18n_msg('Element', code='studio.a1c1675f5df836a8'), 'x', 'y', 'z', 'KIND', i18n_msg('Fixed', code='studio.d4b3f49cd2e4254f')])
        # Keep per-atom KIND data and existing editing indices intact.
        self.coords.setColumnHidden(4, True)
        self.coords.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.coords.horizontalHeader().setMinimumSectionSize(64)
        self.coords.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.coords.horizontalHeader().setSectionResizeMode(FIXED_COLUMN, QHeaderView.ResizeMode.ResizeToContents)
        self.coords.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.coords.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.coords.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.coords.setSortingEnabled(True)
        self.coords.model().layoutChanged.connect(self._update_atom_numbers)
        self.coords.itemSelectionChanged.connect(self._selection_changed)
        self.coords.cellChanged.connect(lambda *_: self.changed.emit())
        self.coords.setMinimumHeight(190)
        self.coords.setMaximumHeight(360)
        card.content.addWidget(self.coords)
        layout.addWidget(card)
        layout.addStretch()
        self.st = None
        self.periodic.currentIndexChanged.connect(self._update_import_hint)
        self.cell.cellChanged.connect(self._update_import_hint)
        self.fix_button.clicked.connect(lambda: self.apply_fixed(self.components.currentText()))
        self.unfix_button.clicked.connect(lambda: self.apply_fixed(None))
        self.clear_fixed_button.clicked.connect(self.clear_fixed)
        self.range_button.clicked.connect(self.choose_coordinate_range)
        # Clear only on mouse presses, scoped to a visible owner with selection.
        # Focus changes, combo popups and range-dialog interactions preserve it.
        self._selection_host = None
        self._selection_filter_active = False

    def _sync_selection_filter(self):
        host = self.window()
        if host is not self._selection_host:
            if self._selection_host is not None:
                self._selection_host.removeEventFilter(self)
            self._selection_host = host
            host.installEventFilter(self)
        active = host.isVisible() and bool(self.selected_atom_ids())
        if active != self._selection_filter_active:
            application = QApplication.instance()
            if active:
                application.installEventFilter(self)
            else:
                application.removeEventFilter(self)
            self._selection_filter_active = active

    def eventFilter(self, watched, event):
        if watched is self._selection_host and event.type() in (QEvent.Type.Show, QEvent.Type.Hide):
            self._sync_selection_filter()
        if (event.type() == QEvent.Type.MouseButtonPress
                and event.button() == Qt.MouseButton.LeftButton
                and isinstance(watched, QWidget) and self.selected_atom_ids()):
            target = QApplication.widgetAt(event.globalPosition().toPoint()) or watched
            if target.window() is self.window():
                protected = (self.coords, self.actions_bar, self.view)
                if not any(target is widget or widget.isAncestorOf(target) for widget in protected):
                    # A viewport may be a plain QWidget inside an editor or
                    # item view. Such controls are not background blank space.
                    current = target
                    while current is not None and current is not self.window():
                        if isinstance(current, (QAbstractItemView, QAbstractButton, QComboBox,
                                                QLineEdit, QAbstractSpinBox, QPlainTextEdit,
                                                QTextEdit, QAbstractSlider, QSplitterHandle,
                                                QTabBar, QMenuBar)):
                            break
                        current = current.parentWidget()
                    else:
                        self.clear_atom_selection()
        return super().eventFilter(watched, event)

    def clear_atom_selection(self):
        self.coords.selectionModel().clear()
        self._selection_changed()
        self.action_status.hide()

    def _view_atom_clicked(self, atom_id, modifiers):
        ids = self.selected_atom_ids()
        if modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier):
            ids.symmetric_difference_update({atom_id})
        elif modifiers & Qt.KeyboardModifier.ShiftModifier:
            ids.add(atom_id)
        else:
            ids = {atom_id}
        self.select_atom_ids(ids)

    def set_structure(self, structure):
        self.st = structure
        self._import_notices = []
        for widget in (self.cell, self.coords, self.periodic):
            widget.blockSignals(True)
        self.coords.setSortingEnabled(False)
        self.coords.clearSelection()
        cell = structure.cell if structure else ((0, 0, 0),)*3
        for i in range(3):
            for j in range(3):
                self.cell.setItem(i, j, QTableWidgetItem(i18n_str(cell[i][j])))
        self.coords.setRowCount(len(structure.symbols) if structure else 0)
        if structure:
            for i, (symbol, position) in enumerate(zip(structure.symbols, structure.positions)):
                item = QTableWidgetItem(symbol)
                item.setData(ATOM_ID_ROLE, structure.atom_ids[i])
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.coords.setItem(i, 0, item)
                for j, value in enumerate(position, 1):
                    self.coords.setItem(i, j, CoordinateItem(i18n_str(value)))
                self.coords.setItem(i,4,QTableWidgetItem(structure.labels[i]))
            self.periodic.setCurrentText(structure.periodic)
            self.summary.setText(i18n_msg('{p0} atoms · {p1}\nSource: {p2}', code='studio.1e186b1b2fbae2a3', p0=len(structure.symbols), p1=i18n_join(", ", structure.elements), p2=Path(structure.source).name if structure.source else i18n_msg('Structure Embedded in Project', code='studio.363f2b5862ff4102')))
            self.summary.setToolTip(structure.source or i18n_msg('Structure stored in the project configuration', code='studio.8fe24b751141071f'))
        else:
            self.periodic.setCurrentText('NONE')
            self.summary.setText(i18n_msg('No structure imported', code='studio.3b2ba961a7fc56f5'))
        self._apply_periodicity_lock()
        self._update_fixed_cells()
        self.coords.setSortingEnabled(True)
        self._update_atom_numbers()
        for widget in (self.cell, self.coords, self.periodic):
            widget.blockSignals(False)
        self.view.set_structure(structure)
        self.view.set_selected_atoms([])
        self.action_status.hide()
        self._selection_changed()
        self._update_import_hint()

    def _apply_periodicity_lock(self):
        locked = bool(self.st and self.st.periodicity_locked)
        self.periodic.setEditable(False)
        self.periodic.setEnabled(not locked)
        if locked:
            blocked = self.periodic.blockSignals(True)
            self.periodic.setCurrentText('NONE')
            self.periodic.blockSignals(blocked)
        self.periodic.setToolTip(i18n_msg('The imported structure is a non-periodic molecule. Periodicity is fixed to NONE.', code='periodicity.lock_tooltip') if locked else '')

    def _periodic_changed(self, *_):
        if self.st and self.st.periodicity_locked:
            self._apply_periodicity_lock()
            return
        self.changed.emit()

    def confirm_isolated_molecule(self):
        try:
            structure = self._current_structure()
            if structure.structure_type != 'unclassified' or structure.periodic != 'NONE':
                return
            answer = QMessageBox.question(self,
                i18n_msg('Confirm Isolated Molecule', code='periodicity.confirm_title'),
                i18n_msg('Confirm that this is an isolated non-periodic molecule? PERIODIC will be fixed to NONE. The cell vectors and coordinates will remain unchanged.', code='periodicity.confirm_text'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
            selected, notices = self.selected_atom_ids(), list(self._import_notices)
            data = structure.model_dump()
            data['structure_type'] = 'isolated_molecule'
            self.set_structure(Structure.model_validate(data))
            self.set_import_notices(notices)
            self.select_atom_ids(selected)
            self.changed.emit()
            self.boundary_confirmed.emit()
        except ValueError as exc:
            self._status(i18n_str(exc))

    def set_import_notices(self, notices):
        self._import_notices = list(notices)
        self._update_import_hint()

    def _update_import_hint(self, *_):
        is_xsd = bool(self.st and self.st.source and Path(self.st.source).suffix.lower() == '.xsd')
        locked = bool(self.st and self.st.periodicity_locked)
        periodic = self.periodic.currentText()
        self.confirm_molecule_button.setVisible(bool(self.st and self.st.symbols
            and self.st.structure_type == 'unclassified' and periodic == 'NONE'))
        self.import_notice.setVisible(is_xsd or locked)
        self.box_button.setVisible(bool(self.st and self.st.symbols and periodic == 'NONE'))
        if not is_xsd and not locked:
            return
        if self.st.structure_type == 'periodic_structure' or periodic != 'NONE':
            text = i18n_msg('Periodic Structure · Confirm Periodicity: current PERIODIC {periodic}. ASE cannot reliably infer slab/wire boundaries from XSD; review the selector below. Vacuum size does not change PBC automatically.', code='xsd.periodic_hint', periodic=periodic)
        else:
            try:
                cell = np.array([[float(self.cell.item(i, j).text()) for j in range(3)] for i in range(3)])
                valid_cell = np.isfinite(cell).all() and abs(np.linalg.det(cell)) >= 1e-8
            except (ValueError, AttributeError):
                valid_cell = False
            text = (i18n_msg('Non-periodic Molecule. Check vacuum and Poisson boundaries.', code='xsd.molecule_hint') if locked else
                    i18n_msg('XSD structure type is unconfirmed. Review PERIODIC, or explicitly confirm an isolated molecule before locking NONE.', code='periodicity.unconfirmed_hint'))
            if not valid_cell:
                text += i18n_msg('\nEnter a simulation box manually or generate one using the button below.', code='xsd.missing_box')
        for notice in self._import_notices:
            if getattr(notice, 'code', '') == 'xsd.expanded':
                text += '\n' + notice
        self.import_notice.setText(text)
        self.import_notice.setToolTip(i18n_join('\n', self._import_notices))

    def generate_box(self):
        try:
            selected = self.selected_atom_ids()
            notices = list(self._import_notices)
            dialog = SimulationBoxDialog(self._current_structure(), self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            updated = dialog.generated_structure
            self.set_structure(updated)
            self.set_import_notices(notices)
            self.select_atom_ids(selected)
            self._status(i18n_msg('Centered simulation box generated. Review vacuum and Poisson convergence.', code='box.done'))
            self.changed.emit()
            self.box_generated.emit()
        except (ValueError, TypeError) as exc:
            self._status(i18n_str(exc))

    def collect(self, data):
        if self.st is None:
            return []
        try:
            rows = {self.coords.item(row, 0).data(ATOM_ID_ROLE): row for row in range(self.coords.rowCount())}
            if len(rows) != self.coords.rowCount() or not set(rows) <= set(self.st.atom_ids):
                raise ValueError(i18n_msg('Invalid atom ID', code='studio.e05cd1577b16fa42'))
            ids = [atom_id for atom_id in self.st.atom_ids if atom_id in rows]
            st = self.st.reordered(ids).model_dump()
            st['cell'] = [[float(self.cell.item(i, j).text()) for j in range(3)] for i in range(3)]
            st['positions'] = [[float(self.coords.item(rows[atom_id], j).text()) for j in range(1, 4)] for atom_id in ids]
            st['periodic'] = 'NONE' if self.st.periodicity_locked else self.periodic.currentText()
            labels = [self.coords.item(rows[atom_id], KIND_COLUMN).text().strip() for atom_id in ids]
            st['kind_labels'] = labels if labels != st['symbols'] else []
            data['structure'] = st
            return []
        except (ValueError, AttributeError):
            return [i18n_msg('SUBSYS: cell or coordinates contain invalid numbers', code='studio.84bfbc9f8ff5db0e')]

    def selected_atom_ids(self):
        return {self.coords.item(index.row(), 0).data(ATOM_ID_ROLE)
                for index in self.coords.selectionModel().selectedRows()}

    def _selection_changed(self):
        ids = self.selected_atom_ids()
        self.view.set_selected_atoms(ids)
        fixed = len(self.st.fixed_atoms) if self.st else 0
        self.fixed_count.setText(i18n_msg('Fixed: {p0} atoms · Selected: {p1} atoms', code='studio.06ef9262cb4ac576', p0=fixed, p1=len(ids)))
        for button in [self.fix_button, self.unfix_button]:
            button.setEnabled(bool(ids))
        self.clear_fixed_button.setEnabled(bool(fixed))
        self.range_button.setEnabled(self.st is not None and bool(self.st.symbols))
        self._sync_selection_filter()

    def _update_atom_numbers(self, *_):
        if not self.st:
            return
        numbers = {atom_id: i for i, atom_id in enumerate(self.st.atom_ids, 1)}
        for row in range(self.coords.rowCount()):
            item = self.coords.item(row, 0)
            if item:
                self.coords.setVerticalHeaderItem(row, QTableWidgetItem(i18n_str(numbers[item.data(ATOM_ID_ROLE)])))

    def _update_fixed_cells(self):
        fixed = {atom.atom_id: atom.components for atom in self.st.fixed_atoms} if self.st else {}
        for row in range(self.coords.rowCount()):
            atom_id = self.coords.item(row, 0).data(ATOM_ID_ROLE)
            item = QTableWidgetItem(fixed.get(atom_id, '—'))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setToolTip(i18n_msg('Fixed fractional components: ', code='studio.007eaedd5c3ddb19') + fixed[atom_id] if atom_id in fixed else i18n_msg('Not fixed', code='studio.42bf633a6e628976'))
            self.coords.setItem(row, FIXED_COLUMN, item)

    def _current_structure(self):
        data = {}
        errors = self.collect(data)
        if errors or not data.get('structure'):
            raise ValueError(i18n_msg('Correct invalid cell or coordinate values first', code='studio.8ab436fd945cf042'))
        return Structure.model_validate(data['structure'])

    def _status(self, text):
        self.action_status.setText(text)
        self.action_status.show()

    def apply_fixed(self, components, *, all_atoms=False):
        ids = set(self.st.atom_ids) if all_atoms and self.st else self.selected_atom_ids()
        if not ids:
            self._status(i18n_msg('Select atoms first', code='studio.904b699d134086dc'))
            return
        try:
            updated = set_fixed_atoms(self._current_structure(), ids, components)
        except ValueError as exc:
            self._status(i18n_str(exc))
            return
        if updated.fixed_atoms == self.st.fixed_atoms:
            self._status(i18n_msg('Constraints are unchanged', code='studio.797db3bfa2fecd61'))
            return
        self.st = updated
        sorting = self.coords.isSortingEnabled()
        self.coords.blockSignals(True)
        self.coords.setSortingEnabled(False)
        self._update_fixed_cells()
        self.coords.setSortingEnabled(sorting)
        self.coords.blockSignals(False)
        self.view.set_structure(updated)
        self._selection_changed()
        self._status(i18n_msg('Updated constraints for {p0} atoms', code='studio.31271b08f236be6b', p0=len(ids)))
        self.changed.emit()
        self.constraints_changed.emit()

    def clear_fixed(self):
        self.apply_fixed(None, all_atoms=True)

    def select_atom_ids(self, atom_ids):
        ids = set(atom_ids)
        selection = QItemSelection()
        model = self.coords.model()
        for row in range(self.coords.rowCount()):
            if self.coords.item(row, 0).data(ATOM_ID_ROLE) in ids:
                selection.select(model.index(row, 0), model.index(row, self.coords.columnCount() - 1))
        self.coords.selectionModel().select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect |
                                           QItemSelectionModel.SelectionFlag.Rows)
        self._selection_changed()
        self.action_status.hide()

    def choose_coordinate_range(self):
        try:
            structure = self._current_structure()
        except ValueError as exc:
            self._status(i18n_str(exc))
            return
        dialog = CoordinateRangeDialog(structure, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.select_atom_ids(dialog.selected_ids)
            if not dialog.selected_ids:
                self._status(i18n_msg('No atoms match the range', code='studio.962b3bd541bb11d3'))
