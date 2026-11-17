"""Typed section tree, not template substitution. All coordinates are Angstrom."""
from dataclasses import dataclass, field
from pathlib import Path
from core.models import Project
from core.validator import validate_project
from core.kind_validator import project_catalog, active_kinds
from core.database_resources import selected_resources, MERGED_POTENTIAL
from core.file_references import serialize_file_reference
from core.atom_constraints import fixed_atom_groups
from core.vibrational import spectroscopy_path


class GenerationError(ValueError):
    pass


def scalar(value):
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    if isinstance(value, float):
        return format(value, '.12g')
    return str(value)


@dataclass
class Section:
    name: str
    parameter: str = ''
    keywords: list[tuple[str, object]] = field(default_factory=list)
    children: list['Section'] = field(default_factory=list)

    def get_or_add(self, name, parameter=None):
        """Enable a shared section without replacing other features' content."""
        child = next((node for node in self.children if node.name == name), None)
        if child is None:
            child = Section(name)
            self.children.append(child)
        if parameter is not None:
            child.parameter = parameter
        return child

    def update_keywords(self, values):
        keys = {key for key, _ in values}
        self.keywords = [(key, value) for key, value in self.keywords if key not in keys] + values

    def render(self, depth=0):
        indent = '  ' * depth
        lines = [f'{indent}&{self.name}' + (f' {self.parameter}' if self.parameter else '')]
        for key, value in self.keywords:
            val = ' '.join(scalar(v) for v in value) if isinstance(value, (tuple, list)) else scalar(value)
            lines.append(f'{indent}  {key} {val}'.rstrip())
        for child in self.children:
            lines.extend(child.render(depth + 1))
        lines.append(f'{indent}&END {self.name}')
        return lines


def add_spectroscopy_sections(force_eval, dft, config, periodicity):
    """IR and Raman share one vibrational driver, retaining unrelated sections."""
    if config.ir_enabled:
        path = spectroscopy_path('IR', periodicity)
        values = [('MAX_MOMENT', 1), ('PERIODIC', path.berry_phase)]
        if not path.berry_phase:
            values.append(('REFERENCE', 'COM'))
        dft.get_or_add('PRINT').get_or_add('MOMENTS', 'ON').update_keywords(values)
    if config.raman_enabled:
        path = spectroscopy_path('RAMAN', periodicity)
        linres = force_eval.get_or_add('PROPERTIES').get_or_add('LINRES')
        linres.update_keywords([('EPS', config.linres_eps), ('MAX_ITER', config.linres_max_iter)])
        linres.update_keywords([('PRECONDITIONER', config.linres_preconditioner)])
        if config.linres_preconditioner != 'NONE':
            # Round-trip precision for this explicit estimate, independent of OT.
            linres.update_keywords([('ENERGY_GAP', repr(config.linres_energy_gap))])
        polar = linres.get_or_add('POLAR', 'TRUE')
        polar.update_keywords([('DO_RAMAN', True), ('PERIODIC_DIPOLE_OPERATOR', path.berry_phase)])
        polar.get_or_add('PRINT').get_or_add('POLAR_MATRIX', 'ON')


def build_sections(project: Project, coordinate_file: str | None = None, catalog=None,
                   *, file_bindings: dict[str, str] | None = None):
    catalog = catalog or project_catalog(project)
    result = validate_project(project,catalog)
    if not result.ok:
        raise GenerationError('\n'.join(result.errors))
    g, d, st, m = project.global_settings, project.dft, project.structure, project.motion
    glob = Section('GLOBAL', keywords=[('PROJECT', g.project_name), ('RUN_TYPE', g.run_type), ('PRINT_LEVEL', g.print_level)])
    if d.poisson_solver == 'WAVELET':
        glob.keywords.append(('PREFERRED_FFT_LIBRARY', 'FFTSG'))
    sc = d.scf
    scf = Section('SCF', keywords=[('SCF_GUESS', sc.guess), ('EPS_SCF', sc.eps_scf), ('MAX_SCF', sc.max_scf)])
    if sc.method == 'OT':
        ot = Section('OT', keywords=[('MINIMIZER', sc.minimizer), ('PRECONDITIONER', sc.preconditioner)])
        if sc.energy_gap is not None:
            # Keep this optional value's round-trip float precision without
            # changing the established serialization of other parameters.
            ot.keywords.append(('ENERGY_GAP', repr(sc.energy_gap)))
        scf.children.append(ot)
    else:
        scf.keywords.append(('ADDED_MOS', sc.added_mos))
        scf.children.extend([
            Section('DIAGONALIZATION', keywords=[('ALGORITHM', sc.diagonalization)]),
            Section('MIXING', keywords=[('METHOD', sc.mixing_method), ('ALPHA', sc.mixing_alpha)])])
        if sc.smearing:
            scf.children.append(Section('SMEAR', keywords=[('METHOD', 'FERMI_DIRAC'), ('ELECTRONIC_TEMPERATURE', sc.electronic_temperature)]))
    if sc.outer_scf:
        scf.children.append(Section('OUTER_SCF', keywords=[('EPS_SCF', sc.eps_scf), ('MAX_SCF', sc.outer_max_scf)]))
    basis_files,potential_files = selected_resources(project,catalog)
    bindings = file_bindings or {}
    basis_files = [bindings.get(p, p) for p in basis_files]
    potential_file = potential_files[0] if len(potential_files)==1 else MERGED_POTENTIAL
    potential_file = bindings.get(potential_file, potential_file)
    dft = Section('DFT', keywords=[('BASIS_SET_FILE_NAME', serialize_file_reference(Path(p).as_posix(), 'BASIS_SET_FILE_NAME')) for p in basis_files] + [
        ('POTENTIAL_FILE_NAME', serialize_file_reference(Path(potential_file).as_posix(), 'POTENTIAL_FILE_NAME')), ('CHARGE', d.charge),
        ('MULTIPLICITY', d.multiplicity), ('UKS', d.uks)], children=[
            Section('QS', keywords=[('METHOD', 'GPW'), ('EPS_DEFAULT', d.eps_default)]),
            Section('MGRID', keywords=[('CUTOFF', d.cutoff), ('REL_CUTOFF', d.rel_cutoff), ('NGRIDS', d.ngrids)]),
            Section('POISSON', keywords=[('PERIODIC', st.periodic), ('POISSON_SOLVER', d.poisson_solver)]),
            scf, Section('XC', children=[Section('XC_FUNCTIONAL', d.xc_functional)])])
    if d.surface_dipole_correction:
        dft.keywords.extend([('SURFACE_DIPOLE_CORRECTION', 'T'), ('SURF_DIP_DIR', d.surf_dip_dir)])
    subsys = Section('SUBSYS', children=[Section('CELL', keywords=[
        ('A', st.cell[0]), ('B', st.cell[1]), ('C', st.cell[2]), ('PERIODIC', st.periodic)])])
    if coordinate_file is None:
        subsys.children.append(Section('COORD', keywords=[('UNIT', 'ANGSTROM')] + [
            (s, p) for s, p in zip(st.labels, st.positions)]))
    else:
        subsys.children.append(Section('TOPOLOGY', keywords=[('COORD_FILE_FORMAT', 'XYZ'),
            ('COORD_FILE_NAME', serialize_file_reference(Path(coordinate_file).as_posix(), 'COORD_FILE_NAME'))]))
    for label,element in sorted(active_kinds(project).items()):
        kind = project.kinds[label]
        subsys.children.append(Section('KIND', label, keywords=[('ELEMENT', element), ('BASIS_SET', kind.basis_set), ('POTENTIAL', kind.potential)]))
    sections = [glob, Section('FORCE_EVAL', keywords=[('METHOD', 'Quickstep')], children=[dft, subsys])]
    if g.run_type == 'CELL_OPT':
        config = project.cell_opt
        sections[-1].keywords.append(('STRESS_TENSOR', config.stress_tensor))
        if config.initial_symmetry != 'NONE':
            subsys.children[0].keywords.append(('SYMMETRY', config.initial_symmetry))
    if g.run_type == 'VIBRATIONAL_ANALYSIS':
        v = project.vibrational
        vibration = Section('VIBRATIONAL_ANALYSIS', keywords=[
            ('DX', v.dx), ('NPROC_REP', v.nproc_rep), ('PROC_DIST_TYPE', v.proc_dist_type),
            ('FULLY_PERIODIC', v.fully_periodic), ('INTENSITIES', v.intensities),
            ('THERMOCHEMISTRY', v.thermochemistry)])
        if v.thermochemistry:
            vibration.keywords.extend([('TC_TEMPERATURE', v.tc_temperature), ('TC_PRESSURE', v.tc_pressure)])
        vibration.children.append(Section('PRINT', children=[
            Section('MOLDEN_VIB', 'ON' if v.molden_vib else 'OFF'),
            Section('HESSIAN', 'ON' if v.hessian else 'OFF')]))
        sections.insert(1, vibration)
        add_spectroscopy_sections(sections[-1], dft, v, st.periodic)
    if g.run_type in {'GEO_OPT', 'CELL_OPT', 'MD'}:
        if g.run_type == 'CELL_OPT':
            config = project.cell_opt
            parameters = [(key.upper(), getattr(config, key)) for key in [
                'optimizer', 'max_iter', 'external_pressure', 'pressure_tolerance',
                'max_force', 'rms_force', 'max_dr', 'rms_dr', 'keep_angles', 'keep_symmetry', 'constraint']]
            motion = Section('MOTION', children=[Section('CELL_OPT', keywords=parameters)])
        elif g.run_type == 'GEO_OPT':
            motion = Section('MOTION', children=[Section('GEO_OPT', keywords=[
                ('OPTIMIZER', m.optimizer), ('MAX_ITER', m.max_iter), ('MAX_FORCE', m.max_force),
                ('RMS_FORCE', m.rms_force), ('MAX_DR', m.max_dr), ('RMS_DR', m.rms_dr)])])
        else:
            md = project.md
            dynamics = Section('MD', keywords=[('ENSEMBLE', md.ensemble), ('STEPS', md.steps),
                ('TIMESTEP', repr(md.timestep)), ('TEMPERATURE', repr(md.temperature)),
                ('INITIALIZATION_METHOD', md.initialization_method)])
            csvr = Section('CSVR', keywords=[('TIMECON', repr(md.timecon))])
            if md.ensemble == 'NVT':
                dynamics.children.append(Section('THERMOSTAT', keywords=[('TYPE', 'CSVR')], children=[csvr]))
            if md.continue_from_restart:
                from core.md import inspect_restart
                state = inspect_restart(project)
                if 'econs_start_val' in state.dynamics:
                    dynamics.keywords.append(('ECONS_START_VAL', repr(state.dynamics['econs_start_val'])))
                restart_path = bindings.get(md.restart_file, Path(md.restart_file).expanduser().resolve().as_posix())
                sections.insert(1, Section('EXT_RESTART', keywords=[
                    ('RESTART_FILE_NAME', serialize_file_reference(restart_path, 'RESTART_FILE_NAME')),
                    ('RESTART_DEFAULT', False), ('RESTART_POS', True), ('RESTART_VEL', True),
                    ('RESTART_CELL', True), ('RESTART_COUNTERS', True),
                    ('RESTART_THERMOSTAT', md.ensemble == 'NVT')]))
                if md.ensemble == 'NVT':
                    # Restore CSVR's energy and stochastic stream explicitly;
                    # RESTART_THERMOSTAT's historical description refers to Nose.
                    previous = state.dynamics['+thermostat']['+csvr']
                    csvr.children.extend([
                        Section('THERMOSTAT_ENERGY', keywords=[('', repr(float(value))) for value in previous['+thermostat_energy']['*']]),
                        Section('RNG_INIT', keywords=[('', value) for value in previous['+rng_init']['*']])])
            dynamics.children.append(Section('PRINT', children=[Section('ENERGY', 'ON', children=[
                Section('EACH', keywords=[('MD', 1)])])]))
            trajectory = Section('TRAJECTORY', 'ON' if md.write_trajectory else 'OFF')
            if md.write_trajectory:
                trajectory.keywords.append(('FORMAT', md.trajectory_format))
                trajectory.children.append(Section('EACH', keywords=[('MD', md.trajectory_interval)]))
            restart = Section('RESTART', 'ON' if md.write_restart else 'OFF')
            if md.write_restart:
                restart.keywords.append(('BACKUP_COPIES', md.backup_copies))
                restart.children.append(Section('EACH', keywords=[('MD', md.restart_interval)]))
            motion = Section('MOTION', children=[dynamics, Section('PRINT', children=[trajectory, restart])])
        groups = fixed_atom_groups(st)
        if groups:
            motion.children.append(Section('CONSTRAINT', children=[
                Section('FIXED_ATOMS', keywords=[('COMPONENTS_TO_FIX', components)] +
                        [('LIST', numbers[start:start+32]) for start in range(0, len(numbers), 32)])
                for components, numbers in groups.items()]))
        sections.append(motion)
    return sections


def generate_input(project: Project, coordinate_file: str | None = None, catalog=None) -> str:
    return '\n\n'.join('\n'.join(s.render()) for s in build_sections(project, coordinate_file,catalog)) + '\n'
