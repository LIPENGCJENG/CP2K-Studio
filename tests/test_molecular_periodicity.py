"""Confirmed boundaries are persistent metadata, never inferred from NONE."""
from pathlib import Path
import pytest
from pydantic import ValidationError
from core.models import Structure, FixedAtom, BoxGenerationSettings
from core.structure import load_structure, generate_nonperiodic_box, generate_simulation_box
from core.project_io import save_project, load_project
from core.presets import Preset, capture_preset, apply_preset
from core.generator import generate_input, GenerationError
from core.validator import validate_project

FIXTURES = Path(__file__).parent / 'fixtures' / 'xsd'


@pytest.mark.parametrize('filename,kind,locked', [('h2o_ms23.xsd', 'isolated_molecule', True),
    ('rutile_ms23.xsd', 'periodic_structure', False), ('slab_ms23.xsd', 'periodic_structure', False)])
def test_type_comes_from_xsd_system_not_filename_or_current_periodicity(filename, kind, locked):
    structure = load_structure(FIXTURES / filename)
    assert structure.structure_type == kind and structure.periodicity_locked is locked
    if not locked:
        structure.periodic = 'NONE'
        assert not structure.periodicity_locked and structure.structure_type == 'periodic_structure'


def test_legacy_none_with_xsd_source_is_not_inferred_as_confirmed():
    data = load_structure(FIXTURES / 'h2o_ms23.xsd').model_dump()
    data.pop('structure_type')
    old = Structure.model_validate(data)
    assert old.periodic == 'NONE' and old.structure_type == 'unclassified'
    assert not old.periodicity_locked


def test_assignment_and_corrupt_project_data_cannot_override_lock(water):
    structure = load_structure(FIXTURES / 'h2o_ms23.xsd')
    before = structure.model_dump_json()
    with pytest.raises(ValidationError):
        structure.periodic = 'XYZ'
    assert structure.model_dump_json() == before
    bad = structure.model_dump()
    bad['periodic'] = 'XZ'
    with pytest.raises(ValidationError):
        Structure.model_validate(bad)
    water.structure = structure.model_copy(update={'periodic': 'XYZ'})
    assert not validate_project(water).ok
    with pytest.raises(GenerationError):
        generate_input(water)


def test_cell_box_coordinates_constraints_and_reordering_remain_editable():
    original = load_structure(FIXTURES / 'h2o_ms23.xsd')
    original.fixed_atoms = [FixedAtom(atom_id=2, components='Z')]
    boxed = generate_nonperiodic_box(original, 5)
    boxed.cell = ((14,0,0), (0,15,0), (0,0,16))
    boxed.positions[0] = (4.1, 5.2, 6.3)
    reordered = boxed.reordered([3, 2, 1])
    assert reordered.periodicity_locked and reordered.periodic == 'NONE'
    assert reordered.fixed_atoms == boxed.fixed_atoms and reordered.cell == boxed.cell


def test_project_and_coordinate_preset_preserve_molecular_type(water, tmp_path):
    water.structure = generate_simulation_box(load_structure(FIXTURES / 'h2o_ms23.xsd'), BoxGenerationSettings(mode='CUBIC', cubic_margin=5))
    water.dft.poisson_solver = 'WAVELET'
    path = tmp_path / 'molecule.json'
    save_project(water, path)
    restored = load_project(path)
    assert restored.structure.periodicity_locked
    assert restored.structure == water.structure
    preset = capture_preset(water, 'molecule', include_coordinates=True, include_cell=True)
    assert preset.coordinates.structure_type == 'isolated_molecule'
    target = water.model_copy(deep=True)
    target.structure.structure_type = 'unclassified'
    applied = apply_preset(target, preset).project
    assert applied.structure.periodicity_locked and applied.structure.periodic == 'NONE'


@pytest.mark.parametrize('coordinates', [False, True])
def test_periodic_cell_preset_is_rejected_without_mutating_locked_project(water, coordinates):
    water.structure = generate_nonperiodic_box(load_structure(FIXTURES / 'h2o_ms23.xsd'), 5)
    before = water.model_dump_json()
    data = {'name': 'periodic', 'cell_settings': {'cell': [[8,0,0], [0,8,0], [0,0,8]], 'periodic': 'XYZ'}}
    if coordinates:
        data['coordinates'] = {'symbols': ['O','H','H'], 'positions': [[0,0,0],[0,.7,.5],[0,-.7,.5]]}
    with pytest.raises(ValidationError):
        apply_preset(water, Preset.model_validate(data))
    assert water.model_dump_json() == before


def test_periodic_typed_coordinates_cannot_unlock_molecule(water):
    water.structure = load_structure(FIXTURES / 'h2o_ms23.xsd')
    preset = Preset(name='periodic coordinates', coordinates={
        'symbols': ['O','H','H'], 'positions': [[0,0,0],[0,.7,.5],[0,-.7,.5]],
        'structure_type': 'periodic_structure'})
    with pytest.raises(ValueError):
        apply_preset(water, preset)
    assert water.structure.periodicity_locked


@pytest.mark.parametrize('run_type', ['ENERGY', 'GEO_OPT', 'VIBRATIONAL_ANALYSIS'])
def test_cell_and_poisson_none_match_for_every_task(water, validator, run_type):
    water.structure = generate_simulation_box(load_structure(FIXTURES / 'h2o_ms23.xsd'), BoxGenerationSettings(mode='CUBIC', cubic_margin=5))
    water.dft.poisson_solver = 'WAVELET'
    water.global_settings.run_type = run_type
    result = validator.parse(generate_input(water))
    assert result.ok, result.errors
    force = result.tree['+force_eval'][0]
    assert force['+subsys']['+cell']['periodic'] == force['+dft']['+poisson']['periodic'] == 'none'
    assert result.tree['+global']['preferred_fft_library'] == 'fftsg'
