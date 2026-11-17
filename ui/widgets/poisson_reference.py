"""Compact, read-only reference; no solver selection or physics validation."""
from dataclasses import dataclass
from html import escape
from PySide6.QtCore import Qt, QSize, QEvent, QSignalBlocker
from PySide6.QtGui import QPalette
from i18n.messages import i18n_msg, i18n_render
from i18n.language_manager import language_manager
from i18n.qt import (QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                     QSizePolicy, QStyleOptionHeader, QStyle)
from ui.theme import COLORS


@dataclass(frozen=True)
class SolverReference:
    solver: str
    periodicity: str
    applications: tuple
    constraints: tuple


# Full cell text and tooltips share these messages. Display values such as ANY
# are references, never CP2K configuration values.
REFERENCE_ROWS = (
    SolverReference('PERIODIC', 'XYZ', (
        i18n_msg('3D crystalline materials', code='poisson.app.periodic_crystal'),
        i18n_msg('Amorphous bulk models', code='poisson.app.periodic_amorphous'),
        i18n_msg('3D periodic solid–liquid interface supercells', code='poisson.app.periodic_interface'),
    ), (
        i18n_msg('For asymmetric slabs, assess surface dipoles and whether dipole correction is appropriate.', code='poisson.note.periodic_dipole'),
        i18n_msg('Suitable for 3D periodic cell optimization with a supported stress calculation.', code='poisson.note.periodic_cell'),
    )),
    SolverReference('WAVELET', 'NONE, XZ, XYZ', (
        i18n_msg('0D isolated molecules, clusters and ion pairs', code='poisson.app.wavelet_molecule'),
        i18n_msg('2D orthogonal surface models with the nonperiodic normal along Y', code='poisson.app.wavelet_surface'),
    ), (
        i18n_msg('Cell shape: NONE requires a cubic cell; XZ requires an orthogonal cell satisfying the solver geometry conditions.', code='poisson.note.wavelet_shape'),
        i18n_msg('Boundaries: electron density must decay sufficiently at nonperiodic faces. Test vacuum convergence; this can avoid unnecessarily large grids.', code='poisson.note.wavelet_density'),
        i18n_msg('FFT grid: sizes may be restricted by the implementation and factorization requirements.', code='poisson.note.wavelet_grid'),
        i18n_msg('FFT setting: PREFERRED_FFT_LIBRARY FFTSG is required.', code='poisson.note.wavelet_fft'),
    )),
    SolverReference('MT', 'NONE, XY, XZ, YZ', (
        i18n_msg('Isolated clusters with net charge', code='poisson.app.mt_charge'),
        i18n_msg('Elongated isolated molecules or finite polymer segments', code='poisson.app.mt_polymer'),
        i18n_msg('2D periodic surface models', code='poisson.app.mt_surface'),
    ), (
        i18n_msg('Size: nonperiodic cell lengths must accommodate the electron-density extent D; use L > 2D as a reference and check convergence.', code='poisson.note.mt_size'),
        i18n_msg('Geometry: nonperiodic directions must satisfy the solver cell-orthogonality requirements.', code='poisson.note.mt_geometry'),
    )),
    SolverReference('ANALYTIC', 'NONE, Z, XY', (
        i18n_msg('1D periodic systems', code='poisson.app.analytic_wire'),
    ), (
        i18n_msg('Size: nonperiodic cell lengths must accommodate the electron-density distribution.', code='poisson.note.analytic_size'),
        i18n_msg('Geometry: for Z periodicity, check the XY cross-section shape requirements; for XY periodicity, check the nonperiodic direction orthogonality.', code='poisson.note.analytic_geometry'),
        i18n_msg('Listed directions are reference orientations. The official 2026.1 description covers 0D, 1D and 2D generally; Studio retains its existing dimension-based validation.', code='poisson.note.analytic_scope'),
    )),
    SolverReference('MULTIPOLE', 'NONE', (
        i18n_msg('Electrostatic decoupling of QM regions, for example in QM/MM calculations', code='poisson.app.multipole_qmmm'),
    ), (
        i18n_msg('Cell shape: use an orthogonal QM simulation box meeting the solver requirements.', code='poisson.note.multipole_shape'),
        i18n_msg('Applicability: intended for specific electrostatic boundary and QM periodic-image decoupling needs.', code='poisson.note.multipole_scope'),
        i18n_msg('Reference only: this solver is not available in the current Studio selector.', code='poisson.note.reference_only'),
    )),
    SolverReference('IMPLICIT', 'ANY', (
        i18n_msg('Implicit solvation effects', code='poisson.app.implicit_solvent'),
        i18n_msg('Constant-potential electrodes and related interface models', code='poisson.app.implicit_electrode'),
    ), (
        i18n_msg('Supported boundary conditions and grid requirements depend on the selected model and configuration.', code='poisson.note.implicit_model'),
        i18n_msg('ANY denotes 0D/1D/2D/3D coverage, not a value to write into the CP2K PERIODIC keyword.', code='poisson.note.implicit_any'),
        i18n_msg('Reference only: this solver is not available in the current Studio selector.', code='poisson.note.reference_only'),
    )),
)

APPLICATIONS = i18n_msg('Recommended Applications', code='poisson.applications')
CONSTRAINTS = i18n_msg('Constraints & Notes', code='poisson.constraints')


class _SingleLineHeader(QHeaderView):
    def paintSection(self, painter, rect, index):
        option = QStyleOptionHeader()
        self.initStyleOptionForIndex(option, index)
        option.rect = rect
        text, option.text = option.text, ''
        painter.save()
        self.style().drawControl(QStyle.ControlElement.CE_Header, option, painter, self)
        painter.setFont(self.font())
        painter.setPen(option.palette.color(QPalette.ColorRole.ButtonText))
        text = self.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, max(0, rect.width() - 8))
        painter.drawText(rect.adjusted(4, 0, -4, 0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextSingleLine, text)
        painter.restore()


class PoissonReference(QTableWidget):
    ROW_HEIGHT = 28
    HEADER_HEIGHT = 28

    def __init__(self, parent=None):
        super().__init__(len(REFERENCE_ROWS), 4, parent)
        self._fitting = False
        self.setObjectName('poissonReference')
        self.setHorizontalHeader(_SingleLineHeader(Qt.Orientation.Horizontal, self))
        self.setHorizontalHeaderLabels(['POISSON_SOLVER', 'PERIODIC', '', ''])
        for row in range(self.rowCount()):
            for column in range(self.columnCount()):
                item = QTableWidgetItem()
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.setItem(row, column, item)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.verticalHeader().hide()
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.verticalHeader().setMinimumSectionSize(self.ROW_HEIGHT)
        self.verticalHeader().setMaximumSectionSize(self.ROW_HEIGHT)
        self.verticalHeader().setDefaultSectionSize(self.ROW_HEIGHT)
        header = self.horizontalHeader()
        header.setMinimumSectionSize(1)
        header.setSectionsMovable(False)
        header.setSectionsClickable(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setStretchLastSection(False)
        header.setFixedHeight(self.HEADER_HEIGHT)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWordWrap(False)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet('QTableWidget, QHeaderView { font-size:11px; } '
            'QHeaderView::section { font-size:11px; padding:4px; } '
            f'QToolTip {{ background:{COLORS["card"]}; color:{COLORS["foreground"]}; '
            f'border:1px solid {COLORS["border"]}; border-radius:6px; padding:8px; max-width:420px; }}')
        language_manager().callback(self, 'poisson-reference', lambda table: table._render_content())
        self._render_content()

    @staticmethod
    def _tooltip(title, entries):
        items = ''.join('<li>' + escape(text) + '</li>' for text in entries)
        return ('<qt><table width="360" cellspacing="0" cellpadding="0"><tr><td><b>'
                + escape(title) + '</b><ul>' + items + '</ul></td></tr></table></qt>')

    def _render_content(self):
        blocker = QSignalBlocker(self)
        headers = ['POISSON_SOLVER', 'PERIODIC', i18n_render(APPLICATIONS), i18n_render(CONSTRAINTS)]
        for column, title in enumerate(headers):
            self.horizontalHeaderItem(column).setText(title)
            self.horizontalHeaderItem(column).setToolTip(title)
        separator = i18n_render(i18n_msg('; ', code='poisson.separator'))
        for row, entry in enumerate(REFERENCE_ROWS):
            applications = [i18n_render(text) for text in entry.applications]
            constraints = [i18n_render(text) for text in entry.constraints]
            for column, text in enumerate([entry.solver, entry.periodicity,
                                          separator.join(applications), separator.join(constraints)]):
                self.item(row, column).setText(text)  # Delegate alone elides the full display text.
                tooltip = (self._tooltip(headers[column], applications if column == 2 else constraints)
                           if column >= 2 else text)
                self.item(row, column).setToolTip(tooltip)
        del blocker
        self.fit_content()

    def fit_content(self):
        if self._fitting:
            return
        self._fitting = True
        try:
            self.ensurePolished()
            width = max(4, self.viewport().width())
            # Roughly 18/17/27/38, lending space to solver/PBC names when narrow.
            # Every column can still shrink; no horizontal overflow is hidden.
            widths = []
            for column, fraction, cap in [(0, .18, .30), (1, .17, .27)]:
                natural = max(self.fontMetrics().horizontalAdvance(self.horizontalHeaderItem(column).text()),
                    *(self.fontMetrics().horizontalAdvance(self.item(row, column).text()) for row in range(self.rowCount()))) + 12
                widths.append(max(1, int(max(width * fraction, min(natural, width * cap)))))
            remaining = width - sum(widths)
            widths.append(max(1, int(remaining * 27 / 65)))
            widths.append(max(1, width - sum(widths)))
            for column, column_width in enumerate(widths):
                self.setColumnWidth(column, column_width)
            self.setFixedHeight(self.HEADER_HEIGHT + self.ROW_HEIGHT * self.rowCount() + 2 * self.frameWidth())
        finally:
            self._fitting = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_fitting'):
            self.fit_content()

    def changeEvent(self, event):
        super().changeEvent(event)
        if hasattr(self, '_fitting') and event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self.fit_content()

    def minimumSizeHint(self):
        return QSize(0, self.minimumHeight())
