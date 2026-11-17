"""AIMD checks and conservative, self-contained text restart inspection."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import math
import numpy as np
from ase import Atoms
from ase.cell import Cell
from ase.neighborlist import neighbor_list
from i18n.messages import i18n_msg


@dataclass(frozen=True)
class MDRestart:
    subsys: dict
    dynamics: dict
    labels: tuple


@lru_cache(maxsize=8)
def _parse_restart(path, signature, xml_path, xml_signature):
    from core.validator import InputValidator
    file = Path(path)
    if file.stat().st_size > 100 * 1024 * 1024:
        raise ValueError(i18n_msg('MD: restart exceeds the 100 MB limit.', code='md.restart_size'))
    text = file.read_text(encoding='utf-8')
    if any(line.lstrip().startswith('@') for line in text.splitlines()):
        raise ValueError(i18n_msg('MD: only self-contained text restart files without preprocessor directives are supported.', code='md.restart_preprocessor'))
    parsed = InputValidator(xml_path).parse(text, file.parent)
    if not parsed.ok:
        raise ValueError(i18n_msg('MD: restart XML validation failed: {detail}', code='md.restart_xml', detail='\n'.join(parsed.errors)))
    tree = parsed.tree
    evaluations = tree.get('+force_eval', [])
    if len(evaluations) != 1 or evaluations[0].get('method', 'qs').lower() not in {'quickstep', 'qs'}:
        raise ValueError(i18n_msg('MD: restart must contain one Quickstep FORCE_EVAL.', code='md.restart_method'))
    if tree.get('+global', {}).get('run_type', '').lower() not in {'md', 'molecular_dynamics'}:
        raise ValueError(i18n_msg('MD: select a molecular-dynamics restart, not an XYZ frame or optimization restart.', code='md.restart_task'))
    subsys = evaluations[0].get('+subsys', {})
    dynamics = tree.get('+motion', {}).get('+md', {})
    rows = subsys.get('+coord', {}).get('*', [])
    labels = tuple(row.split()[0] for row in rows if len(row.split()) >= 4)
    if not rows or len(labels) != len(rows):
        raise ValueError(i18n_msg('MD: restart requires complete embedded atomic coordinates.', code='md.restart_coords'))
    return MDRestart(subsys, dynamics, labels)


def inspect_restart(project, path=None):
    """Return parsed state; never apply restart coordinates to the project."""
    from core.schema import BUNDLED_XML
    value = path or project.md.restart_file
    file = Path(value).expanduser().resolve()
    if not value or not file.is_file():
        raise ValueError(i18n_msg('MD: choose an existing, readable .restart file.', code='md.restart_missing'))
    xml = Path(project.xml_spec or BUNDLED_XML).resolve()
    def signature(p):
        stat = p.stat()
        return stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size, stat.st_ino
    state = _parse_restart(str(file), signature(file), str(xml), signature(xml))
    st = project.structure
    if st is None or state.labels != tuple(st.labels):
        raise ValueError(i18n_msg('MD: restart atom count, KIND labels or atom order differ from the current structure. Import matching structure settings first.', code='md.restart_atoms'))
    elements = {k.get('_'): k.get('element', k.get('_')) for k in state.subsys.get('+kind', [])}
    if any(elements.get(label, '').capitalize() != element for label, element in st.kind_elements.items()):
        raise ValueError(i18n_msg('MD: restart KIND element definitions do not match the current structure.', code='md.restart_elements'))
    velocities = state.subsys.get('+velocity', {}).get('*', [])
    array = np.asarray(velocities, dtype=float)
    if array.shape != (len(st.symbols), 3) or not np.isfinite(array).all():
        raise ValueError(i18n_msg('MD: restart is missing complete finite atomic velocities; a final XYZ frame is not a full MD restart.', code='md.restart_velocity'))
    cell = state.subsys.get('+cell', {})
    if all(axis in cell for axis in ['a', 'b', 'c']):
        matrix = np.asarray([cell[axis] for axis in ['a', 'b', 'c']], dtype=float)
    elif 'abc' in cell:
        matrix = Cell.fromcellpar([*cell['abc'], *cell.get('alpha_beta_gamma', (90, 90, 90))]).array
    else:
        matrix = np.zeros((3, 3))
    if (matrix.shape != (3, 3) or not np.isfinite(matrix).all() or np.linalg.det(matrix) <= 1e-8
            or not np.allclose(matrix, st.cell, rtol=1e-8, atol=1e-8)
            or cell.get('periodic', 'xyz').upper() != st.periodic):
        raise ValueError(i18n_msg('MD: restart cell or periodicity is missing, invalid or differs from the current fixed-volume cell. Import matching cell settings first.', code='md.restart_cell'))
    dynamics = state.dynamics
    if (type(dynamics.get('step_start_val')) is not int or dynamics['step_start_val'] < 0
            or not math.isfinite(dynamics.get('time_start_val', float('nan')))
            or dynamics['time_start_val'] < 0):
        raise ValueError(i18n_msg('MD: restart requires valid STEP_START_VAL and TIME_START_VAL counters.', code='md.restart_counters'))
    if dynamics.get('ensemble', '').upper() != project.md.ensemble:
        raise ValueError(i18n_msg('MD: restart ensemble must match the selected NVT/NVE ensemble in this release.', code='md.restart_ensemble'))
    if project.md.ensemble == 'NVT':
        thermostat = dynamics.get('+thermostat', {})
        csvr = thermostat.get('+csvr', {})
        energy = csvr.get('+thermostat_energy', {}).get('*', [])
        rng = csvr.get('+rng_init', {}).get('*', [])
        if (thermostat.get('type', '').upper() != 'CSVR' or thermostat.get('region', 'global') != 'global'
                or len(energy) != 1 or not np.isfinite(np.asarray(energy, dtype=float)).all()
                or len(rng) != 1 or not str(rng[0]).strip()):
            raise ValueError(i18n_msg('MD: NVT restart requires the GLOBAL CSVR thermostat energy and RNG state. Incomplete or other thermostat restarts are not supported.', code='md.restart_csvr'))
        # CP2K 2026.1 uses (A40,I2,3L2,ES25.16,18F20.1), not a generic
        # whitespace-separated seed list. Preserve and check every field.
        record = str(rng[0])
        try:
            if len(record) != 433 or not all(32 <= ord(c) <= 126 for c in record):
                raise ValueError()
            if int(record[40:42]) != 1:  # CSVR uses Gaussian streams.
                raise ValueError()
            if any(record[start:start+2].strip().upper() not in {'T', 'F'} for start in [42, 44, 46]):
                raise ValueError()
            values = [float(record[48:73].replace('D', 'E'))] + [float(record[n:n+20]) for n in range(73, 433, 20)]
            if not all(math.isfinite(v) for v in values):
                raise ValueError()
        except ValueError:
            raise ValueError(i18n_msg('MD: CSVR RNG state is not a valid CP2K 2026.1 fixed-width stream record.', code='md.restart_rng')) from None
    return state


def validate_md(project, result):
    if project.global_settings.run_type != 'MD':
        return
    md, st = project.md, project.structure
    info, warn, error = result.infos, result.warnings, result.errors
    info.append(i18n_msg('MD: start from a sufficiently relaxed structure to reduce unphysical initial forces. No geometry optimization has been verified.', code='md.relax_info'))
    info.append(i18n_msg('MD: test timestep convergence. Simulation length does not establish statistical equilibrium; diffusion and other dynamical properties usually require longer sampling.', code='md.sampling_info'))
    info.append(i18n_msg('MD: check total-energy drift in NVE, and temperature stability and thermal equilibration in NVT.', code='md.ensemble_info'))
    if project.dft.scf.eps_scf > 1e-6:
        warn.append(i18n_msg('MD: EPS_SCF exceeds 1E-6; test tighter SCF thresholds for reliable forces and energy conservation.', code='md.scf_warning'))
    if md.timestep > 2 or (st and 'H' in st.symbols and md.timestep > 1):
        warn.append(i18n_msg('MD: the selected timestep is large for unconstrained AIMD, especially with hydrogen. Test a smaller timestep.', code='md.timestep_warning'))
    if md.ensemble == 'NVT' and md.timecon < md.timestep:
        warn.append(i18n_msg('MD: CSVR TIMECON is smaller than TIMESTEP; strong thermostat coupling may distort dynamics.', code='md.timecon_warning'))
    if md.ensemble == 'NVT' and md.temperature == 0:
        warn.append(i18n_msg('MD: zero-temperature CSVR dynamics needs special care; verify initialization and thermostat suitability.', code='md.zero_temperature'))
    if st:
        if st.fixed_atoms:
            info.append(i18n_msg('MD: FIXED_ATOMS are retained in fractional coordinates. Check constrained degrees of freedom and thermostat temperature interpretation.', code='md.fixed_info'))
            if len(st.fixed_atoms) == len(st.symbols) and all(a.components == 'XYZ' for a in st.fixed_atoms):
                error.append(i18n_msg('MD: all atomic components are fixed; no dynamical degrees of freedom remain.', code='md.all_fixed'))
        try:
            positions = np.asarray(st.positions)
            if md.continue_from_restart:
                state = inspect_restart(project)
                from core.file_references import serialize_file_reference, FileReferenceError
                try:
                    serialize_file_reference(Path(md.restart_file).expanduser().resolve().as_posix(), 'RESTART_FILE_NAME')
                except FileReferenceError as exc:
                    warn.append(i18n_msg('MD: {detail}', code='md.path_warning', detail=exc))
                # Coordinates in restarts may be scaled or in bohr; normalize
                # only this check's temporary array, never the project data.
                coord = state.subsys['+coord']
                positions = np.array([[float(v) for v in row.split()[1:4]] for row in coord['*']])
                if coord.get('scaled', False):
                    positions = positions @ np.asarray(st.cell)
                elif coord.get('unit', 'angstrom').lower() in {'bohr', 'au'}:
                    from ase.units import Bohr
                    positions *= Bohr
                elif coord.get('unit', 'angstrom').lower() not in {'angstrom', 'angstroms'}:
                    raise ValueError(i18n_msg('MD: unsupported restart coordinate unit.', code='md.restart_unit'))
                if not np.isfinite(positions).all():
                    raise ValueError(i18n_msg('MD: restart coordinates must be finite.', code='md.restart_finite'))
                info.append(i18n_msg('MD: EXT_RESTART restores positions, velocities, cell and counters at runtime; the viewer shows the project structure. Verify electronic settings and continuity after restarting. WFN restart is separate and SCF_GUESS is unchanged. Restart state has only been checked statically.', code='md.restart_info'))
            atoms = Atoms(st.symbols, positions=positions, cell=st.cell, pbc=[axis in st.periodic for axis in 'XYZ'])
            distances = neighbor_list('d', atoms, .2, self_interaction=False)
            if len(distances):
                error.append(i18n_msg('MD: an initial atom pair is closer than 0.2 Å, including periodic images. Check the structure before dynamics.', code='md.overlap_error'))
        except (OSError, ValueError, TypeError, KeyError) as exc:
            error.append(i18n_msg('MD: restart or initial structure check failed: {detail}', code='md.restart_error', detail=exc))
    elif md.continue_from_restart:
        error.append(i18n_msg('MD: a matching project structure is required before continuing from restart.', code='md.restart_structure'))
