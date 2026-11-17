"""One modal editor; only successful confirmation produces a new structure."""
import numpy as np
from i18n.messages import i18n_msg, i18n_str
from i18n.language_manager import language_manager
from i18n.qt import (QDialog, QVBoxLayout, QFormLayout, QComboBox, QLabel, QWidget,
                    QDoubleSpinBox, QDialogButtonBox, QLayout, set_button_text)
from core.models import BoxGenerationSettings
from core.structure import generate_simulation_box
from ui.theme import COLORS


class SimulationBoxDialog(QDialog):
    def __init__(self, structure, parent=None):
        super().__init__(parent)
        self.structure = structure.model_copy(deep=True)
        self.generated_structure = None
        self._manual_changed = False
        self.setWindowTitle(i18n_msg('Generate Simulation Box', code='xsd.box_title'))
        self.setMinimumWidth(370)
        box = QVBoxLayout(self)
        box.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        form = QFormLayout()
        self.mode = QComboBox()
        for text, value in [(i18n_msg('Vacuum Padding', code='box.padding'), 'VACUUM_PADDING'),
                            (i18n_msg('Cubic Box', code='box.cubic'), 'CUBIC'),
                            (i18n_msg('Manual Input', code='box.manual'), 'MANUAL')]:
            self.mode.addItem(text, value)
        form.addRow(i18n_msg('Generation Method', code='box.method'), self.mode)
        box.addLayout(form)
        settings = structure.box_generation
        self.pages = []
        for _ in range(3):
            page = QWidget()
            self.pages.append(page)
            box.addWidget(page)
        self.padding = self._number(settings.vacuum_margin, margin=True)
        self.cubic_padding = self._number(settings.cubic_margin, margin=True)
        for page, spin in zip(self.pages[:2], [self.padding, self.cubic_padding]):
            row = QFormLayout(page)
            row.setContentsMargins(0, 0, 0, 0)
            row.addRow(i18n_msg('Vacuum margin on each side (Å)', code='box.margin'), spin)
        lengths = settings.manual_lengths
        if lengths is None:
            cell = np.asarray(structure.cell)
            if np.isfinite(cell).all() and abs(np.linalg.det(cell)) > 1e-8:
                lengths = np.linalg.norm(cell, axis=1)
            else:
                lengths = np.ptp(structure.positions, axis=0) + 2 * settings.vacuum_margin
        manual_form = QFormLayout(self.pages[2])
        manual_form.setContentsMargins(0, 0, 0, 0)
        self.lengths = []
        for axis, value in zip('ABC', lengths):
            spin = self._number(float(value))
            self.lengths.append(spin)
            manual_form.addRow(f'{axis} (Å)', spin)
            spin.valueChanged.connect(self._manual_edited)
        self.note = QLabel(i18n_msg('Generates an orthogonal PERIODIC NONE box and centers the molecule. Review vacuum and Poisson convergence.', code='box.note'))
        self.note.setWordWrap(True)
        self.note.setObjectName('muted')
        box.addWidget(self.note)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setStyleSheet('color:' + COLORS['error'])
        self.error.hide()
        box.addWidget(self.error)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        set_button_text(self.buttons.button(QDialogButtonBox.StandardButton.Ok), i18n_msg('OK', code='box.ok'))
        set_button_text(self.buttons.button(QDialogButtonBox.StandardButton.Cancel), i18n_msg('Cancel', code='studio.2cd0f3be8738a86c'))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        box.addWidget(self.buttons)
        self.mode.currentIndexChanged.connect(self._update_mode)
        self.mode.setCurrentIndex(self.mode.findData(settings.mode))
        self._update_mode()
        language_manager().callback(self, 'box-layout', lambda dialog: dialog._resize())

    @staticmethod
    def _number(value, *, margin=False):
        spin = QDoubleSpinBox()
        spin.setDecimals(3)
        spin.setRange(.01 if margin else .001, max(1000.0 if margin else 1e9, value))
        spin.setValue(value)
        spin.setKeyboardTracking(False)
        return spin

    def _manual_edited(self, *_):
        self._manual_changed = True

    def _resize(self):
        self.layout().activate()
        self.adjustSize()

    def _update_mode(self, *_):
        for index, page in enumerate(self.pages):
            page.setVisible(index == self.mode.currentIndex())
        self.error.hide()
        self._resize()

    def accept(self):
        try:
            for spin in [self.padding, self.cubic_padding, *self.lengths]:
                spin.interpretText()
            data = self.structure.box_generation.model_dump()
            data.update(mode=self.mode.currentData(), vacuum_margin=self.padding.value(),
                        cubic_margin=self.cubic_padding.value())
            if self._manual_changed or data['manual_lengths'] is not None or data['mode'] == 'MANUAL':
                data['manual_lengths'] = tuple(spin.value() for spin in self.lengths)
            self.generated_structure = generate_simulation_box(self.structure, BoxGenerationSettings.model_validate(data))
        except (ValueError, TypeError) as exc:
            self.error.setText(i18n_str(exc))
            self.error.show()
            self._resize()
            return
        super().accept()
