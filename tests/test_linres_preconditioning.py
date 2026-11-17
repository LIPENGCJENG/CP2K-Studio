"""Raman response parameters are independent of SCF/OT parameters."""
from copy import deepcopy
import json
import math

import pytest
from pydantic import ValidationError

from core.models import Project, VibrationalConfig, LINRES_PRECONDITIONERS
from core.generator import generate_input
from core.validator import validate_project
from core.schema import CP2KSchema
from core.input_export import export_input
from core.input_import import import_input
from core.project_io import save_project, load_project, export_bundle
from core.presets import capture_preset, apply_preset, Preset, PresetStore
from core.comprehensive_check import comprehensive_check
from core.vibrational import validate_spectroscopy_input


@pytest.fixture
def raman(vib_project):
    vib_project.vibrational.raman_enabled = True
    vib_project.structure.periodic = 'NONE'
    vib_project.dft.poisson_solver = 'MT'
    return vib_project


def test_studio_defaults_and_native_enums_match_target_xml():
    v = VibrationalConfig()
    assert v.linres_preconditioner == 'FULL_ALL' and v.linres_energy_gap == .1
    assert v.linres_eps == 1e-7 and v.linres_max_iter == 200
    assert Project().vibrational == v
    assert LINRES_PRECONDITIONERS == ('NONE','FULL_ALL','FULL_SINGLE_INVERSE','FULL_SINGLE','FULL_KINETIC','FULL_S_INVERSE')
    schema = CP2KSchema()
    path = 'FORCE_EVAL/PROPERTIES/LINRES'
    assert set(schema.keyword(path, 'PRECONDITIONER')['enum']) == set(LINRES_PRECONDITIONERS)
    assert schema.keyword(path, 'PRECONDITIONER')['default'] == 'NONE'
    assert float(schema.keyword(path, 'ENERGY_GAP')['default']) == .2


@pytest.mark.parametrize('periodic', ['NONE', 'XYZ'])
@pytest.mark.parametrize('ir', [False, True])
def test_new_defaults_generate_and_export_only_in_raman_linres(raman, validator, tmp_path, periodic, ir):
    p = raman
    p.vibrational.ir_enabled = ir
    p.structure.periodic = periodic
    p.dft.poisson_solver = 'MT' if periodic == 'NONE' else 'PERIODIC'
    p.vibrational.fully_periodic = periodic == 'XYZ'
    scf = p.dft.scf.model_dump()
    text = generate_input(p)
    parsed = validator.parse(text)
    assert parsed.ok, parsed.errors
    force = parsed.tree['+force_eval'][0]
    linres = force['+properties']['+linres']
    assert linres['eps'] == 1e-7 and linres['max_iter'] == 200
    assert linres['preconditioner'] == 'full_all' and linres['energy_gap'] == .1
    assert ('+moments' in force['+dft'].get('+print', {})) is ir
    assert linres['+polar']['periodic_dipole_operator'] is (periodic == 'XYZ')
    assert not validate_spectroscopy_input(p, parsed.tree)
    assert all(message.code != 'vib.linres_warning' for message in validate_project(p).warnings)
    single = tmp_path / 'input.inp'
    export_input(p, single)
    assert single.read_text() == text
    folder = export_bundle(p, tmp_path / 'bundle').parent
    bundled = validator.parse((folder / 'input.inp').read_text(), folder)
    assert bundled.ok and bundled.tree['+force_eval'][0]['+properties']['+linres'] == linres
    assert load_project(folder / 'project.cp2kstudio.json').vibrational == p.vibrational
    p.vibrational.raman_enabled = False
    assert '&LINRES' not in generate_input(p)
    assert p.dft.scf.model_dump() == scf


def test_missing_defaults_and_explicit_old_project_preset_values(raman, tmp_path):
    data = raman.model_dump()
    keys = ['linres_eps', 'linres_preconditioner', 'linres_energy_gap']
    for key in keys:
        del data['vibrational'][key]
    path = tmp_path / 'missing-fields.json'
    path.write_text(json.dumps(data))
    loaded = load_project(path)
    assert loaded.vibrational == raman.vibrational
    legacy = dict(linres_eps=1e-8, linres_preconditioner='NONE', linres_energy_gap=.2,
                  linres_max_iter=200, raman_enabled=True)
    data['vibrational'] = legacy
    path.write_text(json.dumps(data))
    loaded = load_project(path)
    assert loaded.vibrational.model_dump(include=set(legacy)) == legacy
    save_project(loaded, path)
    assert load_project(path) == loaded
    preset = Preset(name='Explicit old defaults', parameters={'vibrational': legacy})
    applied = apply_preset(raman, preset).project
    assert applied.vibrational == loaded.vibrational
    assert applied.dft.scf == raman.dft.scf


@pytest.mark.parametrize('eps,warning', [
    (1e-8, False), (5e-8, False), (1e-7, False),
    (math.nextafter(1e-7, 0), False),
    (math.nextafter(1e-7, math.inf), True), (1e-6, True),
])
@pytest.mark.parametrize('enabled', [False, True])
def test_linres_warning_uses_strict_default_threshold(raman, eps, warning, enabled):
    raman.vibrational.raman_enabled = enabled
    raman.vibrational.linres_eps = eps
    before = raman.model_dump_json(), generate_input(raman)
    messages = [m for m in validate_project(raman).warnings if m.code == 'vib.linres_warning']
    assert bool(messages) is (enabled and warning)
    for message in messages:
        for language in ['en_US', 'zh_CN']:
            text = message.render(language)
            assert '1e-7' in text and '1e-8' not in text
    assert (raman.model_dump_json(), generate_input(raman)) == before


@pytest.mark.parametrize('value', [0, -1, float('nan'), float('inf'), -float('inf'), True, None, 'invalid'])
def test_invalid_gap_is_a_localized_model_error(value):
    with pytest.raises(ValidationError) as caught:
        VibrationalConfig(raman_enabled=True, linres_energy_gap=value)
    message = caught.value.errors()[0]['ctx']['error'].args[0]
    assert message.code == 'vib.linres_energy_gap_error'
    assert 'positive' in message.render('en_US') and '正实数' in message.render('zh_CN')


@pytest.mark.parametrize('value', ['INVALID', 'FULL_SINGLE_INVERSES', None, 0])
def test_invalid_preconditioner_is_not_silently_replaced(value):
    with pytest.raises(ValidationError) as caught:
        VibrationalConfig(raman_enabled=True, linres_preconditioner=value)
    message = caught.value.errors()[0]['ctx']['error'].args[0]
    assert message.code == 'vib.linres_preconditioner_error'
    assert 'select' in message.render('en_US') and '请选择' in message.render('zh_CN')


@pytest.mark.parametrize('preconditioner', LINRES_PRECONDITIONERS)
@pytest.mark.parametrize('periodic', ['NONE','XYZ'])
@pytest.mark.parametrize('ir', [False, True])
def test_all_preconditioners_xml_hierarchy_precision_and_ot_independence(raman, validator, preconditioner, periodic, ir):
    p = raman
    p.vibrational.linres_preconditioner = preconditioner
    p.vibrational.linres_energy_gap = .0012345678901234567
    p.vibrational.linres_eps = 3e-10
    p.vibrational.linres_max_iter = 321
    p.vibrational.ir_enabled = ir
    p.vibrational.fully_periodic = periodic == 'XYZ'
    p.structure.periodic = periodic
    p.dft.poisson_solver = 'MT' if periodic == 'NONE' else 'PERIODIC'
    p.dft.scf.preconditioner = 'FULL_KINETIC'
    p.dft.scf.energy_gap = .08123456789012345
    before = p.model_dump_json()
    checked = validator.parse(generate_input(p))
    assert checked.ok, checked.errors
    assert not validate_spectroscopy_input(p, checked.tree)
    force = checked.tree['+force_eval'][0]
    linres = force['+properties']['+linres']
    ot = force['+dft']['+scf']['+ot']
    assert linres['preconditioner'].upper() == preconditioner
    assert linres['eps'] == 3e-10 and linres['max_iter'] == 321
    assert ot['preconditioner'] == 'full_kinetic' and ot['energy_gap'] == p.dft.scf.energy_gap
    if preconditioner == 'NONE':
        assert 'energy_gap' not in linres
    else:
        assert linres['energy_gap'] == p.vibrational.linres_energy_gap
    assert linres['+polar']['periodic_dipole_operator'] is (periodic == 'XYZ')
    assert ('+moments' in force['+dft'].get('+print', {})) is ir
    text = generate_input(p)
    assert text.count('&LINRES\n') == 1 and text.count('&VIBRATIONAL_ANALYSIS\n') == 1
    assert p.model_dump_json() == before


def test_full_all_advice_is_info_only_and_only_when_raman_is_requested(raman):
    p = raman
    p.vibrational.linres_eps = 1e-8  # Isolate preconditioner advice from accuracy warnings.
    p.vibrational.linres_preconditioner = 'FULL_ALL'
    p.vibrational.linres_energy_gap = .01
    result = validate_project(p)
    assert result.ok and not result.warnings
    info = next(m for m in result.infos if m.code == 'vib.linres_full_all_info')
    assert 'underestimate' in info.render('en_US') and '低估' in info.render('zh_CN')
    assert 'guarantee' in info.render('en_US') and '不保证' in info.render('zh_CN')
    report = comprehensive_check(p)
    assert report.validation.ok and not report.validation.warnings
    assert [stage.state for stage in report.stages] == ['ready'] * 4
    p.vibrational.raman_enabled = False
    p.vibrational.ir_enabled = True
    result = validate_project(p)
    assert all(m.code != 'vib.linres_full_all_info' for m in result.infos)
    assert '&LINRES' not in generate_input(p)
    assert p.vibrational.linres_preconditioner == 'FULL_ALL' and p.vibrational.linres_energy_gap == .01


@pytest.mark.parametrize('legacy_mode', [None, 'RAMAN'])
def test_old_project_and_preset_missing_fields_keep_eps_and_iterations(raman, tmp_path, legacy_mode):
    values = {'linres_eps': 6e-10, 'linres_max_iter': 345}
    values.update({'mode': legacy_mode} if legacy_mode else {'raman_enabled': True})
    data = raman.model_dump()
    data['vibrational'] = values
    before = deepcopy(data)
    path = tmp_path / 'old.json'
    path.write_text(json.dumps(data))
    p = load_project(path)
    assert p.vibrational.linres_preconditioner == 'FULL_ALL' and p.vibrational.linres_energy_gap == .1
    assert p.vibrational.linres_eps == 6e-10 and p.vibrational.linres_max_iter == 345
    assert p.dft == raman.dft and data == before
    preset = Preset(name='Older Raman', parameters={'vibrational': values})
    restored = apply_preset(raman, preset).project
    assert restored.vibrational == p.vibrational


@pytest.mark.parametrize('preconditioner', ['NONE','FULL_ALL','FULL_SINGLE'])
def test_project_preset_inp_and_bundle_roundtrip(raman, validator, tmp_path, preconditioner):
    p = raman
    p.vibrational.ir_enabled = True
    p.vibrational.linres_preconditioner = preconditioner
    p.vibrational.linres_energy_gap = .007654321098765432
    path = tmp_path / 'project.json'
    save_project(p, path)
    assert load_project(path) == p
    preset = capture_preset(p, 'LINRES controls')
    store = PresetStore(tmp_path / 'presets')
    stored = store.save(preset)
    target = p.model_copy(deep=True)
    target.vibrational = VibrationalConfig()
    assert apply_preset(target, store.load(stored.id)).project.vibrational == p.vibrational
    text = generate_input(p)
    single = tmp_path / 'input.inp'
    export_input(p, single)
    assert single.read_text() == text
    restored, warnings = import_input(single)
    assert restored.vibrational.linres_preconditioner == preconditioner
    assert restored.vibrational.linres_energy_gap == (.2 if preconditioner == 'NONE' else p.vibrational.linres_energy_gap)
    assert generate_input(restored) == text
    assert not any('preconditioner' in str(m).lower() or 'energy_gap' in str(m).lower() for m in warnings)
    folder = export_bundle(p, tmp_path / 'bundle').parent
    parsed = validator.parse((folder / 'input.inp').read_text(), folder)
    assert parsed.ok and not validate_spectroscopy_input(p, parsed.tree)
    assert load_project(folder / 'project.cp2kstudio.json').vibrational == p.vibrational
    assert (folder / 'run.sh').exists() and (folder / 'EXPORT_NOTES.txt').exists()


@pytest.mark.parametrize('damage', ['preconditioner','energy_gap'])
def test_final_input_semantics_check_the_selected_linres_parameters(raman, validator, damage):
    raman.vibrational.linres_preconditioner = 'FULL_ALL'
    raman.vibrational.linres_energy_gap = .01
    tree = validator.parse(generate_input(raman)).tree
    node = tree['+force_eval'][0]['+properties']['+linres']
    node[damage] = 'none' if damage == 'preconditioner' else .2
    assert validate_spectroscopy_input(raman, tree)


@pytest.mark.parametrize('task', ['ENERGY','GEO_OPT','CELL_OPT','MD'])
def test_other_tasks_are_unchanged(water, task):
    water.global_settings.run_type = task
    before = generate_input(water), water.dft.model_dump()
    water.vibrational.raman_enabled = True
    water.vibrational.linres_preconditioner = 'FULL_SINGLE'
    water.vibrational.linres_energy_gap = .004
    assert (generate_input(water), water.dft.model_dump()) == before
