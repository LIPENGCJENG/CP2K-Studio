"""Modeless, cancellable local inspection; no project fields are collected."""
import threading
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, QTimer, Qt, Slot
from i18n.qt import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit, QApplication
from i18n.messages import i18n_msg
from i18n.language_manager import language_manager
from core.environment_check import EnvironmentDetector, EnvironmentReport, CheckItem, SUMMARY
from core.run_config import RunEnvironment


def failed_report():
    return EnvironmentReport(items=[CheckItem('cp2k','detector.failed',
        i18n_msg('Environment Check',code='env.button'),'unknown',
        i18n_msg('Inspection could not be completed. Recheck or copy the partial report.',code='env.worker_failed'))])


class ProbeSignals(QObject):
    progress = Signal(int, object)
    finished = Signal(int, object)


class ProbeWorker(QRunnable):
    def __init__(self, generation, detector, cancel):
        super().__init__()
        self.generation, self.detector, self.cancel = generation, detector, cancel
        self.signals = ProbeSignals()

    def run(self):
        try:
            result = self.detector.run(lambda text: self.signals.progress.emit(self.generation, text))
        except Exception:
            result = failed_report()
        self.signals.finished.emit(self.generation,result)


class EnvironmentCheckDialog(QDialog):
    def __init__(self, parent=None, *, config_provider=None, detector_factory=EnvironmentDetector):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle(i18n_msg('Environment Check',code='env.button'))
        self.resize(780,650)
        self.setMinimumSize(460,320)
        if self.screen():
            area=self.screen().availableGeometry()
            self.resize(min(780,max(460,area.width()-60)),min(650,max(320,area.height()-80)))
        self.config_provider=config_provider or (lambda: RunEnvironment())
        self.detector_factory=detector_factory
        self.report=None
        self._generation=0
        self._cancel=None
        self._workers={}
        self._running=False
        self._closed=False
        layout=QVBoxLayout(self)
        layout.setContentsMargins(20,20,20,20)
        layout.setSpacing(12)
        heading=QLabel(i18n_msg('Environment Check',code='env.button'))
        heading.setObjectName('heading')
        layout.addWidget(heading)
        self.summary=QLabel(i18n_msg('Checking environment…',code='env.checking'))
        self.summary.setWordWrap(True)
        self.summary.setObjectName('cardTitle')
        layout.addWidget(self.summary)
        self.progress=QLabel()
        self.progress.setObjectName('muted')
        self.progress.setWordWrap(True)
        layout.addWidget(self.progress)
        self.output=QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.output,1)
        controls=QHBoxLayout()
        self.recheck=QPushButton(i18n_msg('Recheck',code='env.recheck'))
        self.copy=QPushButton(i18n_msg('Copy Report',code='env.copy'))
        self.close_button=QPushButton(i18n_msg('Close',code='env.close'))
        self.copy.setEnabled(False)
        controls.addWidget(self.recheck)
        controls.addWidget(self.copy)
        controls.addStretch()
        controls.addWidget(self.close_button)
        layout.addLayout(controls)
        self.recheck.clicked.connect(self.start_check)
        self.copy.clicked.connect(self.copy_report)
        self.close_button.clicked.connect(self.close)
        language_manager().callback(self,'environment-report',lambda dialog: dialog.render_report())
        self._auto_start=QTimer(self)
        self._auto_start.setSingleShot(True)
        self._auto_start.timeout.connect(self.start_check)
        self._auto_start.start(0)

    @Slot()
    def start_check(self):
        if self._running or self._closed:return
        self._generation+=1
        self._running=True
        self.recheck.setEnabled(False)
        self.summary.setText(i18n_msg('Checking environment…',code='env.checking'))
        self.progress.setText(i18n_msg('Inspecting this computer without changing calculation settings.',code='env.readonly'))
        cancel=threading.Event()
        self._cancel=cancel
        # Snapshot on the GUI thread; the worker never reads any project/widget.
        try:
            config=self.config_provider().model_copy(deep=True)
            detector=self.detector_factory(config,cancel=cancel)
        except Exception:
            self.on_finished(self._generation,failed_report())
            return
        worker=ProbeWorker(self._generation,detector,cancel)
        self._workers[self._generation]=worker
        self.destroyed.connect(lambda _=None, token=cancel: token.set())
        worker.signals.progress.connect(self.on_progress)
        worker.signals.finished.connect(self.on_finished)
        QThreadPool.globalInstance().start(worker)

    @Slot(int,object)
    def on_progress(self,generation,text):
        if generation==self._generation:
            self.progress.setText(text)

    @Slot(int,object)
    def on_finished(self,generation,result):
        self._workers.pop(generation,None)
        if generation!=self._generation:return
        self._running=False
        self.report=result
        self.recheck.setEnabled(True)
        self.copy.setEnabled(True)
        self.progress.setText(i18n_msg('Inspection finished. No calculation was run.',code='env.finished'))
        self.render_report()

    def render_report(self):
        if self.report is None:return
        if not self._running:
            self.summary.setText(SUMMARY[self.report.summary])
        scrollbar=self.output.verticalScrollBar()
        position=scrollbar.value()
        self.output.setPlainText(self.report.text())
        scrollbar.setValue(position)

    def copy_report(self):
        if self.report:
            QApplication.clipboard().setText(self.report.text())
            self.progress.setText(i18n_msg('Report copied to clipboard.',code='env.copied'))

    def closeEvent(self,event):
        self._closed=True
        self._auto_start.stop()
        self._generation+=1
        if self._cancel:self._cancel.set()
        super().closeEvent(event)

    def reject(self):
        self._closed=True
        self._auto_start.stop()
        if self._cancel:self._cancel.set()
        super().reject()
