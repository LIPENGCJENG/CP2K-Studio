"""Execution-only panel: no process launching or scientific parameter edits."""
from i18n.messages import i18n_msg, i18n_str
from PySide6.QtCore import Signal, Qt, QSignalBlocker
from i18n.qt import QWidget, QLabel, QComboBox, QSpinBox
from ui.widgets.section_card import SectionCard, AdaptiveGrid, page_layout
from core.run_config import RunEnvironment, MAX_PARALLEL, OS_LABELS


class RunEnvironmentPanel(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        layout = page_layout(self)
        title = QLabel(i18n_msg('07 · Runtime Settings', code='studio.94039019f8868e02'))
        title.setObjectName('heading')
        layout.addWidget(title)
        group = SectionCard(i18n_msg('Target Operating System', code='studio.647b20d8b66de930'))
        self.operating_system = QComboBox()
        self.operating_system.setAccessibleName(i18n_msg('Target Operating System', code='studio.647b20d8b66de930'))
        for value, label in OS_LABELS.items():
            self.operating_system.addItem(label, value)
        group.content.addWidget(self.operating_system)
        layout.addWidget(group)
        group = SectionCard(i18n_msg('MPI / OpenMP Settings', code='studio.87218a622e2c2621'))
        form = AdaptiveGrid()
        group.content.addWidget(form)
        self.mpi_processes, self.omp_threads = QSpinBox(), QSpinBox()
        for spin in (self.mpi_processes, self.omp_threads):
            spin.setRange(1, MAX_PARALLEL)
            spin.setMaximumWidth(240)
            spin.setMinimumWidth(180)
        self.mpi_processes.setValue(16)
        self.omp_threads.setValue(1)
        form.add_field(i18n_msg('MPI Processes', code='studio.50867c721b9898fe'), self.mpi_processes)
        form.add_field(i18n_msg('OpenMP Threads per Process', code='studio.2151e9c4f0a07820'), self.omp_threads)
        layout.addWidget(group)
        group = SectionCard(i18n_msg('Logical Execution Slots', code='studio.77f1e559989ef41f'), i18n_msg('MPI × OpenMP; this is not the physical core count and does not allocate resources.', code='studio.f37272c3d72c4a4a'))
        form = AdaptiveGrid()
        group.content.addWidget(form)
        self.cpu_slots, self.mode = QLabel(), QLabel()
        self.cpu_slots.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.add_field(i18n_msg('Required Logical Cores', code='studio.10d9ce32248249c0'), self.cpu_slots)
        form.add_field(i18n_msg('Execution Mode', code='studio.f6c67c56f2637ff4'), self.mode)
        layout.addWidget(group)
        self.platform_note = QLabel()
        self.platform_note.setWordWrap(True)
        layout.addWidget(self.platform_note)
        hint = QLabel(i18n_msg('The target environment must provide mpirun and cp2k.psmp on PATH with compatible MPI implementations.', code='studio.c3a93b0864d416e9'))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch()
        self.operating_system.currentIndexChanged.connect(self._edited)
        self.mpi_processes.valueChanged.connect(self._edited)
        self.omp_threads.valueChanged.connect(self._edited)
        self.update_derived()

    def config(self):
        return RunEnvironment(operating_system=self.operating_system.currentData(),
            mpi_processes=self.mpi_processes.value(), omp_threads=self.omp_threads.value())

    def _edited(self, *_):
        self.update_derived()
        self.changed.emit()

    def update_derived(self):
        config = self.config()
        self.cpu_slots.setText(i18n_str(config.required_cpu_slots))
        self.mode.setText(config.mode_label)
        if config.operating_system == 'linux':
            self.platform_note.setText('')
        else:
            self.platform_note.setText(i18n_msg('Windows / WSL2: run bash run.sh in the WSL2 Linux terminal; Bash commands do not run directly in native PowerShell.', code='studio.f0bf6628232e46da')
                if config.operating_system == 'wsl2' else i18n_msg('{p0}: enter the package folder in a Bash terminal and run bash run.sh.', code='studio.92d64f06f8ed50d9', p0=config.os_label))
        self.platform_note.setVisible(config.operating_system != 'linux')

    def load(self, data):
        config = RunEnvironment.model_validate(data.get('run_environment', {}))
        widgets = (self.operating_system, self.mpi_processes, self.omp_threads)
        blockers = [QSignalBlocker(w) for w in widgets]
        self.operating_system.setCurrentIndex(self.operating_system.findData(config.operating_system))
        self.mpi_processes.setValue(config.mpi_processes)
        self.omp_threads.setValue(config.omp_threads)
        del blockers
        self.update_derived()

    def collect(self, data):
        try:
            data['run_environment'] = self.config().model_dump()
            return []
        except ValueError as exc:
            return [i18n_msg('run_environment: {p0}', p0=exc)]
