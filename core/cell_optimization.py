"""Conservative CP2K 2026.1 DIRECT_CELL_OPT checks; never rotate a structure."""
import numpy as np
from ase.cell import Cell
from i18n.messages import i18n_msg


def matches_cell_symmetry(cell, symmetry):
    """Check metric constraints before CP2K can impose an initial cell symmetry."""
    a, b, c, alpha, beta, gamma = Cell(cell).cellpar()
    equal = lambda x, y: bool(np.isclose(x, y, rtol=1e-6, atol=1e-8))
    angle = lambda x, y: bool(np.isclose(x, y, rtol=0, atol=1e-4))
    orthogonal = all(angle(x, 90) for x in [alpha, beta, gamma])
    if symmetry in {'NONE', 'TRICLINIC'}:
        return True
    if symmetry == 'MONOCLINIC':
        return angle(alpha, 90) and angle(gamma, 90)
    if symmetry == 'MONOCLINIC_GAMMA_AB':
        return equal(a, b) and angle(alpha, 90) and angle(beta, 90)
    if symmetry == 'ORTHORHOMBIC':
        return orthogonal
    if symmetry in {'TETRAGONAL', 'TETRAGONAL_AB', 'TETRAGONAL_AC', 'TETRAGONAL_BC'}:
        pair = {'TETRAGONAL_AC': (a, c), 'TETRAGONAL_BC': (b, c)}.get(symmetry, (a, b))
        return orthogonal and equal(*pair)
    if symmetry == 'CUBIC':
        return orthogonal and equal(a, b) and equal(b, c)
    if symmetry == 'RHOMBOHEDRAL':
        return equal(a, b) and equal(b, c) and angle(alpha, beta) and angle(beta, gamma)
    if symmetry in {'HEXAGONAL', 'HEXAGONAL_GAMMA_60', 'HEXAGONAL_GAMMA_120'}:
        return (equal(a, b) and angle(alpha, 90) and angle(beta, 90)
                and angle(gamma, 120 if symmetry.endswith('120') else 60))
    return False


def validate_cell_optimization(project, result):
    if project.global_settings.run_type != 'CELL_OPT':
        return
    config, structure = project.cell_opt, project.structure
    # The generator currently implements Quickstep/GPW with LDA/GGA only.
    # Scope stress support explicitly instead of assuming every Poisson backend
    # remains compatible with an evolving, potentially nonorthogonal cell.
    if project.dft.poisson_solver != 'PERIODIC':
        result.errors.append(i18n_msg('CELL_OPT: this release supports analytical stress with Quickstep/GPW and POISSON_SOLVER PERIODIC only. Other solver combinations are not implemented; the solver was not changed.', code='cellopt.stress_error'))
    if not structure or not structure.symbols:
        return  # Shared completeness checks report missing structure.
    if structure.periodic != 'XYZ':
        result.errors.append(i18n_msg('CELL_OPT: only PERIODIC XYZ is supported in this release. Use GEO_OPT for nonperiodic systems; 1D/2D cell optimization is not implemented. Periodicity was not changed.', code='cellopt.periodicity_error'))
    cell = np.asarray(structure.cell, dtype=float)
    with np.errstate(over='ignore', invalid='ignore'):
        volume = np.linalg.det(cell)
    if not np.isfinite(volume) or volume <= 1e-8:
        result.errors.append(i18n_msg('CELL_OPT: the cell must have finite positive volume and three independent right-handed vectors.', code='cellopt.volume_error'))
        return
    if (not np.allclose([cell[0, 1], cell[0, 2], cell[1, 2]], 0, rtol=0, atol=1e-8)
            or np.any(np.diag(cell) <= 0)):
        result.errors.append(i18n_msg('CELL_OPT: CP2K requires A along +X and B in the XY plane, with positive diagonal components. Reorient the cell and all atomic coordinates together before importing; no components have been truncated or rotated.', code='cellopt.orientation_error'))
    if config.keep_symmetry and config.initial_symmetry == 'NONE':
        result.errors.append(i18n_msg('CELL_OPT / KEEP_SYMMETRY: select an explicit initial CELL / SYMMETRY compatible with the current cell. NONE cannot preserve a requested cell symmetry.', code='cellopt.symmetry_missing'))
    if not matches_cell_symmetry(cell, config.initial_symmetry):
        result.errors.append(i18n_msg('CELL_OPT: initial CELL / SYMMETRY {symmetry} does not match the current cell lengths and angles. Correct the selection or geometry; the cell was not modified.', code='cellopt.symmetry_mismatch', symmetry=config.initial_symmetry))
    if structure.fixed_atoms:
        result.warnings.append(i18n_msg('CELL_OPT: FIXED_ATOMS constraints are retained and fix fractional coordinates. Cartesian positions can move as the cell changes; confirm these constraints match the intended optimization.', code='cellopt.fixed_warning'))
    result.infos.append(i18n_msg('CELL_OPT uses analytical stress with the current Gamma-point GPW configuration. Test basis, grid, SCF and Brillouin-zone sampling convergence for cell parameters and stress; static validation does not certify convergence. This workflow is for 3D bulk crystals, not vacuum slabs. PERIODIC XYZ alone does not identify whether a structure is bulk; confirm the physical model before using it.', code='cellopt.convergence_info'))
