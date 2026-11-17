from i18n.messages import i18n_msg
from copy import deepcopy
from PySide6.QtCore import QEvent, Qt
from i18n.qt import QStackedWidget, QSizePolicy, QLayout, QLabel, QFrame
from ui.forms import FormPanel
from ui.widgets.section_card import AdaptiveGrid
from ui.widgets.help_icon import attach_field_help
from ui.theme import COLORS


class ActiveStack(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.layout().setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

    def fit_current(self):
        if self.currentWidget():
            height = self.currentWidget().sizeHint().height()
            if self.minimumHeight() != height or self.maximumHeight() != height:
                self.setFixedHeight(height)
                self.updateGeometry()

    def event(self, event):
        result = super().event(event)
        if event.type() == QEvent.Type.LayoutRequest:
            self.fit_current()
        return result

    def sizeHint(self):
        return self.currentWidget().sizeHint() if self.currentWidget() else super().sizeHint()

    def minimumSizeHint(self):
        return self.currentWidget().minimumSizeHint() if self.currentWidget() else super().minimumSizeHint()


class SCFPanel(FormPanel):
    def __init__(self):
        super().__init__('04 · SCF')
        self.layout.removeItem(self.form)
        self.section(i18n_msg('SCF Basic Settings', code='studio.953a6174a85a454b'))
        self._target.threshold = 0  # Four fields stay in a two-column grid.
        eps = self.add('dft.scf.eps_scf', 'EPS_SCF', 'float', unit='Ha')
        maximum = self.add('dft.scf.max_scf', 'MAX_SCF', 'int')
        guess = self.add('dft.scf.guess', 'SCF_GUESS', 'choice', ['ATOMIC', 'CORE', 'RANDOM'])
        self.outer_max = self.add('dft.scf.outer_max_scf', 'OUTER_SCF / MAX_SCF', 'int')
        for container, field in zip(self._target.items, [eps, maximum, guess, self.outer_max]):
            field.setMinimumWidth(eps.minimumWidth())
            field.setMaximumWidth(eps.maximumWidth())
            field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            container.layout().setAlignment(field, Qt.AlignmentFlag(0))
        outer = self.add('dft.scf.outer_scf', i18n_msg('Enable OUTER_SCF', code='studio.81e0db11b47de9f6'),
                         'bool', inline=True, control_layout=self._target.items[3].layout())
        outer.toggled.connect(self.outer_max.setEnabled)
        self.section(i18n_msg('SCF Solver', code='studio.159e6116ca2c0cc5'), columns=1)
        self.method = self.add('dft.scf.method', 'METHOD', 'choice', ['OT', 'DIAGONALIZATION'])
        self.stack = ActiveStack()
        self.stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.ot = FormPanel('OT', embedded=True)
        self.ot.section(i18n_msg('OT Settings', code='studio.db98905d1e735c49'), columns=1)
        minimizer = self.ot.add('dft.scf.minimizer', 'MINIMIZER', 'choice', ['CG', 'DIIS', 'BROYDEN'])
        self.minimizer_label, self.minimizer_help = attach_field_help(minimizer, i18n_msg(
            'MINIMIZER · OT Minimization Algorithm\n\nDIIS — Usually faster\n• Often converges faster for well-behaved systems.\n• More sensitive to the initial electronic structure and preconditioner.\n• Try CG if iterations oscillate or fail to converge.\n\nCG — Usually more robust\n• Conjugate gradients offer reliable convergence.\n• Suitable for difficult-to-converge systems.\n• May be slower than DIIS for some systems.\n\nRecommendation: Try DIIS first; switch to CG for persistent oscillations or convergence difficulties.',
            code='scf.minimizer_help'))
        self.ot.add('dft.scf.preconditioner', 'PRECONDITIONER', 'choice', ['FULL_ALL', 'FULL_KINETIC', 'FULL_SINGLE_INVERSE', 'FULL_S_INVERSE', 'NONE'])
        self.energy_gap = self.ot.add('dft.scf.energy_gap', 'ENERGY_GAP', 'optional_float',
            placeholder=i18n_msg('Auto (-1.0)', code='scf.energy_gap_auto'), unit='Ha')
        self.energy_gap_label, self.energy_gap_help = attach_field_help(self.energy_gap, i18n_msg(
            "ENERGY_GAP · OT Preconditioner Gap\n\nENERGY_GAP is an estimated electronic gap used by the OT preconditioner, in Hartree (Ha). It does not modify the physical band gap.\n\nRecommendations:\n• For wide-gap insulators or polymers, values around 0.08–0.1 Ha may be tested and compared with smaller values.\n• For small-gap systems, such as oxygen-deficient oxides, trying 0.2–0.5 Ha may help damp unstable SCF iterations.\n• With the FULL_ALL preconditioner, ENERGY_GAP should generally underestimate the actual HOMO–LUMO gap. Smaller values such as 0.001–0.002 Ha are also recommended in CP2K documentation.\n• Larger values do not guarantee faster convergence and may reduce preconditioning efficiency.\n• Auto uses CP2K's default behavior.\n\nCompare iteration counts, total runtime, and convergence stability.",
            code='scf.energy_gap_help'))
        self.diag = FormPanel('DIAGONALIZATION', embedded=True)
        self.diag.layout.removeItem(self.diag.form)
        diagonalization_card = self.diag.section(i18n_msg('DIAGONALIZATION Settings', code='studio.d96d3c8878c314fd'))
        subtitle = QLabel(i18n_msg('Diagonalization Parameters', code='studio.cd6b53247ad1090d'))
        subtitle.setObjectName('fieldLabel')
        diagonalization_card.content.insertWidget(0, subtitle)
        self.diag.add('dft.scf.diagonalization', 'ALGORITHM', 'choice', ['STANDARD', 'DAVIDSON'])
        self.diag.add('dft.scf.added_mos', 'ADDED_MOS', 'int')
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFixedHeight(1)
        separator.setStyleSheet(i18n_msg('background:{p0}; border:0;', p0=COLORS["border"]))
        diagonalization_card.content.addWidget(separator)
        subtitle = QLabel(i18n_msg('Mixing & Electronic Smearing', code='studio.3bef0599de223a3b'))
        subtitle.setObjectName('fieldLabel')
        diagonalization_card.content.addWidget(subtitle)
        self.diag._target = AdaptiveGrid()
        diagonalization_card.content.addWidget(self.diag._target)
        self.diag.add('dft.scf.mixing_method', 'MIXING / METHOD', 'choice', ['BROYDEN_MIXING', 'PULAY_MIXING', 'DIRECT_P_MIXING'])
        self.diag.add('dft.scf.mixing_alpha', 'MIXING / ALPHA', 'float')
        smear = self.diag.add('dft.scf.smearing', i18n_msg('Fermi–Dirac Smearing', code='studio.b770653c619f7dae'), 'bool')
        self.temperature = self.diag.add('dft.scf.electronic_temperature', 'ELECTRONIC_TEMPERATURE', 'float', unit='K')
        smear.toggled.connect(self.temperature.setEnabled)
        for panel in [self.ot, self.diag]:
            self.stack.addWidget(panel)
            panel.changed.connect(lambda *_: self.changed.emit())
        self.layout.addWidget(self.stack)
        self.layout.addStretch()
        self.method.currentIndexChanged.connect(self.stack.setCurrentIndex)
        self.stack.currentChanged.connect(lambda *_: self.stack.fit_current())

    def load(self, data):
        super().load(data)
        self.ot.load(data)
        self.diag.load(data)
        self.stack.setCurrentIndex(self.method.currentIndex())
        self.stack.fit_current()
        self.outer_max.setEnabled(data['dft']['scf']['outer_scf'])
        self.temperature.setEnabled(data['dft']['scf']['smearing'])

    def collect(self, data, paths=None):
        active = set(self.fields)
        if not self.fields['dft.scf.outer_scf'][0].isChecked():
            active.discard('dft.scf.outer_max_scf')
        errors = super().collect(data, active)
        if self.method.currentData() == 'OT':
            errors += self.ot.collect(data)
            data['dft']['scf']['smearing'] = False
            data['dft']['scf']['added_mos'] = 0
        else:
            # Preserve a valid pending OT gap even when switching solver before
            # the debounced refresh. An invalid inactive draft must not block DIAG.
            candidate = deepcopy(data)
            if not self.ot.collect(candidate, {'dft.scf.energy_gap'}):
                data['dft']['scf']['energy_gap'] = candidate['dft']['scf']['energy_gap']
            active = set(self.diag.fields)
            if not self.diag.fields['dft.scf.smearing'][0].isChecked():
                active.discard('dft.scf.electronic_temperature')
            errors += self.diag.collect(data, active)
        return errors
