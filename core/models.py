"""Single, serializable source of truth. Incomplete projects are valid drafts."""
from i18n.messages import i18n_msg
import math
from typing import Literal, Annotated, get_args
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator, model_validator
from core.run_config import RunEnvironment
from ase.data import atomic_numbers

Periodic = Literal['NONE', 'X', 'Y', 'Z', 'XY', 'XZ', 'YZ', 'XYZ']
StructureType = Literal['unclassified', 'isolated_molecule', 'periodic_structure']
Vector = tuple[float, float, float]
FixedComponents = Literal['XYZ', 'X', 'Y', 'Z', 'XY', 'XZ', 'YZ']
LinresPreconditioner = Literal['NONE', 'FULL_ALL', 'FULL_SINGLE_INVERSE', 'FULL_SINGLE', 'FULL_KINETIC', 'FULL_S_INVERSE']
LINRES_PRECONDITIONERS = get_args(LinresPreconditioner)
CellSymmetry = Literal['NONE', 'TRICLINIC', 'MONOCLINIC', 'MONOCLINIC_GAMMA_AB',
    'ORTHORHOMBIC', 'TETRAGONAL_AB', 'TETRAGONAL_AC', 'TETRAGONAL_BC', 'TETRAGONAL',
    'RHOMBOHEDRAL', 'HEXAGONAL', 'HEXAGONAL_GAMMA_60', 'HEXAGONAL_GAMMA_120', 'CUBIC']
AtomID = Annotated[int, Field(strict=True, gt=0)]


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, validate_assignment=True)

    @field_validator('*')
    @classmethod
    def safe_strings(cls, value):
        if isinstance(value, str) and any(c in value for c in '\r\n\x00'):
            raise ValueError(i18n_msg('Text fields cannot contain newlines or NUL characters', code='studio.0fe848c9c6c07ae3'))
        return value


class FixedAtom(Model):
    atom_id: int = Field(strict=True, gt=0)
    components: FixedComponents = 'XYZ'


class BoxGenerationSettings(Model):
    mode: Literal['VACUUM_PADDING', 'CUBIC', 'MANUAL'] = 'VACUUM_PADDING'
    vacuum_margin: float = Field(default=10.0, gt=0)
    cubic_margin: float = Field(default=10.0, gt=0)
    manual_lengths: Vector | None = None

    @field_validator('manual_lengths')
    @classmethod
    def positive_lengths(cls, value):
        if value is not None and any(length <= 0 for length in value):
            raise ValueError(i18n_msg('All A/B/C box lengths must be finite positive numbers.', code='box.invalid_lengths'))
        return value


class Structure(Model):
    symbols: list[str] = Field(default_factory=list)
    positions: list[Vector] = Field(default_factory=list)
    cell: tuple[Vector, Vector, Vector] = ((0, 0, 0), (0, 0, 0), (0, 0, 0))
    periodic: Periodic = 'NONE'
    source: str | None = None
    structure_type: StructureType = 'unclassified'
    # Last successful box-generation setting, independent of manual cell edits.
    box_vacuum_margin: float = Field(default=10.0, gt=0)
    box_generation: BoxGenerationSettings = Field(default_factory=BoxGenerationSettings)
    kind_labels: list[str] = Field(default_factory=list)
    # Persistent identity, independent of table row and CP2K's 1-based LIST.
    atom_ids: list[AtomID] = Field(default_factory=list)
    fixed_atoms: list[FixedAtom] = Field(default_factory=list)

    @model_validator(mode='before')
    @classmethod
    def molecular_periodicity(cls, data):
        # Check before assignment, so a rejected update cannot leave a mutated
        # Pydantic instance with contradictory boundary conditions.
        if (isinstance(data, dict) and data.get('structure_type') == 'isolated_molecule'
                and data.get('periodic', 'NONE') != 'NONE'):
            raise ValueError(i18n_msg('CELL: a confirmed isolated molecule must use PERIODIC NONE. Periodic presets or project data cannot override this structure type.', code='periodicity.molecule_error'))
        if isinstance(data, dict) and 'box_generation' not in data and 'box_vacuum_margin' in data:
            data = {**data, 'box_generation': {'vacuum_margin': data['box_vacuum_margin']}}
        return data

    @property
    def periodicity_locked(self):
        return self.structure_type == 'isolated_molecule'

    @model_validator(mode='after')
    def consistency(self):
        if len(self.symbols) != len(self.positions):
            raise ValueError(i18n_msg('Element and coordinate counts differ', code='studio.3c7ff8799e4cbc68'))
        if not self.atom_ids:
            object.__setattr__(self, 'atom_ids', list(range(1, len(self.symbols) + 1)))
        if (len(self.atom_ids) != len(self.symbols) or len(set(self.atom_ids)) != len(self.atom_ids)
                or any(type(i) is not int or i < 1 for i in self.atom_ids)):
            raise ValueError(i18n_msg('Atom IDs must be unique positive integers corresponding to this structure', code='studio.78d4e2923e2ab09d'))
        fixed_ids = [atom.atom_id for atom in self.fixed_atoms]
        if len(set(fixed_ids)) != len(fixed_ids) or not set(fixed_ids) <= set(self.atom_ids):
            raise ValueError(i18n_msg('Fixed atom IDs are duplicated or absent from the current structure', code='studio.69538b36b7981e5e'))
        if any(s not in atomic_numbers or s == 'X' for s in self.symbols):
            raise ValueError(i18n_msg('The structure contains invalid elements or dummy atoms', code='studio.92f32b7edc292e79'))
        if self.kind_labels and len(self.kind_labels) != len(self.symbols):
            raise ValueError(i18n_msg('KIND label count differs from atom count', code='studio.b82781d7de03f191'))
        import re
        if any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*', s) for s in self.kind_labels):
            raise ValueError(i18n_msg('Invalid atom KIND label', code='studio.8111a7b668ccfcbc'))
        mapping = {}
        for label,symbol in zip(self.kind_labels,self.symbols):
            if label in mapping and mapping[label] != symbol:
                raise ValueError(i18n_msg('One KIND label cannot refer to different elements', code='studio.90f6280efb0dea6e'))
            mapping[label] = symbol
        return self

    @property
    def elements(self):
        return sorted(set(self.symbols))

    @property
    def labels(self):
        return self.kind_labels or self.symbols

    @property
    def kind_elements(self):
        return dict(zip(self.labels, self.symbols))

    def reordered(self, atom_ids):
        """Return an ordered subset, preserving identity, KIND and constraints.

        Use this boundary for deletion/reordering rather than independently
        mutating the parallel symbol/position/identity lists.
        """
        ids = list(atom_ids)
        if len(set(ids)) != len(ids) or not set(ids) <= set(self.atom_ids):
            raise ValueError(i18n_msg('Reordering or deletion used duplicate or unknown atom IDs', code='studio.af2d61440d4e288c'))
        indices = {atom_id: i for i, atom_id in enumerate(self.atom_ids)}
        data = self.model_dump()
        for name in ['symbols', 'positions', 'atom_ids', 'kind_labels']:
            if data[name]:
                data[name] = [data[name][indices[atom_id]] for atom_id in ids]
        data['fixed_atoms'] = [atom for atom in data['fixed_atoms'] if atom['atom_id'] in ids]
        return Structure.model_validate(data)


class DatabaseReference(Model):
    path: str
    sha256: str = ''
    entry_sha256: str = ''
    version: str = ''
    source: str = ''
    pack: bool = True


class CustomDatabase(Model):
    path: str
    category: Literal['basis', 'potential']
    version: str = ''


class DatabaseSettings(Model):
    data_directory: str = ''
    declared_version: str = ''
    custom_files: list[CustomDatabase] = Field(default_factory=list)


class RecommendationRecord(Model):
    used: bool = False
    basis_set: str = ''
    potential: str = ''
    note: str = ''


class Kind(Model):
    element: str | None = None
    basis_set: str = ''
    potential: str = ''
    basis_ref: DatabaseReference | None = None
    potential_ref: DatabaseReference | None = None
    recommendation: RecommendationRecord = Field(default_factory=RecommendationRecord)

    @field_validator('element')
    @classmethod
    def valid_element(cls, value):
        if value is not None and (value not in atomic_numbers or value == 'X'):
            raise ValueError(i18n_msg('ELEMENT must be a real element', code='studio.8513a8530df01c40'))
        return value


class GlobalConfig(Model):
    project_name: str = Field(default='cp2k_project', pattern=r'^[A-Za-z0-9][A-Za-z0-9_.-]*$')
    run_type: Literal['ENERGY', 'GEO_OPT', 'VIBRATIONAL_ANALYSIS', 'CELL_OPT', 'MD'] = 'ENERGY'
    print_level: Literal['LOW', 'MEDIUM', 'HIGH'] = 'LOW'


class SCFConfig(Model):
    method: Literal['OT', 'DIAGONALIZATION'] = 'OT'
    eps_scf: float = Field(default=1e-6, gt=0, lt=1)
    max_scf: int = Field(default=100, ge=1)
    guess: Literal['ATOMIC', 'CORE', 'RANDOM'] = 'ATOMIC'
    minimizer: Literal['CG', 'DIIS', 'BROYDEN'] = 'CG'
    preconditioner: Literal['FULL_ALL', 'FULL_KINETIC', 'FULL_SINGLE_INVERSE', 'FULL_S_INVERSE', 'NONE'] = 'FULL_ALL'
    energy_gap: float | None = Field(default=None, strict=True)  # None: omit, use CP2K Auto.
    outer_scf: bool = False
    outer_max_scf: int = Field(default=10, ge=1)
    diagonalization: Literal['STANDARD', 'DAVIDSON'] = 'STANDARD'
    mixing_method: Literal['BROYDEN_MIXING', 'PULAY_MIXING', 'DIRECT_P_MIXING'] = 'BROYDEN_MIXING'
    mixing_alpha: float = Field(default=0.4, gt=0, le=1)
    added_mos: int = Field(default=0, ge=0)
    smearing: bool = False
    electronic_temperature: float = Field(default=300, gt=0)


class DFTConfig(Model):
    charge: int | None = 0
    multiplicity: int | None = Field(default=1, ge=1)
    uks: bool = False
    xc_functional: Literal['PBE', 'BLYP', 'PADE'] | None = None
    basis_files: list[str] = Field(default_factory=list)
    potential_file: str = ''
    potential_files: list[str] = Field(default_factory=list)
    cutoff: float = Field(default=400, gt=0)
    rel_cutoff: float = Field(default=50, gt=0)
    ngrids: int = Field(default=4, ge=1, le=10)
    eps_default: float = Field(default=1e-10, gt=0, lt=1)
    poisson_solver: Literal['PERIODIC', 'MT', 'WAVELET', 'ANALYTIC'] | None = None
    surface_dipole_correction: bool = False
    surf_dip_dir: Literal['X', 'Y', 'Z'] = 'Z'
    scf: SCFConfig = Field(default_factory=SCFConfig)


class MotionConfig(Model):
    optimizer: Literal['BFGS', 'LBFGS', 'CG'] = 'BFGS'
    max_iter: int = Field(default=200, ge=1)
    max_force: float = Field(default=4.5e-4, gt=0)
    rms_force: float = Field(default=3e-4, gt=0)
    max_dr: float = Field(default=3e-3, gt=0)
    rms_dr: float = Field(default=1.5e-3, gt=0)


class CellOptimizationConfig(MotionConfig):
    """Independent joint cell/coordinate optimization; pressures are in bar."""
    max_iter: int = Field(default=200, strict=True, ge=1)
    stress_tensor: Literal['ANALYTICAL'] = 'ANALYTICAL'
    external_pressure: float = 0.0
    pressure_tolerance: float = Field(default=100.0, gt=0)
    keep_angles: bool = False
    keep_symmetry: bool = False
    constraint: Literal['NONE', 'X', 'Y', 'Z', 'XY', 'XZ', 'YZ'] = 'NONE'
    # Used only for this task's FORCE_EVAL/SUBSYS/CELL/SYMMETRY.
    initial_symmetry: CellSymmetry = 'NONE'

    @model_validator(mode='before')
    @classmethod
    def migrate_legacy_type(cls, data):
        # Old Studio projects/presets stored a non-selectable mode. Consume it
        # without mutating the source document or serializing it again.
        if isinstance(data, dict) and 'type' in data:
            if str(data['type']).upper() != 'DIRECT_CELL_OPT':
                raise ValueError(i18n_msg('CELL_OPT: legacy TYPE must be DIRECT_CELL_OPT. Other optimization schemes cannot be migrated to joint cell/coordinate optimization.', code='cellopt.legacy_type_error'))
            data = {key: value for key, value in data.items() if key != 'type'}
        return data


class VibrationalConfig(Model):
    ir_enabled: bool = Field(default=False, strict=True)
    raman_enabled: bool = Field(default=False, strict=True)
    dx: float = Field(default=0.01, gt=0)
    nproc_rep: int = Field(default=1, strict=True, ge=1)
    proc_dist_type: Literal['BLOCKED', 'INTERLEAVED'] = 'BLOCKED'
    fully_periodic: bool = False
    thermochemistry: bool = False
    tc_temperature: float = Field(default=273.15, gt=0)
    tc_pressure: float = Field(default=101325.0, gt=0)
    molden_vib: bool = True
    hessian: bool = False
    linres_eps: float = Field(default=1e-7, gt=0, lt=1)
    linres_max_iter: int = Field(default=200, strict=True, ge=1)
    linres_preconditioner: LinresPreconditioner = 'FULL_ALL'
    linres_energy_gap: float = Field(default=0.1, strict=True, gt=0)

    @field_validator('linres_preconditioner', mode='before')
    @classmethod
    def valid_linres_preconditioner(cls, value):
        if value not in LINRES_PRECONDITIONERS:
            raise ValueError(i18n_msg('VIBRATIONAL_ANALYSIS / LINRES / PRECONDITIONER: select NONE, FULL_ALL, FULL_SINGLE_INVERSE, FULL_SINGLE, FULL_KINETIC or FULL_S_INVERSE.', code='vib.linres_preconditioner_error'))
        return value

    @field_validator('linres_energy_gap', mode='before')
    @classmethod
    def valid_linres_energy_gap(cls, value):
        try:
            valid = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0
        except (ValueError, TypeError, OverflowError):
            valid = False
        if not valid:
            raise ValueError(i18n_msg('VIBRATIONAL_ANALYSIS / LINRES / ENERGY_GAP: enter a finite positive real number in Ha.', code='vib.linres_energy_gap_error'))
        return value

    @model_validator(mode='before')
    @classmethod
    def migrate_legacy_mode(cls, data):
        """Normalize full projects and partial preset patches without defaults.

        Explicit new switches win when a document contains both generations.
        Never modify the source mapping or reset unrelated LINRES parameters.
        """
        if not isinstance(data, dict) or 'mode' not in data:
            return data
        aliases = {
            'FREQUENCIES': (False, False), 'FREQUENCIES_ONLY': (False, False),
            'FREQUENCIES & NORMAL MODES': (False, False),
            'FREQUENCIES_AND_NORMAL_MODES': (False, False),
            'IR': (True, False), 'IR_INTENSITIES': (True, False), 'IR INTENSITIES': (True, False),
            'RAMAN': (False, True), 'RAMAN_INTENSITIES': (False, True), 'RAMAN INTENSITIES': (False, True),
            'IR_RAMAN': (True, True), 'IR+RAMAN': (True, True), 'IR + RAMAN': (True, True),
        }
        legacy = str(data['mode']).strip().upper()
        if legacy not in aliases:
            raise ValueError(i18n_msg('VIBRATIONAL_ANALYSIS: unknown legacy mode {mode}; the IR/Raman switches cannot be migrated safely.', code='vib.legacy_mode_error', mode=data['mode']))
        result = {key: value for key, value in data.items() if key != 'mode'}
        ir, raman = aliases[legacy]
        result.setdefault('ir_enabled', ir)
        result.setdefault('raman_enabled', raman)
        return result

    @property
    def enabled_spectra(self):
        return tuple(name for name, enabled in [('IR', self.ir_enabled), ('RAMAN', self.raman_enabled)] if enabled)

    @property
    def spectra_label(self):
        return ' + '.join(self.enabled_spectra) or 'FREQUENCIES'

    @property
    def intensities(self):
        # Derived from the switches so contradictory projects cannot
        # request intensities without the corresponding property calculation.
        return self.ir_enabled or self.raman_enabled


class MDConfig(Model):
    """Born–Oppenheimer MD; time in fs, temperature in K."""
    ensemble: Literal['NVT', 'NVE'] = 'NVT'
    steps: int = Field(default=2000, strict=True, ge=1)
    timestep: float = Field(default=0.5, gt=0)
    temperature: float = Field(default=300.0, ge=0)
    initialization_method: Literal['DEFAULT'] = 'DEFAULT'
    thermostat_type: Literal['CSVR'] = 'CSVR'
    timecon: float = Field(default=100.0, gt=0)
    write_trajectory: bool = True
    trajectory_format: Literal['XYZ', 'EXTXYZ'] = 'XYZ'
    trajectory_interval: int = Field(default=10, strict=True, ge=1)
    write_restart: bool = True
    restart_interval: int = Field(default=100, strict=True, ge=1)
    backup_copies: int = Field(default=2, strict=True, ge=0)
    continue_from_restart: bool = False
    restart_file: str = ''

    @field_validator('steps', 'trajectory_interval', 'restart_interval', 'backup_copies', mode='before')
    @classmethod
    def valid_integer(cls, value, info):
        minimum = 0 if info.field_name == 'backup_copies' else 1
        if type(value) is not int or value < minimum:
            raise ValueError(i18n_msg('MD: {parameter} must be an integer greater than or equal to {minimum}.',
                code='md.integer_error', parameter=info.field_name.upper(), minimum=minimum))
        return value

    @field_validator('timestep', 'temperature', 'timecon', mode='before')
    @classmethod
    def valid_real(cls, value, info):
        nonnegative = info.field_name == 'temperature'
        valid = isinstance(value, (int, float)) and not isinstance(value, bool)
        try:
            valid = valid and math.isfinite(value) and (value >= 0 if nonnegative else value > 0)
        except OverflowError:
            valid = False
        if not valid:
            if nonnegative:
                message = i18n_msg('MD: {parameter} must be a finite nonnegative number.', code='md.nonnegative_error', parameter=info.field_name.upper())
            else:
                message = i18n_msg('MD: {parameter} must be a finite positive number.', code='md.positive_error', parameter=info.field_name.upper())
            raise ValueError(message)
        return value

    @field_validator('ensemble', 'thermostat_type', 'initialization_method', 'trajectory_format', mode='before')
    @classmethod
    def supported_option(cls, value, info):
        choices = {'ensemble': ('NVT', 'NVE'), 'thermostat_type': ('CSVR',),
                   'initialization_method': ('DEFAULT',), 'trajectory_format': ('XYZ', 'EXTXYZ')}
        if value not in choices[info.field_name]:
            raise ValueError(i18n_msg('MD: unsupported {parameter}; supported values: {choices}.', code='md.option_error',
                parameter=info.field_name.upper(), choices=', '.join(choices[info.field_name])))
        return value

    @property
    def simulation_time_ps(self):
        return self.steps * self.timestep / 1000


class Project(Model):
    _migration_warnings: list[str] = PrivateAttr(default_factory=list)
    format_version: Literal[1] = 1
    cp2k_version: Literal['2026.1'] = '2026.1'
    global_settings: GlobalConfig = Field(default_factory=GlobalConfig)
    dft: DFTConfig = Field(default_factory=DFTConfig)
    structure: Structure | None = None
    kinds: dict[str, Kind] = Field(default_factory=dict)
    motion: MotionConfig = Field(default_factory=MotionConfig)
    cell_opt: CellOptimizationConfig = Field(default_factory=CellOptimizationConfig)
    vibrational: VibrationalConfig = Field(default_factory=VibrationalConfig)
    md: MDConfig = Field(default_factory=MDConfig)
    run_environment: RunEnvironment = Field(default_factory=RunEnvironment)
    xml_spec: str | None = None
    databases: DatabaseSettings = Field(default_factory=DatabaseSettings)

    @field_validator('kinds')
    @classmethod
    def valid_kinds(cls, value):
        import re
        for label, kind in value.items():
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*', label):
                raise ValueError(i18n_msg('Invalid KIND label format', code='studio.f7f0fb9407a14124'))
            if kind.element is None and (label not in atomic_numbers or label == 'X'):
                raise ValueError(i18n_msg('KIND {p0} requires an explicit ELEMENT', code='studio.da7d29a23b2baf91', p0=label))
        return value
