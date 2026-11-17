"""Independent IR/Raman switches, legacy migration and one Hessian workflow."""
from copy import deepcopy
import json
import zipfile

import pytest
from pydantic import ValidationError

from core.models import Project, VibrationalConfig
from core.generator import generate_input, Section, add_spectroscopy_sections, GenerationError
from core.validator import validate_project
from core.vibrational import validate_spectroscopy_input
from core.project_io import save_project, load_project, export_bundle
from core.input_export import export_input
from core.input_import import import_input
from core.presets import Preset, PresetStore, capture_preset, apply_preset
from core.comprehensive_check import comprehensive_check
from core.run_script_generator import generate_run_script

COMBINATIONS = [(False, False), (True, False), (False, True), (True, True)]


@pytest.fixture
def spectra_project(vib_project):
    vib_project.structure.periodic = 'NONE'
    vib_project.dft.poisson_solver = 'MT'
    return vib_project


def test_new_defaults_and_serialization_have_switches_without_mode():
    config = Project().vibrational
    assert not config.ir_enabled and not config.raman_enabled and not config.intensities
    assert config.dx == .01 and config.nproc_rep == 4 and not config.fully_periodic
    assert config.linres_eps == 1e-7 and config.linres_max_iter == 200
    assert not {'mode', 'intensities', 'enabled_spectra', 'spectra_label'} & config.model_dump().keys()
    assert config.model_dump()['ir_enabled'] is False and config.model_dump()['raman_enabled'] is False


@pytest.mark.parametrize('ir,raman', COMBINATIONS)
@pytest.mark.parametrize('periodic', ['NONE', 'XYZ'])
def test_four_combinations_one_hessian_valid_xml_and_exact_property_paths(spectra_project, validator, periodic, ir, raman):
    p = spectra_project
    p.structure.periodic = periodic
    p.dft.poisson_solver = 'MT' if periodic == 'NONE' else 'PERIODIC'
    p.vibrational.ir_enabled, p.vibrational.raman_enabled = ir, raman
    p.vibrational.dx = .008
    p.vibrational.linres_eps = 2.345678e-10
    p.vibrational.linres_max_iter = 287
    p.vibrational.fully_periodic = periodic == 'XYZ'
    before = p.model_dump_json()
    text = generate_input(p)
    parsed = validator.parse(text)
    assert parsed.ok, parsed.errors
    assert not validate_spectroscopy_input(p, parsed.tree)
    tree = parsed.tree
    assert tree['+global']['run_type'] == 'vibrational_analysis'
    assert text.count('&VIBRATIONAL_ANALYSIS\n') == 1 and text.count('&HESSIAN ') == 1
    assert '&MOTION' not in text
    vib = tree['+vibrational_analysis']
    assert vib['intensities'] is (ir or raman) and vib['dx'] == .008
    assert vib['fully_periodic'] is (periodic == 'XYZ')
    force = tree['+force_eval'][0]
    dft = force['+dft']
    moments = dft.get('+print', {}).get('+moments')
    polar = force.get('+properties', {}).get('+linres', {}).get('+polar')
    assert (moments is not None) is ir and (polar is not None) is raman
    assert text.count('&MOMENTS ON') == int(ir) and text.count('&POLAR TRUE') == int(raman)
    assert text.count('&LINRES\n') == int(raman)
    if ir:
        assert moments['_'] == 'ON' and moments['max_moment'] == 1
        assert moments['periodic'] is (periodic == 'XYZ')
    if raman:
        linres = force['+properties']['+linres']
        assert linres['eps'] == p.vibrational.linres_eps and linres['max_iter'] == 287
        assert polar['_'] and polar['do_raman']
        assert polar['periodic_dipole_operator'] is (periodic == 'XYZ')
    assert p.model_dump_json() == before


@pytest.mark.parametrize('legacy,flags', [
    ('FREQUENCIES', (False,False)), ('IR', (True,False)), ('RAMAN', (False,True)),
    ('Frequencies & Normal Modes', (False,False)), ('IR_INTENSITIES', (True,False)),
    ('Raman Intensities', (False,True)), ('IR+RAMAN', (True,True))])
def test_legacy_project_and_preset_normalize_before_merging(spectra_project, tmp_path, legacy, flags):
    p = spectra_project
    data = p.model_dump()
    legacy_values = {'mode': legacy, 'linres_eps': 3e-10, 'linres_max_iter': 432}
    data['vibrational'] = dict(legacy_values)
    before = deepcopy(data)
    path = tmp_path / 'old.json'
    path.write_text(json.dumps(data))
    restored = load_project(path)
    assert (restored.vibrational.ir_enabled, restored.vibrational.raman_enabled) == flags
    assert restored.vibrational.linres_eps == 3e-10 and restored.vibrational.linres_max_iter == 432
    assert restored.dft == p.dft and restored.structure == p.structure
    assert data == before
    save_project(restored, tmp_path / 'new.json')
    serialized = json.loads((tmp_path / 'new.json').read_text())['vibrational']
    assert 'mode' not in serialized and serialized['ir_enabled'] is flags[0]
    target = p.model_copy(deep=True)
    target.vibrational.ir_enabled = target.vibrational.raman_enabled = True
    target.vibrational.dx = .007
    patch = {'vibrational': legacy_values}
    source = deepcopy(patch)
    store = PresetStore(tmp_path / 'old-presets')
    store.directory.mkdir(parents=True, exist_ok=True)
    raw_preset = {'id': 'legacy', 'name': 'Legacy preset', 'format_version': 1,
                  'cp2k_version': '2026.1', 'parameters': patch}
    store.path('legacy').write_text(json.dumps(raw_preset))
    preset = store.load('legacy')
    applied = apply_preset(target, preset).project
    assert (applied.vibrational.ir_enabled, applied.vibrational.raman_enabled) == flags
    assert applied.vibrational.linres_eps == 3e-10 and applied.vibrational.linres_max_iter == 432
    assert applied.vibrational.dx == .007  # Partial migration must not inject defaults.
    assert applied.structure == target.structure and patch == source
    assert 'mode' not in preset.parameters['vibrational']


def test_explicit_new_fields_take_precedence_and_partial_new_presets_stay_partial(spectra_project):
    value = VibrationalConfig(mode='IR', ir_enabled=False, raman_enabled=True)
    assert not value.ir_enabled and value.raman_enabled
    spectra_project.vibrational.ir_enabled = spectra_project.vibrational.raman_enabled = True
    preset = Preset(name='IR off', parameters={'vibrational': {'ir_enabled': False}})
    applied = apply_preset(spectra_project, preset).project
    assert not applied.vibrational.ir_enabled and applied.vibrational.raman_enabled
    assert preset.parameters['vibrational'] == {'ir_enabled': False}
    with pytest.raises(ValidationError):
        VibrationalConfig(mode='unrecognized')


@pytest.mark.parametrize('ir,raman', COMBINATIONS)
@pytest.mark.parametrize('periodic', ['NONE', 'XYZ'])
def test_all_combinations_roundtrip_preset_input_package_and_check(spectra_project, validator, tmp_path, periodic, ir, raman):
    p = spectra_project
    p.structure.periodic = periodic
    p.dft.poisson_solver = 'MT' if periodic == 'NONE' else 'PERIODIC'
    p.vibrational.ir_enabled, p.vibrational.raman_enabled = ir, raman
    p.vibrational.fully_periodic = periodic == 'XYZ'
    p.vibrational.linres_eps = 9e-10
    text = generate_input(p)
    single = tmp_path / 'vibration.inp'
    export_input(p, single)
    assert single.read_text() == text
    imported, _ = import_input(single)
    assert (imported.vibrational.ir_enabled, imported.vibrational.raman_enabled) == (ir, raman)
    if raman:
        assert imported.vibrational.linres_eps == p.vibrational.linres_eps
    assert generate_input(imported) == text
    saved = tmp_path / 'project.json'
    save_project(p, saved)
    assert load_project(saved) == p
    store = PresetStore(tmp_path / 'presets')
    preset = store.save(capture_preset(p, 'Four combinations'))
    target = p.model_copy(deep=True)
    target.vibrational = VibrationalConfig()
    assert apply_preset(target, store.load(preset.id)).project.vibrational == p.vibrational
    assert not {'mode', 'intensities'} & preset.parameters['vibrational'].keys()
    report = comprehensive_check(p)
    assert report.validation.ok and not report.validation.warnings
    assert all(stage.state == 'ready' for stage in report.stages)
    folder = export_bundle(p, tmp_path / 'bundle').parent
    final = validator.parse((folder / 'input.inp').read_text(), folder)
    assert final.ok and not validate_spectroscopy_input(p, final.tree)
    assert (folder / 'run.sh').read_text() == generate_run_script(p.run_environment)
    assert load_project(folder / 'project.cp2kstudio.json').vibrational == p.vibrational
    notes = (folder / 'EXPORT_NOTES.txt').read_text()
    assert 'CP2K has not run' in notes and not (folder / 'output.out').exists()
    if ir and raman:
        assert 'IR + RAMAN' in notes
        archive = export_bundle(p, tmp_path / 'both.zip', archive=True)
        with zipfile.ZipFile(archive) as handle:
            inp = handle.read('input.inp').decode()
            assert '&MOMENTS ON' in inp and '&POLAR TRUE' in inp


@pytest.mark.parametrize('ir,raman', COMBINATIONS)
def test_checks_follow_each_enabled_property(spectra_project, ir, raman):
    p = spectra_project
    p.vibrational.ir_enabled, p.vibrational.raman_enabled = ir, raman
    p.vibrational.linres_eps = 1e-6
    p.dft.scf.method = 'DIAGONALIZATION'
    result = validate_project(p)
    assert ('vib.raman_solver_error' in {m.code for m in result.errors}) is raman
    assert ('vib.linres_warning' in {m.code for m in result.warnings}) is raman
    p.dft.scf.method = 'OT'
    p.structure.periodic = 'XY'
    p.dft.poisson_solver = 'MT'
    result = validate_project(p)
    messages = [m for m in result.errors if m.code == 'vib.partial_spectra_error']
    assert {m.params['mode'] for m in messages} == set(p.vibrational.enabled_spectra)
    if ir or raman:
        with pytest.raises(GenerationError):
            generate_input(p)


@pytest.mark.parametrize('damage', ['IR', 'RAMAN', 'INTENSITIES'])
def test_combined_final_semantics_require_both_properties(spectra_project, validator, damage):
    p = spectra_project
    p.vibrational.ir_enabled = p.vibrational.raman_enabled = True
    tree = validator.parse(generate_input(p)).tree
    force = tree['+force_eval'][0]
    if damage == 'IR':
        force['+dft']['+print'].pop('+moments')
    elif damage == 'RAMAN':
        force['+properties']['+linres'].pop('+polar')
    else:
        tree['+vibrational_analysis']['intensities'] = False
    assert validate_spectroscopy_input(p, tree)


def test_property_merging_is_additive_idempotent_and_never_deletes_independent_sections():
    moments = Section('MOMENTS', 'ON', keywords=[('FILENAME', 'moments.dat')])
    dft_print = Section('PRINT', children=[moments, Section('MO', 'ON')])
    dft = Section('DFT', children=[dft_print])
    polar = Section('POLAR', 'TRUE', keywords=[('DO_RAMAN', True)])
    linres = Section('LINRES', keywords=[('EPS', 1e-8)], children=[polar, Section('LOCALIZE')])
    force = Section('FORCE_EVAL', children=[dft, Section('PROPERTIES', children=[linres])])
    config = VibrationalConfig(ir_enabled=True, raman_enabled=True)
    add_spectroscopy_sections(force, dft, config, 'NONE')
    once = force.render()
    add_spectroscopy_sections(force, dft, config, 'NONE')
    assert force.render() == once
    assert dft.children == [dft_print] and dft_print.children[0] is moments
    assert ('FILENAME', 'moments.dat') in moments.keywords
    assert linres.children[0] is polar and linres.children[1].name == 'LOCALIZE'
    assert sum(node.name == 'POLAR' for node in linres.children) == 1
    add_spectroscopy_sections(force, dft, VibrationalConfig(), 'NONE')
    assert force.render() == once  # Disabled switches do not erase another feature's settings.


@pytest.mark.parametrize('task', ['ENERGY', 'GEO_OPT', 'CELL_OPT', 'MD'])
def test_other_tasks_ignore_both_switches_and_invalid_inactive_resources(water, task):
    water.global_settings.run_type = task
    before = generate_input(water)
    water.vibrational.ir_enabled = water.vibrational.raman_enabled = True
    water.vibrational.nproc_rep = 999
    water.vibrational.fully_periodic = True
    assert generate_input(water) == before
