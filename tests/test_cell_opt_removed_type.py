"""Never reintroduce CELL_OPT/TYPE through legacy projects, presets or XML."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from core.models import CellOptimizationConfig
from core.presets import Preset, PresetStore, apply_preset, capture_preset
from core.project_io import load_project, save_project
from core.generator import generate_input
from core.schema import CP2KSchema
from core.validator import InputValidator
from core.comprehensive_check import comprehensive_check
from i18n.language_manager import language_manager
from tests.test_cell_optimization import crystal
from tests.test_cell_opt_ui import cell_window
from tests.test_vibrational_ui import window
from tests.test_layout_workflow import wait_for_worker


def test_legacy_type_is_consumed_without_mutation_or_new_serialized_field():
    data = {'type':'DIRECT_CELL_OPT', 'optimizer':'CG', 'max_iter':321,
            'external_pressure':-17.5, 'pressure_tolerance':75.0, 'constraint':'XY'}
    original = deepcopy(data)
    migrated = CellOptimizationConfig.model_validate(data)
    assert data == original
    assert 'type' not in CellOptimizationConfig.model_fields
    assert 'type' not in migrated.model_dump() and 'type' not in CellOptimizationConfig().model_dump()
    for key, value in data.items():
        if key != 'type':
            assert getattr(migrated, key) == value


def test_old_project_and_preset_keep_parameters_but_never_emit_type(crystal, tmp_path):
    legacy = crystal.model_dump()
    legacy['cell_opt'].update(type='DIRECT_CELL_OPT', optimizer='LBFGS', max_iter=387,
        external_pressure=123.5, pressure_tolerance=87.6, max_force=1e-4, rms_force=5e-5,
        max_dr=.002, rms_dr=.001, keep_angles=True, keep_symmetry=True,
        initial_symmetry='CUBIC', constraint='Z')
    path = tmp_path/'legacy.json'
    path.write_text(json.dumps(legacy))
    restored = load_project(path)
    for key,value in legacy['cell_opt'].items():
        if key != 'type': assert getattr(restored.cell_opt,key) == value
    text = generate_input(restored)
    assert 'TYPE DIRECT_CELL_OPT' not in text
    checked = InputValidator().parse(text)
    assert checked.ok and 'type' not in checked.tree['+motion']['+cell_opt']
    save_project(restored, path)
    assert 'type' not in json.loads(path.read_text())['cell_opt']
    store = PresetStore(tmp_path/'presets')
    old_preset = Preset(name='legacy cell', parameters={'global_settings':{'run_type':'CELL_OPT'}, 'cell_opt':legacy['cell_opt']})
    preset_path = store.directory / (old_preset.id+'.json')
    preset_path.parent.mkdir(parents=True, exist_ok=True)
    preset_path.write_text(old_preset.model_dump_json())
    migrated = apply_preset(crystal, store.load(old_preset.id)).project
    assert migrated.cell_opt == restored.cell_opt
    assert 'TYPE DIRECT_CELL_OPT' not in generate_input(migrated)
    assert 'type' not in capture_preset(migrated,'new cell').parameters['cell_opt']
    result = comprehensive_check(migrated)
    assert result.validation.ok and not result.validation.errors, result.report()


@pytest.mark.parametrize('legacy_type', ['DIRECT_CELL_OPT', 'GEO_OPT', 'MD'])
def test_historical_schema_acceptance_cannot_approve_removed_keyword(crystal, legacy_type):
    assert legacy_type in CP2KSchema().keyword('MOTION/CELL_OPT','TYPE')['enum']
    text = generate_input(crystal).replace('&CELL_OPT\n', '&CELL_OPT\n    TYPE '+legacy_type+'\n')
    checked = InputValidator().parse(text)
    assert not checked.ok
    assert any(getattr(message,'code',None) == 'cellopt.removed_type_error' for message in checked.errors)
    assert checked.tree['+motion']['+cell_opt']['type'] == legacy_type.lower()


def test_other_legitimate_type_keywords_are_not_removed_or_rejected():
    source = Path(__file__).parent/'fixtures'/'upstream_cell_opt_argon.inp'
    # Test-only adaptation of a known historical line; the official fixture and
    # production input text are never rewritten or globally stripped.
    text = source.read_text().replace('    TYPE DIRECT_CELL_OPT\n', '')
    assert 'TYPE DFTD3' in text
    checked = InputValidator().parse(text)
    assert checked.ok, checked.errors
    assert checked.tree['+force_eval'][0]['+dft']['+xc']['+vdw_potential']['+pair_potential'][0]['type'] == 'dftd3'


@pytest.mark.parametrize('language', ['en_US','zh_CN'])
def test_legacy_ui_load_and_language_switch_never_restore_type(cell_window, app, language):
    w = cell_window
    old = w.project.model_dump()
    old['cell_opt']['type'] = 'DIRECT_CELL_OPT'
    old['cell_opt']['max_iter'] = 299
    w.load_into_ui(type(w.project).model_validate(old))
    w.check_current_configuration()
    wait_for_worker(app,w)
    snapshot = w.project.model_dump_json(), w.preview.toPlainText(), w.dirty, w._revision
    result = w._comprehensive_result
    for target in [language,'zh_CN' if language == 'en_US' else 'en_US',language]:
        language_manager().set_language(target)
        app.processEvents()
        assert 'cell_opt.type' not in w.cell_opt_panel.fields
        assert w.cell_opt_panel.findChild(type(w.global_panel.fields['global_settings.run_type'][0]),'cell_opt.type') is None
        assert 'TYPE DIRECT_CELL_OPT' not in w.preview.toPlainText()
        assert w.project.cell_opt.max_iter == 299
        assert (w.project.model_dump_json(),w.preview.toPlainText(),w.dirty,w._revision) == snapshot
        assert w._comprehensive_result is result and result.validation.ok
