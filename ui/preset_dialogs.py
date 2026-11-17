"""Capture and manage personal presets using one versioned PresetStore."""
from i18n.messages import i18n_msg, i18n_str, i18n_join
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QStandardPaths
from i18n.qt import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QPlainTextEdit, QComboBox, QCheckBox, QDialogButtonBox, QMessageBox,
    QListWidget, QListWidgetItem, QPushButton)
from core.presets import Preset, capture_preset

CATEGORIES = [(i18n_msg('Single Point', code='studio.6257cf612978bdc4'), 'single_point'), (i18n_msg('Geometry Optimization', code='studio.5688511fca2c8507'), 'geo_opt'), (i18n_msg('Custom', code='studio.4eafa9e925b30bcd'), 'custom')]


def default_preset_directory():
    root = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericConfigLocation)
    return Path(root) / 'CP2K-Studio' / 'presets'


class SavePresetDialog(QDialog):
    def __init__(self, store, project, parent=None, *, existing=None, metadata_only=False):
        super().__init__(parent)
        self.store, self.project = store, project.model_copy(deep=True)
        self.existing, self.metadata_only = existing, metadata_only
        self.saved_preset = None
        self.setWindowTitle(i18n_msg('Edit Preset', code='studio.4e32d8dbf1bef946') if metadata_only else i18n_msg('Save Current Settings as Preset', code='studio.00738bccecb44c96'))
        self.resize(570, 430)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit(existing.name if existing else '')
        self.name.setPlaceholderText(i18n_msg('Required, e.g. PBE · OT · Geometry Optimization', code='studio.929111cca381af37'))
        form.addRow(i18n_msg('Preset Name', code='studio.5fe110aa6d1dca31'), self.name)
        self.description = QPlainTextEdit(existing.description if existing else '')
        self.description.setMaximumHeight(90)
        form.addRow(i18n_msg('Description (Optional)', code='studio.19ad97a6aca8b249'), self.description)
        self.category = QComboBox()
        for text, value in CATEGORIES:
            self.category.addItem(text, value)
        initial = existing.category if existing else {'GEO_OPT': 'geo_opt', 'VIBRATIONAL_ANALYSIS': 'custom', 'CELL_OPT': 'custom'}.get(project.global_settings.run_type, 'single_point')
        self.category.setCurrentIndex(self.category.findData(initial))
        form.addRow(i18n_msg('Category', code='studio.515559957fd3acbd'), self.category)
        layout.addLayout(form)
        self.include_cell = QCheckBox(i18n_msg('Include cell and periodicity (confirmation required when applying)', code='studio.538cc19f2f73dc92'))
        self.include_coordinates = QCheckBox(i18n_msg('Include coordinates (excluded by default; confirmation required when applying)', code='studio.675ed6a577012d59'))
        self.include_cell.setChecked(bool(existing and existing.cell_settings and (metadata_only or project.structure is not None)))
        self.include_coordinates.setChecked(bool(existing and existing.coordinates and (metadata_only or project.structure is not None)))
        for widget in [self.include_cell, self.include_coordinates]:
            widget.setEnabled(not metadata_only and project.structure is not None)
            layout.addWidget(widget)
        note = QLabel(i18n_msg('Save reusable calculation parameters without changing the current project. Incomplete drafts are allowed but are not marked as CP2K XML-validated. KIND configurations must be matched to elements when applying.', code='studio.0485ecd6ae412f62'))
        note.setWordWrap(True)
        layout.addWidget(note)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setStyleSheet('color:#f0a69b;')
        layout.addWidget(self.error)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.name.textChanged.connect(self.update_name_state)
        layout.addWidget(self.buttons)
        self.update_name_state()

    def update_name_state(self, *_):
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setEnabled(bool(self.name.text().strip()))

    def build_preset(self):
        if self.metadata_only:
            data = self.existing.model_dump()
            data.update(name=self.name.text(), description=self.description.toPlainText(), category=self.category.currentData())
            return Preset.model_validate(data)
        return capture_preset(self.project, self.name.text(), self.description.toPlainText(), self.category.currentData(),
            include_cell=self.include_cell.isChecked(), include_coordinates=self.include_coordinates.isChecked(),
            preset_id=self.existing.id if self.existing else None)

    def confirm_overwrite(self, name):
        box = QMessageBox(self)
        box.setWindowTitle(i18n_msg('Preset Name Already Exists', code='studio.b94afae5ef8532fa'))
        box.setText(i18n_msg('Preset “{p0}” already exists. Overwrite it, or return and save with another name.', code='studio.9de110d307c3ff3b', p0=name))
        replace = box.addButton(i18n_msg('Overwrite Preset', code='studio.426c18d792670d65'), QMessageBox.ButtonRole.AcceptRole)
        rename = box.addButton(i18n_msg('Save with Another Name', code='studio.4a9f59c187d30c3d'), QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(rename)
        box.exec()
        return box.clickedButton() == replace

    def accept(self):
        try:
            preset = self.build_preset()
            listing = self.store.list()
            same_name = next((p for p in listing.presets if p.name.casefold() == preset.name.casefold()), None)
            updating = self.existing is not None and same_name is not None and same_name.id == self.existing.id
            overwrite = self.existing is not None
            if same_name and not updating:
                if not self.confirm_overwrite(preset.name):
                    self.name.setFocus()
                    self.name.selectAll()
                    return
                overwrite = True
            self.saved_preset = self.store.save(preset, overwrite=overwrite)
            super().accept()
        except (OSError, ValueError) as exc:
            self.error.setText(i18n_str(exc))


class ManagePresetsDialog(QDialog):
    changed = Signal()
    load_requested = Signal(str)

    def __init__(self, store, project, parent=None):
        super().__init__(parent)
        self.store, self.project = store, project.model_copy(deep=True)
        self.setWindowTitle(i18n_msg('Manage My Presets', code='studio.72b4a4fb714a4398'))
        self.resize(760, 520)
        layout = QVBoxLayout(self)
        note = QLabel(i18n_msg('Preset folder: {p0}\nBuilt-in presets remain in the top menu; manage personal presets here.', code='studio.4a00046ddba45a08', p0=store.directory))
        note.setWordWrap(True)
        layout.addWidget(note)
        self.items = QListWidget()
        self.items.currentRowChanged.connect(self.describe)
        layout.addWidget(self.items)
        self.description = QLabel()
        self.description.setWordWrap(True)
        self.description.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.description)
        row = QHBoxLayout()
        self.action_buttons = []
        for text, callback in [(i18n_msg('Load', code='studio.8f8f907784631b04'), self.load_selected), (i18n_msg('Edit / Rename', code='studio.1512e1c6754ba3b8'), self.edit_selected),
                               (i18n_msg('Update from Current Configuration', code='studio.8b73328b3869ac77'), self.update_selected), (i18n_msg('Delete', code='studio.2f9daa828907b93f'), self.delete_selected)]:
            button = QPushButton(text)
            button.clicked.connect(callback)
            row.addWidget(button)
            self.action_buttons.append(button)
        layout.addLayout(row)
        self.problems = QPlainTextEdit()
        self.problems.setReadOnly(True)
        self.problems.setMaximumHeight(100)
        layout.addWidget(self.problems)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.refresh()

    def refresh(self):
        listing = self.store.list()
        self.items.clear()
        self.records = {p.id: p for p in listing.presets}
        for preset in listing.presets:
            item = QListWidgetItem(preset.name + (i18n_msg(' · Draft / Incomplete', code='studio.2ab1ac70f0619483') if preset.incomplete else i18n_msg(' · Complete / Not Certified', code='studio.f3501a1d2d983a3d')))
            item.setData(Qt.ItemDataRole.UserRole, preset.id)
            self.items.addItem(item)
        self.problems.setPlainText(i18n_join('\n', listing.problems))
        self.problems.setVisible(bool(listing.problems))
        if listing.presets:
            self.items.setCurrentRow(0)
        self.describe()

    def selected(self):
        item = self.items.currentItem()
        return self.records.get(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def describe(self, *_):
        selected = self.selected() if hasattr(self, 'records') else None
        for button in self.action_buttons:
            button.setEnabled(selected is not None)
        if selected:
            self.description.setText(i18n_msg('{p0}\nCP2K {p1} · Cell: {p2} · Coordinates: {p3} · Not CP2K syntax-certified', code='studio.bbad784deed494ef', p0=selected.description or i18n_msg('No description', code='studio.8ae96d747e59609e'), p1=selected.cp2k_version, p2=i18n_msg('Included', code='studio.107319b8b39da106') if selected.cell_settings else i18n_msg('Excluded', code='studio.5f60ffcf600ae19c'), p3=i18n_msg('Included', code='studio.107319b8b39da106') if selected.coordinates else i18n_msg('Excluded', code='studio.5f60ffcf600ae19c')))
        else:
            self.description.setText(i18n_msg('No personal presets yet. Save the current settings in step 08.', code='studio.6dbb6181b426442d'))

    def load_selected(self):
        selected = self.selected()
        if selected:
            self.accept()
            self.load_requested.emit('user:' + selected.id)

    def edit_selected(self):
        self.edit(metadata_only=True)

    def update_selected(self):
        self.edit(metadata_only=False)

    def edit(self, metadata_only):
        selected = self.selected()
        if not selected:
            return
        dialog = SavePresetDialog(self.store, self.project, self, existing=selected, metadata_only=metadata_only)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.changed.emit()

    def delete_selected(self):
        selected = self.selected()
        if not selected:
            return
        answer = QMessageBox.question(self, i18n_msg('Delete Preset', code='studio.28786d90697520ac'), i18n_msg('Delete personal preset “{p0}”?', code='studio.ac6bba918bb666e0', p0=selected.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            try:
                self.store.delete(selected.id)
                self.refresh()
                self.changed.emit()
            except OSError as exc:
                QMessageBox.warning(self, i18n_msg('Delete Failed', code='studio.c228558cf257fc49'), i18n_str(exc))
