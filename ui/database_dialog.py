"""Local database source management. Networking happens only on button click."""
from i18n.messages import i18n_msg, i18n_str, i18n_join
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool
from i18n.qt import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,
    QTableWidget,QTableWidgetItem,QHeaderView,QComboBox,QFileDialog,QDialogButtonBox,QPlainTextEdit,QCheckBox,QMessageBox)
from core.models import DatabaseSettings,CustomDatabase
from core.database_manager import scan_databases, download_official_data


class DownloadSignals(QObject):
    done = Signal(object)


class Download(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals=DownloadSignals()

    def run(self):
        try:
            download_official_data()
            error=''
        except Exception as exc:
            error=i18n_str(exc)
        self.signals.done.emit(error)


class DatabaseDialog(QDialog):
    def __init__(self,settings,parent=None):
        super().__init__(parent)
        self.settings=settings.model_copy(deep=True)
        self.setWindowTitle(i18n_msg('Database Manager · CP2K 2026.1', code='studio.e09840682cd491bd'))
        self.resize(1100,670)
        layout=QVBoxLayout(self)
        note=QLabel(i18n_msg('Priority: specified folder → local installation → verified official cache. Unknown or different versions are never mixed silently.\nThe bundled cache is from official v2026.1; startup does not access the network. A user-declared version is not official certification.', code='studio.f66b15184e610044'))
        note.setWordWrap(True)
        layout.addWidget(note)
        row=QHBoxLayout()
        self.directory=QLineEdit(self.settings.data_directory)
        self.directory.setPlaceholderText(i18n_msg('CP2K data folder (leave empty for local discovery and the official cache)', code='studio.6d7dd1c1cd1e8add'))
        row.addWidget(self.directory)
        browse=QPushButton(i18n_msg('Browse Folder…', code='studio.e7f468a900163753'));browse.clicked.connect(self.browse)
        row.addWidget(browse)
        self.version=QComboBox();self.version.addItems([i18n_msg('Not declared', code='studio.524a0bd8be900fcf'),'2026.1','2025.2'])
        self.version.setCurrentText(self.settings.declared_version or i18n_msg('Not declared', code='studio.524a0bd8be900fcf'))
        self.version.setToolTip(i18n_msg('Declare the version explicitly if no manifest or official fingerprint identifies it; this produces a Warning', code='studio.05a15885f61ad974'))
        row.addWidget(self.version)
        layout.addLayout(row)
        row=QHBoxLayout()
        scan=QPushButton(i18n_msg('Rescan', code='studio.daf5103f90cc7d3a'));scan.clicked.connect(self.rescan);row.addWidget(scan)
        self.download=QPushButton(i18n_msg('Get Official 2026.1 Data', code='studio.2e29276b7336ba30'));self.download.clicked.connect(self.fetch)
        row.addWidget(self.download);layout.addLayout(row)
        self.table=QTableWidget(0,6)
        self.table.setHorizontalHeaderLabels([i18n_msg('Status', code='studio.6320b4a8722a851f'),i18n_msg('Type', code='studio.ba40014ff496f64e'),i18n_msg('Source / CP2K Version', code='studio.c6a64b78b6f8ce82'),i18n_msg('File Path', code='studio.c71200b5952e3781'),i18n_msg('Entries', code='studio.860082f1436f1ecc'),i18n_msg('Description', code='studio.4262c45dc797bb0c')])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        self.details=QPlainTextEdit();self.details.setReadOnly(True);self.details.setMaximumHeight(120)
        layout.addWidget(self.details)
        self.table.itemSelectionChanged.connect(self.show_details)
        self.advanced=QCheckBox(i18n_msg('Advanced: explicitly add custom files (user-declared version)', code='studio.e527613ccf080158'))
        layout.addWidget(self.advanced)
        self.extra=QDialogButtonBox()
        for category,label in [('basis',i18n_msg('Add Custom Basis Set…', code='studio.d3385bff4858c436')),('potential',i18n_msg('Add Custom Pseudopotential…', code='studio.7c9068cfbaf9b93c'))]:
            button=self.extra.addButton(label,QDialogButtonBox.ButtonRole.ActionRole)
            button.clicked.connect(lambda checked=False,c=category:self.add_custom(c))
        self.extra.setVisible(False)
        self.advanced.toggled.connect(self.extra.setVisible)
        layout.addWidget(self.extra)
        self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept);self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.worker=None
        self.rescan()

    def show_details(self):
        row=self.table.currentRow()
        if 0<=row<len(self.catalog.statuses):
            status=self.catalog.statuses[row]
            self.details.setPlainText(i18n_msg('{p0}\n{p1} · CP2K {p2}\nSHA256 {p3}\n{p4}', p0=status.path, p1=status.source, p2=status.version or i18n_msg('Unknown', code='studio.4d8c1c5b42830791'), p3=status.sha256 or i18n_msg('Not read', code='studio.3b3307980018c0c4'), p4=status.detail))

    def browse(self):
        value=QFileDialog.getExistingDirectory(self,i18n_msg('Choose CP2K Data Folder', code='studio.e6d3b78d75637d43'))
        if value:
            self.directory.setText(value);self.rescan()

    def rescan(self):
        self.settings.data_directory=self.directory.text().strip()
        self.settings.declared_version='' if self.version.currentIndex()==0 else self.version.currentText()
        self.catalog=scan_databases(self.settings)
        self.table.setRowCount(len(self.catalog.statuses))
        from PySide6.QtCore import Qt
        for row,status in enumerate(self.catalog.statuses):
            for col,value in enumerate([status.state,status.category,i18n_msg('{p0} / {p1}', p0=status.source, p1=status.version or i18n_msg('Unknown', code='studio.4d8c1c5b42830791')),status.path,status.entries,status.detail]):
                item=QTableWidgetItem(i18n_str(value));item.setToolTip(i18n_str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row,col,item)
        self.details.setPlainText(i18n_join('\n', self.catalog.conflicts) or i18n_msg('No same-element, same-name entries with conflicting contents were found.', code='studio.ec3edaec6058e8d9'))

    def add_custom(self,category):
        paths,_=QFileDialog.getOpenFileNames(self,i18n_msg('Choose Custom CP2K Data Files', code='studio.2df9a7ae05bf73d1'))
        if paths:
            self.settings.custom_files += [CustomDatabase(path=p,category=category,version='2026.1') for p in paths]
            self.rescan()

    def fetch(self):
        if self.worker:
            return
        self.download.setEnabled(False)
        self.download.setText(i18n_msg('Verifying and fetching official data…', code='studio.b288a6b36f6844dc'))
        self.worker=Download()
        self.worker.signals.done.connect(self.fetched)
        QThreadPool.globalInstance().start(self.worker)

    def fetched(self,error):
        self.worker=None
        self.download.setEnabled(True);self.download.setText(i18n_msg('Get Official 2026.1 Data', code='studio.2e29276b7336ba30'))
        if error:
            QMessageBox.warning(self,i18n_msg('Fetch Failed; Existing Data Preserved', code='studio.0723847bee37d038'),error)
        self.rescan()

    def accept(self):
        if not self.worker:
            self.rescan();super().accept()

    def reject(self):
        if not self.worker:
            super().reject()

    def closeEvent(self,event):
        event.ignore() if self.worker else super().closeEvent(event)
