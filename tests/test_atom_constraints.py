"""Stable identity, Cartesian selection, CP2K fractional constraints and IO."""
import json
import pytest
from pydantic import ValidationError
from core.atom_constraints import (COMPONENTS, fixed_atom_groups, select_coordinate_range, set_fixed_atoms)
from core.models import Structure
from core.generator import generate_input
from core.project_io import save_project, load_project, export_bundle
from core.input_export import export_input
from core.input_import import import_input
from core.presets import capture_preset, apply_preset, builtin_preset
from core.comprehensive_check import comprehensive_check


def parsed_groups(validator, text, directory='.'):
    result = validator.parse(text, directory)
    assert result.ok, result.errors
    return {section['components_to_fix'].upper(): [number for numbers in section['list']
            for number in ((numbers,) if isinstance(numbers, int) else numbers)]
            for section in result.tree['+motion']['+constraint']['+fixed_atoms']}


@pytest.mark.parametrize('components', COMPONENTS)
def test_each_component_generates_real_xml_valid_constraint(water, validator, components):
    water.global_settings.run_type = 'GEO_OPT'
    water.structure = set_fixed_atoms(water.structure, [1, 3], components)
    text = generate_input(water)
    assert parsed_groups(validator, text) == {components: [1, 3]}
    assert text.count('&CONSTRAINT\n') == 1
    assert text.count('&FIXED_ATOMS\n') == 1
    assert '&GEO_OPT' in text and 'OPTIMIZER BFGS' in text


def test_replace_remove_clear_and_grouping_never_duplicate_atoms(water):
    st = set_fixed_atoms(water.structure, [1, 2], 'XYZ')
    st = set_fixed_atoms(st, [2, 3], 'Z')
    assert fixed_atom_groups(st) == {'XYZ': [1], 'Z': [2, 3]}
    st = set_fixed_atoms(st, [3], None)
    assert fixed_atom_groups(st) == {'XYZ': [1], 'Z': [2]}
    st = set_fixed_atoms(st, st.atom_ids, None)
    assert not st.fixed_atoms
    assert not water.structure.fixed_atoms


@pytest.mark.parametrize('axis,expected', [('X', [1, 2]), ('Y', [1, 3]), ('Z', [2, 3])])
def test_cartesian_range_includes_negative_decimal_boundaries_in_triclinic_cell(axis, expected):
    st = Structure(symbols=['C'] * 3, positions=[(-1.25, 0, 5), (1.5, 9, -1.25), (8, 1.5, 1.5)],
                   cell=((5, 1, 2), (0, 4, 1), (0, 0, 6)))
    before = st.model_dump()
    assert select_coordinate_range(st, axis, '-1.25e0', '1.5') == expected
    assert st.model_dump() == before


def test_tolerance_empty_ranges_and_validation(water):
    st = Structure(symbols=['H'] * 3, positions=[(0, 0, 3 - 5e-10), (0, 0, 8 + 5e-10), (0, 0, 8 + 5e-8)])
    assert select_coordinate_range(st, 'Z', 3, 8) == [1, 2]
    assert not select_coordinate_range(st, 'X', 1, 2)
    assert not select_coordinate_range(None, 'Z', 1, 2)
    for axis, low, high in [('A', 0, 1), ('Z', 2, 1), ('X', 'bad', 2), ('Y', 'NaN', 2), ('Z', 0, 'inf')]:
        with pytest.raises(ValueError):
            select_coordinate_range(water.structure, axis, low, high)


def test_reordering_and_deletion_map_identity_to_new_input_numbers(water, validator):
    water.global_settings.run_type = 'GEO_OPT'
    water.structure.kind_labels = ['O1', 'H1', 'H1']
    water.kinds['O'].element = 'O'
    water.kinds['H'].element = 'H'
    water.kinds = {'O1': water.kinds['O'], 'H1': water.kinds['H']}
    water.structure = set_fixed_atoms(water.structure, [1], 'XY')
    water.structure = set_fixed_atoms(water.structure, [3], 'Z')
    st = water.structure
    water.structure = st.reordered([3, 1, 2])
    assert water.structure.atom_ids == [3, 1, 2]
    assert water.structure.labels == ['H1', 'O1', 'H1']
    assert water.structure.positions == [st.positions[i] for i in [2, 0, 1]]
    assert parsed_groups(validator, generate_input(water)) == {'Z': [1], 'XY': [2]}
    subset = water.structure.reordered([3, 2])
    assert fixed_atom_groups(subset) == {'Z': [1]}
    assert [atom.atom_id for atom in subset.fixed_atoms] == [3]
    assert not subset.reordered([]).fixed_atoms
    with pytest.raises(ValueError):
        st.reordered([1, 1])
    with pytest.raises(ValueError):
        st.reordered([99])


@pytest.mark.parametrize('field,value', [
    ('atom_ids', [1, 1, 3]), ('atom_ids', [1, 2]), ('atom_ids', [True, 2, 3]),
    ('fixed_atoms', [{'atom_id': 99, 'components': 'Z'}]),
    ('fixed_atoms', [{'atom_id': 1, 'components': 'X'}, {'atom_id': 1, 'components': 'Y'}]),
    ('fixed_atoms', [{'atom_id': 1, 'components': 'ABC'}])])
def test_invalid_identity_or_constraint_data_rejected(water, field, value):
    data = water.structure.model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        Structure.model_validate(data)


def test_legacy_project_roundtrip_coordinates_and_task_switch(water, tmp_path, validator):
    data = water.model_dump()
    data['structure'].pop('atom_ids')
    data['structure'].pop('fixed_atoms')
    legacy = tmp_path / 'legacy.json'
    legacy.write_text(json.dumps(data))
    project = load_project(legacy)
    assert project.structure.atom_ids == [1, 2, 3]
    assert not project.structure.fixed_atoms
    project.structure = set_fixed_atoms(project.structure, [2], 'XZ')
    project.structure.positions[1] = (2.5, 1, 3)
    save_project(project, tmp_path / 'fixed.json')
    restored = load_project(tmp_path / 'fixed.json')
    assert restored == project
    assert '&CONSTRAINT' not in generate_input(restored)  # ENERGY preserves, but does not emit constraints
    restored.global_settings.run_type = 'GEO_OPT'
    assert parsed_groups(validator, generate_input(restored)) == {'XZ': [2]}
    restored.structure = set_fixed_atoms(restored.structure, [2], None)
    assert '&CONSTRAINT' not in generate_input(restored)


def test_presets_do_not_carry_specific_atom_constraints_and_new_coordinates_clear_old_ids(water):
    water.structure = set_fixed_atoms(water.structure, [1], 'XYZ')
    default = capture_preset(water, 'Reusable')
    assert 'fixed_atoms' not in json.dumps(default.model_dump())
    assert apply_preset(water, builtin_preset('geo_opt')).project.structure.fixed_atoms == water.structure.fixed_atoms
    cell_preset = capture_preset(water, 'Cell', include_cell=True)
    assert apply_preset(water, cell_preset).project.structure.fixed_atoms == water.structure.fixed_atoms
    other = water.model_copy(deep=True)
    other.structure = water.structure.reordered([3])
    coordinates = capture_preset(other, 'New coordinates', include_coordinates=True)
    restored = apply_preset(water, coordinates).project.structure
    assert len(restored.symbols) == 1 and restored.atom_ids == [1]
    assert not restored.fixed_atoms


def test_standalone_bundle_and_input_import_keep_constraints_and_coordinate_order(water, tmp_path, validator):
    water.global_settings.run_type = 'GEO_OPT'
    water.structure = set_fixed_atoms(water.structure, [1], 'XYZ')
    water.structure = set_fixed_atoms(water.structure, [3], 'Z')
    expected = {'XYZ': [1], 'Z': [3]}
    standalone = export_input(water, tmp_path / 'single.inp').path
    bundle = export_bundle(water, tmp_path / 'bundle')
    assert parsed_groups(validator, standalone.read_text(), standalone.parent) == expected
    assert parsed_groups(validator, bundle.read_text(), bundle.parent) == expected
    assert (bundle.parent / 'structure.xyz').read_text().splitlines()[2].split()[0] == 'O'
    assert load_project(bundle.parent / 'project.cp2kstudio.json').structure == water.structure
    imported, warnings = import_input(bundle)
    assert fixed_atom_groups(imported.structure) == expected
    assert not any('CONSTRAINT 中未导入' in warning for warning in warnings)
    assert 'run.sh' in {file.name for file in bundle.parent.iterdir()}


def test_comprehensive_check_validates_constrained_input(water):
    water.global_settings.run_type = 'GEO_OPT'
    water.structure = set_fixed_atoms(water.structure, [2, 3], 'YZ')
    result = comprehensive_check(water)
    assert all(stage.state == 'ready' for stage in result.stages), result.report()


def test_many_fixed_atoms_use_repeatable_bounded_list_lines(water, validator):
    water.global_settings.run_type = 'GEO_OPT'
    water.structure = Structure(symbols=['H'] * 70, positions=[(0, 0, i / 100) for i in range(70)],
                                cell=water.structure.cell, periodic='XYZ')
    water.kinds = {'H': water.kinds['H']}
    water.structure = set_fixed_atoms(water.structure, water.structure.atom_ids, 'XYZ')
    text = generate_input(water)
    assert text.count('&FIXED_ATOMS\n') == 1
    assert len([line for line in text.splitlines() if line.strip().startswith('LIST ')]) == 3
    assert parsed_groups(validator, text) == {'XYZ': list(range(1, 71))}
