from i18n.messages import i18n_msg, i18n_str, i18n_join
from i18n.language_manager import language_manager, LANGUAGES
from PySide6.QtWidgets import QToolButton as NativeToolButton
from pathlib import Path
from core.resources import resource_path
from pydantic import ValidationError
from PySide6.QtCore import Qt, QTimer, QObject, Signal, QRunnable, QThreadPool, QUrl, QFileSystemWatcher
from i18n.qt import QAction
from PySide6.QtGui import QKeySequence, QDesktopServices
from i18n.qt import (QMainWindow, QWidget, QVBoxLayout, QLabel,
    QListWidget, QStackedWidget, QSplitter, QScrollArea, QToolBar, QTabWidget,
    QPlainTextEdit, QFileDialog, QMessageBox, QInputDialog, QToolButton, QMenu, QDialog, QSizePolicy,
    QComboBox, QHBoxLayout, set_button_text)
from core.models import Project,Structure
from core.structure import load_structure_with_report, structure_file_filter
from core.generator import generate_input
from core.file_references import FileReferenceError
from core.validator import InputValidator, validate_project, ValidationResult
from core.comprehensive_check import comprehensive_check, ComprehensiveResult, source_signatures, file_signatures
from core.project_io import save_project, load_project, export_bundle
from core.presets import PresetStore, builtin_preset, apply_preset as plan_preset
from core.input_export import export_input
from core.schema import BUNDLED_XML, CP2KSchema
from ui.forms import FormPanel
from ui.theme import apply_theme
from ui.validation_state import step_states, show_step_states, StepState
from ui.widgets.status_badge import StepIndicatorDelegate
from ui.widgets.numeric_field import set_invalid
from ui.widgets.hover_help import HoverHelpBlocker
from ui.widgets.section_card import SectionCard
from ui.dft_panel import DFTPanel
from ui.scf_panel import SCFPanel
from ui.kind_panel import KindPanel
from ui.structure_panel import StructurePanel
from ui.input_editor import InputEditor
from ui.export_panel import ExportPanel
from ui.run_environment_panel import RunEnvironmentPanel
from ui.xml_dialog import XMLDialog
from ui.help_dialog import HelpDialog
from ui.vibrational_panel import TaskPanel
from ui.preset_dialogs import SavePresetDialog, ManagePresetsDialog, default_preset_directory

ROOT = resource_path()


class WorkerSignals(QObject):
    done = Signal(int, object, object)


class Worker(QRunnable):
    def __init__(self, revision, callback):
        super().__init__()
        self.revision, self.callback = revision, callback
        self.signals = WorkerSignals()

    def run(self):
        try:
            value, error = self.callback(), None
        except Exception as exc:
            value, error = None, i18n_str(exc)
        self.signals.done.emit(self.revision, value, error)


class MainWindow(QMainWindow):
    def __init__(self, *, preset_directory=None):
        super().__init__()
        self.language_manager = language_manager().attach()
        # Dispose Qt children in the event loop rather than a later Python GC
        # cycle while another window's timer/worker callback is being dispatched.
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.language_manager.track_window(self)
        self.project = Project()
        self.project_path = None
        self.dirty = False
        self._loading = False
        self._revision = 0
        self._configuration_check_revision = None
        self._configuration_check_snapshot = None
        self._comprehensive_result = None
        self._dependency_signature = {}
        self._dependency_watcher = QFileSystemWatcher(self)
        self._dependency_watcher.fileChanged.connect(self._dependencies_changed)
        self._dependency_watcher.directoryChanged.connect(self._dependencies_changed)
        self._busy = False
        self._draft_errors = []
        self._validation = ValidationResult()
        self._workers = set()
        self.preset_store = PresetStore(preset_directory or default_preset_directory())
        self.last_export_directory = None
        self._schema_validator = None
        self._schema_signature = None
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.setWindowTitle('CP2K Studio · CP2K 2026.1')
        self.resize(1480, 920)
        self.setMinimumSize(1050, 650)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(220)
        self.timer.timeout.connect(self.refresh)
        self._style()
        self._build_ui()
        self.load_into_ui(self.project)
        self.rebuild_preset_menu()
        self.language_manager.callback(self, 'main', lambda window: window.retranslate_ui())
        self.retranslate_ui()

    def _language_selected(self, *_):
        self.language_manager.set_language(self.language_selector.currentData())

    def retranslate_ui(self):
        # Pure presentation: no refresh(), data collection, or validation.
        blocked = self.language_selector.blockSignals(True)
        self.language_selector.setCurrentIndex(self.language_selector.findData(self.language_manager.language))
        self.language_selector.blockSignals(blocked)
        if hasattr(self, '_step_states'):
            show_step_states(self.nav, self._step_states)
        self.nav.doItemsLayout()
        self.structure_panel.view.update()

    def _build_ui(self):
        toolbar = QToolBar(i18n_msg('Project Files', code='studio.79f326be4409d51f'))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        self.project_button = QToolButton()
        self.project_button.setText(i18n_msg('Project', code='studio.a049dca9d8f1e021'))
        self.project_button.setObjectName('projectMenuButton')
        self.project_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.project_menu = QMenu(self)
        self.project_actions = {}
        actions = [('new', i18n_msg('New Project', code='studio.0e1a7040390fb03e'), self.new_project, QKeySequence.StandardKey.New),
                   ('open', i18n_msg('Open Project...', code='studio.c0eaf52157af601f'), self.open_project, QKeySequence.StandardKey.Open),
                   ('save', i18n_msg('Save Project', code='studio.a637cf4680fb5487'), self.save, QKeySequence.StandardKey.Save)]
        for name, label, callback, shortcut in actions:
            action = QAction(label, self)
            action.setShortcut(shortcut)
            action.triggered.connect(callback)
            # Keep window shortcuts active while the popup menu is closed.
            self.addAction(action)
            self.project_menu.addAction(action)
            self.project_actions[name] = action
        self.project_button.setMenu(self.project_menu)
        toolbar.addWidget(self.project_button)
        self.preset_button = QToolButton()
        self.preset_button.setText(i18n_msg('Presets', code='studio.71d67829caf43b18'))
        self.preset_button.setObjectName('presetMenuButton')
        self.preset_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.preset_menu = QMenu(self)
        self.preset_menu.aboutToShow.connect(self.rebuild_preset_menu)
        self.preset_button.setMenu(self.preset_menu)
        toolbar.addWidget(self.preset_button)
        self.xml_action = toolbar.addAction(i18n_msg('XML Schema', code='studio.18f7c81abe3fb5c7'), self.open_xml_settings)
        self.export_action = QAction(i18n_msg('Export Calculation Package', code='studio.74a1fb3c37f0f2a1'), self)
        self.export_action.triggered.connect(self.export)
        self.environment_action = toolbar.addAction(i18n_msg('Environment Check', code='env.button'), self.show_environment_check)
        self.local_run_action = toolbar.addAction(i18n_msg('Local Run', code='local.button'), self.start_local_run)
        toolbar.addAction(i18n_msg('Help', code='studio.cb4ba40bf823511d'), self.show_help)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        self.language_control = QWidget()
        language_row = QHBoxLayout(self.language_control)
        language_row.setContentsMargins(0, 0, 0, 0)
        language_row.setSpacing(6)
        self.language_label = QLabel(i18n_msg('Language:'))
        self.language_selector = QComboBox()
        self.language_selector.setObjectName('languageSelector')
        self.language_selector.setFixedWidth(160)
        self.language_selector.setStyleSheet('QComboBox { padding-top:6px; padding-bottom:6px; }')
        self.language_label.setBuddy(self.language_selector)
        for code, name in LANGUAGES.items():
            self.language_selector.addItem(name, code)
        language_row.addWidget(self.language_label)
        language_row.addWidget(self.language_selector)
        toolbar.addWidget(self.language_control)
        self.language_selector.currentIndexChanged.connect(self._language_selected)
        menu = self.menuBar().addMenu(i18n_msg('File', code='studio.39932f24fe11a6ba'))
        menu.addAction(i18n_msg('Save Project As…', code='studio.52aefded530dd2ec'), lambda: self.save(force_dialog=True))
        menu.addAction(i18n_msg('Open Water Example…', code='studio.0dc2da7d79a720cc'), self.open_example)
        menu.addAction(i18n_msg('Import Existing INP…', code='studio.890b0f9253480355'), self.import_inp)
        menu.addAction(i18n_msg('Database Manager…', code='studio.cd1ec226a7396f90'), lambda:self.kind_panel.manage_databases())
        menu.addAction(self.export_action)
        menu.addSeparator()
        menu.addAction(i18n_msg('Quit', code='studio.498e1d59b4d787ee'), self.close)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(split)
        nav_container = QWidget()
        nav_container.setFixedWidth(190)
        nav_container.setObjectName('navigation')
        nav_layout = QVBoxLayout(nav_container)
        brand = QLabel('CP2K\nSTUDIO')
        brand.setObjectName('brand')
        nav_layout.addWidget(brand)
        badge = QLabel('2026.1 · INPUT BUILDER')
        badge.setObjectName('muted')
        nav_layout.addWidget(badge)
        self.nav = QListWidget()
        self.nav.setObjectName('stepNavigation')
        self.nav.setItemDelegate(StepIndicatorDelegate(self.nav))
        self.nav.setWordWrap(True)
        self.nav.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.nav.addItems([i18n_msg('01  Structure & Cell', code='studio.ea618ebc5acdddab'), '02  GLOBAL', '03  DFT', '04  SCF', i18n_msg('05  Basis Sets & Pseudopotentials', code='studio.32ebcdaa48de6986'), i18n_msg('06  Geometry Optimization', code='studio.b16f44f63f620bf3'), i18n_msg('07  Runtime Settings', code='studio.56aa9cc7f7010ba2'), i18n_msg('08  Export & Presets', code='studio.c86dd81d809dee26')])
        self._hover_help_blocker = HoverHelpBlocker(self)
        for action in toolbar.actions():
            action.setStatusTip('')
        for widget in [toolbar, *toolbar.findChildren(NativeToolButton), self.language_control,
                       self.language_selector, self.language_label, self.nav, self.nav.viewport()]:
            self._hover_help_blocker.install_on(widget)
        nav_layout.addWidget(self.nav)
        note = QLabel(i18n_msg('Complete the configuration before exporting.', code='studio.2764c68b25e3bdb7'))
        note.setWordWrap(True)
        note.setObjectName('muted')
        nav_layout.addWidget(note)
        split.addWidget(nav_container)
        self.stack = QStackedWidget()
        self.stack.setMinimumWidth(360)
        split.addWidget(self.stack)
        self.global_panel = FormPanel('02 · GLOBAL')
        # All GLOBAL fields belong to cards; remove the unused flat-form slot.
        self.global_panel.layout.removeItem(self.global_panel.form)
        self.global_panel.section(i18n_msg('Project Name', code='studio.867698fb7b0c730c'), columns=1)
        self.global_panel.add('global_settings.project_name', None).setAccessibleName(i18n_msg('Project Name', code='studio.867698fb7b0c730c'))
        self.global_panel.section(i18n_msg('Calculation Task', code='studio.6f4d044498527dbe'))
        run_captions = {
            'ENERGY': i18n_msg('Energy', code='run_type.energy'),
            'GEO_OPT': i18n_msg('Geometry optimization', code='run_type.geo_opt'),
            'CELL_OPT': i18n_msg('Cell optimization', code='run_type.cell_opt'),
            'MD': i18n_msg('Ab initio molecular dynamics', code='run_type.md'),
            'VIBRATIONAL_ANALYSIS': i18n_msg('Vibration Analysis', code='run_type.vibrational'),
        }
        run_type = self.global_panel.add('global_settings.run_type', 'RUN_TYPE', 'choice', list(run_captions))
        for index, value in enumerate(run_captions):
            run_type.setItemText(index, run_captions[value])
        self.global_panel.add('global_settings.print_level', 'PRINT_LEVEL', 'choice', ['LOW', 'MEDIUM', 'HIGH'])
        self.global_panel.layout.addStretch()
        self.structure_panel = StructurePanel()
        self.structure_panel.import_requested.connect(self.import_structure)
        self.structure_panel.box_generated.connect(self.refresh)
        self.structure_panel.boundary_confirmed.connect(self.refresh)
        self.dft_panel = DFTPanel()
        self.scf_panel = SCFPanel()
        self.kind_panel = KindPanel()
        self.motion_panel = FormPanel(i18n_msg('06 · Geometry Optimization', code='studio.acc062999902c75c'))
        self.motion_panel.layout.removeItem(self.motion_panel.form)
        self.motion_panel.section(i18n_msg('Optimizer & Iteration Settings', code='studio.1e07f6cdf4c14689'))
        self.motion_panel.add('motion.optimizer', 'OPTIMIZER', 'choice', ['BFGS', 'LBFGS', 'CG'])
        self.motion_panel.add('motion.max_iter', 'MAX_ITER', 'int')
        self.motion_panel.section(i18n_msg('Convergence Thresholds', code='studio.b78b772cbbd1f76f'))
        for key in ['max_force', 'rms_force', 'max_dr', 'rms_dr']:
            self.motion_panel.add('motion.' + key, key.upper(), 'float', unit='Ha/Bohr' if 'force' in key else 'Bohr')
        self.motion_panel.layout.addStretch()
        self.task_panel = TaskPanel(self.motion_panel)
        self.vibrational_panel = self.task_panel.vibrational
        self.cell_opt_panel = self.task_panel.cell_opt
        self.md_panel = self.task_panel.md
        self.global_panel.fields['global_settings.run_type'][0].currentIndexChanged.connect(
            lambda *_: self.update_task_page(self.global_panel.fields['global_settings.run_type'][0].currentData()))
        self.run_panel = RunEnvironmentPanel()
        self.panels = [self.structure_panel, self.global_panel, self.dft_panel, self.scf_panel,
                       self.kind_panel, self.task_panel, self.run_panel]
        for panel in self.panels:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(panel)
            self.stack.addWidget(scroll)
            panel.changed.connect(self.edited)
        self.export_panel = ExportPanel()
        self.export_panel.check_requested.connect(self.check_current_configuration)
        self.export_panel.input_requested.connect(self.export_inp)
        self.export_panel.bundle_requested.connect(self.export)
        self.export_panel.preset_requested.connect(self.save_as_preset)
        self.export_panel.directory_requested.connect(self.open_export_directory)
        self.export_panel.navigate_requested.connect(self.nav.setCurrentRow)
        self.export_panel.xml_requested.connect(self.open_xml_settings)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.export_panel)
        self.stack.addWidget(scroll)
        self.kind_panel.changed.connect(self.refresh)
        self.run_panel.changed.connect(self.refresh)
        self.structure_panel.constraints_changed.connect(self.refresh)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)
        right = QWidget()
        right.setObjectName('previewPane')
        right.setMinimumWidth(340)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 20, 12, 12)
        self.preview_splitter = QSplitter(Qt.Orientation.Vertical)
        self.preview_splitter.setObjectName('previewSplitter')
        self.preview_splitter.setChildrenCollapsible(False)
        self.preview_splitter.setHandleWidth(6)
        right_layout.addWidget(self.preview_splitter)
        self.structure_view_card = SectionCard(i18n_msg('3D Structure Viewer', code='studio.bf78457b5577d76a'), help_text=
            i18n_msg('Left-drag empty space to rotate · Click an atom to select · Right-drag to pan · Scroll to zoom. Bonds are not inferred.', code='studio.aed0843ffedd93b3'))
        self.structure_view_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.structure_view_card.setMinimumHeight(280)
        self.structure_panel.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.structure_view_card.content.addWidget(self.structure_panel.view, 1)
        self.preview_splitter.addWidget(self.structure_view_card)
        self.input_preview_pane = QWidget()
        self.input_preview_pane.setMinimumHeight(220)
        input_layout = QVBoxLayout(self.input_preview_pane)
        input_layout.setContentsMargins(0, 8, 0, 0)
        input_layout.setSpacing(12)
        title = QLabel(i18n_msg('INP · Live Preview', code='studio.dd4f801cad97027e'))
        title.setObjectName('heading')
        input_layout.addWidget(title)
        self.preview = InputEditor()
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.preview, 'input.inp')
        self.tabs.addTab(self.report, i18n_msg('Validation Report', code='studio.73ded52ed89ccae6'))
        input_layout.addWidget(self.tabs)
        hint = QLabel(i18n_msg('Coordinates in Å', code='studio.2511cb9a63dc70a0'))
        hint.setObjectName('muted')
        input_layout.addWidget(hint)
        self.preview_splitter.addWidget(self.input_preview_pane)
        self.preview_splitter.setStretchFactor(0, 1)
        self.preview_splitter.setStretchFactor(1, 1)
        self.preview_splitter.setSizes([480, 320])
        split.addWidget(right)
        split.setCollapsible(0, False)
        split.setSizes([190, 640, 650])
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 1)
        self.statusBar().showMessage(i18n_msg('Ready', code='studio.b073db9c0bd6f2ed'))

    def _style(self):
        apply_theme()

    def update_task_page(self, run_type):
        self.task_panel.set_run_type(run_type)
        self.nav.item(5).setText(i18n_msg('06  Vibrational Analysis', code='vib.nav')
                                 if run_type == 'VIBRATIONAL_ANALYSIS' else
                                 i18n_msg('06  Cell Optimization', code='cellopt.nav')
                                 if run_type == 'CELL_OPT' else
                                 i18n_msg('06  Molecular Dynamics', code='md.nav')
                                 if run_type == 'MD' else
                                 i18n_msg('06  Geometry Optimization', code='studio.b16f44f63f620bf3'))
        self.nav.doItemsLayout()

    def _invalidate_check(self):
        self._configuration_check_revision = None
        self._configuration_check_snapshot = None
        self._comprehensive_result = None
        paths = self._dependency_watcher.files() + self._dependency_watcher.directories()
        if paths:
            self._dependency_watcher.removePaths(paths)
        self._dependency_signature = {}

    def _watch_sources(self, signatures):
        paths = self._dependency_watcher.files() + self._dependency_watcher.directories()
        if paths:
            self._dependency_watcher.removePaths(paths)
        self._dependency_signature = dict(signatures)
        existing = {i18n_str(Path(path).parent) for path in signatures if Path(path).parent.is_dir()}
        existing.update(path for path in signatures if Path(path).is_file())
        if existing:
            self._dependency_watcher.addPaths(sorted(existing))

    def _dependencies_changed(self, *_):
        if self._dependency_signature and file_signatures(self._dependency_signature) != self._dependency_signature:
            self._revision += 1
            self._invalidate_check()
            self._schema_validator = None
            self._schema_signature = None
            self.refresh()
            self.statusBar().showMessage(i18n_msg('The XML schema or a dependency changed. Run comprehensive validation again.', code='studio.0245b3f019b965c7'))

    def edited(self):
        if self._loading:
            return
        self.dirty = True
        self._revision += 1
        self._invalidate_check()
        # Never allow export of a previous valid model while new text is pending.
        self.export_action.setEnabled(False)
        self.export_panel.status.setText(i18n_msg('Parameters changed; validation is out of date. Click “Validate Configuration” again.', code='studio.508380ae2a94a6f3'))
        self.export_panel.status.setStyleSheet('')
        sender=self.sender()
        if hasattr(self,'_step_states'):
            states=list(self._step_states)
            if sender in self.panels:
                states[self.panels.index(sender)]=StepState('unchecked')
            states[7]=StepState('unchecked')
            self._step_states[7]=states[7]
            show_step_states(self.nav,states)
        self.timer.start()

    def load_into_ui(self, project):
        self._loading = True
        self._invalidate_check()
        self.project = project
        self._migration_notices = list(project._migration_warnings)
        self._schema_validator = None
        self._schema_signature = None
        data = project.model_dump()
        for panel in self.panels:
            if panel is self.structure_panel:
                panel.set_structure(project.structure)
            else:
                panel.load(data)
        self.update_task_page(project.global_settings.run_type)
        self._loading = False
        self._revision += 1
        self.refresh()

    def refresh(self):
        self.timer.stop()
        if self._dependency_signature and file_signatures(self._dependency_signature) != self._dependency_signature:
            self._revision += 1
            self._invalidate_check()
        data = self.project.model_dump()
        errors = []
        for panel in self.panels:
            if panel is self.kind_panel:
                try:
                    panel.sync_structure(Structure.model_validate(data['structure']) if data['structure'] else None)
                    panel.set_xc(data['dft']['xc_functional'])
                except ValueError:
                    pass
            errors += panel.collect(data)
        candidate = None
        try:
            candidate = Project.model_validate(data)
            if not errors:
                self.project = candidate
        except ValidationError as exc:
            errors += [i18n_msg('{p0}: {p1}', p0=i18n_join('.', (i18n_str(p) for p in e['loc'])),
                p1=i18n_str(e.get('ctx', {}).get('error')) if e.get('ctx', {}).get('error') else e['msg']) for e in exc.errors()]
            for issue in exc.errors():
                widget=self.findChild(QWidget,i18n_join('.', (i18n_str(p) for p in issue['loc'])))
                if widget is not None:
                    set_invalid(widget,True)
        self._current_run_type = data['global_settings']['run_type']
        self.vibrational_panel.set_periodicity(data['structure']['periodic'] if data.get('structure') else None)
        self._draft_errors = errors
        if (self._configuration_check_revision is not None
                and self._configuration_check_snapshot != self.project.model_dump()):
            self._invalidate_check()
        self._validation = validate_project(candidate or self.project, self.kind_panel.catalog)
        self._validation.errors = list(dict.fromkeys([*errors, *self._validation.errors]))
        self.kind_panel.update_status(self.project)
        self._display_validation(self._validation)
        if self._validation.ok:
            try:
                self.preview.show_text(generate_input(self.project,catalog=self.kind_panel.catalog))
            except FileReferenceError as exc:
                self.preview.show_text('! ' + i18n_str(exc))
            except Exception as exc:
                self._validation.errors.append(i18n_str(exc))
                self._display_validation(self._validation)
        if not self._validation.ok:
            self.preview.show_text(i18n_msg('! Configuration is incomplete or invalid; no runnable input was generated.\n! Valid draft settings can still be saved.\n\n', code='studio.1f73ff1dc17e0340') +
                                   i18n_join('\n', ('! ' + e for e in self._validation.errors)))
        self.structure_panel.view.set_structure(self.project.structure)
        self.export_action.setEnabled(self._validation.ok and not self._busy)
        name = self.project_path.name if self.project_path else i18n_msg('Untitled Project', code='studio.d55e16c0a7d0ce8c')
        self.setWindowTitle(i18n_msg('CP2K Studio · {p0}', p0=name) + (' *' if self.dirty else ''))

    def _display_validation(self, result):
        lines = [i18n_msg('CP2K 2026.1 · Configuration Check', code='studio.9da7cf46a3db5697'), '']
        lines += [i18n_msg('Error · ', code='studio.52d4395a320bcf3c') + e for e in result.errors]
        if not result.errors:
            lines.append(i18n_msg('Configuration check passed.', code='studio.3c9e08a34715d9c1'))
        lines += ['', *[i18n_msg('Project Migration · ', code='studio.5d5ede6dd286d2f1') + w for w in self._migration_notices],
                  *[i18n_msg('Warning · ', code='studio.45f51b987466bddc') + w for w in result.warnings],
                  *[i18n_msg('Info · ', code='validation.info_prefix')+i for i in result.infos], '', i18n_msg('Syntax validation does not verify numerical accuracy or convergence.', code='studio.99ec5b4f0c08b1eb')]
        checked = self._configuration_check_revision == self._revision and self._comprehensive_result is not None
        shown = self._comprehensive_result.validation if checked else result
        self.report.setPlainText(self._comprehensive_result.report() if checked else i18n_join('\n', lines))
        self.export_panel.update_state(self.project, shown, self._busy, checked=checked)
        self._step_states = step_states(self.project, result, run_type=self._current_run_type)
        if checked:
            self._step_states[7] = step_states(self.project, shown, checked=True)[7]
        show_step_states(self.nav, self._step_states)

    def check_current_configuration(self):
        if self._busy:
            return
        self.refresh()
        self._invalidate_check()
        self._display_validation(self._validation)
        project = self.project.model_copy(deep=True)
        snapshot = project.model_dump()
        draft_errors = list(self._draft_errors)
        self._watch_sources(source_signatures(project, self.kind_panel.catalog))
        self.tabs.setCurrentIndex(1)
        self.report.setPlainText(i18n_msg('CP2K Studio · Comprehensive Validation\nChecking configuration, XML, dependencies, and calculation package…', code='studio.ff478f9da21b1017'))
        self.statusBar().showMessage(i18n_msg('Running comprehensive validation…', code='studio.108b77566772f0c8'))
        def finished(revision, value, error):
            if (revision != self._revision or snapshot != self.project.model_dump()
                    or (value and value.signatures and file_signatures(value.signatures) != value.signatures)):
                self._invalidate_check()
                self._display_validation(self._validation)
                self.statusBar().showMessage(i18n_msg('Configuration or dependencies changed during validation. Please run it again.', code='studio.d90fe896b4f7ea59'))
                return
            if error:
                value = ComprehensiveResult()
                value.stages[0].executed = True
                value.stages[0].errors.append(i18n_msg('Validation failed to run: {p0}. Check the files and configuration, then retry.', code='studio.e475f6d0ee160ef8', p0=error))
                for stage in value.stages[1:]:
                    stage.reason = i18n_msg('The validation service encountered an error.', code='studio.1d9d5a8ef86b170a')
            self._comprehensive_result = value
            self._configuration_check_revision = self._revision
            self._configuration_check_snapshot = snapshot
            self._watch_sources(value.signatures or self._dependency_signature)
            self._display_validation(self._validation)
            summary = value.validation
            self.statusBar().showMessage(i18n_msg('Validation finished · {p0} errors · {p1} warnings; no calculation was run', code='studio.7cf761111bf3b957', p0=len(summary.errors), p1=len(summary.warnings)))
            self.tabs.setCurrentIndex(1)
        self._start_worker(lambda: comprehensive_check(project, draft_errors=draft_errors,
                           validator_factory=self.validation_service), finished)

    def _error(self, title, exc):
        QMessageBox.warning(self, title, i18n_str(exc))

    def _can_leave(self):
        if not self.dirty:
            return True
        choice = QMessageBox.question(self, i18n_msg('Unsaved Project', code='studio.635a265f503379b5'), i18n_msg('Save the current changes?', code='studio.62b2bd3c00c5214c'),
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save)
        if choice == QMessageBox.StandardButton.Cancel:
            return False
        return self.save() if choice == QMessageBox.StandardButton.Save else True

    def new_project(self):
        if self._can_leave():
            self.project_path = None
            self.dirty = False
            self.load_into_ui(Project())

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, i18n_msg('Open CP2K Studio Project', code='studio.a41dc714971719a0'), '', i18n_msg('CP2K Studio (*.json);;All Files (*)', code='studio.1cba47f6efcec745'))
        if path:
            self._open_path(path)

    def _open_path(self, path):
        try:
            project = load_project(path)
            if not self._can_leave():
                return
            self.project_path = Path(path)
            self.dirty = False
            self.load_into_ui(project)
            if project._migration_warnings:
                self.tabs.setCurrentIndex(1)
                self.statusBar().showMessage(i18n_msg('Runtime settings were migrated from an older format. Review the report and step 07.', code='studio.dc29063153e16021'))
        except Exception as exc:
            self._error(i18n_msg('Cannot Open Project', code='studio.8cf36a6b4cf16b94'), exc)

    def open_example(self):
        self._open_path(ROOT / 'examples' / 'water.cp2kstudio.json')
        # Treat the bundled demonstration as a new project to preserve the example.
        if self.project_path == ROOT / 'examples' / 'water.cp2kstudio.json':
            self.project_path = None
            self.dirty = True
            self.refresh()

    def save(self, checked=False, force_dialog=False):
        self.refresh()
        if self._draft_errors:
            self._error(i18n_msg('Cannot Save Yet', code='studio.1a8735c6e13148f3'), i18n_msg('Correct the invalid fields first:\n', code='studio.f7dfcbf254ddad12') + i18n_join('\n', self._draft_errors))
            return False
        path = i18n_str(self.project_path) if self.project_path and not force_dialog else ''
        if not path:
            path, _ = QFileDialog.getSaveFileName(self, i18n_msg('Save Project (Drafts Allowed)', code='studio.bed343b1926b5b52'),
                self.project.global_settings.project_name + '.cp2kstudio.json', 'CP2K Studio (*.json)')
        if not path:
            return False
        try:
            save_project(self.project, path)
            self.project_path = Path(path)
            self.dirty = False
            self.refresh()
            self.statusBar().showMessage(i18n_msg('Project saved: {p0}', code='studio.646961ecbf06c5b6', p0=path))
            return True
        except Exception as exc:
            self._error(i18n_msg('Save Failed', code='studio.6309a3bb5ba4c714'), exc)
            return False

    def import_structure(self):
        path, _ = QFileDialog.getOpenFileName(self, i18n_msg('Import Structure', code='studio.0336447acd3a1674'), '', structure_file_filter())
        if not path:
            return
        try:
            imported = load_structure_with_report(path)
            structure = imported.structure
            # Preserve current editable chemistry fields; only replace structure and element rows.
            data = self.project.model_dump()
            self.kind_panel.collect(data)
            self.project.structure = structure
            self.structure_panel.set_structure(structure)
            self.structure_panel.set_import_notices(imported.notices)
            self.kind_panel.set_elements(structure.kind_elements, data['kinds'])
            self.nav.setCurrentRow(0)
            self.edited()
            self.refresh()
        except Exception as exc:
            self._error(i18n_msg('Structure Import Failed', code='studio.dc367c4e73066bd0'), exc)

    def apply_preset(self, name):
        self.refresh()
        if self._draft_errors:
            self._error(i18n_msg('Cannot Apply Preset', code='studio.4f2cdc9031872d17'), i18n_join('\n', self._draft_errors))
            return
        try:
            preset = self.preset_store.load(name[5:]) if name.startswith('user:') else builtin_preset(name)
            planned = plan_preset(self.project, preset)
            if planned.changes or planned.includes_structure:
                if not self.confirm_preset_application(preset, planned):
                    return False
            self.dirty = True
            self.load_into_ui(planned.project)
            self.statusBar().showMessage(i18n_msg('Preset applied: {p0}', code='studio.dfb8a1454043632b', p0=self.preset_display_name(preset)) + (i18n_msg(' · Review unmatched elements and draft warnings', code='studio.2578ac877384dae9') if planned.warnings else ''))
            if planned.warnings:
                self.report.appendPlainText(i18n_msg('\nPreset Notes:\n', code='studio.06b3347c508bfe57') + i18n_join('\n', planned.warnings))
                self.tabs.setCurrentIndex(1)
            return True
        except Exception as exc:
            self._error(i18n_msg('Cannot Read Preset', code='studio.d9cf91ba5e91c8e8'), exc)
            return False

    @staticmethod
    def preset_display_name(preset):
        return {"builtin-single_point": i18n_msg("Single-Point Preset", code="studio.5091f86f26dfeeeb"),
                "builtin-geo_opt": i18n_msg("Geometry Optimization Preset", code="studio.bd64d9d635949360")}.get(preset.id, preset.name)

    def confirm_preset_application(self, preset, planned):
        details = i18n_msg('Settings to update: ', code='studio.13fe698a1554dc96') + i18n_join('、', planned.changes)
        if planned.includes_structure:
            details += i18n_msg('\nThis preset explicitly includes the cell or coordinates. Confirming will replace those settings.', code='studio.cd4c8608417c225b')
        else:
            details += i18n_msg('\nThe current structure, coordinates, and cell will be preserved.', code='studio.0b0c5632b664f1fa')
        if planned.warnings:
            details += '\n\n' + i18n_join('\n', planned.warnings)
        return QMessageBox.question(self, i18n_msg('Apply Preset', code='studio.57a1cd214175a24d'), i18n_msg('Apply “{p0}”?\n\n{p1}', code='studio.b6aa28c1ffe87e11', p0=self.preset_display_name(preset), p1=details),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def rebuild_preset_menu(self):
        self.preset_menu.clear()
        for title, name in [(i18n_msg('Single-Point Preset', code='studio.5091f86f26dfeeeb'), 'single_point'), (i18n_msg('Geometry Optimization Preset', code='studio.bd64d9d635949360'), 'geo_opt')]:
            action = self.preset_menu.addAction(title)
            action.triggered.connect(lambda checked=False, value=name: self.apply_preset(value))
        self.my_presets_menu = self.preset_menu.addMenu(i18n_msg('My Presets', code='studio.3cbfca23b6e20dd5'))
        listing = self.preset_store.list()
        for preset in listing.presets:
            action = self.my_presets_menu.addAction(preset.name + (i18n_msg(' · Draft', code='studio.0efb1ee4ab8edf50') if preset.incomplete else ''))
            action.setToolTip(preset.description or i18n_msg('Not certified by CP2K syntax validation', code='studio.d8cd1b51d67a610b'))
            action.triggered.connect(lambda checked=False, value=preset.id: self.apply_preset('user:' + value))
        if not listing.presets:
            empty = self.my_presets_menu.addAction(i18n_msg('No personal presets; save one in step 08', code='studio.d460429579dafac9'))
            empty.setEnabled(False)
        if listing.problems:
            problem = self.my_presets_menu.addAction(i18n_msg('{p0} preset files could not be read; review them in the manager', code='studio.1530fbb4606e0326', p0=len(listing.problems)))
            problem.setEnabled(False)
        self.preset_menu.addSeparator()
        self.preset_menu.addAction(i18n_msg('Manage Presets…', code='studio.e728dcf9078295a9'), self.manage_presets)

    def save_as_preset(self):
        self.refresh()
        if self._draft_errors:
            self._error(i18n_msg('Cannot Save Preset', code='studio.3e13d1a6b98cfbfd'), i18n_msg('Correct the invalid fields first:\n', code='studio.f7dfcbf254ddad12') + i18n_join('\n', self._draft_errors))
            return
        dialog = SavePresetDialog(self.preset_store, self.project, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.rebuild_preset_menu()
            saved = dialog.saved_preset
            self.statusBar().showMessage(i18n_msg('Preset saved: {p0}', code='studio.c825bc2249725e61', p0=saved.name) + (i18n_msg(' (Draft / Incomplete)', code='studio.bcd798341592e388') if saved.incomplete else i18n_msg(' (Not XML-Certified)', code='studio.ca49ec7ca1226495')))

    def manage_presets(self):
        self.refresh()
        if self._draft_errors:
            self._error(i18n_msg('Correct the current fields first', code='studio.a4e9891ad4f837a6'), i18n_join('\n', self._draft_errors))
            return
        dialog = ManagePresetsDialog(self.preset_store, self.project, self)
        dialog.changed.connect(self.rebuild_preset_menu)
        dialog.load_requested.connect(self.apply_preset)
        dialog.exec()
        self.rebuild_preset_menu()

    def import_inp(self):
        path,_=QFileDialog.getOpenFileName(self,i18n_msg('Import Supported INP Settings', code='studio.c81292edbf6efb64'),'',i18n_msg('CP2K (*.inp *.restart);;All Files (*)', code='studio.c2dfd14c0296c58b'))
        if not path:
            return
        try:
            from core.input_import import import_input
            project,warnings=import_input(path)
            if not self._can_leave():
                return
            self.project_path=None;self.dirty=True
            self.load_into_ui(project)
            QMessageBox.information(self,i18n_msg('INP Import Complete', code='studio.34de73496924c727'),i18n_msg('Supported settings were restored. Review them and save as a project.\n\n', code='studio.bf83c5fff371dde6')+i18n_join('\n', warnings))
        except Exception as exc:
            self._error(i18n_msg('INP Import Failed', code='studio.8a5efa5b228fa0cb'),exc)

    def open_xml_settings(self):
        dialog = XMLDialog(self.project.xml_spec, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.set_xml_spec(dialog.selected_path)

    def set_xml_spec(self, path):
        # Validate through the same dialog/service path even for programmatic callers.
        schema = CP2KSchema(path)
        for section in ['GLOBAL', 'FORCE_EVAL/DFT/SCF', 'MOTION/GEO_OPT']:
            schema.section(section)
        self.project.xml_spec = i18n_str(schema.path) if path else None
        self._schema_validator = None
        self._schema_signature = None
        self.edited()
        self.refresh()
        self.statusBar().showMessage(i18n_msg('XML schema updated; subsequent validation will use the selected file', code='studio.edf2d947adf78e23'))

    def validation_service(self, project):
        path = Path(project.xml_spec or BUNDLED_XML).expanduser().resolve()
        signature = (i18n_str(path), file_signatures([path])[i18n_str(path)])
        if self._schema_signature != signature or self._schema_validator is None:
            self._schema_validator = InputValidator(project.xml_spec)
            self._schema_signature = signature
        return self._schema_validator

    def _start_worker(self, callback, finished):
        self._busy = True
        self.export_action.setEnabled(False)
        self.export_panel.set_busy(True)
        worker = Worker(self._revision, callback)
        self._workers.add(worker)
        def done(revision, value, error):
            self._workers.discard(worker)
            self._busy = False
            self.refresh()
            finished(revision, value, error)
        worker.signals.done.connect(done)
        self.pool.start(worker)

    def ready_to_export(self):
        self.refresh()
        if self._busy:
            self._error(i18n_msg('Background Task Still Running', code='studio.5f55a8a20e03c950'), i18n_msg('Wait for validation or export to finish', code='studio.6b5ab7f8d1d55dc6'))
            return False
        if not self._validation.ok:
            self._error(i18n_msg('Cannot Export This Configuration', code='studio.92c4fbdb0e47bd8e'), i18n_join('\n', self._validation.errors))
            return False
        if self._configuration_check_revision == self._revision and self._comprehensive_result:
            checked = self._comprehensive_result.validation
            if checked.errors:
                self._error(i18n_msg('Comprehensive Validation Failed', code='studio.8fa92f9e2d4d76e9'), i18n_join('\n', checked.errors))
                return False
            if checked.warnings:
                self.statusBar().showMessage(i18n_msg('There are {p0} warnings; the actual files will be checked again during export.', code='studio.cb3369b5545f6da3', p0=len(checked.warnings)))
        return True

    def export_inp(self):
        if not self.ready_to_export():
            return
        path, _ = QFileDialog.getSaveFileName(self, i18n_msg('Export CP2K Input', code='studio.a28ffa3b4bd36466'),
            self.project.global_settings.project_name + '.inp', 'CP2K Input (*.inp)')
        if not path:
            return
        if not Path(path).suffix:
            path += '.inp'
            if Path(path).exists() and QMessageBox.question(self, i18n_msg('Overwrite Input File', code='studio.e1657b1e62de9d29'), i18n_msg('Overwrite {p0}?', code='studio.2746f204a01c802c', p0=path),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return
        project = self.project.model_copy(deep=True)
        self.statusBar().showMessage(i18n_msg('Generating, validating, and exporting INP…', code='studio.b2701880f1be6fed'))
        def finished(revision, value, error):
            if error:
                self._error(i18n_msg('INP Export Failed', code='studio.ecac498859c2e71e'), error)
                self.statusBar().showMessage(i18n_msg('INP Export Failed', code='studio.ecac498859c2e71e'))
                return
            self.record_export(value.path)
            dependencies = i18n_join('\n', value.dependencies)
            self.show_export_success(value.path, i18n_msg('Coordinates are embedded in the INP. These dependency files must remain accessible:\n', code='studio.d996dcb969ea459d') + dependencies +
                i18n_msg('\n\nExport a calculation package when moving to another computing environment.', code='studio.d1526f82e8b99974'))
        self._start_worker(lambda: export_input(project, path, overwrite=True), finished)

    def record_export(self, path):
        self.last_export_directory = Path(path).parent
        self.export_panel.directory_button.setEnabled(True)
        self.statusBar().showMessage(i18n_msg('Exported: {p0}', code='studio.5c7ef7224c1de956', p0=path))

    def open_export_directory(self):
        if self.last_export_directory:
            QDesktopServices.openUrl(QUrl.fromLocalFile(i18n_str(self.last_export_directory)))

    def show_export_success(self, path, details):
        box = QMessageBox(self)
        box.setWindowTitle(i18n_msg('Export Complete', code='studio.3e6886d17a1cf43c'))
        box.setText(i18n_msg('Exported:\n{p0}\n\nXML syntax validation passed; no calculation was run.', code='studio.1a87117c3c3dc6ef', p0=path))
        box.setDetailedText(details)
        box.setInformativeText(i18n_msg('Expand the dependency details, or use “Open Export Folder” in step 08.', code='studio.148183c6f2305ffe'))
        open_button = box.addButton(i18n_msg('Open Containing Folder', code='studio.348e2fde4e191226'), QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Ok)
        box.exec()
        if box.clickedButton() == open_button:
            self.open_export_directory()

    def show_bundle_export_success(self, path):
        box = QMessageBox(self)
        box.setWindowTitle(i18n_msg('Export Complete', code='studio.3e6886d17a1cf43c'))
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText(i18n_msg('Exported:\n{p0}', code='studio.4a1fb92e018434dd', p0=path))
        box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse |
                                    Qt.TextInteractionFlag.TextSelectableByKeyboard)
        open_button = box.addButton(i18n_msg('Open Containing Folder', code='studio.348e2fde4e191226'), QMessageBox.ButtonRole.ActionRole)
        ok_button = box.addButton(QMessageBox.StandardButton.Ok)
        set_button_text(ok_button, i18n_msg('OK', code='studio.fac2a67ad87807c4'))
        box.setDefaultButton(ok_button)
        box.setEscapeButton(ok_button)
        box.exec()
        if box.clickedButton() == open_button:
            QDesktopServices.openUrl(QUrl.fromLocalFile(i18n_str(Path(path).resolve().parent)))

    def export(self):
        if not self.ready_to_export():
            return
        format_name, selected = QInputDialog.getItem(self, i18n_msg('Calculation Package Format', code='studio.7c2aa04c4bc126ea'), i18n_msg('Export as:', code='studio.81eadc7355d0cf3b'), [i18n_msg('Folder', code='studio.7c7802d8adaed72e'), i18n_msg('ZIP Archive', code='studio.aeef5e29dcd4d482')], 0, False)
        if not selected:
            return
        archive = format_name == i18n_msg('ZIP Archive', code='studio.aeef5e29dcd4d482')
        parent = QFileDialog.getExistingDirectory(self, i18n_msg('Choose Parent Folder for the Calculation Package', code='studio.1541a806c8a607ba'))
        if not parent:
            return
        name, ok = QInputDialog.getText(self, i18n_msg('Export Calculation Package', code='studio.74a1fb3c37f0f2a1'),
            i18n_msg('ZIP filename (must not already exist):', code='studio.45f313de6bac191c') if archive else i18n_msg('New folder name (must not already exist):', code='studio.efe40b2a65426a0f'), text=self.project.global_settings.project_name)
        if not ok or not name:
            return
        if name in {'.', '..'} or any(c in name for c in '/\\'):
            self._error(i18n_msg('Invalid Folder Name', code='studio.cb65a8eed82eb073'), i18n_msg('Enter a single folder name', code='studio.15aae2216543728f'))
            return
        if archive and not name.lower().endswith('.zip'):
            name += '.zip'
        project = self.project.model_copy(deep=True)
        self.statusBar().showMessage(i18n_msg('Validating and exporting calculation package…', code='studio.e44a9dcdd2b3bab0'))
        def finished(revision, value, error):
            if error:
                self._error(i18n_msg('Export Failed', code='studio.6e4445df69575d79'), error)
                self.statusBar().showMessage(i18n_msg('Export Failed', code='studio.6e4445df69575d79'))
            else:
                self.record_export(value)
                self.show_bundle_export_success(value)
        self._start_worker(lambda: export_bundle(project, Path(parent)/name, archive=archive), finished)

    def show_help(self):
        HelpDialog(self).exec()

    def show_environment_check(self):
        from shiboken6 import isValid
        from ui.environment_dialog import EnvironmentCheckDialog
        dialog=getattr(self,'_environment_dialog',None)
        if dialog is None or not isValid(dialog):
            dialog=EnvironmentCheckDialog(self,config_provider=self.run_panel.config)
            self._environment_dialog=dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def start_local_run(self):
        from ui.local_run_dialog import LocalRunController
        if not hasattr(self, '_local_run_controller'):
            self._local_run_controller = LocalRunController(self, self.local_run_action)
        self._local_run_controller.choose_folder()

    def closeEvent(self, event):
        if self._busy:
            self._error(i18n_msg('Background Task Still Running', code='studio.5f55a8a20e03c950'), i18n_msg('Wait for the current validation or export to finish before closing', code='studio.d3f26170bc076496'))
            event.ignore()
        elif self._can_leave():
            self.timer.stop()
            event.accept()
        else:
            event.ignore()
