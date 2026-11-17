"""Four AIMD cards, using the existing model-backed scientific form fields."""
from copy import deepcopy
import math
from i18n.messages import i18n_msg
from i18n.qt import QLabel, QHBoxLayout, QPushButton, QFileDialog
from ui.forms import FormPanel
from core.models import MDConfig


class MDPanel(FormPanel):
    def __init__(self):
        super().__init__(i18n_msg('06 · Molecular Dynamics', code='md.page_title'))
        self.layout.removeItem(self.form)
        basic = self.section(i18n_msg('MD Basic Settings', code='md.basic_title'), help_text=i18n_msg(
            'Born–Oppenheimer AIMD uses the existing Quickstep DFT forces. NVT maintains constant temperature and volume; NVE conserves energy. TIMESTEP is in fs; test timestep convergence, especially for hydrogen and fast vibrations. TEMPERATURE is the NVT target, or initializes velocities in NVE when none are supplied. NVE is not continuously thermostatted. STEPS counts additional steps from the restart counter.', code='md.basic_help'))
        self.ensemble = self.add('md.ensemble', i18n_msg('ENSEMBLE', code='md.ensemble_label'), 'choice', ['NVT', 'NVE'])
        self.ensemble.setItemText(0, i18n_msg('NVT — Constant T & V', code='md.nvt'))
        self.ensemble.setItemText(1, i18n_msg('NVE — Constant Energy', code='md.nve'))
        self.steps = self.add('md.steps', i18n_msg('STEPS', code='md.steps_label'), 'int')
        self.timestep = self.add('md.timestep', i18n_msg('TIMESTEP', code='md.timestep_label'), 'float', unit='fs')
        self.add('md.temperature', i18n_msg('TEMPERATURE', code='md.temperature_label'), 'float', unit='K')
        initialization = self.add('md.initialization_method', 'INITIALIZATION_METHOD', 'choice', ['DEFAULT'])
        initialization.setEnabled(False)
        self.total_time = QLabel()
        self.total_time.setObjectName('muted')
        self.total_time.setWordWrap(True)
        basic.content.addWidget(self.total_time)
        self.steps.textChanged.connect(self.update_time)
        self.timestep.textChanged.connect(self.update_time)
        self.thermostat_card = self.section(i18n_msg('Thermostat Settings', code='md.thermostat_title'), help_text=i18n_msg(
            'CSVR is used only for NVT. TIMECON is the coupling time in fs; excessively short coupling may perturb dynamics. NVE generates no thermostat. Switching ensemble preserves TIMECON.', code='md.thermostat_help'))
        thermostat = self.add('md.thermostat_type', i18n_msg('THERMOSTAT TYPE', code='md.thermostat_type'), 'choice', ['CSVR'])
        thermostat.setEnabled(False)
        self.timecon = self.add('md.timecon', 'CSVR / TIMECON', 'float', unit='fs')
        self.section(i18n_msg('Trajectory & Output', code='md.output_title'), help_text=i18n_msg(
            'Trajectory files are generated only by CP2K. EXTXYZ preserves cell information for periodic systems. The energy file records MD step/time, temperature, kinetic and potential energies and the conserved quantity. Studio does not run dynamics or append previous trajectories.', code='md.output_help'))
        self.write_trajectory = self.add('md.write_trajectory', i18n_msg('Write Trajectory', code='md.write_trajectory'), 'bool', inline=True)
        self.trajectory_format = self.add('md.trajectory_format', i18n_msg('Trajectory Format', code='md.trajectory_format'), 'choice', ['XYZ', 'EXTXYZ'])
        self.trajectory_interval = self.add('md.trajectory_interval', i18n_msg('Trajectory Interval', code='md.trajectory_interval'), 'int', unit=i18n_msg('steps', code='md.steps_unit'))
        restart_card = self.section(i18n_msg('Restart Settings', code='md.restart_title'), help_text=i18n_msg(
            'MD restart is separate from WFN restart. Continuation requires matching atom/KIND order and cell, positions, velocities and counters; NVT also requires GLOBAL CSVR energy and RNG state. Self-contained text .restart files are supported. SCF_GUESS is unchanged. Static checks do not prove physical continuity; verify the resumed trajectory and electronic settings. The package copies the source under data/ and never overwrites it.', code='md.restart_help'))
        self.write_restart = self.add('md.write_restart', i18n_msg('Write Restart', code='md.write_restart'), 'bool', inline=True)
        self.restart_interval = self.add('md.restart_interval', i18n_msg('Restart Interval', code='md.restart_interval'), 'int', unit=i18n_msg('steps', code='md.steps_unit'))
        self.backups = self.add('md.backup_copies', i18n_msg('Backup Copies', code='md.backup_copies'), 'int')
        self.continue_restart = self.add('md.continue_from_restart', i18n_msg('Continue from Restart', code='md.continue'), 'bool', inline=True)
        row = QHBoxLayout()
        self.restart_file = self.add('md.restart_file', None, 'text', control_layout=row)
        self.restart_file.setPlaceholderText(i18n_msg('Select a complete MD .restart file', code='md.restart_placeholder'))
        self.browse = QPushButton(i18n_msg('Choose Restart…', code='md.choose_restart'))
        self.browse.clicked.connect(self.choose_restart)
        row.addWidget(self.browse)
        restart_card.content.addLayout(row)
        for control in [self.ensemble, self.write_trajectory, self.write_restart, self.continue_restart]:
            signal = control.currentIndexChanged if control is self.ensemble else control.toggled
            signal.connect(self.update_enabled)
        self.layout.addStretch()
        self.update_enabled()
        self.update_time()

    def choose_restart(self):
        path, _ = QFileDialog.getOpenFileName(self, i18n_msg('Choose MD Restart', code='md.choose_restart_title'),
            self.restart_file.text(), i18n_msg('CP2K Restart (*.restart);;All Files (*)', code='md.restart_filter'))
        if path:
            self.restart_file.setText(path)

    def update_time(self, *_):
        try:
            steps, timestep = int(self.steps.text()), float(self.timestep.text())
            total = steps * timestep / 1000
            if steps <= 0 or timestep <= 0 or not math.isfinite(total):
                raise ValueError()
            self.total_time.setText(i18n_msg('Total Simulation Time: {time} ps', code='md.total_time', time=f'{total:.3f}'))
        except (ValueError, OverflowError):
            self.total_time.setText(i18n_msg('Total Simulation Time: —', code='md.total_time_invalid'))

    def update_enabled(self, *_):
        self.thermostat_card.setEnabled(self.ensemble.currentData() == 'NVT')
        for field in [self.trajectory_format, self.trajectory_interval]:
            field.setEnabled(self.write_trajectory.isChecked())
        for field in [self.restart_interval, self.backups]:
            field.setEnabled(self.write_restart.isChecked())
        for field in [self.restart_file, self.browse]:
            field.setEnabled(self.continue_restart.isChecked())

    def load(self, data):
        super().load(data)
        self.update_enabled()
        self.update_time()

    def collect(self, data, paths=None):
        inactive = set()
        if self.ensemble.currentData() == 'NVE':
            inactive.add('md.timecon')
        if not self.write_trajectory.isChecked():
            inactive.update(['md.trajectory_format', 'md.trajectory_interval'])
        if not self.write_restart.isChecked():
            inactive.update(['md.restart_interval', 'md.backup_copies'])
        if not self.continue_restart.isChecked():
            inactive.add('md.restart_file')
        # Valid disabled drafts survive toggles; invalid disabled drafts do not
        # block a different ensemble/output mode.
        for path in inactive:
            candidate = dict(data)
            candidate['md'] = deepcopy(data['md'])
            if not super().collect(candidate, {path}):
                try:
                    MDConfig.model_validate(candidate['md'])
                    data['md'][path.split('.')[1]] = candidate['md'][path.split('.')[1]]
                except ValueError:
                    pass
        return super().collect(data, set(self.fields) - inactive)
