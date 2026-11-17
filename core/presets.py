"""Reusable calculation presets, separate from projects and CP2K input files."""
from i18n.messages import i18n_msg, i18n_str
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from core.resources import resource_path
from typing import Literal
from uuid import uuid4
import yaml
from pydantic import Field, field_validator, model_validator
from core.models import Model, Project, Structure, Kind, Vector, Periodic, StructureType, VibrationalConfig
from core.project_io import _atomic_text, _resolved_resources, relocate_project_resources
from core.validator import validate_project

BUILTIN_DIRECTORY = resource_path('presets')


class CellSettings(Model):
    cell: tuple[Vector, Vector, Vector]
    periodic: Periodic


class Coordinates(Model):
    symbols: list[str]
    positions: list[Vector]
    kind_labels: list[str] = Field(default_factory=list)
    structure_type: StructureType = 'unclassified'

    @model_validator(mode='after')
    def valid_structure(self):
        Structure(**self.model_dump())
        return self


class Preset(Model):
    format_version: Literal[1] = 1
    cp2k_version: Literal['2026.1'] = '2026.1'
    id: str = Field(default_factory=lambda: uuid4().hex, pattern=r'^[A-Za-z0-9_-]+$')
    name: str
    description: str = ''
    category: Literal['single_point', 'geo_opt', 'custom'] = 'custom'
    parameters: dict = Field(default_factory=dict)
    cell_settings: CellSettings | None = None
    coordinates: Coordinates | None = None
    incomplete: bool = True
    validation_messages: list[str] = Field(default_factory=list)
    syntax_validated: Literal[False] = False

    @field_validator('*')
    @classmethod
    def safe_strings(cls, value, info):
        if info.field_name == 'description':
            if '\x00' in value:
                raise ValueError(i18n_msg('Description cannot contain NUL characters', code='studio.5b1f33296bb9dd40'))
            return value
        return Model.safe_strings(value)

    @field_validator('name')
    @classmethod
    def nonempty_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError(i18n_msg('Preset name cannot be empty', code='studio.1e396cf6fce01868'))
        return value

    @field_validator('parameters')
    @classmethod
    def calculation_parameters_only(cls, value):
        allowed = {'global_settings', 'dft', 'motion', 'vibrational', 'cell_opt', 'md', 'kinds', 'databases'}
        if set(value) - allowed:
            raise ValueError(i18n_msg('Preset calculation parameters cannot implicitly include structure, XML, or project format settings', code='studio.2d7c76018b9d74f8'))
        # Migrate the patch before merging with existing new-style switches;
        # otherwise an old mode could be shadowed by the target's False values.
        if 'vibrational' in value:
            value = dict(value, vibrational=VibrationalConfig.migrate_legacy_mode(value['vibrational']))
        Project.model_validate(value)  # Validate nested partial patches against the real models.
        return value


def capture_preset(project, name, description='', category='custom', *, include_cell=False,
                   include_coordinates=False, preset_id=None):
    project = _resolved_resources(project, Path.cwd())
    data = project.model_dump()
    checked = validate_project(project)
    values = dict(name=name, description=description, category=category,
        parameters={key: data[key] for key in ['global_settings', 'dft', 'motion', 'vibrational', 'cell_opt', 'md', 'kinds', 'databases']},
        incomplete=not checked.ok, validation_messages=checked.errors)
    if preset_id:
        values['id'] = preset_id
    if include_cell or include_coordinates:
        if project.structure is None:
            raise ValueError(i18n_msg('No structure is available to save cell or coordinate settings', code='studio.ebf896674bae4bbe'))
        if include_cell:
            values['cell_settings'] = CellSettings(cell=project.structure.cell, periodic=project.structure.periodic)
        if include_coordinates:
            values['coordinates'] = Coordinates(symbols=project.structure.symbols,
                positions=project.structure.positions, kind_labels=project.structure.kind_labels,
                structure_type=project.structure.structure_type)
    return Preset(**values)


def builtin_preset(name):
    definitions = {'single_point': (i18n_msg('Single-Point Preset', code='studio.5091f86f26dfeeeb'), 'single_point'), 'geo_opt': (i18n_msg('Geometry Optimization Preset', code='studio.bd64d9d635949360'), 'geo_opt')}
    if name not in definitions:
        raise KeyError(i18n_msg('Unknown built-in preset: {p0}', code='studio.585d3ad95c8aa494', p0=name))
    title, category = definitions[name]
    patch = yaml.safe_load((BUILTIN_DIRECTORY / f'{name}.yaml').read_text(encoding='utf-8'))
    return Preset(id=f'builtin-{name}', name=title, category=category, parameters=patch,
                  description=i18n_msg('Only workflow settings are applied; missing chemistry is not filled in.', code='studio.fb99d1d00258e087'))


def _merge(target, patch):
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = deepcopy(value)


@dataclass
class PresetApplication:
    project: Project
    changes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    includes_structure: bool = False


def apply_preset(project: Project, preset: Preset) -> PresetApplication:
    """Plan an application without mutating either the current project or preset."""
    data = project.model_dump()
    patch = deepcopy(preset.parameters)
    saved_kinds = patch.pop('kinds', None)
    _merge(data, patch)
    structure = deepcopy(data['structure'])
    if preset.coordinates:
        st = Structure.model_validate(structure or {})
        structure = st.model_dump()
        coordinates = preset.coordinates.model_dump()
        if st.periodicity_locked:
            if preset.coordinates.structure_type == 'periodic_structure':
                raise ValueError(i18n_msg('CELL: a periodic preset cannot unlock a confirmed isolated molecule. Import the new periodic structure explicitly.', code='periodicity.preset_error'))
            if preset.coordinates.structure_type == 'unclassified':
                # Older coordinate presets have no reliable source type.
                coordinates.pop('structure_type')
        structure.update(coordinates)
        # Explicit coordinate replacement is a new identity domain. Reusable
        # presets never carry or inherit another structure's fixed atom IDs.
        structure['atom_ids'] = []
        structure['fixed_atoms'] = []
        structure['source'] = None
    if preset.cell_settings:
        structure = structure or Structure().model_dump()
        structure.update(preset.cell_settings.model_dump())
    data['structure'] = structure
    warnings = []
    if saved_kinds is not None:
        saved = {label: Kind.model_validate(kind) for label, kind in saved_kinds.items()}
        st = Structure.model_validate(structure) if structure else None
        if st and st.symbols:
            matched = {}
            for label, element in st.kind_elements.items():
                exact = saved.get(label)
                options = [(key, kind) for key, kind in saved.items() if (kind.element or key) == element]
                if exact and (exact.element or label) == element:
                    chosen = exact
                elif options and all(kind.model_dump(exclude={'recommendation'}) == options[0][1].model_dump(exclude={'recommendation'}) for _, kind in options):
                    chosen = options[0][1]
                else:
                    chosen = Kind(element=element)
                    warnings.append(i18n_msg('KIND {p0} / {p1}: no unique preset match exists. Selection remains empty; configure its basis and pseudopotential.', code='studio.a777b684a3f0c770', p0=label, p1=element))
                record = chosen.model_dump()
                record['element'] = element
                matched[label] = record
            data['kinds'] = matched
        else:
            data['kinds'] = saved_kinds
            warnings.append(i18n_msg('No atomic structure is present. Preset KINDs were retained; verify element configurations after importing a structure.', code='studio.d8dc82764a17f88e'))
    candidate = relocate_project_resources(Project.model_validate(data))
    changes = []
    for label, old, new in [
        ('GLOBAL', project.global_settings, candidate.global_settings),
        ('DFT / SCF', project.dft, candidate.dft), (i18n_msg('Basis, pseudopotential, and database sources', code='studio.082c13c38ebd1e32'), project.kinds, candidate.kinds),
        (i18n_msg('Geometry Optimization', code='studio.5688511fca2c8507'), project.motion, candidate.motion),
        (i18n_msg('Vibrational Analysis', code='vib.name'), project.vibrational, candidate.vibrational),
        (i18n_msg('Cell Optimization', code='cellopt.name'), project.cell_opt, candidate.cell_opt),
        (i18n_msg('Molecular Dynamics', code='md.name'), project.md, candidate.md),
        (i18n_msg('Database Settings', code='studio.ff513eba23a1b94e'), project.databases, candidate.databases)]:
        if old != new:
            changes.append(label)
    if preset.cell_settings and (not project.structure or project.structure.cell != candidate.structure.cell or project.structure.periodic != candidate.structure.periodic):
        changes.append(i18n_msg('Cell & Periodicity', code='studio.5261b980378d173d'))
    if preset.coordinates:
        changes.append(i18n_msg('Atomic structure and coordinates (explicitly included in preset)', code='studio.624c007a881b5b2d'))
    if preset.incomplete and not preset.id.startswith('builtin-'):
        warnings.append(i18n_msg('This preset was saved as an incomplete draft. Validate the configuration after applying it.', code='studio.d341957c4dfe9dc2'))
    return PresetApplication(candidate, changes, warnings, bool(preset.cell_settings or preset.coordinates))


@dataclass
class PresetListing:
    presets: list[Preset] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


class PresetStore:
    """UUID file names, atomic writes and explicit collision handling."""
    def __init__(self, directory):
        self.directory = Path(directory)

    def path(self, identifier):
        if not identifier or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in identifier):
            raise ValueError(i18n_msg('Invalid preset identifier', code='studio.12860345cff0140d'))
        return self.directory / f'{identifier}.json'

    def list(self):
        result = PresetListing()
        try:
            paths = sorted(self.directory.glob('*.json'))
        except OSError as exc:
            result.problems.append(i18n_str(exc))
            return result
        for path in paths:
            try:
                preset = self.load(path.stem)
                result.presets.append(preset)
            except (OSError, ValueError) as exc:
                result.problems.append(f'{path.name}：{exc}')
        result.presets.sort(key=lambda p: p.name.casefold())
        return result

    def load(self, identifier):
        path = self.path(identifier)
        if path.stat().st_size > 100 * 1024 * 1024:
            raise ValueError(i18n_msg('Preset file exceeds 100 MB', code='studio.8ca34bc2eb1ba4ff'))
        preset = Preset.model_validate_json(path.read_text(encoding='utf-8'))
        if preset.id != identifier:
            raise ValueError(i18n_msg('Preset filename does not match its identifier', code='studio.52944b7bcb075369'))
        return preset

    def save(self, preset: Preset, *, overwrite=False):
        preset = Preset.model_validate(preset.model_dump())
        listing = self.list()
        duplicate = next((p for p in listing.presets if p.name.casefold() == preset.name.casefold() and p.id != preset.id), None)
        target = duplicate.id if duplicate else preset.id
        path = self.path(target)
        if (duplicate or path.exists()) and not overwrite:
            raise FileExistsError(i18n_msg('Preset “{p0}” already exists; confirm overwrite or choose another name', code='studio.c1f8311bbe7e3e0c', p0=preset.name))
        data = preset.model_dump()
        data['id'] = target
        saved = Preset.model_validate(data)
        _atomic_text(path, saved.model_dump_json(indent=2) + '\n')
        if duplicate and preset.id != target and self.path(preset.id).exists():
            self.path(preset.id).unlink()
        return saved

    def delete(self, identifier):
        self.path(identifier).unlink()
