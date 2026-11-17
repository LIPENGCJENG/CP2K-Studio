"""Small reusable forms; widget contents remain drafts until validated."""
from i18n.messages import i18n_msg, i18n_str, i18n_join
from math import isfinite
from PySide6.QtCore import Signal
from i18n.qt import (QWidget, QFormLayout, QLabel, QLineEdit,
                              QComboBox, QCheckBox, QPlainTextEdit)
from ui.widgets.section_card import SectionCard, AdaptiveGrid, page_layout
from ui.widgets.numeric_field import NumericField, set_invalid


def get_value(data, path):
    for part in path.split('.'):
        data = data[part]
    return data


def set_value(data, path, value):
    parts = path.split('.')
    for part in parts[:-1]:
        data = data[part]
    data[parts[-1]] = value


class FormPanel(QWidget):
    changed = Signal()

    def __init__(self, title, description='', parent=None, *, embedded=False):
        super().__init__(parent)
        self.fields = {}
        self.layout = page_layout(self)
        self._target = None
        self.cards = []
        if embedded:
            self.layout.setContentsMargins(0, 0, 0, 0)
        heading = QLabel(title)
        heading.setObjectName('heading')
        heading.setWordWrap(True)
        if not embedded:
            self.layout.addWidget(heading)
        else:
            heading.deleteLater()
        if description:
            label = QLabel(description)
            label.setWordWrap(True)
            label.setObjectName('muted')
            self.layout.addWidget(label)
        self.form = QFormLayout()
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.form.setVerticalSpacing(12)
        self.layout.addLayout(self.form)

    def section(self, title, description='', columns=2, *, help_text=''):
        card = SectionCard(title, description, help_text=help_text)
        self._target = AdaptiveGrid(columns=columns)
        card.content.addWidget(self._target)
        self.layout.addWidget(card)
        self.cards.append(card)
        return card

    def add(self, path, label, kind='text', choices=None, placeholder='', unit='', *, inline=False, control_layout=None):
        if kind == 'choice':
            widget = QComboBox()
            for value in choices:
                widget.addItem(i18n_msg('— Select explicitly —', code='studio.621cb18802e2551d') if value is None else i18n_str(value), value)
            widget.setMinimumContentsLength(10)
            widget.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            widget.currentIndexChanged.connect(lambda *_: self.changed.emit())
        elif kind == 'bool':
            widget = QCheckBox(label if inline else '')
            if inline:
                label = None
            widget.toggled.connect(lambda *_: self.changed.emit())
        elif kind == 'lines':
            widget = QPlainTextEdit()
            widget.setMaximumHeight(92)
            widget.setPlaceholderText(placeholder)
            widget.textChanged.connect(lambda *_: self.changed.emit())
        else:
            widget = NumericField(unit) if kind in {'int', 'optional_int', 'float', 'optional_float'} else QLineEdit()
            widget.setPlaceholderText(placeholder)
            widget.textChanged.connect(lambda *_: self.changed.emit())
        widget.setObjectName(path)
        self.fields[path] = (widget, kind)
        if control_layout is not None:
            control_layout.addWidget(widget)
        elif self._target is not None:
            self._target.add_field(label, widget)
        else:
            self.form.addRow(label, widget)
        return widget

    def load(self, data):
        for path, (widget, kind) in self.fields.items():
            value = get_value(data, path)
            widget.blockSignals(True)
            if kind == 'choice':
                widget.setCurrentIndex(max(0, widget.findData(value)))
            elif kind == 'bool':
                widget.setChecked(value)
            elif kind == 'lines':
                widget.setPlainText(i18n_join('\n', value))
            else:
                widget.setText('' if value is None else i18n_str(value))
            set_invalid(widget, False)
            widget.blockSignals(False)

    def collect(self, data, paths=None):
        errors = []
        for path, (widget, kind) in self.fields.items():
            if paths is not None and path not in paths:
                continue
            try:
                if kind == 'choice':
                    value = widget.currentData()
                elif kind == 'bool':
                    value = widget.isChecked()
                elif kind == 'lines':
                    value = [line.strip() for line in widget.toPlainText().splitlines() if line.strip()]
                else:
                    value = widget.text().strip()
                    if kind == 'int':
                        value = int(value)
                    elif kind == 'optional_int':
                        value = int(value) if value else None
                    elif kind == 'float':
                        value = float(value)
                    elif kind == 'optional_float':
                        value = None if not value or value.casefold() == 'auto' else float(value)
                        if value is not None and not isfinite(value):
                            raise ValueError('nonfinite optional number')
                    elif kind == 'optional_text':
                        value = value or None
                set_value(data, path, value)
                set_invalid(widget, False)
            except (ValueError, TypeError):
                set_invalid(widget, True)
                if kind == 'optional_float':
                    errors.append(i18n_msg('{p0}: enter a finite real number or leave blank for Auto',
                        code='scf.optional_number_error', p0=path.rsplit('.', 1)[-1].upper()))
                else:
                    errors.append(i18n_msg('{p0}: enter a valid number', code='studio.217fa2782cc1be44', p0=path))
        return errors
