from i18n.messages import i18n_msg
from ui.forms import FormPanel
from i18n.qt import QSizePolicy, QHBoxLayout, QLabel
from ui.widgets.poisson_reference import PoissonReference
from ui.widgets.help_icon import attach_field_help
from PySide6.QtCore import Qt


class DFTPanel(FormPanel):
    def __init__(self):
        super().__init__('03 · DFT')
        self.layout.removeItem(self.form)
        self.section(i18n_msg('Electronic State', code='studio.aa878a5d377835ba'), columns=3)
        self._target.threshold = 0  # Keep these three related fields on one row.
        charge = self.add('dft.charge', 'CHARGE', 'optional_int')
        multiplicity = self.add('dft.multiplicity', 'MULTIPLICITY', 'optional_int')
        uks = self.add('dft.uks', i18n_msg('Spin-polarized UKS', code='studio.52358a7cb44c6b1a'), 'bool', inline=True)
        for field in [charge, multiplicity]:
            field.setMinimumWidth(80)
            field.setMaximumWidth(200)
        charge.ensurePolished()
        uks.setStyleSheet(i18n_msg('QCheckBox {{ min-height:{p0}px; }}', p0=charge.sizeHint().height()))
        self._target.grid.setHorizontalSpacing(8)
        self._target.grid.setColumnStretch(1, 1)
        for container in self._target.items[:2]:
            container.layout().itemAt(0).widget().setWordWrap(False)
        # Match the input row, below its labels, without a fixed-height spacer.
        self._target.grid.setAlignment(self._target.items[2], Qt.AlignmentFlag.AlignBottom)
        method_card = self.section(i18n_msg('DFT Method & XC Functional', code='studio.4bb93242a34a7d81'), columns=1,
                     help_text=i18n_msg('Quickstep / GPW · Γ point; the calculation method is unchanged.', code='studio.d5d15bb7eb25d40a'))
        method_card.title_label.setWordWrap(False)
        method_card.title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.add('dft.xc_functional', 'XC_FUNCTIONAL', 'choice', [None, 'PBE', 'BLYP', 'PADE'])
        self.section(i18n_msg('MGRID / Plane-Wave Grid', code='studio.f9a657e9dc6c9f9e'))
        self.add('dft.cutoff', 'CUTOFF', 'float', unit='Ry')
        self.add('dft.rel_cutoff', 'REL_CUTOFF', 'float', unit='Ry')
        self.add('dft.ngrids', 'NGRIDS', 'int')
        eps_default = self.add('dft.eps_default', 'QS / EPS_DEFAULT', 'float')
        self.eps_default_label, self.eps_default_help = attach_field_help(eps_default, i18n_msg(
            'EPS_DEFAULT · Quickstep Numerical Accuracy\n\nEPS_DEFAULT controls the default numerical accuracy thresholds used by Quickstep.\n\nFor demanding calculations, the following heuristic may be considered:\nEPS_DEFAULT ≤ (EPS_SCF)² × 100\n\nExamples:\n• EPS_SCF = 1E-6 → EPS_DEFAULT ≤ 1E-10\n• EPS_SCF = 1E-7 → EPS_DEFAULT ≤ 1E-12\n• EPS_SCF = 1E-8 → EPS_DEFAULT ≤ 1E-14\n\nThis is a heuristic, not a mandatory CP2K rule. Tighter thresholds may increase computational cost. Convergence testing is still required for accurate energies, forces, stresses, and vibrational frequencies.',
            code='dft.eps_default_help'))
        self.poisson_card = self.section(i18n_msg('Poisson & Periodicity', code='studio.3abb25ebb0073bc6'), columns=1)
        self.add('dft.poisson_solver', 'POISSON_SOLVER', 'choice', [None, 'PERIODIC', 'MT', 'WAVELET', 'ANALYTIC'])
        self.poisson_reference = PoissonReference()
        self.poisson_card.content.addWidget(self.poisson_reference)
        self.surface_dipole_card = self.section(i18n_msg('Surface Dipole Correction', code='dipole.title'), columns=1,
            help_text=i18n_msg('Surface Dipole Correction\n\nReduces artificial electrostatic fields caused by interactions between periodic images of asymmetric slab models.\n\n• Intended primarily for asymmetric slabs modeled using 3D periodic supercells.\n• Does not replace nonperiodic boundary conditions.', code='dipole.help'))
        self.surface_dipole_card.title_label.setWordWrap(False)
        self.surface_dipole_card.title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.surface_dipole = self.add('dft.surface_dipole_correction',
            i18n_msg('Enable Surface Dipole Correction', code='dipole.enable'), 'bool', inline=True)
        direction_row = QHBoxLayout()
        direction_row.setSpacing(8)
        direction_label = QLabel('SURF_DIP_DIR')
        direction_label.setObjectName('fieldLabel')
        direction_row.addWidget(direction_label)
        self.surf_dip_dir = self.add('dft.surf_dip_dir', None, 'choice', ['X','Y','Z'], control_layout=direction_row)
        direction_label.setBuddy(self.surf_dip_dir)
        self.surf_dip_dir.setMinimumWidth(144)
        self.surf_dip_dir.setMaximumWidth(240)
        direction_row.setStretch(1, 1)
        direction_row.addStretch()
        self.surface_dipole_card.content.addLayout(direction_row)
        self.surface_dipole.toggled.connect(self.update_surface_dipole)
        self.update_surface_dipole()
        self.layout.addStretch()

    def update_surface_dipole(self, *_):
        self.surf_dip_dir.setEnabled(self.surface_dipole.isChecked())

    def load(self, data):
        super().load(data)
        self.update_surface_dipole()
