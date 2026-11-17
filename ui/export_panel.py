"""Step eight presents status, input delivery and reusable configuration capture."""
from i18n.messages import i18n_msg, i18n_join
from pathlib import Path
import re
from ui.widgets.section_card import SectionCard, page_layout
from ui.theme import COLORS
from PySide6.QtCore import Qt, Signal
from i18n.qt import (QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                              QListWidget, QListWidgetItem)


def _contains_message_code(message, code):
    # Comprehensive reports wrap diagnostics with a stage prefix. Keep the
    # originating rule identity instead of routing by its translated title.
    return (getattr(message, 'code', '') == code
            or any(_contains_message_code(value, code)
                   for value in getattr(message, 'params', {}).values()))


def error_page(message):
    if _contains_message_code(message, 'vib.scf_warning'):
        return 3, '04 SCF'
    text = message.upper()
    if (getattr(message, 'code', '').startswith('md.')
            or re.search(r'(?:^|\s)MD(?:[：:]|\.[A-Z_]+\s*:)', text) or '分子动力学' in text):
        return 5, i18n_msg('06 Molecular Dynamics', code='md.error_page')
    if 'CELL_OPT' in text:
        return 5, i18n_msg('06 Cell Optimization', code='cellopt.error_page')
    if any(s in text for s in ['VIBRATIONAL', '振动分析', 'NPROC_REP', 'THERMOCHEMISTRY']):
        return 5, i18n_msg('06 Vibrational Analysis', code='vib.error_page')
    if 'RUN_ENVIRONMENT' in text:
        return 6, i18n_msg('07 Runtime Settings', code='studio.e913fb5c6113b608')
    if 'XML' in text:
        return -1, i18n_msg('Top Toolbar: XML Schema', code='studio.311def56f4616726')
    if 'KIND' in text or any(s in text for s in ['基组', '赝势', '数据库', 'BASIS', 'POTENTIAL']):
        return 4, i18n_msg('05 Basis Sets & Pseudopotentials', code='studio.6275eb51c31a24d4')
    if 'SCF' in text:
        return 3, '04 SCF'
    if 'POISSON' in text or 'DFT' in text or 'XC' in text:
        return 2, '03 DFT'
    if any(s in text for s in ['CELL', 'SUBSYS', 'STRUCTURE', '晶胞', '坐标', '结构', '周期']):
        return 0, i18n_msg('01 Structure & Cell', code='studio.be6ce7489badaec9')
    if any(s in text for s in ['GLOBAL', 'PROJECT_NAME', 'RUN_TYPE']):
        return 1, '02 GLOBAL'
    if any(s in text for s in ['MOTION', 'GEO_OPT', 'MAX_FORCE', 'RMS_FORCE', 'MAX_DR', 'RMS_DR']):
        return 5, i18n_msg('06 Geometry Optimization', code='studio.5bf6471ffb2ae052')
    return 2, '03 DFT'


class ExportPanel(QWidget):
    check_requested = Signal()
    input_requested = Signal()
    bundle_requested = Signal()
    preset_requested = Signal()
    directory_requested = Signal()
    navigate_requested = Signal(int)
    xml_requested = Signal()

    def __init__(self):
        super().__init__()
        layout = page_layout(self)
        title = QLabel(i18n_msg('08 · Export & Presets', code='studio.69883ef520401d5a'))
        title.setObjectName('heading')
        layout.addWidget(title)
        status_group = SectionCard(i18n_msg('Current Configuration', code='studio.256efb657a687a83'))
        status_layout = status_group.content
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.TextFormat.PlainText)
        status_layout.addWidget(self.summary)
        self.run_summary = QLabel()
        self.run_summary.setWordWrap(True)
        status_layout.addWidget(self.run_summary)
        self.status = QLabel()
        self.status.setWordWrap(True)
        status_layout.addWidget(self.status)
        self.errors = QListWidget()
        self.errors.setMaximumHeight(120)
        self.errors.itemClicked.connect(self.locate_error)
        status_layout.addWidget(self.errors)
        self.check_button = QPushButton(i18n_msg('Validate Configuration', code='studio.9edac2fe10788eb8'))
        self.check_button.clicked.connect(lambda *_: self.check_requested.emit())
        status_layout.addWidget(self.check_button)
        layout.addWidget(status_group)
        group = SectionCard(i18n_msg('Export CP2K Input', code='studio.a28ffa3b4bd36466'), help_text=(
            i18n_msg('Generate input for CP2K. Standalone INP uses the same generator as the preview; export a calculation package when moving to another computing environment.\n\nCoordinates are embedded in standalone INP; basis and pseudopotential dependencies must remain accessible. Multiple pseudopotential sources produce the required merged file.', code='studio.700fe78d70968dbd')))
        box = group.content
        self.bundle_button = QPushButton(i18n_msg('Export Calculation Package…', code='studio.5a2a8c4abb373954'))
        self.bundle_button.setObjectName('primary')
        self.bundle_button.clicked.connect(lambda *_: self.bundle_requested.emit())
        box.addWidget(self.bundle_button)
        row = QHBoxLayout()
        self.input_button = QPushButton(i18n_msg('Export .inp File', code='studio.50e54d4173bdb499'))
        self.input_button.clicked.connect(lambda *_: self.input_requested.emit())
        row.addWidget(self.input_button)
        self.directory_button = QPushButton(i18n_msg('Open Export Folder', code='studio.8863740eb2039729'))
        self.directory_button.setEnabled(False)
        self.directory_button.clicked.connect(lambda *_: self.directory_requested.emit())
        row.addWidget(self.directory_button)
        box.addLayout(row)
        self.run_note_base = i18n_msg('Packages include run.sh; run "bash run.sh" in the target terminal. Standalone INP export does not generate a script.', code='studio.5f2c3726cf5a68f8')
        self.run_note = QLabel(self.run_note_base)
        self.run_note.setWordWrap(True)
        box.addWidget(self.run_note)
        layout.addWidget(group)
        group = SectionCard(i18n_msg('Save Current Settings as Preset', code='studio.00738bccecb44c96'), help_text=(
            i18n_msg('Save current DFT, SCF, basis, optimization, and related settings for reuse. Cell and coordinates are excluded by default; incomplete drafts are marked accordingly.', code='studio.6c9eacd0d1efad66')))
        group.title_label.setWordWrap(False)
        group.title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        box = group.content
        self.preset_button = QPushButton(i18n_msg('Save as Preset', code='studio.d2aa9ac606d79c4a'))
        self.preset_button.setObjectName('primary')
        self.preset_button.clicked.connect(lambda *_: self.preset_requested.emit())
        box.addWidget(self.preset_button)
        layout.addWidget(group)
        layout.addStretch()

    def update_state(self, project, result, busy=False, *, checked=False):
        run = project.run_environment
        self.run_summary.setText(i18n_msg('Target system: {p0}\nMPI processes: {p1}    OpenMP threads: {p2}\nRequired logical cores: {p3} · {p4}', code='studio.7e8f59aa8196df78', p0=run.os_label, p1=run.mpi_processes, p2=run.omp_threads, p3=run.required_cpu_slots, p4=run.mode_label))
        st = project.structure
        structure = i18n_msg('{p0} · {p1} atoms', code='studio.349e181aa4b43e79', p0=Path(st.source).name if st.source else i18n_msg('Structure Embedded in Project', code='studio.363f2b5862ff4102'), p1=len(st.symbols)) if st and st.symbols else i18n_msg('No Structure Imported', code='studio.9d5f4ff4800d3f67')
        self.summary.setText(i18n_msg('Project: {p0}    Task: {p1}\nDFT: Quickstep / GPW    SCF: {p2}\nStructure: {p3}', code='studio.c51bdb837205503c', p0=project.global_settings.project_name, p1=project.global_settings.run_type, p2=project.dft.scf.method, p3=structure))
        if not checked:
            self.status.setText(i18n_msg('Not validated yet · Live configuration: {p0} errors, {p1} warnings\nClick “Validate Configuration” to check these settings.', code='studio.1bf8fb13f5531f16', p0=len(result.errors), p1=len(result.warnings)))
            self.status.setStyleSheet('color:' + COLORS['muted'] + ';')
        elif result.errors:
            modules = list(dict.fromkeys(error_page(e)[1] for e in result.errors))
            self.status.setText(i18n_msg('{p0} errors · Update: ', code='studio.3a963a308279d4d3', p0=len(result.errors)) + i18n_join('、', modules) + i18n_msg('\nClick an error below to locate its settings.', code='studio.9a531bcc5beb203e'))
            self.status.setStyleSheet('color:' + COLORS['error'] + ';')
        elif result.warnings:
            self.status.setText(i18n_msg('Configuration checked · {p0} warnings · See the validation report', code='studio.d6d9ef96ac44a283', p0=len(result.warnings)))
            self.status.setStyleSheet('color:' + COLORS['warning'] + ';')
        else:
            self.status.setText(i18n_msg('Validation passed · {p0} warnings', code='studio.cd741ca95e098949', p0=len(result.warnings)))
            self.status.setStyleSheet('color:' + COLORS['success'] + ';')
        self.errors.clear()
        for error in result.errors:
            page, module = error_page(error)
            item = QListWidgetItem(i18n_msg('{p0} · {p1}', p0=module, p1=error))
            item.setData(Qt.ItemDataRole.UserRole, page)
            item.setToolTip(error)
            self.errors.addItem(item)
        self.errors.setVisible(bool(result.errors))
        self.set_busy(busy)

    def set_busy(self, busy):
        for button in [self.input_button, self.bundle_button, self.preset_button, self.check_button]:
            button.setEnabled(not busy)

    def locate_error(self, item):
        page = item.data(Qt.ItemDataRole.UserRole)
        self.xml_requested.emit() if page == -1 else self.navigate_requested.emit(page)
