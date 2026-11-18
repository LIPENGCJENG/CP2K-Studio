"""One native run configuration, with asynchronous EXE/DLL validation."""
from dataclasses import replace
from pathlib import Path
from PySide6.QtCore import Qt, QThreadPool, Slot
from i18n.qt import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QPushButton, QSpinBox, QFileDialog, QScrollArea, QWidget, QFrame)
from i18n.messages import i18n_msg
from core.windows_run_config import WindowsRunSettings, guess_dll_directory


class WindowsLocalRunDialog(QDialog):
    def __init__(self, package, backend, parent=None):
        super().__init__(parent)
        self.backend, self.package, self.launch_package = backend, package, None
        self._closed = False
        self._worker = None
        self._accept_after_check = False
        self.setWindowTitle(i18n_msg('Local Run', code='local.button'))
        self.resize(650, 580)
        if self.screen():
            area=self.screen().availableGeometry()
            self.resize(min(650,area.width()-60),min(580,area.height()-80))
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24,20,24,20)
        outer.setSpacing(12)
        heading = QLabel(i18n_msg('Local Run', code='local.button'))
        heading.setObjectName('heading'); outer.addWidget(heading)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body=QWidget();layout=QVBoxLayout(body);layout.setContentsMargins(0,0,0,0);layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(body);outer.addWidget(scroll,1)
        form = QFormLayout()
        form.setSpacing(10)
        directory = QLabel(str(package.directory))
        directory.setTextFormat(Qt.TextFormat.PlainText)
        directory.setWordWrap(True)
        directory.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow(i18n_msg('Calculation Folder', code='winrun.folder'), directory)
        self.executable = QLineEdit(package.settings.executable)
        self.dll_directory = QLineEdit(package.settings.dll_directory)
        self.browse_exe = QPushButton(i18n_msg('Browse…', code='winrun.browse'))
        self.browse_dll = QPushButton(i18n_msg('Browse…', code='winrun.browse'))
        for caption, field, button in [
            (i18n_msg('CP2K Executable', code='winrun.executable'), self.executable, self.browse_exe),
            (i18n_msg('Runtime DLL Directory', code='winrun.dll_directory'), self.dll_directory, self.browse_dll)]:
            row = QHBoxLayout(); row.addWidget(field,1); row.addWidget(button)
            form.addRow(caption, row)
        self.mode = QLabel(i18n_msg('Windows Native / Serial or OpenMP', code='winrun.mode'))
        if package.checked:
            self._show_mode(package.checked.mode)
        form.addRow(i18n_msg('Execution Mode', code='winrun.execution_mode'), self.mode)
        self.threads = QSpinBox(); self.threads.setRange(1, 2147483647)
        self.threads.setValue(package.settings.omp_threads)
        form.addRow(i18n_msg('OpenMP Threads', code='winrun.threads'), self.threads)
        form.addRow(i18n_msg('Output File', code='winrun.output'), QLabel('output.out'))
        layout.addLayout(form)
        self.status = QLabel()
        self.status.setTextFormat(Qt.TextFormat.PlainText); self.status.setWordWrap(True)
        self.status.setText(package.error or (i18n_msg('Verified CP2K {version} · {mode}', code='winrun.verified', version=package.checked.version, mode=package.checked.mode) if package.checked else
            i18n_msg('Choose CP2K. Start Calculation checks --version and its runtime DLLs before launching.', code='winrun.choose_exe')))
        layout.addWidget(self.status)
        note = QLabel(i18n_msg('This run uses one native CP2K process and the threads shown above. Exported MPI/run.sh settings are not used or changed. Serial builds require 1 thread. Only run packages you trust.', code='winrun.run_scope'))
        note.setWordWrap(True); layout.addWidget(note)
        if package.old_output or package.previous_uncertain:
            warning = QLabel(i18n_msg('Existing output.out may be overwritten by CP2K; other restart/trajectory outputs may also be written by the selected input. Studio does not delete or back up results. Check any previous terminals before starting. Cancel to preserve the folder.', code='winrun.old_output'))
            warning.setWordWrap(True); layout.addWidget(warning)
        buttons = QHBoxLayout(); buttons.addStretch()
        self.cancel_button = QPushButton(i18n_msg('Cancel', code='local.cancel'))
        self.start_button = QPushButton(i18n_msg('Start Calculation', code='winrun.start'))
        self.start_button.setObjectName('primary')
        self.cancel_button.setDefault(True); self.start_button.setAutoDefault(False)
        buttons.addWidget(self.cancel_button); buttons.addWidget(self.start_button); outer.addLayout(buttons)
        self.browse_exe.clicked.connect(self.choose_executable)
        self.browse_dll.clicked.connect(self.choose_dll)
        self.cancel_button.clicked.connect(self.reject)
        self.start_button.clicked.connect(self.validate_and_accept)
        self.executable.textEdited.connect(self.invalidate_check)
        self.dll_directory.textEdited.connect(self.invalidate_check)

    def _show_mode(self, mode):
        label=i18n_msg('Serial',code='env.build_serial') if mode=='Serial' else mode
        self.mode.setText(i18n_msg('Windows Native / {mode}',code='winrun.native_mode',mode=label))

    def invalidate_check(self):
        self.mode.setText(i18n_msg('Windows Native / Serial or OpenMP', code='winrun.mode'))
        self.status.setText(i18n_msg('Start Calculation will verify this EXE and its runtime before launching.', code='winrun.recheck_exe'))

    def choose_executable(self):
        path, _ = QFileDialog.getOpenFileName(self, i18n_msg('Browse CP2K Executable…', code='winrun.browse_executable'),
            self.executable.text(), i18n_msg('Windows Executable (*.exe)', code='winrun.exe_filter'))
        if path:
            self.executable.setText(path)
            if not self.dll_directory.text():
                self.dll_directory.setText(guess_dll_directory(path))
            self.status.setText(i18n_msg('Start Calculation will verify this EXE and its runtime before launching.', code='winrun.recheck_exe'))
            self._validate(False)

    def choose_dll(self):
        path = QFileDialog.getExistingDirectory(self, i18n_msg('Runtime DLL Directory', code='winrun.dll_directory'), self.dll_directory.text())
        if path:
            self.dll_directory.setText(path)

    def _set_checking(self, value):
        for widget in [self.executable,self.dll_directory,self.browse_exe,self.browse_dll,self.threads,self.start_button]:
            widget.setEnabled(not value)

    def validate_and_accept(self):
        self._validate(True)

    def _validate(self, accept_after):
        from ui.local_run_dialog import LaunchWorker
        self._accept_after_check = accept_after
        settings = WindowsRunSettings(self.executable.text(), self.dll_directory.text(), self.threads.value())
        self._set_checking(True)
        self.status.setText(i18n_msg('Checking CP2K --version and runtime DLL loading…', code='winrun.checking'))
        backend, directory = self.backend, self.package.directory
        # The worker must not read a Qt object after the user closes this dialog.
        worker = LaunchWorker(lambda: backend.prepare(directory, settings))
        self._worker = worker
        worker.signals.finished.connect(self.validated)
        QThreadPool.globalInstance().start(worker)

    @Slot(object, object)
    def validated(self, package, error):
        self._worker = None
        if self._closed:
            return
        self._set_checking(False)
        if error is not None:
            self.status.setText(error)
            return
        self.status.setText(i18n_msg('Verified CP2K {version} · {mode}', code='winrun.verified', version=package.checked.version, mode=package.checked.mode))
        self._show_mode(package.checked.mode)
        if not self._accept_after_check:
            return
        if package.old_output and not self.package.old_output:
            # A new log appeared while the dialog was open: obtain a fresh
            # confirmation rather than accepting a warning the user never saw.
            self.package = package
            self.status.setText(i18n_msg('output.out appeared while configuring this run. CP2K may overwrite it. Click Start Calculation again to confirm, or Cancel.', code='winrun.log_appeared'))
            return
        self.launch_package = package
        self.accept()

    def reject(self):
        self._closed = True
        super().reject()

    def closeEvent(self, event):
        self._closed = True
        super().closeEvent(event)
