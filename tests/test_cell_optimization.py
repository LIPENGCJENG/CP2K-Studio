"""CELL_OPT syntax, scope, independent state and final exported artifacts."""
import json
from io import TextIOWrapper
from pathlib import Path
import zipfile
import numpy as np
import pytest
from ase.build import bulk
from ase.cell import Cell
from pydantic import ValidationError
from core.models import Project, Structure, Kind, CellOptimizationConfig, FixedAtom
from core.generator import generate_input, GenerationError
from core.validator import validate_project
from core.cell_optimization import matches_cell_symmetry
from core.schema import CP2KSchema
from core.comprehensive_check import comprehensive_check
from core.project_io import save_project, load_project, export_bundle
from core.input_export import export_input
from core.input_import import import_input
from core.presets import Preset, PresetStore, capture_preset, apply_preset
from core.run_script_generator import generate_run_script


@pytest.fixture
def crystal(water):
    atoms = bulk('Si', 'diamond', a=5.43, cubic=True)
    water.structure = Structure(symbols=atoms.get_chemical_symbols(), positions=atoms.positions.tolist(),
        cell=atoms.cell.tolist(), periodic='XYZ', structure_type='periodic_structure')
    water.kinds = {'Si': Kind(basis_set='DZVP-MOLOPT-SR-GTH', potential='GTH-PBE-q4')}
    water.dft.poisson_solver = 'PERIODIC'
    water.global_settings.run_type = 'CELL_OPT'
    return water


def codes(messages):
    return {getattr(message, 'code', None) for message in messages}


@pytest.mark.parametrize('optimizer', ['BFGS', 'LBFGS', 'CG'])
@pytest.mark.parametrize('constraint', ['NONE', 'X', 'Y', 'Z', 'XY', 'XZ', 'YZ'])
def test_direct_cell_opt_generates_all_parameters_with_target_xml(crystal, validator, optimizer, constraint):
    c = crystal.cell_opt
    c.optimizer, c.constraint = optimizer, constraint
    c.external_pressure = -125.25
    c.pressure_tolerance = 80.5
    c.max_iter = 321
    c.max_force, c.rms_force, c.max_dr, c.rms_dr = 1.5e-4, 1e-4, 2e-3, 1e-3
    c.keep_angles = c.keep_symmetry = True
    c.initial_symmetry = 'CUBIC'
    before = crystal.model_dump_json()
    text = generate_input(crystal)
    parsed = validator.parse(text)
    assert parsed.ok, parsed.errors
    tree = parsed.tree
    assert tree['+global']['run_type'] == 'cell_opt'
    assert '+cell_opt' not in tree and '+vibrational_analysis' not in tree
    assert '+geo_opt' not in tree['+motion']
    node = tree['+motion']['+cell_opt']
    assert 'type' not in node and 'TYPE DIRECT_CELL_OPT' not in text
    for key in ['optimizer', 'constraint']:
        assert node[key] == getattr(c, key).lower()
    for key in ['external_pressure', 'pressure_tolerance', 'max_iter', 'max_force', 'rms_force', 'max_dr', 'rms_dr', 'keep_angles', 'keep_symmetry']:
        assert node[key] == getattr(c, key)
    assert 'EXTERNAL_PRESSURE -125.25' in text
    force = tree['+force_eval'][0]
    assert force['stress_tensor'] == 'analytical'
    assert force['+subsys']['+cell']['symmetry'] == 'cubic'
    assert force['+subsys']['+cell']['periodic'] == force['+dft']['+poisson']['periodic'] == 'xyz'
    assert crystal.model_dump_json() == before


def test_official_2026_1_fixture_and_explicit_zero_pressure(crystal, validator):
    source = Path(__file__).parent / 'fixtures' / 'upstream_cell_opt_argon.inp'
    checked = validator.parse(source.read_text())
    # Preserve the historical upstream fixture, but do not certify its removed
    # keyword as compatible with the executable behavior reported by users.
    assert 'cellopt.removed_type_error' in codes(checked.errors)
    assert checked.tree['+motion']['+cell_opt']['type'] == 'direct_cell_opt'
    actual = validator.parse(generate_input(crystal))
    assert actual.ok
    for tree in [checked.tree, actual.tree]:
        assert tree['+force_eval'][0]['stress_tensor'] == 'analytical'
    node = actual.tree['+motion']['+cell_opt']
    assert 'type' not in node
    assert node['external_pressure'] == 0 and node['pressure_tolerance'] == 100
    assert not node['keep_angles'] and not node['keep_symmetry']
    assert 'EXTERNAL_PRESSURE ' in generate_input(crystal)
    schema = CP2KSchema()
    assert schema.keyword('MOTION/CELL_OPT', 'CONSTRAINT')['enum'] == ['NONE', 'X', 'Y', 'Z', 'XY', 'XZ', 'YZ']


@pytest.mark.parametrize('periodic', ['NONE', 'X', 'Y', 'Z', 'XY', 'XZ', 'YZ'])
def test_other_periodicities_are_blocked_without_mutation(crystal, periodic):
    crystal.structure.periodic = periodic
    before = crystal.model_dump_json()
    result = validate_project(crystal)
    assert 'cellopt.periodicity_error' in codes(result.errors)
    with pytest.raises(GenerationError):
        generate_input(crystal)
    assert crystal.model_dump_json() == before


@pytest.mark.parametrize('solver', ['WAVELET', 'MT', 'ANALYTIC', None])
def test_unsupported_stress_solver_combinations_are_explicit(crystal, solver):
    crystal.dft.poisson_solver = solver
    before = crystal.model_dump_json()
    assert 'cellopt.stress_error' in codes(validate_project(crystal).errors)
    assert crystal.model_dump_json() == before


@pytest.mark.parametrize('cell,code', [
    (((0,0,0),(0,5,0),(0,0,5)), 'cellopt.volume_error'),
    (((5,0,0),(5,0,0),(0,0,5)), 'cellopt.volume_error'),
    (((-5,0,0),(0,5,0),(0,0,5)), 'cellopt.volume_error'),
    (((1e200,0,0),(0,1e200,0),(0,0,1e200)), 'cellopt.volume_error'),
    (((0,5,0),(-5,0,0),(0,0,5)), 'cellopt.orientation_error'),
    (((5,0,0),(0,5,1),(0,0,5)), 'cellopt.orientation_error')])
def test_invalid_cells_and_noncanonical_orientation_are_rejected(crystal, cell, code):
    crystal.structure.cell = cell
    before = crystal.model_dump_json()
    assert code in codes(validate_project(crystal).errors)
    assert crystal.model_dump_json() == before


def test_general_triclinic_cell_preserves_all_components_and_coordinates(crystal, validator):
    crystal.structure.cell = ((5.43,0,0), (.823456789123,5.12,0), (.23,.45,5.67891234567))
    crystal.structure.positions[0] = (.123456789123, .45, .67)
    before = crystal.model_dump_json()
    text = generate_input(crystal)
    parsed = validator.parse(text)
    assert parsed.ok
    assert parsed.tree['+force_eval'][0]['+subsys']['+cell']['b'][0] == .823456789123
    assert 'Si 0.123456789123 0.45 0.67' in text
    assert crystal.model_dump_json() == before


def test_keep_symmetry_requires_explicit_matching_metric(crystal, validator):
    crystal.cell_opt.keep_symmetry = True
    assert 'cellopt.symmetry_missing' in codes(validate_project(crystal).errors)
    crystal.cell_opt.initial_symmetry = 'CUBIC'
    assert validate_project(crystal).ok
    assert validator.parse(generate_input(crystal)).ok
    crystal.structure.cell = ((5,0,0),(0,6,0),(0,0,7))
    assert 'cellopt.symmetry_mismatch' in codes(validate_project(crystal).errors)
    crystal.cell_opt.initial_symmetry = 'ORTHORHOMBIC'
    assert validate_project(crystal).ok


@pytest.mark.parametrize('symmetry,parameters', [
    ('CUBIC', [5,5,5,90,90,90]), ('ORTHORHOMBIC',[5,6,7,90,90,90]),
    ('TETRAGONAL_AB',[5,5,7,90,90,90]), ('TETRAGONAL_AC',[5,7,5,90,90,90]),
    ('TETRAGONAL_BC',[7,5,5,90,90,90]), ('MONOCLINIC',[5,6,7,90,110,90]),
    ('MONOCLINIC_GAMMA_AB',[5,5,7,90,90,110]), ('RHOMBOHEDRAL',[5,5,5,75,75,75]),
    ('HEXAGONAL_GAMMA_60',[5,5,7,90,90,60]), ('HEXAGONAL_GAMMA_120',[5,5,7,90,90,120]),
    ('TRICLINIC',[5,6,7,75,85,95])])
def test_initial_symmetry_metrics(symmetry, parameters):
    assert matches_cell_symmetry(Cell.fromcellpar(parameters), symmetry)
    assert not matches_cell_symmetry(Cell.fromcellpar([5,6,7,75,85,95]), 'CUBIC')


@pytest.mark.parametrize('key,value', [('max_iter', 0), ('max_force', -1), ('rms_force',0),
    ('max_dr',float('nan')), ('rms_dr',float('inf')), ('external_pressure',float('inf')),
    ('pressure_tolerance',0), ('type','GEO_OPT'), ('stress_tensor','NUMERICAL'), ('constraint','XYZ')])
def test_invalid_cell_opt_parameters_are_rejected(key, value):
    with pytest.raises(ValidationError):
        CellOptimizationConfig(**{key:value})


def test_fixed_atoms_are_preserved_after_reorder_and_all_tasks_are_isolated(crystal, validator):
    crystal.structure.fixed_atoms = [FixedAtom(atom_id=1, components='XYZ'), FixedAtom(atom_id=3,components='Z')]
    crystal.structure = crystal.structure.reordered(list(reversed(crystal.structure.atom_ids)))
    assert 'cellopt.fixed_warning' in codes(validate_project(crystal).warnings)
    tree = validator.parse(generate_input(crystal)).tree
    sections = tree['+motion']['+constraint']['+fixed_atoms']
    by_component = {s['components_to_fix']: s['list'][0] for s in sections}
    assert by_component == {'xyz': 8, 'z': 6}
    crystal.cell_opt.initial_symmetry = 'CUBIC'
    for task in ['ENERGY', 'GEO_OPT', 'VIBRATIONAL_ANALYSIS']:
        crystal.global_settings.run_type = task
        text = generate_input(crystal)
        assert '&CELL_OPT' not in text and 'STRESS_TENSOR' not in text and 'SYMMETRY CUBIC' not in text
        assert ('&FIXED_ATOMS' in text) is (task == 'GEO_OPT')


def test_legacy_projects_presets_and_cell_opt_roundtrip(crystal, tmp_path):
    old = crystal.model_dump()
    old['global_settings']['run_type'] = 'GEO_OPT'
    old.pop('cell_opt')
    path = tmp_path / 'project.json'
    path.write_text(json.dumps(old))
    assert load_project(path).cell_opt == CellOptimizationConfig()
    legacy_preset = Preset(name='legacy', parameters={'global_settings': {'run_type': 'GEO_OPT'}, 'motion': {'max_iter':333}})
    applied = apply_preset(crystal, legacy_preset).project
    assert applied.motion.max_iter == 333 and applied.cell_opt == crystal.cell_opt
    crystal.cell_opt.external_pressure = 12.3
    crystal.cell_opt.optimizer = 'LBFGS'
    save_project(crystal, path)
    restored = load_project(path)
    assert restored == crystal
    store = PresetStore(tmp_path / 'presets')
    preset = store.save(capture_preset(crystal, 'Si cell optimization'))
    assert preset.coordinates is None and preset.cell_settings is None
    applied = apply_preset(Project(), store.load(preset.id)).project
    assert applied.cell_opt == crystal.cell_opt and applied.global_settings.run_type == 'CELL_OPT'
    text = generate_input(restored)
    inp = tmp_path / 'cell.inp'
    inp.write_text(text)
    imported, warnings = import_input(inp)
    assert imported.cell_opt == restored.cell_opt
    assert imported.structure.cell == restored.structure.cell


def test_comprehensive_check_standalone_and_final_zip_keep_requested_input(crystal, tmp_path, validator):
    before = crystal.model_dump_json()
    result = comprehensive_check(crystal)
    assert all(s.executed for s in result.stages)
    assert result.validation.ok and not result.validation.warnings, result.report()
    standalone = export_input(crystal, tmp_path / 'standalone.inp')
    assert standalone.path.read_text() == generate_input(crystal)
    assert 'TYPE DIRECT_CELL_OPT' not in standalone.path.read_text()
    destination = export_bundle(crystal, tmp_path / 'cell.zip', archive=True)
    with zipfile.ZipFile(destination) as archive:
        assert {'input.inp','structure.xyz','run.sh','EXPORT_NOTES.txt','project.cp2kstudio.json'} <= set(archive.namelist())
        # Match Path.read_text's universal-newline behavior. Windows exports
        # may use CRLF, while the XML parser expects logical text lines.
        with TextIOWrapper(archive.open('input.inp'), encoding='utf-8') as stream:
            text = stream.read()
        parsed = validator.parse(text)
        assert parsed.ok, parsed.errors
        tree = parsed.tree
        assert 'type' not in tree['+motion']['+cell_opt']
        assert tree['+motion']['+cell_opt']['external_pressure'] == 0
        assert 'COORD_FILE_NAME structure.xyz' in text
        assert archive.read('run.sh').decode() == generate_run_script(crystal.run_environment)
        notes = archive.read('EXPORT_NOTES.txt').decode()
        assert 'INITIAL structure' in notes and '初始结构' in notes
        assert 'No calculation' in notes and 'ANALYTICAL' in notes
        config = Project.model_validate_json(archive.read('project.cp2kstudio.json'))
        assert config.cell_opt == crystal.cell_opt and config.structure == crystal.structure
    assert crystal.model_dump_json() == before
