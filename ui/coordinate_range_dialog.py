"""Select by Cartesian position; this dialog never creates constraints."""
from i18n.messages import i18n_msg, i18n_str
from i18n.qt import QDialog, QVBoxLayout, QFormLayout, QComboBox, QLabel, QDialogButtonBox, set_button_text
from core.atom_constraints import select_coordinate_range
from ui.widgets.numeric_field import NumericField
from ui.theme import COLORS


class CoordinateRangeDialog(QDialog):
    def __init__(self, structure, parent=None):
        super().__init__(parent)
        self.structure = structure
        self.selected_ids = []
        self.setWindowTitle(i18n_msg('Select Atoms by Coordinate Range', code='studio.6486ad9312cad7fc'))
        self.setMinimumWidth(330)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.axis = QComboBox()
        self.axis.addItems(['X', 'Y', 'Z'])
        self.axis.setCurrentText('Z')
        self.minimum = NumericField('Å')
        self.maximum = NumericField('Å')
        self.minimum.setPlaceholderText(i18n_msg('e.g. -3.0 or -3e0', code='studio.5c4739d3a58813d6'))
        self.maximum.setPlaceholderText(i18n_msg('e.g. 8.0', code='studio.797152927a6b5fcf'))
        form.addRow(i18n_msg('Axis (Cartesian)', code='studio.b49fbd64fc3aadaf'), self.axis)
        form.addRow(i18n_msg('Minimum (Å)', code='studio.645720ed6b2e7056'), self.minimum)
        form.addRow(i18n_msg('Maximum (Å)', code='studio.458886e6f1789318'), self.maximum)
        layout.addLayout(form)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setStyleSheet('color:' + COLORS['error'])
        self.error.hide()
        layout.addWidget(self.error)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        set_button_text(self.buttons.button(QDialogButtonBox.StandardButton.Ok), i18n_msg('Select Atoms', code='studio.d91b106122b3fea9'))
        set_button_text(self.buttons.button(QDialogButtonBox.StandardButton.Cancel), i18n_msg('Cancel', code='studio.2cd0f3be8738a86c'))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def accept(self):
        try:
            self.selected_ids = select_coordinate_range(self.structure, self.axis.currentText(),
                                                       self.minimum.text(), self.maximum.text())
        except ValueError as exc:
            self.error.setText(i18n_str(exc))
            self.error.show()
            return
        super().accept()
