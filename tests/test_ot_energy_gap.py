"""Optional OT gap: authoritative XML, backward compatibility and delivery."""
import json
import pytest
from pydantic import ValidationError
from core.models import Project, SCFConfig
from core.generator import generate_input, GenerationError
from core.validator import validate_project
from core.comprehensive_check import comprehensive_check
from core.project_io import save_project, load_project, export_bundle
from core.input_export import export_input
from core.input_import import import_input
from core.presets import capture_preset, apply_preset, Preset
from core.schema import CP2KSchema


@pytest.mark.parametrize('task', ['ENERGY', 'GEO_OPT', 'CELL_OPT', 'VIBRATIONAL_ANALYSIS'])
@pytest.mark.parametrize('gap', [-1.0, 0.0, .001, .08, .1, .2, .5, 1.234567890123456e-5])
def test_explicit_gap_uses_ot_only_and_preserves_float_precision(water, validator, task, gap):
    water.global_settings.run_type = task
    baseline = generate_input(water)
    water.dft.scf.energy_gap = gap
    before = water.model_dump_json()
    text = generate_input(water)
    # This optional keyword is the only INP change for every existing task.
    line = next(line for line in text.splitlines(keepends=True) if 'ENERGY_GAP' in line)
    assert line.strip() == f'ENERGY_GAP {repr(gap)}'
    assert text.replace(line, '') == baseline
    parsed = validator.parse(text)
    assert parsed.ok, parsed.errors
    scf = parsed.tree['+force_eval'][0]['+dft']['+scf']
    assert scf['+ot']['energy_gap'] == gap
    assert 'energy_gap' not in scf and scf['+ot']['minimizer'] == 'cg'
    assert water.model_dump_json() == before
    water.dft.scf.method = 'DIAGONALIZATION'
    diag = generate_input(water)
    assert 'ENERGY_GAP' not in diag and '&OT' not in diag
    water.dft.scf.energy_gap = None
    assert generate_input(water) == diag


def test_auto_is_model_default_and_official_default_is_negative_one(water, validator):
    assert Project().dft.scf.energy_gap is None
    assert float(CP2KSchema().keyword('FORCE_EVAL/DFT/SCF/OT', 'ENERGY_GAP')['default']) == -1.0
    assert 'ENERGY_GAP' not in generate_input(water)
    assert validator.parse(generate_input(water)).ok


@pytest.mark.parametrize('invalid', [float('nan'), float('inf'), -float('inf'), 'bad', True])
def test_invalid_gap_rejected_by_model_and_generator(water, invalid):
    with pytest.raises(ValidationError):
        SCFConfig(energy_gap=invalid)
    object.__setattr__(water.dft.scf, 'energy_gap', invalid)
    assert not validate_project(water).ok
    with pytest.raises(GenerationError):
        generate_input(water)


@pytest.mark.parametrize('gap', [None, -1.0, .08123456789012345])
def test_old_and_new_projects_presets_and_input_restore_gap_and_cg(water, tmp_path, gap):
    data = water.model_dump()
    data['dft']['scf'].pop('energy_gap')
    path = tmp_path / 'old.json'
    path.write_text(json.dumps(data))
    legacy = load_project(path)
    assert legacy.dft.scf.energy_gap is None and legacy.dft.scf.minimizer == 'CG'
    water.dft.scf.energy_gap = gap
    save_project(water, path)
    restored = load_project(path)
    assert restored.dft == water.dft
    preset = Preset.model_validate_json(capture_preset(restored, 'OT settings').model_dump_json())
    assert apply_preset(legacy, preset).project.dft == water.dft
    old_preset = Preset(name='Legacy', parameters={'dft': {'scf': {'minimizer': 'CG'}}})
    assert apply_preset(water, old_preset).project.dft.scf.energy_gap == gap
    path = tmp_path / 'ot.inp'
    path.write_text(generate_input(water))
    imported, warnings = import_input(path)
    assert imported.dft.scf.energy_gap == gap and imported.dft.scf.minimizer == 'CG'
    assert not any('energy_gap' in str(w).lower() for w in warnings)


@pytest.mark.parametrize('task', ['ENERGY', 'GEO_OPT', 'CELL_OPT', 'VIBRATIONAL_ANALYSIS'])
def test_check_standalone_and_package_share_gap_and_do_not_adjust_accuracy(water, validator, tmp_path, task):
    water.global_settings.run_type = task
    water.dft.scf.energy_gap = .08123456789012345
    water.dft.scf.eps_scf = 1e-9  # Heuristic does not become an extra mandatory rule.
    before = water.model_dump_json()
    checked = comprehensive_check(water)
    assert checked.validation.ok, checked.report()
    text = generate_input(water)
    standalone = export_input(water, tmp_path / 'standalone.inp')
    assert standalone.path.read_text() == text
    bundle = export_bundle(water, tmp_path / 'package')
    parsed = validator.parse(bundle.read_text(), bundle.parent)
    assert parsed.ok, parsed.errors
    assert parsed.tree['+force_eval'][0]['+dft']['+scf']['+ot']['energy_gap'] == water.dft.scf.energy_gap
    assert 'ENERGY_GAP 0.08123456789012345' in bundle.read_text()
    assert (bundle.parent / 'run.sh').is_file() and (bundle.parent / 'EXPORT_NOTES.txt').is_file()
    assert water.dft.eps_default == 1e-10 and water.model_dump_json() == before
