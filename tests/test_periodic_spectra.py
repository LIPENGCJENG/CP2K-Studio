"""Production paths and static checks; no numerical spectroscopy is claimed."""
from tests.vibrational_helpers import set_model_spectra, set_ui_spectra
from copy import deepcopy
import zipfile

import pytest

from core.comprehensive_check import comprehensive_check
from core.generator import generate_input, GenerationError
from core.input_export import export_input
from core.input_import import import_input
from core.models import FixedAtom, VibrationalConfig
from core.presets import capture_preset, apply_preset, PresetStore
from core.project_io import save_project, load_project, export_bundle
from core.run_script_generator import generate_run_script
from core.validator import validate_project
from core.vibrational import spectroscopy_path, SpectroscopyPath, validate_spectroscopy_input
from ui.validation_state import step_states


@pytest.fixture
def periodic(water):
    water.global_settings.run_type = 'VIBRATIONAL_ANALYSIS'
    water.dft.scf.eps_scf = 1e-9
    water.vibrational.fully_periodic = True
    return water


@pytest.mark.parametrize('boundary', ['NONE', 'XYZ'])
@pytest.mark.parametrize('mode', ['FREQUENCIES', 'IR', 'RAMAN'])
def test_path_matrix_xml_structure_and_no_mutation(periodic, validator, boundary, mode):
    p = periodic
    p.structure.periodic = boundary
    p.dft.poisson_solver = 'PERIODIC' if boundary == 'XYZ' else 'MT'
    set_model_spectra(p.vibrational, mode)
    p.vibrational.dx = .0045
    p.vibrational.linres_eps = 3.1e-9
    p.vibrational.linres_max_iter = 321
    before = p.model_dump_json()
    text = generate_input(p)
    parsed = validator.parse(text)
    assert parsed.ok, parsed.errors
    assert not validate_spectroscopy_input(p, parsed.tree)
    tree = parsed.tree
    assert tree['+vibrational_analysis']['intensities'] is (mode != 'FREQUENCIES')
    assert tree['+vibrational_analysis']['dx'] == .0045
    assert tree['+vibrational_analysis']['fully_periodic'] is True
    force = tree['+force_eval'][0]
    dft = force['+dft']
    assert '+motion' not in tree
    assert dft['+poisson']['periodic'].upper() == boundary
    assert force['+subsys']['+cell']['periodic'].upper() == boundary
    if mode == 'IR':
        node = dft['+print']['+moments']
        assert node['periodic'] is (boundary == 'XYZ') and node['max_moment'] == 1
        assert node['_'] == 'ON' and '+properties' not in force
        assert text.count('&MOMENTS ON') == 1 and text.count('&PRINT') == 2
        if boundary == 'NONE':
            assert node['reference'] == 'com'
        else:
            assert 'reference' not in node  # No molecular-origin setting for Berry phase.
    elif mode == 'RAMAN':
        linres = force['+properties']['+linres']
        assert linres['eps'] == 3.1e-9 and linres['max_iter'] == 321
        node = linres['+polar']
        assert node['_'] and node['do_raman']
        assert node['periodic_dipole_operator'] is (boundary == 'XYZ')
        assert '+print' not in dft
        assert text.count('&LINRES') == text.count('&POLAR TRUE') == 1
    else:
        assert '+print' not in dft and '+properties' not in force
    assert p.model_dump_json() == before


def test_switches_leave_no_properties_or_constraint_residue(periodic, validator):
    p = periodic
    p.structure.fixed_atoms = [FixedAtom(atom_id=1, components='Z')]
    for boundary in ['XYZ', 'NONE', 'XYZ', 'NONE']:
        p.structure.periodic = boundary
        p.dft.poisson_solver = 'PERIODIC' if boundary == 'XYZ' else 'MT'
        for mode in ['IR', 'RAMAN', 'FREQUENCIES', 'RAMAN', 'IR']:
            set_model_spectra(p.vibrational, mode)
            text = generate_input(p)
            tree = validator.parse(text).tree
            assert not validate_spectroscopy_input(p, tree)
            assert ('&MOMENTS' in text) is (mode == 'IR')
            assert ('&POLAR TRUE' in text) is (mode == 'RAMAN')
            assert '&FIXED_ATOMS' not in text and '&MOTION' not in text
    assert p.structure.fixed_atoms[0].components == 'Z'


@pytest.mark.parametrize('mode', ['IR', 'RAMAN'])
def test_info_only_periodic_support_passes_all_stages(periodic, mode):
    periodic.vibrational.linres_eps = 1e-8  # Isolate Info severity from accuracy warnings.
    set_model_spectra(periodic.vibrational, mode)
    before = periodic.model_dump_json()
    local = validate_project(periodic)
    assert local.ok and not local.warnings
    codes = {m.code for m in local.infos}
    assert 'vib.periodic_experimental_info' in codes
    assert ('vib.berry_branch_info' in codes) is (mode == 'IR')
    for language in ['en_US', 'zh_CN']:
        message = next(m for m in local.infos if m.code == 'vib.periodic_experimental_info')
        assert ('experimental' if language == 'en_US' else '实验性') in message.render(language)
    checked = comprehensive_check(periodic)
    assert checked.validation.ok and not checked.validation.warnings
    assert [stage.state for stage in checked.stages] == ['ready'] * 4
    assert step_states(periodic, checked.validation, checked=True)[5].state == 'ready'
    assert step_states(periodic, checked.validation, checked=True)[7].state == 'ready'
    assert periodic.model_dump_json() == before


@pytest.mark.parametrize('mode', ['IR', 'RAMAN'])
def test_fully_periodic_remains_independent(periodic, mode):
    set_model_spectra(periodic.vibrational, mode)
    periodic.vibrational.fully_periodic = False
    result = validate_project(periodic)
    assert result.ok and 'vib.periodic_info' in {m.code for m in result.infos}
    assert all('FULLY_PERIODIC' not in str(m) for m in result.warnings)
    assert 'FULLY_PERIODIC FALSE' in generate_input(periodic)
    assert not periodic.vibrational.fully_periodic


@pytest.mark.parametrize('mode', ['IR', 'RAMAN'])
@pytest.mark.parametrize('setting', ['smearing', 'added_mos'])
def test_fractional_or_empty_orbitals_are_rejected_without_changing_scf(periodic, mode, setting):
    set_model_spectra(periodic.vibrational, mode)
    periodic.dft.scf.method = 'DIAGONALIZATION'
    periodic.dft.scf.added_mos = 2
    periodic.dft.scf.smearing = setting == 'smearing'
    before = periodic.model_dump_json()
    result = validate_project(periodic)
    assert 'vib.occupations_error' in {m.code for m in result.errors}
    with pytest.raises(GenerationError):
        generate_input(periodic)
    assert periodic.model_dump_json() == before


def test_periodic_ir_with_full_integer_diagonalization_is_allowed(periodic):
    set_model_spectra(periodic.vibrational, 'IR')
    periodic.dft.scf.method = 'DIAGONALIZATION'
    assert validate_project(periodic).ok
    assert 'PERIODIC TRUE' in generate_input(periodic)


@pytest.mark.parametrize('mode', ['IR', 'RAMAN'])
@pytest.mark.parametrize('damage', ['operator', 'intensities', 'fully_periodic', 'method', 'kpoints', 'boundary', 'property'])
def test_actual_inp_semantics_catch_xml_valid_wrong_paths(periodic, validator, mode, damage):
    set_model_spectra(periodic.vibrational, mode)
    tree = deepcopy(validator.parse(generate_input(periodic)).tree)
    force = tree['+force_eval'][0]
    if damage == 'operator':
        if mode == 'IR':
            force['+dft']['+print']['+moments']['periodic'] = False
        else:
            force['+properties']['+linres']['+polar']['periodic_dipole_operator'] = False
    elif damage in {'intensities', 'fully_periodic'}:
        tree['+vibrational_analysis'][damage] = False
    elif damage == 'method':
        force['+dft']['+qs']['method'] = 'gapw'
    elif damage == 'kpoints':
        force['+dft']['+kpoints'] = {'scheme': 'MONKHORST-PACK 2 2 2'}
    elif damage == 'boundary':
        force['+dft']['+poisson']['periodic'] = 'none'
    elif damage == 'property':
        force['+dft'].pop('+print', None)
        force.pop('+properties', None)
    errors = validate_spectroscopy_input(periodic, tree)
    assert errors
    assert errors[0].code == ('vib.kpoints_error' if damage == 'kpoints' else 'vib.property_path_error')


@pytest.mark.parametrize('mode', ['IR', 'RAMAN'])
def test_roundtrip_export_preset_and_bilingual_notes(periodic, validator, tmp_path, mode):
    p = periodic
    set_model_spectra(p.vibrational, mode)
    p.vibrational.linres_eps = 2e-9
    before = generate_input(p)
    path = tmp_path / 'crystal.json'
    save_project(p, path)
    assert load_project(path) == p
    store = PresetStore(tmp_path / 'presets')
    preset = store.save(capture_preset(p, 'Periodic ' + mode))
    assert preset.coordinates is None
    target = p.model_copy(deep=True)
    target.vibrational = VibrationalConfig()
    restored = apply_preset(target, store.load(preset.id)).project
    assert generate_input(restored) == before
    single = tmp_path / 'inline.inp'
    export_input(p, single)
    assert single.read_text() == before
    imported, _ = import_input(single)
    assert generate_input(imported) == before
    folder = export_bundle(p, tmp_path / mode).parent
    parsed = validator.parse((folder / 'input.inp').read_text(), folder)
    assert parsed.ok and not validate_spectroscopy_input(p, parsed.tree)
    assert load_project(folder / 'project.cp2kstudio.json').vibrational == p.vibrational
    assert (folder / 'run.sh').read_text() == generate_run_script(p.run_environment)
    notes = (folder / 'EXPORT_NOTES.txt').read_text()
    assert 'Berry-phase' in notes and 'experimental' in notes and '实验性' in notes
    assert 'not implemented' not in notes and '尚未实现' not in notes
    assert not list(folder.glob('*.hess')) and not (folder / 'output.out').exists()
    archive = export_bundle(p, tmp_path / (mode + '.zip'), archive=True)
    with zipfile.ZipFile(archive) as zipped:
        text = zipped.read(next(n for n in zipped.namelist() if n.endswith('input.inp'))).decode()
        assert 'COORD_FILE_NAME structure.xyz' in text
        assert ('PERIODIC_DIPOLE_OPERATOR TRUE' in text) is (mode == 'RAMAN')


@pytest.mark.parametrize('mode', ['IR', 'RAMAN'])
def test_inp_import_rejects_wrong_operator_and_explicit_kpoints(periodic, tmp_path, mode):
    set_model_spectra(periodic.vibrational, mode)
    text = generate_input(periodic)
    token = 'PERIODIC TRUE' if mode == 'IR' else 'PERIODIC_DIPOLE_OPERATOR TRUE'
    path = tmp_path / 'wrong.inp'
    path.write_text(text.replace(token, token.replace('TRUE', 'FALSE')))
    with pytest.raises(ValueError):
        import_input(path)
    path.write_text(text.replace('&DFT\n', '&DFT\n    &KPOINTS\n      SCHEME MONKHORST-PACK 2 2 2\n    &END KPOINTS\n'))
    with pytest.raises(ValueError) as caught:
        import_input(path)
    assert 'KPOINTS' in str(caught.value)


def test_export_rechecks_actual_operator_before_writing(periodic, tmp_path, monkeypatch):
    import core.input_export as module
    set_model_spectra(periodic.vibrational, 'IR')
    text = generate_input(periodic).replace('PERIODIC TRUE', 'PERIODIC FALSE')
    monkeypatch.setattr(module, 'generate_input', lambda *a, **k: text)
    path = tmp_path / 'wrong.inp'
    with pytest.raises(GenerationError):
        export_input(periodic, path)
    assert not path.exists()


@pytest.mark.parametrize('operation', ['bundle', 'comprehensive'])
def test_package_and_comprehensive_check_reject_actual_wrong_operator(periodic, tmp_path, monkeypatch, operation):
    import core.project_io as io_module
    import core.comprehensive_check as check_module
    periodic.vibrational.linres_eps = 1e-8  # Keep the configuration stage warning-free.
    set_model_spectra(periodic.vibrational, 'RAMAN')
    original = io_module._write_bundle_files

    def corrupt(project, directory, *args, **kwargs):
        text = original(project, directory, *args, **kwargs)
        text = text.replace('PERIODIC_DIPOLE_OPERATOR TRUE', 'PERIODIC_DIPOLE_OPERATOR FALSE')
        (directory / 'input.inp').write_text(text)
        return text

    if operation == 'bundle':
        monkeypatch.setattr(io_module, '_write_bundle_files', corrupt)
        with pytest.raises(GenerationError):
            export_bundle(periodic, tmp_path / 'wrong-package')
        assert not (tmp_path / 'wrong-package').exists()
    else:
        monkeypatch.setattr(check_module, '_write_bundle_files', corrupt)
        result = comprehensive_check(periodic)
        assert result.stages[0].state == 'ready'
        assert result.stages[1].state == 'error'
        assert any('PERIODIC XYZ' in str(e) for e in result.stages[1].errors)


def test_path_selection_does_not_depend_on_fully_periodic():
    assert spectroscopy_path('IR', 'XYZ') is SpectroscopyPath.PERIODIC_IR
    assert spectroscopy_path('RAMAN', 'NONE') is SpectroscopyPath.MOLECULAR_RAMAN
    assert spectroscopy_path('IR', 'XY') is SpectroscopyPath.UNSUPPORTED
