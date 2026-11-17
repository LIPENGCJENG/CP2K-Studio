"""Local Run is a tool, independent of project state and project workers."""
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot, Qt
from shiboken6 import isValid
from i18n.qt import (QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
                     QFileDialog, QMessageBox, QSizePolicy)
from i18n.messages import i18n_msg, i18n_str
from core.local_run import LocalRunBackend


class LocalRunConfirmation(QDialog):
    def __init__(self, package, parent=None):
        super().__init__(parent)
        self.setWindowTitle(i18n_msg('Local Run', code='local.button'))
        self.resize(540, 340)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        heading = QLabel(i18n_msg('Local Run', code='local.button'))
        heading.setObjectName('heading')
        layout.addWidget(heading)
        for title, text in [
            (i18n_msg('Calculation Directory', code='local.directory'), str(package.directory)),
            (i18n_msg('Run Command', code='local.command'), 'bash run.sh'),
            (i18n_msg('Output Monitor', code='local.output_monitor'),
             i18n_msg('Follow output.out (equivalent to tail -n 30 -F).', code='local.follow')),
        ]:
            caption = QLabel(title)
            caption.setObjectName('cardTitle')
            layout.addWidget(caption)
            value = QLabel(text)
            value.setTextFormat(Qt.TextFormat.PlainText)
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            layout.addWidget(value)
        note = QLabel(i18n_msg('This executes the selected run.sh on your computer. Only run packages you created or trust.', code='local.trust'))
        note.setWordWrap(True)
        layout.addWidget(note)
        if package.old_output:
            old = QLabel(i18n_msg('Existing output.out is retained. Unchanged old content will be skipped by the monitor; run.sh itself may overwrite results.', code='local.old_output'))
            old.setWordWrap(True)
            old.setObjectName('muted')
            layout.addWidget(old)
        if package.previous_uncertain:
            warning = QLabel(i18n_msg('A previous launch has no confirmed exit status. Check existing terminals and processes before running again. Manually started jobs cannot be detected reliably.', code='local.uncertain'))
            warning.setWordWrap(True)
            layout.addWidget(warning)
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.cancel_button = QPushButton(i18n_msg('Cancel', code='local.cancel'))
        self.run_button = QPushButton(i18n_msg('Run', code='local.run'))
        self.run_button.setObjectName('primary')
        # Enter must not accidentally execute a package while reading the dialog.
        self.cancel_button.setDefault(True)
        self.run_button.setAutoDefault(False)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.run_button)
        layout.addLayout(buttons)
        self.cancel_button.clicked.connect(self.reject)
        self.run_button.clicked.connect(self.accept)
        self.adjustSize()


class LaunchSignals(QObject):
    finished = Signal(object, object)


class LaunchWorker(QRunnable):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.signals = LaunchSignals()

    def run(self):
        try:
            result, error = self.callback(), None
        except Exception as exc:
            result, error = None, i18n_str(exc)
        self.signals.finished.emit(result, error)


class LocalRunController(QObject):
    def __init__(self, parent, action, *, backend=None):
        super().__init__(parent)
        self.action = action
        self.backend = backend or LocalRunBackend()
        self.busy = False
        self._worker = None

    def _set_busy(self, value):
        self.busy = value
        self.action.setEnabled(not value)

    def choose_folder(self):
        if self.busy:
            return
        self._set_busy(True)
        directory = QFileDialog.getExistingDirectory(self.parent(),
            i18n_msg('Select Calculation Folder', code='local.select_folder'))
        if not isValid(self):
            return
        if not directory:
            self._set_busy(False)
            return
        self._start(lambda: self.backend.inspect(directory), self._inspected)

    def _start(self, callback, handler):
        worker = LaunchWorker(callback)
        self._worker = worker
        worker.signals.finished.connect(handler)
        # This pool and the system terminals are not owned by MainWindow's
        # project worker. Closing Studio never sends a stop signal to run.sh.
        QThreadPool.globalInstance().start(worker)

    def _message(self, title, text, warning=False):
        box = QMessageBox(self.parent())
        box.setWindowTitle(title)
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText(text)
        box.setIcon(QMessageBox.Icon.Warning if warning else QMessageBox.Icon.Information)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.exec()

    @Slot(object, object)
    def _inspected(self, package, error):
        self._worker = None
        if error is not None:
            self._set_busy(False)
            self._message(i18n_msg('Cannot Start Local Run', code='local.cannot_start'), error, True)
            return
        dialog = LocalRunConfirmation(package, self.parent())
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        if not isValid(self):
            return
        if not accepted:
            self._set_busy(False)
            return
        self._start(lambda: self.backend.launch(package, confirmed=True), self._launched)

    @Slot(object, object)
    def _launched(self, result, error):
        self._worker = None
        self._set_busy(False)
        if error is not None:
            self._message(i18n_msg('Cannot Start Local Run', code='local.cannot_start'), error, True)
            return
        if result.monitor_error:
            text = i18n_msg('The calculation terminal was opened, but the output monitor could not be opened: {error}\n\nThe script may already be running. Check the calculation terminal; do not start it again just to open a monitor.', code='local.partial', error=result.monitor_error)
        elif result.script_started:
            text = i18n_msg('run.sh started in the calculation terminal. A separate terminal follows output.out. Startup does not confirm CP2K success; inspect the script exit code and logs. Closing the monitor or Studio does not stop the calculation.', code='local.started')
        else:
            text = i18n_msg('Terminal launch requests were sent, but script startup has not been confirmed. Check both terminals before retrying. Terminal startup is not proof of CP2K success.', code='local.unconfirmed')
        self._message(i18n_msg('Local Run', code='local.button'), text,
                      bool(result.monitor_error) or not result.script_started)
