"""Only two DFT keywords, preserved drafts, and non-mutating applicability info."""
import json
import pytest
from pydantic import ValidationError
from core.models import DFTConfig, Project
from core.generator import generate_input
from core.validator import validate_project
from core.comprehensive_check import comprehensive_check
from core.project_io import save_project, load_project, export_bundle
from core.presets import capture_preset, apply_preset, Preset
from core.input_export import export_input
from core.input_import import import_input
from ui.validation_state import step_states


def dipole_infos(result):
    return [m for m in result.infos if getattr(m,'code','').startswith('dipole.')]


@pytest.mark.parametrize('task', ['ENERGY','GEO_OPT','CELL_OPT','VIBRATIONAL_ANALYSIS'])
@pytest.mark.parametrize('direction', ['X','Y','Z'])
def test_enabled_keywords_are_direct_dft_children_for_every_task(water, validator, task, direction):
    water.global_settings.run_type = task
    water.dft.surface_dipole_correction = True
    water.dft.surf_dip_dir = direction
    before = water.model_dump_json()
    text = generate_input(water)
    assert 'SURFACE_DIPOLE_CORRECTION T\n' in text and 'SURF_DIP_DIR '+direction+'\n' in text
    assert 'SURF_DIP_POS' not in text and 'SURF_DIP_SWITCH' not in text
    parsed = validator.parse(text)
    assert parsed.ok, parsed.errors
    dft = parsed.tree['+force_eval'][0]['+dft']
    assert dft['surface_dipole_correction'] is True and dft['surf_dip_dir'] == direction.lower()
    assert dft['+poisson'] == {'periodic':'xyz','poisson_solver':'periodic'}
    assert 'surface_dipole_correction' not in dft['+poisson'] and '+surface_dipole_correction' not in dft
    assert water.model_dump_json() == before


@pytest.mark.parametrize('task', ['ENERGY','GEO_OPT','CELL_OPT','VIBRATIONAL_ANALYSIS'])
def test_default_disabled_output_and_checks_are_identical(water, task):
    water.global_settings.run_type = task
    baseline = generate_input(water)
    assert not water.dft.surface_dipole_correction and water.dft.surf_dip_dir == 'Z'
    water.dft.surf_dip_dir = 'Y'
    assert generate_input(water) == baseline
    assert 'SURFACE_DIPOLE_CORRECTION' not in baseline and 'SURF_DIP_DIR' not in baseline
    assert not dipole_infos(validate_project(water))


@pytest.mark.parametrize('direction', ['NONE','XY','A','x',None,42])
def test_invalid_direction_rejected(direction):
    with pytest.raises(ValidationError):
        DFTConfig(surface_dipole_correction=True,surf_dip_dir=direction)


@pytest.mark.parametrize('periodic,solver,code', [
    ('XYZ','PERIODIC',None), ('NONE','MT','dipole.molecule_info'),
    ('XY','MT','dipole.partial_info'), ('XZ','WAVELET','dipole.partial_info'),
    ('YZ','ANALYTIC','dipole.partial_info'), ('X','ANALYTIC','dipole.partial_info'),
    ('XYZ','WAVELET','dipole.solver_info')])
def test_general_applicability_is_info_and_does_not_change_existing_severity(water, periodic, solver, code):
    water.structure.periodic = periodic
    water.dft.poisson_solver = solver
    baseline = validate_project(water)
    water.dft.surface_dipole_correction = True
    before = water.model_dump_json()
    result = validate_project(water)
    assert result.errors == baseline.errors and result.warnings == baseline.warnings
    codes = {getattr(m,'code','') for m in dipole_infos(result)}
    assert 'dipole.applicability_info' in codes
    if code: assert code in codes
    else: assert len(codes) == 1
    assert water.model_dump_json() == before
    assert [s.state for s in step_states(water,result,checked=True)] == [s.state for s in step_states(water,baseline,checked=True)]


def test_known_invalid_poisson_settings_remain_errors_and_invalid_direction_never_passes(water):
    water.structure.periodic = 'NONE'
    water.dft.surface_dipole_correction = True
    assert not validate_project(water).ok  # PERIODIC solver with NONE remains an error.
    object.__setattr__(water.dft,'surf_dip_dir','INVALID')
    assert not validate_project(water).ok
    assert not validate_project(Project(dft=DFTConfig(surface_dipole_correction=True))).ok


def test_old_and_new_projects_presets_and_input_restore_values(water, tmp_path):
    old = water.model_dump()
    old['dft'].pop('surface_dipole_correction');old['dft'].pop('surf_dip_dir')
    path = tmp_path/'legacy.json';path.write_text(json.dumps(old))
    legacy = load_project(path)
    assert not legacy.dft.surface_dipole_correction and legacy.dft.surf_dip_dir == 'Z'
    for enabled in [True,False]:
        water.dft.surface_dipole_correction = enabled
        water.dft.surf_dip_dir = 'X'
        save_project(water,path)
        assert load_project(path).dft == water.dft
        preset = capture_preset(water,'dipole parameters')
        assert apply_preset(legacy,preset).project.dft == water.dft
    old_preset = Preset(name='old preset',parameters={'dft':{'cutoff':550}})
    applied = apply_preset(water,old_preset).project
    assert not applied.dft.surface_dipole_correction and applied.dft.surf_dip_dir == 'X'
    water.dft.surface_dipole_correction = True
    inp = tmp_path/'import.inp';inp.write_text(generate_input(water))
    imported, _ = import_input(inp)
    assert imported.dft.surface_dipole_correction and imported.dft.surf_dip_dir == 'X'


@pytest.mark.parametrize('enabled', [False,True])
def test_comprehensive_check_and_exports_use_same_configuration(water, tmp_path, validator, enabled):
    water.dft.surface_dipole_correction = enabled
    water.dft.surf_dip_dir = 'Y'
    before = water.model_dump_json()
    checked = comprehensive_check(water)
    assert checked.validation.ok and not checked.validation.warnings, checked.report()
    assert bool(dipole_infos(checked.validation)) is enabled
    assert step_states(water,checked.validation,checked=True)[7].state == 'ready'
    text = generate_input(water)
    standalone = export_input(water,tmp_path/'surface.inp')
    assert standalone.path.read_text() == text
    bundle = export_bundle(water,tmp_path/'package')
    parsed = validator.parse(bundle.read_text(),bundle.parent)
    assert parsed.ok, parsed.errors
    dft = parsed.tree['+force_eval'][0]['+dft']
    assert ('surface_dipole_correction' in dft) is enabled
    if enabled: assert dft['surface_dipole_correction'] is True and dft['surf_dip_dir'] == 'y'
    assert 'SURF_DIP_POS' not in bundle.read_text() and 'SURF_DIP_SWITCH' not in bundle.read_text()
    assert water.model_dump_json() == before
