"""AIMD input/XML, real package dependencies and independent task state."""
import json
from pathlib import Path
import zipfile
import numpy as np
import pytest
from pydantic import ValidationError
from core.models import Project, MDConfig
from core.generator import generate_input, build_sections, Section, GenerationError
from core.validator import validate_project
from core.project_io import save_project, load_project, export_bundle
from core.input_export import export_input
from core.input_import import import_input
from core.presets import capture_preset, apply_preset, Preset
from core.comprehensive_check import comprehensive_check, source_signatures
from core.kind_validator import project_catalog
from core.atom_constraints import set_fixed_atoms
from core.file_references import generated_file_references
from core.md import inspect_restart
from core.run_script_generator import generate_run_script
from ui.validation_state import step_states


@pytest.fixture
def md_project(water):
    water.global_settings.run_type = 'MD'
    return water


# Synthetic dynamics state, not output from a real MD run. The RNG record
# follows CP2K v2026.1 parallel_rng_types_unittest.F's documented dump format.
RNG_RECORD = 'qtb_rng_gaussian'.ljust(40) + ' 1 F T F' + f'{0:25.16E}' + ''.join(f'{12:20.1f}' for _ in range(18))


def restart_text(project):
    source = project.model_copy(deep=True)
    source.md.continue_from_restart = False
    sections = build_sections(source)
    force = next(s for s in sections if s.name == 'FORCE_EVAL')
    subsys = next(s for s in force.children if s.name == 'SUBSYS')
    subsys.children.append(Section('VELOCITY', keywords=[('', (.001, .002, .003)) for _ in source.structure.symbols]))
    motion = next(s for s in sections if s.name == 'MOTION')
    md = next(s for s in motion.children if s.name == 'MD')
    md.keywords.extend([('STEP_START_VAL', 100), ('TIME_START_VAL', 50.0), ('ECONS_START_VAL', -17.1234)])
    if source.md.ensemble == 'NVT':
        csvr = next(s for s in md.children if s.name == 'THERMOSTAT').children[0]
        csvr.children.extend([Section('THERMOSTAT_ENERGY', keywords=[('', repr(.0123456789012345))]),
            Section('RNG_INIT', keywords=[('', RNG_RECORD)])])
    return '\n\n'.join('\n'.join(s.render()) for s in sections) + '\n'


@pytest.mark.parametrize('ensemble', ['NVT', 'NVE'])
@pytest.mark.parametrize('fmt', ['XYZ', 'EXTXYZ'])
def test_md_placement_ensemble_outputs_defaults_and_xml(md_project, validator, ensemble, fmt):
    p = md_project
    p.md.ensemble, p.md.trajectory_format = ensemble, fmt
    before = p.model_dump_json()
    parsed = validator.parse(generate_input(p))
    assert parsed.ok, parsed.errors
    t = parsed.tree
    assert t['+global']['run_type'] == 'md' and '+md' not in t and '+vibrational_analysis' not in t
    assert t['+force_eval'][0]['method'] == 'quickstep'
    assert '+geo_opt' not in t['+motion'] and '+cell_opt' not in t['+motion']
    md = t['+motion']['+md']
    assert (md['steps'], md['timestep'], md['temperature']) == (2000, .5, 300)
    assert md['initialization_method'] == 'default'
    assert ('+thermostat' in md) is (ensemble == 'NVT')
    if ensemble == 'NVT':
        assert md['+thermostat']['type'] == 'csvr'
        assert md['+thermostat']['+csvr']['timecon'] == 100
    assert md['+print']['+energy']['+each']['md'] == 1
    prints = t['+motion']['+print'][0]
    assert prints['+trajectory']['format'] == fmt.lower() and prints['+trajectory']['+each']['md'] == 10
    assert prints['+restart']['backup_copies'] == 2 and prints['+restart']['+each']['md'] == 100
    assert p.md.simulation_time_ps == 1 and p.model_dump_json() == before
    checked = validate_project(p)
    assert checked.ok and not checked.warnings
    assert len([i for i in checked.infos if i.code.startswith('md.')]) == 3
    assert step_states(p, checked, checked=True)[5].state == step_states(p, checked, checked=True)[7].state == 'ready'


@pytest.mark.parametrize('field,value', [('steps', 0), ('steps', 1.5), ('steps', True), ('timestep', 0),
    ('timestep', float('nan')), ('temperature', -1), ('temperature', float('inf')), ('timecon', -2),
    ('trajectory_interval', 0), ('restart_interval', 0), ('backup_copies', -1), ('ensemble', 'NPT_I'), ('thermostat_type', 'NOSE')])
def test_invalid_parameters_rejected(field, value):
    with pytest.raises(ValidationError): MDConfig(**{field: value})


def test_requested_values_disabled_prints_zero_temperature_and_fixed_atoms(md_project, validator):
    p = md_project
    p.md = MDConfig(ensemble='NVE', steps=123, timestep=.1234567890123456, temperature=0,
        timecon=55, write_trajectory=False, write_restart=False)
    p.structure = set_fixed_atoms(p.structure, [p.structure.atom_ids[0]], 'Z')
    before = p.model_dump_json()
    t = validator.parse(generate_input(p)).tree
    assert t['+motion']['+md']['timestep'] == .1234567890123456
    assert t['+motion']['+md']['temperature'] == 0
    assert t['+motion']['+print'][0]['+trajectory']['_'] == 'OFF' and t['+motion']['+print'][0]['+restart']['_'] == 'OFF'
    assert t['+motion']['+constraint']['+fixed_atoms'][0]['components_to_fix'] == 'z'
    assert p.model_dump_json() == before
    p.structure = set_fixed_atoms(p.structure, p.structure.atom_ids, 'XYZ')
    assert 'md.all_fixed' in {m.code for m in validate_project(p).errors}


def test_only_infos_pass_but_real_md_warnings_and_overlaps_keep_severity(md_project):
    p = md_project
    p.dft.scf.eps_scf = 1e-5
    p.md.timestep = 3
    p.md.timecon = 1
    codes = {m.code for m in validate_project(p).warnings}
    assert {'md.scf_warning', 'md.timestep_warning', 'md.timecon_warning'} <= codes
    assert step_states(p, validate_project(p), checked=True)[5].state == 'warning'
    p.structure.positions[1] = p.structure.positions[0]
    assert 'md.overlap_error' in {m.code for m in validate_project(p).errors}
    with pytest.raises(GenerationError): generate_input(p)


def test_legacy_project_and_preset_roundtrip_keep_independent_states(md_project, tmp_path):
    p = md_project
    old = p.model_dump();old.pop('md');old['global_settings']['run_type'] = 'ENERGY'
    path = tmp_path / 'legacy.json';path.write_text(json.dumps(old))
    legacy = load_project(path)
    assert legacy.md == MDConfig()
    p.md.timecon, p.md.steps, p.md.trajectory_format = 37, 4321, 'EXTXYZ'
    p.motion.max_iter = 345
    p.cell_opt.external_pressure = 65
    p.vibrational.dx = .007
    save_project(p, path)
    restored = load_project(path)
    assert restored == p
    preset = Preset.model_validate_json(capture_preset(p, 'AIMD').model_dump_json())
    assert apply_preset(legacy, preset).project.md == p.md
    assert apply_preset(legacy, preset).project.motion == p.motion
    for task in ['GEO_OPT', 'CELL_OPT', 'VIBRATIONAL_ANALYSIS', 'ENERGY', 'MD']:
        restored.global_settings.run_type = task
        assert restored.md == p.md


@pytest.mark.parametrize('ensemble', ['NVT', 'NVE'])
def test_full_restart_references_state_precision_files_notes_and_safe_export(md_project, validator, tmp_path, ensemble):
    p = md_project
    p.md.ensemble = ensemble
    path = tmp_path / 'previous.restart'
    path.write_text(restart_text(p))
    p.md.continue_from_restart = True;p.md.restart_file = str(path)
    before = p.model_dump_json(), path.read_bytes()
    state = inspect_restart(p)
    assert state.dynamics['step_start_val'] == 100
    text = generate_input(p)
    parsed = validator.parse(text)
    assert parsed.ok, parsed.errors
    ext = parsed.tree['+ext_restart']
    assert not ext['restart_default'] and all(ext[key] for key in ['restart_pos','restart_vel','restart_cell','restart_counters'])
    assert ext['restart_thermostat'] is (ensemble == 'NVT')
    if ensemble == 'NVT':
        csvr = parsed.tree['+motion']['+md']['+thermostat']['+csvr']
        assert csvr['+rng_init']['*'] == [RNG_RECORD]
        assert csvr['+thermostat_energy']['*'] == [.0123456789012345]
    standalone = export_input(p, tmp_path / 'input.inp')
    assert standalone.path.read_text() == text and str(path) in standalone.dependencies
    imported, _ = import_input(standalone.path)
    assert imported.md.ensemble == ensemble and imported.md.continue_from_restart
    assert imported.md.restart_file == str(path)
    assert str(path) in source_signatures(p, project_catalog(p))
    # Unsafe source basenames are copied to portable collision-safe paths.
    unusual = tmp_path / '中文 previous (MD).restart'
    path.rename(unusual);p.md.restart_file = str(unusual)
    source_bytes = unusual.read_bytes()
    package = export_bundle(p, tmp_path / 'job')
    parsed = validator.parse(package.read_text(), package.parent)
    assert parsed.ok, parsed.errors
    refs = [r.value for r in generated_file_references(package.read_text()) if r.keyword == 'RESTART_FILE_NAME']
    assert len(refs) == 1 and refs[0].startswith('data/') and '(' not in refs[0]
    assert (package.parent / refs[0]).read_bytes() == source_bytes
    assert unusual.read_bytes() == source_bytes == before[1]
    reopened = load_project(package.parent / 'project.cp2kstudio.json')
    assert validate_project(reopened).ok
    assert reopened.md.restart_file == str(package.parent / refs[0])
    assert (package.parent / 'run.sh').read_text() == generate_run_script(p.run_environment)
    notes = (package.parent / 'EXPORT_NOTES.txt').read_text()
    assert 'BORN–OPPENHEIMER AIMD' in notes and 'project-1.ener' in notes and '连续性' in notes
    assert not list(package.parent.glob('*.ener')) and not list(package.parent.glob('*pos-*.xyz'))
    checked = comprehensive_check(p)
    assert checked.validation.ok, checked.report()
    archive = export_bundle(p, tmp_path / 'job.zip', archive=True)
    with zipfile.ZipFile(archive) as z:
        assert {'input.inp','structure.xyz','run.sh','EXPORT_NOTES.txt','project.cp2kstudio.json'} <= set(z.namelist())
        assert refs[0] in z.namelist()


@pytest.mark.parametrize('defect', ['missing', 'coords', 'velocities', 'counter', 'cell', 'elements', 'ensemble', 'rng', 'csvr', 'preprocessor'])
def test_incomplete_or_mismatched_restart_blocks_export_with_specific_error(md_project, tmp_path, defect):
    p = md_project
    text = restart_text(p)
    if defect == 'coords': text = text.replace('O 0 0 -0.065587', 'H 0 0 -0.065587')
    elif defect == 'velocities': text = text.replace('&VELOCITY', '&CORE_VELOCITY').replace('&END VELOCITY', '&END CORE_VELOCITY')
    elif defect == 'counter': text = text.replace('STEP_START_VAL 100', 'STEP_START_VAL -1')
    elif defect == 'cell': text = text.replace('A 6 0 0', 'A 7 0 0')
    elif defect == 'elements': text = text.replace('ELEMENT O', 'ELEMENT C')
    elif defect == 'ensemble': text = text.replace('ENSEMBLE NVT', 'ENSEMBLE NVE')
    elif defect == 'rng': text = text.replace(RNG_RECORD, '1 2 3')
    elif defect == 'csvr': text = text.replace('&THERMOSTAT_ENERGY', '&RNG_INIT').replace('&END THERMOSTAT_ENERGY', '&END RNG_INIT')
    elif defect == 'preprocessor': text = '@INCLUDE missing.inp\n' + text
    file = tmp_path / 'invalid.restart'
    if defect != 'missing': file.write_text(text)
    p.md.continue_from_restart = True;p.md.restart_file = str(file)
    result = validate_project(p)
    assert any(m.code == 'md.restart_error' for m in result.errors)
    assert step_states(p, result, checked=True)[5].state == 'error'
    with pytest.raises(GenerationError): export_bundle(p, tmp_path / 'failed')
    assert not (tmp_path / 'failed').exists()


def test_original_force_eval_and_four_task_inputs_do_not_depend_on_inactive_md_settings(water, validator):
    for task in ['ENERGY','GEO_OPT','CELL_OPT','VIBRATIONAL_ANALYSIS']:
        water.global_settings.run_type = task
        baseline = generate_input(water)
        water.md = MDConfig(ensemble='NVE', steps=987, timecon=83, continue_from_restart=True, restart_file='missing.restart')
        assert generate_input(water) == baseline
        water.global_settings.run_type = 'MD';water.md.continue_from_restart = False
        old = validator.parse(baseline).tree
        current = validator.parse(generate_input(water)).tree
        if task != 'CELL_OPT':
            assert old['+force_eval'] == current['+force_eval']


@pytest.mark.parametrize('valid_but_changed', [False, True])
def test_comprehensive_check_opens_final_restart_and_catches_tampered_copy(md_project, tmp_path, monkeypatch, valid_but_changed):
    from core import comprehensive_check as checks
    p = md_project
    file = tmp_path / 'previous.restart';file.write_text(restart_text(p))
    p.md.restart_file = str(file);p.md.continue_from_restart = True
    source = file.read_bytes()
    writer = checks._write_bundle_files
    def tamper(project, directory, *args, **kwargs):
        text = writer(project, directory, *args, **kwargs)
        ref = next(r for r in generated_file_references(text) if r.keyword == 'RESTART_FILE_NAME')
        copied = directory / ref.value
        copied.write_text(copied.read_text().replace('0.001', '0.004') if valid_but_changed else 'not a restart')
        return text
    monkeypatch.setattr(checks, '_write_bundle_files', tamper)
    result = checks.comprehensive_check(p)
    assert not result.validation.ok and result.stages[2].errors
    assert file.read_bytes() == source


def test_complete_state_changes_are_detected_without_changing_structure(md_project, tmp_path):
    p = md_project
    file = tmp_path / 'previous.restart';file.write_text(restart_text(p))
    p.md.restart_file = str(file);p.md.continue_from_restart = True
    before = p.structure.model_dump_json()
    assert validate_project(p).ok
    file.write_text(file.read_text().replace('STEP_START_VAL 100', 'STEP_START_VAL -1'))
    assert not validate_project(p).ok
    assert p.structure.model_dump_json() == before


def test_restart_with_native_default_qs_method_is_accepted(md_project, tmp_path):
    p = md_project
    file = tmp_path / 'implicit-qs.restart'
    file.write_text(restart_text(p).replace('  METHOD Quickstep\n', ''))
    p.md.restart_file = str(file);p.md.continue_from_restart = True
    assert validate_project(p).ok


def test_partial_input_restart_is_not_silently_promoted_to_full_continuation(md_project, tmp_path):
    p = md_project
    source = tmp_path / 'previous.restart';source.write_text(restart_text(p))
    p.md.continue_from_restart = True;p.md.restart_file = str(source)
    text = generate_input(p).replace('RESTART_VEL TRUE', 'RESTART_VEL FALSE')
    file = tmp_path / 'partial.inp';file.write_text(text)
    with pytest.raises(ValueError, match='EXT_RESTART'):
        import_input(file)


def test_md_diagnostic_routing_does_not_capture_unrelated_database_filenames():
    from ui.export_panel import error_page
    assert error_page('md.steps: invalid value')[0] == 5
    assert error_page('MD: restart is missing')[0] == 5
    assert error_page('KIND O: data/CUSTOMD.POT is missing')[0] == 4
