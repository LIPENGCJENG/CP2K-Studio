"""Draft completeness, cross-field checks, then the authoritative XML parser."""
from i18n.messages import i18n_msg, i18n_str
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from threading import RLock
import re
import numpy as np
from core.models import Project
from core.schema import CP2KSchema
from core.kind_validator import validate_kinds, active_kinds, project_catalog, resource_paths
from core.file_references import serialize_file_reference, FileReferenceError


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    tree: dict | None = None
    infos: list[str] = field(default_factory=list)

    @property
    def ok(self):
        return not self.errors


def _token(value):
    return bool(re.fullmatch(r'[A-Za-z0-9_+.,()/*=\-]+', value))


def _path_safe(value):
    # Source filesystem names may need normalization during bundle export.
    # Their INP spelling is checked separately by the file serializer.
    return not any(c in value for c in '\r\n\x00')


def validate_project(project: Project, catalog=None) -> ValidationResult:
    # Revalidate nested mutable containers too (e.g. programmatic list edits).
    try:
        project = Project.model_validate(project.model_dump())
    except ValueError as exc:
        return ValidationResult(errors=[i18n_str(exc)])
    result = ValidationResult()
    err, warn = result.errors, result.warnings
    st, dft = project.structure, project.dft
    if not st or not st.symbols:
        err.append(i18n_msg('SUBSYS: import a nonempty structure', code='studio.ca7f89367263988f'))
    else:
        cell = np.array(st.cell)
        if np.linalg.det(cell) < 1e-8:
            err.append(i18n_msg('CELL: provide three independent right-handed cell vectors (a box is also required for nonperiodic systems)', code='studio.7c4841cad4d6ad33'))
        labels = set(st.labels)
        for label in labels:
            kind = project.kinds.get(label)
            if kind and (not _token(kind.basis_set) or not _token(kind.potential)):
                err.append(i18n_msg('KIND {p0}: basis or pseudopotential name is empty or contains invalid characters', code='studio.207ab9fea7e8c88c', p0=label))
        if set(project.kinds) - labels:
            warn.append(i18n_msg('KINDs absent from the current structure will not be exported', code='studio.83f827f106c66d59'))
        solver = dft.poisson_solver
        if solver == 'PERIODIC' and st.periodic != 'XYZ':
            err.append(i18n_msg('POISSON: the PERIODIC solver requires XYZ periodicity', code='studio.3816b7dab122782b'))
        if solver == 'MT' and st.periodic not in {'NONE', 'XY', 'XZ', 'YZ'}:
            err.append(i18n_msg('POISSON: MT supports only 0D or 2D systems', code='studio.76ff8199fee0aa41'))
        if solver == 'MT':
            result.infos.append(i18n_msg('MT requires a sufficiently large simulation cell. Check the electron-density extent, vacuum size, and convergence.', code='poisson.mt_info'))
        if solver == 'ANALYTIC' and st.periodic == 'XYZ':
            err.append(i18n_msg('POISSON: ANALYTIC supports only 0D, 1D, and 2D systems', code='studio.d7699e3602889b44'))
        if solver == 'WAVELET' and st.periodic not in {'NONE', 'XZ', 'XYZ'}:
            err.append(i18n_msg('POISSON: WAVELET supports only NONE, XZ, or XYZ periodicity', code='studio.5fe7a7185adbc017'))
        if solver == 'WAVELET':
            # The generator sets the documented required FFT library.
            if not np.allclose(cell, np.diag(np.diag(cell)), atol=1e-10) or np.any(np.diag(cell) <= 0):
                err.append(i18n_msg('WAVELET: only axis-aligned, orthogonal, positive cell vectors are currently supported', code='studio.9fb2cb7210b85d80'))
            if st.periodic == 'NONE' and not np.allclose(cell, np.eye(3) * cell[0, 0], rtol=1e-10, atol=1e-10):
                err.append(i18n_msg('WAVELET with PERIODIC NONE requires an orthogonal cubic box (A = B = C). Use Generate Simulation Box → Cubic Box; the current cell has not been changed.', code='box.wavelet_cubic'))
            warn.append(i18n_msg('WAVELET sets FFTSG; electron density must approach zero at nonperiodic boundaries', code='studio.24d25b06c30f6626'))
        if dft.surface_dipole_correction:
            result.infos.append(i18n_msg('DFT / SURFACE_DIPOLE_CORRECTION: confirm an asymmetric slab with its surface normal parallel to Cartesian {direction} and sufficient vacuum. Studio does not infer surface symmetry or verify electron-density decay.', code='dipole.applicability_info', direction=dft.surf_dip_dir))
            if st.periodic == 'NONE':
                result.infos.append(i18n_msg('DFT / SURFACE_DIPOLE_CORRECTION: this correction is intended primarily for 3D periodic asymmetric slabs and is generally inappropriate for an isolated PERIODIC NONE molecule. Review whether to disable it; boundary settings have not been changed.', code='dipole.molecule_info'))
            elif st.periodic != 'XYZ':
                result.infos.append(i18n_msg('DFT / SURFACE_DIPOLE_CORRECTION: partial periodicity {periodic} requires review of compatibility between the Poisson boundary treatment and dipole correction. This does not certify the combination; settings have not been changed.', code='dipole.partial_info', periodic=st.periodic))
            elif solver is not None and solver != 'PERIODIC':
                result.infos.append(i18n_msg('DFT / SURFACE_DIPOLE_CORRECTION: review compatibility with POISSON_SOLVER {solver}. The standard 3D periodic slab workflow uses PERIODIC; Studio has not changed the solver.', code='dipole.solver_info', solver=solver))
    if dft.charge is None:
        err.append(i18n_msg('DFT: explicitly set total CHARGE (enter 0 for a neutral system)', code='studio.a9d84cb7d9c13cda'))
    if dft.multiplicity is None:
        err.append(i18n_msg('DFT: explicitly set spin MULTIPLICITY', code='studio.bcb243f50f952247'))
    elif dft.multiplicity != 1 and not dft.uks:
        err.append(i18n_msg('DFT: enable UKS when MULTIPLICITY is greater than 1', code='studio.d6e30a303277592e'))
    if dft.xc_functional is None:
        err.append(i18n_msg('XC: select a functional', code='studio.ed6e78e4381c9d67'))
    if dft.poisson_solver is None:
        err.append(i18n_msg('POISSON: select an electrostatic solver', code='studio.13030ba077c1e3af'))
    resources = [(i18n_msg('Basis file {p0}', code='studio.a85f6f29a980c76e', p0=i+1), p) for i, p in enumerate(dft.basis_files)]
    resources += [(i18n_msg('Pseudopotential file', code='studio.b7fdc12ded3be5f3'),p) for p in dft.potential_files or ([dft.potential_file] if dft.potential_file else [])]
    catalog = catalog or project_catalog(project)
    basis_paths,potential_paths = resource_paths(project,catalog)
    resources += [(i18n_msg('Basis source', code='studio.0f2583faf419190a'),p) for p in basis_paths] + [(i18n_msg('Pseudopotential source', code='studio.ebb4ca9179d67a26'),p) for p in potential_paths]
    if not basis_paths:
        err.append(i18n_msg('DFT: configure at least one basis file', code='studio.d3f34013070ef297'))
    if not potential_paths:
        err.append(i18n_msg('DFT: configure at least one accessible pseudopotential file', code='studio.f273a1b0557d9cbe'))
    for label, value in resources:
        if not value.strip():
            err.append(i18n_msg('{p0}: path cannot be empty', code='studio.2a38ea9387d5b4d4', p0=label))
        elif not _path_safe(value):
            err.append(i18n_msg('{p0}: path contains a newline or NUL', code='studio.1b3bfcdd6b793c22', p0=label))
        elif not Path(value).expanduser().is_file():
            category = 'basis' if label.startswith(i18n_msg('Basis Set', code='studio.810ecb3582cd0af1')) else 'potential'
            if not catalog.path_for(value,category):
                err.append(i18n_msg('{p0}: file does not exist or is not loaded: {p1}', code='studio.451fbcee836f91fc', p0=label, p1=value))
            else:
                result.infos.append(i18n_msg('{p0}: {p1} was resolved to an actual database file', code='studio.b2fb2f7f78313e8a', p0=label, p1=value))
    # Warn about the actual filenames emitted by the inline generator, not
    # user lookup names or sources hidden behind a merged potential artifact.
    for keyword, paths in [('BASIS_SET_FILE_NAME', basis_paths),
                           ('POTENTIAL_FILE_NAME', potential_paths if len(potential_paths) == 1 else [])]:
        for value in paths:
            try:
                serialize_file_reference(Path(value).as_posix(), keyword)
            except FileReferenceError as exc:
                message = i18n_str(exc)
                if message not in warn:
                    warn.append(message)
    kind_result = validate_kinds(project,catalog)
    err.extend(kind_result.errors)
    warn.extend(i18n_msg('KIND {p0}：{p1}', p0=i.label, p1=i.message) for i in kind_result.issues if i.severity=='Warning')
    result.infos.extend(i18n_msg('KIND {p0}：{p1}', p0=i.label, p1=i.message) for i in kind_result.issues if i.severity=='Info')
    scf = dft.scf
    if scf.method == 'OT' and (scf.smearing or scf.added_mos):
        err.append(i18n_msg('SCF: OT does not support smearing or ADDED_MOS; switch to DIAGONALIZATION', code='studio.e03a01b138e8e14e'))
    if scf.method == 'DIAGONALIZATION' and scf.smearing and scf.added_mos < 1:
        err.append(i18n_msg('SCF: smearing requires at least one additional orbital, ADDED_MOS', code='studio.a9d6812deca09a55'))
    # Only use explicit pseudopotential valences; never infer an absent charge.
    if st and dft.charge is not None and dft.multiplicity is not None:
        valences = {}
        for label,selected in kind_result.selected.items():
            if selected['potential'].q is not None:
                valences[label] = selected['potential'].q
        if len(valences) == len(set(st.labels)):
            electrons = sum(valences[s] for s in st.labels) - dft.charge
            unpaired = dft.multiplicity - 1
            if electrons < 1 or unpaired > electrons or (electrons - unpaired) % 2:
                err.append(i18n_msg('DFT: CHARGE, MULTIPLICITY, and pseudopotential valence electron count have inconsistent parity or counts', code='studio.69cda7083d3901ba'))
        else:
            warn.append(i18n_msg('Some pseudopotential names lack a -qN suffix; valence electron count and multiplicity were not checked', code='studio.aa2b2e275016f35d'))
    from core.vibrational import validate_vibrational
    validate_vibrational(project, result)
    from core.cell_optimization import validate_cell_optimization
    validate_cell_optimization(project, result)
    from core.md import validate_md
    validate_md(project, result)
    return result


class InputValidator:
    """Reuse the XML parser. Lock protects its mutable parse state."""
    def __init__(self, xml_spec=None):
        self.schema = CP2KSchema(xml_spec)
        self._parser = None
        self._base_dir = None
        self._lock = RLock()

    def parse(self, text: str, base_dir: str | Path = '.') -> ValidationResult:
        result = ValidationResult()
        try:
            from cp2k_input_tools.parser import CP2KInputParser
            with self._lock:
                resolved_base = i18n_str(Path(base_dir).resolve())
                if self._parser is None or self._base_dir != resolved_base:
                    self._parser = CP2KInputParser(xmlspec=i18n_str(self.schema.path), base_dir=resolved_base)
                    self._base_dir = resolved_base
                result.tree = self._parser.parse(StringIO(text))
                # Historical 2026.1 XML permits TYPE, but newer executables
                # explicitly reject it. A successful XML parse alone must not
                # approve this known-incompatible keyword for exported inputs.
                cell_opt = result.tree.get('+motion', {}).get('+cell_opt', {})
                if 'type' in cell_opt:
                    result.errors.append(i18n_msg('CELL_OPT: omit MOTION/CELL_OPT/TYPE. This keyword has been removed in newer CP2K executables, which always use joint cell/coordinate optimization. Acceptance by a historical XML schema does not prove runtime compatibility.', code='cellopt.removed_type_error'))
        except Exception as exc:
            result.errors.append(i18n_msg('CP2K 2026.1 syntax validation failed: {p0}', code='studio.40df4cf19ae11085', p0=exc))
        return result
