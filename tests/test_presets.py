import json
import pytest
from pydantic import ValidationError
from core.models import Project, Structure, Kind
from core.presets import Preset, PresetStore, capture_preset, apply_preset, builtin_preset


def test_capture_is_separate_from_project_and_omits_structure(water):
    before = water.model_dump()
    preset = capture_preset(water, '  我的 PBE 参数  ', '第一行\n第二行', 'single_point')
    assert preset.name == '我的 PBE 参数'
    assert preset.coordinates is None and preset.cell_settings is None
    assert preset.parameters['dft']['scf'] == before['dft']['scf']
    assert preset.parameters['kinds'] == before['kinds']
    assert 'structure' not in preset.parameters and 'xml_spec' not in preset.parameters
    assert not preset.incomplete and preset.syntax_validated is False
    assert water.model_dump() == before


def test_incomplete_drafts_are_not_xml_certification():
    preset = capture_preset(Project(), '草稿')
    assert preset.incomplete and preset.validation_messages and not preset.syntax_validated
    assert preset.parameters['dft']['charge'] == 0
    assert preset.parameters['dft']['multiplicity'] == 1
    with pytest.raises(ValidationError):
        Preset(name='误认证', syntax_validated=True)


@pytest.mark.parametrize('data', [
    {'name': '  '}, {'name': 'bad', 'format_version': 2}, {'name': 'bad', 'cp2k_version': '2025.2'},
    {'name': 'bad', 'parameters': {'structure': {}}}, {'name': 'bad', 'parameters': {'xml_spec': 'old.xml'}},
    {'name': 'bad', 'parameters': {'dft': {'cutoff': -1}}}])
def test_preset_schema_rejects_invalid_or_hidden_settings(data):
    with pytest.raises(ValidationError):
        Preset(**data)


def test_builtin_workflow_patch_preserves_chemistry(water):
    before = water.model_copy(deep=True)
    planned = apply_preset(water, builtin_preset('geo_opt'))
    assert planned.project.global_settings.run_type == 'GEO_OPT'
    assert planned.project.structure == before.structure
    assert planned.project.kinds == before.kinds and planned.project.dft == before.dft
    assert water == before


def test_cell_and_coordinates_are_independent_and_explicit(water):
    source = water.model_copy(deep=True)
    source.structure.cell = ((9, 0, 0), (0, 9, 0), (0, 0, 9))
    source.structure.periodic = 'NONE'
    source.structure.positions[0] = (1, 2, 3)
    cell = capture_preset(source, '仅晶胞', include_cell=True)
    result = apply_preset(water, cell)
    assert result.includes_structure
    assert result.project.structure.cell == source.structure.cell
    assert result.project.structure.positions == water.structure.positions
    coords = capture_preset(source, '仅坐标', include_coordinates=True)
    result = apply_preset(water, coords)
    assert result.project.structure.positions == source.structure.positions
    assert result.project.structure.cell == water.structure.cell
    assert result.project.structure.periodic == water.structure.periodic
    with pytest.raises(ValueError, match='没有结构'):
        capture_preset(Project(), '无结构', include_coordinates=True)


def test_different_material_does_not_get_wrong_element_configuration(water):
    preset = capture_preset(water, '水的设置')
    target = water.model_copy(deep=True)
    target.structure = Structure(symbols=['Si'], positions=[(0, 0, 0)], cell=water.structure.cell, periodic='XYZ')
    target.kinds = {'Si': Kind(basis_set='old', potential='old')}
    planned = apply_preset(target, preset)
    assert planned.project.structure == target.structure
    assert planned.project.kinds['Si'].basis_set == ''
    assert planned.project.kinds['Si'].potential == ''
    assert any('Si' in message for message in planned.warnings)


def test_kind_labels_match_by_real_element_without_ambiguous_guess(water):
    source = water.model_copy(deep=True)
    source.structure = Structure(symbols=['O', 'O'], positions=[(0, 0, 0), (1, 0, 0)],
        cell=water.structure.cell, periodic='XYZ', kind_labels=['O1', 'O2'])
    a = source.kinds['O'].model_copy(deep=True)
    a.element = 'O'
    b = a.model_copy(deep=True)
    b.basis_set = 'TZVP-MOLOPT-GTH'
    source.kinds = {'O1': a, 'O2': b}
    planned = apply_preset(water, capture_preset(source, '两种 O'))
    assert planned.project.kinds['O'].basis_set == ''
    b.basis_set = a.basis_set
    source.kinds = {'O1': a, 'O2': b}
    planned = apply_preset(water, capture_preset(source, '相同 O'))
    assert planned.project.kinds['O'].basis_set == a.basis_set


def test_store_roundtrip_duplicate_overwrite_rename_delete(water, tmp_path):
    store = PresetStore(tmp_path / 'presets')
    a = store.save(capture_preset(water, '原名称'))
    assert store.load(a.id) == a
    b = capture_preset(water, '原名称')
    with pytest.raises(FileExistsError):
        store.save(b)
    replaced = store.save(b, overwrite=True)
    assert replaced.id == a.id and len(store.list().presets) == 1
    renamed = Preset.model_validate(dict(replaced.model_dump(), name='新名称'))
    store.save(renamed, overwrite=True)
    assert store.list().presets[0].name == '新名称'
    store.delete(a.id)
    assert store.list().presets == []
    with pytest.raises(FileNotFoundError):
        store.load(a.id)
    with pytest.raises(ValueError):
        store.load('../outside')


def test_bad_missing_and_future_preset_files_do_not_break_listing(water, tmp_path):
    store = PresetStore(tmp_path)
    good = store.save(capture_preset(water, '有效'))
    (tmp_path / 'corrupt.json').write_text('{broken')
    future = dict(good.model_dump(), id='future', format_version=999)
    (tmp_path / 'future.json').write_text(json.dumps(future))
    listing = store.list()
    assert listing.presets == [good]
    assert len(listing.problems) == 2
