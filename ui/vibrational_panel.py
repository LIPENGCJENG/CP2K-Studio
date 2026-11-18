"""Step 06 reuses existing forms and preserves independent task drafts."""
from copy import deepcopy
from PySide6.QtCore import Signal, Qt, QEvent
from PySide6.QtGui import QTextLayout, QTextOption
from i18n.messages import i18n_msg, i18n_render
from i18n.language_manager import language_manager
from i18n.qt import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel, QSizePolicy, QStyleOptionButton, QStyle
from ui.forms import FormPanel
from ui.widgets.help_icon import HelpIcon, attach_field_help
from ui.theme import COLORS
from core.models import MotionConfig, VibrationalConfig, CellOptimizationConfig, MDConfig, LINRES_PRECONDITIONERS
from ui.cell_opt_panel import CellOptimizationPanel
from ui.md_panel import MDPanel


class VibrationalPanel(FormPanel):
    def __init__(self):
        super().__init__(i18n_msg('06 · Vibrational Analysis', code='vib.page_title'))
        self.layout.removeItem(self.form)
        self.periodicity = None
        mode_card = self.section(i18n_msg('Calculation Mode', code='vib.mode_title'), columns=1,
                     help_text=i18n_msg('Frequencies and normal modes are always computed. IR dipole moments and Raman linear-response polarizabilities can be enabled independently or together in one Hessian workflow. NONE uses molecular operators; XYZ uses Berry-phase operators for insulating Gamma-point supercells. Partial-periodic spectra are not supported. Use a stationary structure and converged forces.', code='vib.mode_help'))
        mode_card.content.takeAt(0)
        self._target.deleteLater()
        self._target = None
        self.frequencies_label = QLabel(i18n_msg('✓ Frequencies & Normal Modes', code='vib.always_frequencies'))
        self.frequencies_label.setStyleSheet('color: ' + COLORS['success'] + ';')
        self.frequencies_label.setWordWrap(True)
        mode_card.content.addWidget(self.frequencies_label)
        self.always_label = QLabel(i18n_msg('Always included', code='vib.always_included'))
        self.always_label.setObjectName('muted')
        mode_card.content.addWidget(self.always_label)
        self.ir_enabled = self.add('vibrational.ir_enabled', i18n_msg('IR Intensities', code='vib.ir'), 'bool', inline=True, control_layout=mode_card.content)
        self.raman_enabled = self.add('vibrational.raman_enabled', i18n_msg('Raman Intensities', code='vib.raman'), 'bool', inline=True, control_layout=mode_card.content)
        self.spectra_hint_row = QWidget()
        hint_layout = QHBoxLayout(self.spectra_hint_row)
        hint_layout.setContentsMargins(0, 0, 0, 0)
        hint_layout.setSpacing(6)
        self.spectra_hint = QLabel()
        self.spectra_hint.setObjectName('muted')
        self.spectra_hint.setWordWrap(True)
        self.spectra_hint.setStyleSheet('font-size: 12px;')
        hint_layout.addWidget(self.spectra_hint, 1)
        self.periodic_raman_help = HelpIcon(i18n_msg('This feature depends on CP2K periodic linear response. Start with an insulating Gamma-point supercell and verify polarizability-response and intensity convergence. Support is experimental: XML syntax checks do not verify runtime success or the capabilities of the selected CP2K build.', code='vib.periodic_raman_help'))
        hint_layout.addWidget(self.periodic_raman_help, 0, Qt.AlignmentFlag.AlignTop)
        self.cards[-1].content.addWidget(self.spectra_hint_row)
        self.section(i18n_msg('Finite Differences & Replicas', code='vib.basic_title'),
                     help_text=i18n_msg('DX is in bohr. NPROC_REP is the number of MPI ranks per replica, not the number of replicas; it must divide the MPI total in step 07. FULLY_PERIODIC retains rotations and is never enabled automatically.', code='vib.basic_help'))
        self.add('vibrational.dx', 'DX', 'float', unit='bohr')
        nproc = self.add('vibrational.nproc_rep', 'NPROC_REP', 'int')
        field_layout = nproc.parentWidget().layout()
        self.nproc_label = field_layout.takeAt(0).widget()
        self.nproc_label.ensurePolished()
        self.nproc_help = HelpIcon(i18n_msg(
            'NPROC_REP · MPI Parallel Settings\n\n'
            'NPROC_REP is the number of MPI processes per vibrational replica, not the total MPI process count.\n\n'
            'Number of replicas = total MPI processes ÷ NPROC_REP\n\n'
            'For a total of 16 MPI processes:\n'
            '• NPROC_REP = 4: 4 replicas, each using 4 MPI processes.\n'
            '• NPROC_REP = 8: 2 replicas, each using 8 MPI processes.\n'
            '• NPROC_REP = 16: 1 replica using 16 MPI processes.\n\n'
            'Recommendations:\n'
            'NPROC_REP must be a positive integer and should normally divide the total MPI process count exactly.\n\n'
            'Running multiple replicas concurrently may increase total memory use. If an out-of-memory (OOM) error occurs, reduce the total MPI process count, or increase NPROC_REP to reduce the number of concurrent replicas.\n\n'
            'OpenMP-only: NPROC_REP must be 1.',
            code='vib.nproc_help'))
        self.nproc_help.setText('!')
        self.nproc_help.setStyleSheet(self.nproc_help.styleSheet() +
            f'QLabel#helpIcon {{ background-color:{COLORS["error"]}; color:{COLORS["input"]}; '
            'border-radius:8px; font-size:12px; font-weight:bold; }')
        label_row = QHBoxLayout()
        label_row.setSpacing(6)
        label_row.addWidget(self.nproc_label, 0, Qt.AlignmentFlag.AlignVCenter)
        label_row.addWidget(self.nproc_help, 0, Qt.AlignmentFlag.AlignVCenter)
        label_row.addStretch()
        # Accommodate the 16px icon inside the original label+gap height.
        extra = max(0, self.nproc_help.height() - self.nproc_label.sizeHint().height())
        field_layout.setSpacing(max(0, field_layout.spacing() - extra))
        field_layout.insertLayout(0, label_row)
        self.add('vibrational.proc_dist_type', 'PROC_DIST_TYPE', 'choice', ['BLOCKED', 'INTERLEAVED'])
        fully_periodic = self.add('vibrational.fully_periodic', 'FULLY_PERIODIC', 'bool')
        self.fully_periodic_label, self.fully_periodic_help = attach_field_help(fully_periodic, i18n_msg('FULLY_PERIODIC prevents removal of rotational modes from the Hessian. It is usually appropriate for a 3D periodic crystal, but does not set CELL/PERIODIC or select a dipole operator. Review it explicitly; Studio never changes this option automatically.', code='vib.fully_periodic_help'))
        self.section(i18n_msg('Thermochemistry & Output', code='vib.advanced_title'),
                     help_text=i18n_msg('Thermochemistry is optional and only applies to isolated gas-phase molecules. Temperature is in K and pressure in Pa. Molden and Hessian files are produced by CP2K after running; the Hessian file is binary.', code='vib.advanced_help'))
        self.thermo_grid = self._target
        self.thermo_grid.threshold = 0  # Keep this compact card in two aligned columns.
        self.thermo = self.add('vibrational.thermochemistry', i18n_msg('THERMOCHEMISTRY', code='vib.thermo_label'), 'bool', inline=True)
        temperature = self.add('vibrational.tc_temperature', i18n_msg('TC_TEMPERATURE', code='vib.temperature_label'), 'float', unit='K')
        pressure = self.add('vibrational.tc_pressure', i18n_msg('TC_PRESSURE', code='vib.pressure_label'), 'float', unit='Pa')
        molden_text = i18n_msg('Write Molden Vibrations', code='vib.molden')
        hessian_text = i18n_msg('Write Binary Hessian', code='vib.hessian')
        molden = self.add('vibrational.molden_vib', molden_text, 'bool', inline=True)
        hessian = self.add('vibrational.hessian', hessian_text, 'bool', inline=True)
        self._output_messages = {molden: molden_text, hessian: hessian_text}
        self._wrapping_outputs = False
        for control, text in self._output_messages.items():
            control.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            control.setAccessibleName(text)
        for field in [temperature, pressure]:
            field.setMinimumWidth(100)
        grid = self.thermo_grid.grid
        while grid.count():
            grid.takeAt(0)
        for container, (row, column, span) in zip(self.thermo_grid.items,
                [(0,0,2), (1,0,1), (1,1,1), (2,0,1), (2,1,1)]):
            grid.addWidget(container, row, column, 1, span)
        self.thermo_grid.installEventFilter(self)
        language_manager().callback(self, 'thermo-output-wrap', lambda panel: panel._wrap_output_labels())
        self.raman_card = self.section(i18n_msg('Raman Linear Response', code='vib.linres_title'))
        self.add('vibrational.linres_eps', 'LINRES / EPS', 'float')
        self.add('vibrational.linres_max_iter', 'LINRES / MAX_ITER', 'int')
        self.linres_preconditioner = self.add('vibrational.linres_preconditioner', 'LINRES / PRECONDITIONER', 'choice', LINRES_PRECONDITIONERS)
        self.linres_preconditioner.setMinimumWidth(self.fields['vibrational.linres_eps'][0].minimumWidth())
        self.linres_preconditioner.setMaximumWidth(self.fields['vibrational.linres_eps'][0].sizeHint().width())
        self.linres_preconditioner_label, self.linres_preconditioner_help = attach_field_help(self.linres_preconditioner, i18n_msg(
            'LINRES / PRECONDITIONER\n\n'
            'Controls preconditioning for Raman linear-response calculations. This setting is independent of the SCF/OT preconditioner.\n\n'
            '• NONE: No preconditioning; CP2K default.\n'
            '• FULL_ALL: Often effective, but relatively expensive to construct.\n'
            '• FULL_SINGLE_INVERSE: Useful for larger systems.\n'
            '• FULL_SINGLE: Diagonalization-based preconditioning.\n'
            '• FULL_KINETIC: Fast construction and useful for large systems.\n'
            '• FULL_S_INVERSE: Overlap-matrix-based preconditioning.\n\n'
            'For unstable periodic Raman response calculations, FULL_ALL may be tested together with a suitable ENERGY_GAP. Convergence is not guaranteed.',
            code='vib.linres_preconditioner_help'))
        self.linres_energy_gap = self.add('vibrational.linres_energy_gap', 'LINRES / ENERGY_GAP', 'float', unit='Ha')
        self.linres_energy_gap_label, self.linres_energy_gap_help = attach_field_help(self.linres_energy_gap, i18n_msg(
            'LINRES / ENERGY_GAP\n\n'
            'Estimated electronic gap used by the linear-response preconditioner, in Hartree (Ha). This parameter is independent of SCF/OT ENERGY_GAP.\n\n'
            '• CP2K default: 0.2 Ha.\n'
            '• With FULL_ALL, ENERGY_GAP should underestimate the actual HOMO–LUMO gap.\n'
            '• Smaller values such as 0.001–0.01 Ha may be tested for insulating systems.\n'
            '• An excessively large estimate may reduce preconditioning efficiency or destabilize convergence.\n'
            '• The optimal value depends on the electronic structure; smaller values are not guaranteed to converge faster.\n\n'
            'When PRECONDITIONER is NONE, ENERGY_GAP does not provide a preconditioning effect.',
            code='vib.linres_energy_gap_help'))
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setObjectName('muted')
        self.layout.addWidget(self.note)
        self.layout.addStretch()
        for card in self.cards:
            card.title_label.setWordWrap(False)
            card.title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.ir_enabled.toggled.connect(self.update_options)
        self.raman_enabled.toggled.connect(self.update_options)
        self.linres_preconditioner.currentIndexChanged.connect(self.update_options)
        self.thermo.toggled.connect(self.update_options)
        self.update_options()

    def eventFilter(self, watched, event):
        if watched is self.thermo_grid and event.type() in (QEvent.Type.Resize, QEvent.Type.LayoutRequest):
            self._wrap_output_labels()
        return super().eventFilter(watched, event)

    def _wrap_output_labels(self):
        """Native checkbox captions wrap only when the two-column pane is narrow."""
        if self._wrapping_outputs:
            return
        self._wrapping_outputs = True
        try:
            self.thermo_grid.grid.activate()
            for control, message in self._output_messages.items():
                control.ensurePolished()
                option = QStyleOptionButton()
                control.initStyleOption(option)
                width = max(1, control.style().subElementRect(QStyle.SubElement.SE_CheckBoxContents, option, control).width())
                text = i18n_render(message)
                layout = QTextLayout(text, control.font())
                wrapping = QTextOption()
                wrapping.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
                layout.setTextOption(wrapping)
                layout.beginLayout()
                lines = []
                while True:
                    line = layout.createLine()
                    if not line.isValid():
                        break
                    line.setLineWidth(width)
                    lines.append(text[line.textStart():line.textStart()+line.textLength()].strip())
                layout.endLayout()
                control.setText('\n'.join(lines))
        finally:
            self._wrapping_outputs = False

    def update_options(self, *_):
        ir, raman = self.ir_enabled.isChecked(), self.raman_enabled.isChecked()
        periodic_spectra = self.periodicity == 'XYZ' and (ir or raman)
        self.spectra_hint_row.setVisible(periodic_spectra)
        self.periodic_raman_help.setVisible(periodic_spectra and raman)
        if ir and raman:
            self.spectra_hint.setText(i18n_msg('Periodic IR + Raman: Berry-phase dipole moments and periodic polarizability response share one vibrational analysis.', code='vib.periodic_combined_hint'))
        elif ir:
            self.spectra_hint.setText(i18n_msg('Periodic IR: Intensities are computed using Berry-phase dipole moments.', code='vib.periodic_ir_hint'))
        elif raman:
            self.spectra_hint.setText(i18n_msg('Periodic Raman: Polarizability response uses the periodic Berry-phase dipole operator.', code='vib.periodic_raman_hint'))
        for field_path in ['vibrational.linres_eps', 'vibrational.linres_max_iter', 'vibrational.linres_preconditioner']:
            self.fields[field_path][0].setEnabled(raman)
        self.linres_energy_gap.setEnabled(raman and self.linres_preconditioner.currentData() != 'NONE')
        for field_path in ['vibrational.tc_temperature', 'vibrational.tc_pressure']:
            self.fields[field_path][0].setEnabled(self.thermo.isChecked())
        self.note.setText(i18n_msg('Experimental periodic intensities require an insulating Gamma-point supercell. Verify the electronic gap, response convergence and CP2K runtime support; XML validity alone does not establish a successful spectrum calculation.', code='vib.periodic_note') if periodic_spectra else
            i18n_msg('IR + Raman: dipole moments and polarizabilities use one Hessian workflow. Raman requires closed-shell OT without smearing/ADDED_MOS; response and intensity convergence require a CP2K run.', code='vib.combined_note') if ir and raman else
            i18n_msg('Raman: isolated closed-shell molecules with OT and no smearing/ADDED_MOS. POLAR and DO_RAMAN are activated; response convergence still requires a CP2K run.', code='vib.raman_note') if raman else
            i18n_msg('IR: isolated molecules use the nonperiodic dipole operator; XYZ uses Berry-phase dipole moments. Partial periodicity is not supported for intensities.', code='vib.ir_note') if ir else
            i18n_msg('Use tightly optimized coordinates. Frequencies and normal modes do not certify an energy minimum; check imaginary modes and convergence.', code='vib.frequencies_note'))

    def set_periodicity(self, periodicity):
        self.periodicity = periodicity
        self.update_options()

    def load(self, data):
        self.periodicity = data['structure']['periodic'] if data.get('structure') else None
        super().load(data)
        self.update_options()

    def collect(self, data):
        inactive = set()
        if not self.thermo.isChecked():
            inactive.update(['vibrational.tc_temperature', 'vibrational.tc_pressure'])
        if not self.raman_enabled.isChecked():
            inactive.update(['vibrational.linres_eps', 'vibrational.linres_max_iter',
                             'vibrational.linres_preconditioner', 'vibrational.linres_energy_gap'])
        elif self.linres_preconditioner.currentData() == 'NONE':
            inactive.add('vibrational.linres_energy_gap')
        for path in inactive:
            candidate = dict(data)
            candidate['vibrational'] = dict(data['vibrational'])
            issues = super().collect(candidate, paths=[path])
            if not issues:
                try:
                    VibrationalConfig.model_validate(candidate['vibrational'])
                    data['vibrational'] = candidate['vibrational']
                except ValueError:
                    pass
        return super().collect(data, paths=set(self.fields) - inactive)


class TaskPanel(QWidget):
    changed = Signal()

    def __init__(self, geometry):
        super().__init__()
        self.geometry = geometry
        self.vibrational = VibrationalPanel()
        self.cell_opt = CellOptimizationPanel()
        self.md = MDPanel()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        self.stack.addWidget(geometry)
        self.stack.addWidget(self.vibrational)
        self.stack.addWidget(self.cell_opt)
        self.stack.addWidget(self.md)
        layout.addWidget(self.stack)
        geometry.changed.connect(self.changed)
        self.vibrational.changed.connect(self.changed)
        self.cell_opt.changed.connect(self.changed)
        self.md.changed.connect(self.changed)

    def set_run_type(self, run_type):
        current = {'VIBRATIONAL_ANALYSIS': self.vibrational, 'CELL_OPT': self.cell_opt, 'MD': self.md}.get(run_type, self.geometry)
        self.stack.setCurrentWidget(current)
        for panel in [self.geometry, self.vibrational, self.cell_opt, self.md]:
            policy = QSizePolicy.Policy.Preferred if panel is current else QSizePolicy.Policy.Ignored
            panel.setSizePolicy(policy, policy)
        self.stack.updateGeometry()
        self.geometry.setEnabled(run_type == 'GEO_OPT')
        self.vibrational.setEnabled(run_type == 'VIBRATIONAL_ANALYSIS')
        self.cell_opt.setEnabled(run_type == 'CELL_OPT')
        self.md.setEnabled(run_type == 'MD')

    def load(self, data):
        self.geometry.load(data)
        self.vibrational.load(data)
        self.cell_opt.load(data)
        self.md.load(data)
        self.set_run_type(data['global_settings']['run_type'])

    def collect(self, data):
        run = data['global_settings']['run_type']
        self.set_run_type(run)
        errors = []
        for panel, key, model, active in [
            (self.geometry, 'motion', MotionConfig, run == 'GEO_OPT'),
            (self.vibrational, 'vibrational', VibrationalConfig, run == 'VIBRATIONAL_ANALYSIS'),
            (self.cell_opt, 'cell_opt', CellOptimizationConfig, run == 'CELL_OPT'),
            (self.md, 'md', MDConfig, run == 'MD')]:
            # Valid inactive edits are saved too, including a rapid task switch
            # before the debounce timer. Invalid inactive drafts stay in the UI
            # and cannot block a different calculation task.
            candidate = dict(data)
            candidate[key] = deepcopy(data[key])
            issues = panel.collect(candidate)
            if active:
                data[key] = candidate[key]
                errors.extend(issues)
            elif not issues:
                try:
                    data[key] = model.model_validate(candidate[key]).model_dump()
                except ValueError:
                    pass
        return errors
