"""Independent cell-optimization settings using the existing form controls."""
from i18n.messages import i18n_msg
from core.schema import CP2KSchema
from ui.forms import FormPanel


class CellOptimizationPanel(FormPanel):
    def __init__(self):
        super().__init__(i18n_msg('06 · Cell Optimization', code='cellopt.page_title'))
        self.layout.removeItem(self.form)
        self.section(i18n_msg('Optimization Settings', code='cellopt.settings_title'), help_text=i18n_msg(
            'Cell optimization optimizes atomic coordinates and cell vectors together. The obsolete CELL_OPT / TYPE keyword is omitted. This release supports PERIODIC XYZ, Quickstep/GPW, the PERIODIC Poisson solver and ANALYTICAL stress. External pressure and pressure tolerance are in bar; external pressure is always written explicitly.', code='cellopt.settings_help'))
        self.add('cell_opt.optimizer', i18n_msg('OPTIMIZER', code='cellopt.optimizer_label'), 'choice', ['BFGS', 'LBFGS', 'CG'])
        self.add('cell_opt.max_iter', i18n_msg('MAX_ITER', code='cellopt.iter_label'), 'int')
        self.add('cell_opt.external_pressure', i18n_msg('EXTERNAL_PRESSURE', code='cellopt.pressure_label'), 'float', unit='bar')
        self.add('cell_opt.pressure_tolerance', i18n_msg('PRESSURE_TOLERANCE', code='cellopt.tolerance_label'), 'float', unit='bar')
        self.section(i18n_msg('Convergence Criteria', code='cellopt.convergence_title'))
        for key, label in [
            ('max_force', i18n_msg('MAX_FORCE', code='cellopt.max_force_label')),
            ('rms_force', i18n_msg('RMS_FORCE', code='cellopt.rms_force_label')),
            ('max_dr', i18n_msg('MAX_DR', code='cellopt.max_dr_label')),
            ('rms_dr', i18n_msg('RMS_DR', code='cellopt.rms_dr_label'))]:
            self.add('cell_opt.' + key, label, 'float', unit='Ha/Bohr' if 'force' in key else 'Bohr')
        self.section(i18n_msg('Cell Constraints', code='cellopt.constraints_title'), help_text=i18n_msg(
            'KEEP_ANGLES preserves cell-vector angles. KEEP_SYMMETRY requires an explicit compatible initial CELL / SYMMETRY; it preserves cell shape symmetry, not the atomic space group. CONSTRAINT fixes the specified cell components through the pressure tensor. Existing FIXED_ATOMS are retained in fractional coordinates, so Cartesian positions may move with the cell.', code='cellopt.constraints_help'))
        self.add('cell_opt.keep_angles', i18n_msg('KEEP_ANGLES', code='cellopt.angles_label'), 'bool', inline=True)
        self.add('cell_opt.keep_symmetry', i18n_msg('KEEP_SYMMETRY', code='cellopt.symmetry_label'), 'bool', inline=True)
        schema = CP2KSchema()  # Options come from the bundled target-version specification.
        self.add('cell_opt.constraint', i18n_msg('CONSTRAINT', code='cellopt.constraint_label'), 'choice', schema.keyword('MOTION/CELL_OPT', 'CONSTRAINT')['enum'])
        symmetry = self.add('cell_opt.initial_symmetry', i18n_msg('CELL / SYMMETRY', code='cellopt.initial_symmetry_label'), 'choice', schema.keyword('FORCE_EVAL/SUBSYS/CELL', 'SYMMETRY')['enum'])
        captions = {
            'NONE': i18n_msg('NONE', code='cellopt.sym.none'),
            'TRICLINIC': i18n_msg('TRICLINIC', code='cellopt.sym.triclinic'),
            'MONOCLINIC': i18n_msg('MONOCLINIC', code='cellopt.sym.monoclinic'),
            'MONOCLINIC_GAMMA_AB': i18n_msg('MONOCLINIC_GAMMA_AB', code='cellopt.sym.monoclinic_ab'),
            'ORTHORHOMBIC': i18n_msg('ORTHORHOMBIC', code='cellopt.sym.orthorhombic'),
            'TETRAGONAL_AB': i18n_msg('TETRAGONAL_AB', code='cellopt.sym.tetragonal_ab'),
            'TETRAGONAL_AC': i18n_msg('TETRAGONAL_AC', code='cellopt.sym.tetragonal_ac'),
            'TETRAGONAL_BC': i18n_msg('TETRAGONAL_BC', code='cellopt.sym.tetragonal_bc'),
            'TETRAGONAL': i18n_msg('TETRAGONAL', code='cellopt.sym.tetragonal'),
            'RHOMBOHEDRAL': i18n_msg('RHOMBOHEDRAL', code='cellopt.sym.rhombohedral'),
            'HEXAGONAL': i18n_msg('HEXAGONAL', code='cellopt.sym.hexagonal'),
            'HEXAGONAL_GAMMA_60': i18n_msg('HEXAGONAL_GAMMA_60', code='cellopt.sym.hexagonal_60'),
            'HEXAGONAL_GAMMA_120': i18n_msg('HEXAGONAL_GAMMA_120', code='cellopt.sym.hexagonal_120'),
            'CUBIC': i18n_msg('CUBIC', code='cellopt.sym.cubic')}
        for index in range(symmetry.count()):
            symmetry.setItemText(index, captions[symmetry.itemData(index)])
        self.layout.addStretch()
