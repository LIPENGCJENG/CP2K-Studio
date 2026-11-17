"""Cross-field checks for the implemented full finite-difference workflow.

Reference: CP2K v2026.1 input XML and tests/QS/regtest-gpw-2-1/N2_raman.inp.
XYZ spectroscopy uses CP2K's Berry-phase operators at Gamma. Partial-periodic
spectroscopy and partial/constrained Hessians are not implemented.
"""
from enum import Enum
from i18n.messages import i18n_msg


class SpectroscopyPath(str, Enum):
    FREQUENCIES = 'FREQUENCIES'
    MOLECULAR_IR = 'MOLECULAR_IR'
    MOLECULAR_RAMAN = 'MOLECULAR_RAMAN'
    PERIODIC_IR = 'PERIODIC_IR'
    PERIODIC_RAMAN = 'PERIODIC_RAMAN'
    UNSUPPORTED = 'UNSUPPORTED'

    @property
    def berry_phase(self):
        return self in {self.PERIODIC_IR, self.PERIODIC_RAMAN}


def spectroscopy_path(mode, periodicity):
    """Derived workflow shared by generation, checking, import and UI.

    FULLY_PERIODIC deliberately does not select the dipole operator.
    """
    if mode == 'FREQUENCIES':
        return SpectroscopyPath.FREQUENCIES
    if mode in {'IR', 'RAMAN'} and periodicity in {'NONE', 'XYZ'}:
        return SpectroscopyPath(('PERIODIC_' if periodicity == 'XYZ' else 'MOLECULAR_') + mode)
    return SpectroscopyPath.UNSUPPORTED


def spectroscopy_paths(config, periodicity):
    return tuple((mode, spectroscopy_path(mode, periodicity)) for mode in config.enabled_spectra)


def validate_spectroscopy_input(project, tree):
    """Check the actual parsed final INP, beyond XML keyword validity.

    Scoped to Studio's selected intensity workflow; this does not turn the
    general CP2K XML parser into a restriction on arbitrary CP2K input files.
    """
    if project.global_settings.run_type != 'VIBRATIONAL_ANALYSIS' or not project.vibrational.intensities:
        return []
    config = project.vibrational
    paths = spectroscopy_paths(config, project.structure.periodic)
    forces = (tree or {}).get('+force_eval', [])
    valid = len(forces) == 1 and all(path != SpectroscopyPath.UNSUPPORTED for _, path in paths)
    force = forces[0] if len(forces) == 1 else {}
    dft = force.get('+dft', {})
    vibration = (tree or {}).get('+vibrational_analysis', {})
    valid = valid and vibration.get('intensities') is True
    valid = valid and vibration.get('fully_periodic', False) == project.vibrational.fully_periodic
    valid = valid and force.get('method', 'quickstep').lower() in {'quickstep', 'qs'}
    valid = valid and dft.get('+qs', {}).get('method', 'gpw').lower() == 'gpw'
    cell = force.get('+subsys', {}).get('+cell', {})
    valid = valid and cell.get('periodic', 'xyz').upper() == project.structure.periodic
    valid = valid and dft.get('+poisson', {}).get('periodic', 'xyz').upper() == project.structure.periodic
    if any(path.berry_phase for _, path in paths) and '+kpoints' in dft:
        return [i18n_msg('VIBRATIONAL_ANALYSIS: periodic spectra currently support only the implicit Gamma-point Quickstep/GPW supercell workflow. Explicit KPOINTS with Berry-phase moments or LINRES have not been validated and cannot be imported or exported by Studio.', code='vib.kpoints_error')]
    moments = dft.get('+print', {}).get('+moments')
    polar = force.get('+properties', {}).get('+linres', {}).get('+polar')
    linres = force.get('+properties', {}).get('+linres', {})
    # Check each requested property independently. Other features may own extra
    # MOMENTS or LINRES settings, so their presence is not a mode conflict.
    for mode, path in paths:
        if mode == 'IR':
            valid = valid and moments is not None
            if moments is not None:
                valid = valid and str(moments.get('_', 'HIGH')).upper() not in {'OFF', 'FALSE', '0'}
                valid = valid and moments.get('periodic', True) is path.berry_phase
                valid = valid and moments.get('max_moment', 1) == 1
        else:
            valid = valid and polar is not None
            valid = valid and linres.get('preconditioner', 'NONE').upper() == config.linres_preconditioner
            if config.linres_preconditioner != 'NONE':
                valid = valid and linres.get('energy_gap', 0.2) == config.linres_energy_gap
            if polar is not None:
                valid = valid and polar.get('_', False) is True and polar.get('do_raman', True) is True
                valid = valid and polar.get('periodic_dipole_operator', True) is path.berry_phase
    if not valid:
        return [i18n_msg('VIBRATIONAL_ANALYSIS: the final INP does not match the selected {mode} / PERIODIC {periodic} workflow. Check INTENSITIES, FULLY_PERIODIC, Quickstep/GPW, boundary settings and the required molecular or Berry-phase property operator.', code='vib.property_path_error', mode=config.spectra_label, periodic=project.structure.periodic)]
    return []


def validate_vibrational(project, result):
    if project.global_settings.run_type != 'VIBRATIONAL_ANALYSIS':
        return
    v, st, scf = project.vibrational, project.structure, project.dft.scf
    errors, warnings = result.errors, result.warnings
    mpi = project.run_environment.mpi_processes
    if v.nproc_rep > mpi or mpi % v.nproc_rep:
        errors.append(i18n_msg('VIBRATIONAL_ANALYSIS / NPROC_REP: ranks per replica ({rep}) must not exceed MPI processes ({mpi}) and must divide that total exactly; OpenMP threads do not count as MPI ranks.', code='vib.replica_error', rep=v.nproc_rep, mpi=mpi))
    if scf.eps_scf > 1e-7:
        warnings.append(i18n_msg('VIBRATIONAL_ANALYSIS: EPS_SCF is greater than 1E-7. Consider tightening SCF convergence and test DX and grid convergence for reliable finite-difference frequencies.', code='vib.scf_warning'))
    result.infos.append(i18n_msg('VIBRATIONAL_ANALYSIS: Ensure the structure is sufficiently optimized, and check residual forces and imaginary frequencies.', code='vib.stationary_info'))
    if v.raman_enabled:
        if v.linres_preconditioner == 'FULL_ALL':
            result.infos.append(i18n_msg('VIBRATIONAL_ANALYSIS / LINRES / FULL_ALL: ENERGY_GAP should underestimate the actual HOMO–LUMO gap. This estimate is independent of SCF/OT ENERGY_GAP; test response convergence. Preconditioning does not guarantee convergence or verify periodic Raman runtime support.', code='vib.linres_full_all_info'))
        if scf.method != 'OT' or scf.smearing or scf.added_mos or project.dft.uks or project.dft.multiplicity != 1:
            errors.append(i18n_msg('VIBRATIONAL_ANALYSIS / Raman: the implemented workflow requires closed-shell OT, no smearing and no ADDED_MOS. Other linear-response configurations are not supported by Studio.', code='vib.raman_solver_error'))
        if v.linres_eps > 1e-7:
            warnings.append(i18n_msg('VIBRATIONAL_ANALYSIS / Raman: LINRES EPS is looser than 1e-7; test polarizability-response convergence.', code='vib.linres_warning'))
        result.infos.append(i18n_msg('VIBRATIONAL_ANALYSIS / Raman: POLAR and DO_RAMAN are enabled. XML checks cannot certify response convergence or a successful Raman calculation; no numerical CP2K run has been performed.', code='vib.raman_unverified'))
    if not st or not st.symbols:
        return  # The shared structure validator reports the missing structure.
    periodic = st.periodic != 'NONE'
    paths = spectroscopy_paths(v, st.periodic)
    for mode, path in paths:
        if path == SpectroscopyPath.UNSUPPORTED:
            errors.append(i18n_msg('VIBRATIONAL_ANALYSIS: {mode} with partial periodicity {periodic} is not supported by Studio. Intensity workflows support NONE (molecular operators) or XYZ (Berry-phase operators); boundary conditions have not been changed.', code='vib.partial_spectra_error', mode=mode, periodic=st.periodic))
    if any(path.berry_phase for _, path in paths):
        if scf.smearing or scf.added_mos:
            errors.append(i18n_msg('VIBRATIONAL_ANALYSIS: the implemented periodic Berry-phase intensity workflow requires integer, fully occupied orbitals, without smearing or ADDED_MOS. Metallic or fractionally occupied configurations are not supported; settings have not been changed.', code='vib.occupations_error'))
        result.infos.append(i18n_msg('VIBRATIONAL_ANALYSIS: periodic {mode} is experimental support for insulating, gapped 3D Quickstep/GPW Gamma-point supercells. Static configuration cannot establish an electronic gap or CP2K build support. XML validity is not a successful numerical intensity calculation; this workflow has not been numerically verified by Studio.', code='vib.periodic_experimental_info', mode=v.spectra_label))
        if v.ir_enabled:
            result.infos.append(i18n_msg('VIBRATIONAL_ANALYSIS / IR: MOMENTS uses the Berry-phase dipole operator with MAX_MOMENT 1. Polarization is defined modulo a lattice-dependent quantum; inspect branch continuity across finite displacements and test DX, SCF and grid convergence.', code='vib.berry_branch_info'))
    if v.thermochemistry and (periodic or v.fully_periodic):
        errors.append(i18n_msg('VIBRATIONAL_ANALYSIS / THERMOCHEMISTRY: only an isolated gas-phase molecule with FULLY_PERIODIC F is supported.', code='vib.thermo_error'))
    if v.thermochemistry:
        warnings.append(i18n_msg('VIBRATIONAL_ANALYSIS / THERMOCHEMISTRY: confirm the isolated gas-phase harmonic approximation is appropriate; the application cannot infer this from the coordinates.', code='vib.thermo_warning'))
    if periodic and not v.fully_periodic:
        result.infos.append(i18n_msg('VIBRATIONAL_ANALYSIS: A periodic cell is used with FULLY_PERIODIC F. CP2K will handle rotational modes accordingly. Consider whether FULLY_PERIODIC T is appropriate for the system.', code='vib.periodic_info'))
    if not periodic and v.fully_periodic:
        warnings.append(i18n_msg('VIBRATIONAL_ANALYSIS: FULLY_PERIODIC T retains rotations even for this nonperiodic molecule; review the intended mode analysis.', code='vib.rotations_warning'))
    if len(st.symbols) < 2:
        errors.append(i18n_msg('VIBRATIONAL_ANALYSIS: at least two atoms are required by this molecular/full-mode workflow.', code='vib.atom_count_error'))
    if st.fixed_atoms:
        warnings.append(i18n_msg('VIBRATIONAL_ANALYSIS: saved GEO_OPT fixed-atom constraints are not applied. A full Hessian of all atoms will be computed; partial/constrained vibrational analysis is not implemented.', code='vib.fixed_warning'))
