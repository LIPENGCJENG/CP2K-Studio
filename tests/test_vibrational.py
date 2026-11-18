"""Static production-input checks, not numerical frequency/spectrum claims."""
from tests.vibrational_helpers import set_model_spectra, set_ui_spectra
from pathlib import Path
import zipfile
import pytest
from pydantic import ValidationError
from core.models import Project, VibrationalConfig, FixedAtom
from core.generator import generate_input, GenerationError
from core.validator import validate_project
from core.comprehensive_check import comprehensive_check
from core.project_io import save_project, load_project, export_bundle
from core.input_export import export_input
from core.input_import import import_input
from core.presets import capture_preset, apply_preset, PresetStore
from core.run_script_generator import generate_run_script

FIXTURES = Path(__file__).parent / 'fixtures'


def english(messages):
    return '\n'.join(m.render('en_US') if hasattr(m, 'render') else str(m) for m in messages)


@pytest.mark.parametrize('mode', ['FREQUENCIES', 'IR', 'RAMAN'])
def test_top_level_xml_and_required_properties(vib_project, validator, mode):
    p = vib_project
    set_model_spectra(p.vibrational, mode)
    p.vibrational.dx = .005
    p.vibrational.nproc_rep = 4
    p.run_environment.mpi_processes = 16
    p.vibrational.proc_dist_type = 'INTERLEAVED'
    p.vibrational.hessian = True
    p.structure.positions[0] = (.1234567890123, 0, -.065587123456)
    before = p.model_dump_json()
    text = generate_input(p)
    assert text.index('&GLOBAL') < text.index('&VIBRATIONAL_ANALYSIS') < text.index('&FORCE_EVAL')
    assert '&MOTION' not in text and '&GEO_OPT' not in text and '&CONSTRAINT' not in text
    assert '.123456789012' in text and '0.1235 ' not in text
    parsed = validator.parse(text)
    assert parsed.ok, parsed.errors
    tree = parsed.tree
    vib = tree['+vibrational_analysis']
    assert vib['dx'] == .005 and vib['nproc_rep'] == 4
    assert vib['proc_dist_type'] == 'interleaved' and not vib['fully_periodic']
    assert vib['intensities'] is (mode != 'FREQUENCIES')
    assert vib['+print']['+molden_vib']['_'] == 'ON'
    assert vib['+print']['+hessian']['_'] == 'ON'
    force = tree['+force_eval'][0]
    dft = force['+dft']
    if mode == 'IR':
        moments = dft['+print']['+moments']
        assert moments['_'] == 'ON' and not moments['periodic'] and moments['max_moment'] == 1
        assert '+properties' not in force
    elif mode == 'RAMAN':
        linres = force['+properties']['+linres']
        polar = linres['+polar']
        assert polar['_'] is True and polar['do_raman'] is True
        assert not polar['periodic_dipole_operator']
        assert linres['eps'] == p.vibrational.linres_eps
        assert '+print' not in dft
    else:
        assert '+properties' not in force and '+print' not in dft
    assert p.model_dump_json() == before


def test_official_v2026_1_raman_regression_fixture(vib_project, validator):
    upstream = validator.parse((FIXTURES / 'upstream_vibrational_raman.inp').read_text())
    assert upstream.ok, upstream.errors
    set_model_spectra(vib_project.vibrational, 'RAMAN')
    actual = validator.parse(generate_input(vib_project)).tree
    for tree in [upstream.tree, actual]:
        assert tree['+global']['run_type'] == 'vibrational_analysis'
        assert tree['+vibrational_analysis']['intensities']
        polar = tree['+force_eval'][0]['+properties']['+linres']['+polar']
        assert polar['_'] and polar['do_raman'] and not polar['periodic_dipole_operator']


@pytest.mark.parametrize('field,value', [('dx', 0), ('dx', -1), ('dx', float('nan')),
    ('dx', float('inf')), ('nproc_rep', 0), ('nproc_rep', True), ('nproc_rep', 1.5),
    ('tc_temperature', -1), ('tc_pressure', 0), ('linres_eps', 0), ('linres_max_iter', 1.2)])
def test_invalid_parameters_are_rejected(field, value):
    with pytest.raises(ValidationError):
        VibrationalConfig(**{field: value})


@pytest.mark.parametrize('mpi,rep,omp,valid', [(16, 1, 1, True), (16, 4, 2, True),
    (16, 16, 1, True), (1, 1, 1, True), (16, 3, 1, False), (16, 32, 4, False),
    (16, 17, 1, False), (18, 4, 1, False)])
def test_replica_resource_checks(vib_project, mpi, rep, omp, valid):
    p = vib_project
    p.run_environment.mpi_processes = mpi
    p.run_environment.omp_threads = omp
    p.vibrational.nproc_rep = rep
    result = validate_project(p)
    assert result.ok is valid
    if not valid:
        assert 'NPROC_REP' in english(result.errors)
        with pytest.raises(GenerationError):
            generate_input(p)


@pytest.mark.parametrize('mode', ['IR', 'RAMAN'])
@pytest.mark.parametrize('periodic', ['X', 'Y', 'Z', 'XY', 'XZ', 'YZ'])
def test_partial_periodic_spectroscopy_is_blocked_without_mutating_periodicity(vib_project, mode, periodic):
    p = vib_project
    p.structure.periodic = periodic
    p.dft.poisson_solver = 'ANALYTIC'
    set_model_spectra(p.vibrational, mode)
    before = p.model_dump_json()
    result = validate_project(p)
    assert not result.ok and 'periodic' in english(result.errors)
    with pytest.raises(GenerationError):
        generate_input(p)
    assert p.model_dump_json() == before


def test_fully_periodic_is_explicit_and_thermochemistry_uses_xml_units(vib_project, validator):
    p = vib_project
    p.vibrational.thermochemistry = True
    p.vibrational.tc_temperature = 298.15
    p.vibrational.tc_pressure = 100000
    node = validator.parse(generate_input(p)).tree['+vibrational_analysis']
    assert node['thermochemistry'] and node['tc_temperature'] == 298.15 and node['tc_pressure'] == 100000
    p.vibrational.fully_periodic = True
    assert 'THERMOCHEMISTRY' in english(validate_project(p).errors)
    p.vibrational.thermochemistry = False
    assert validate_project(p).ok
    p.structure.periodic = 'XYZ'
    p.dft.poisson_solver = 'PERIODIC'
    p.vibrational.fully_periodic = False
    result = validate_project(p)
    assert 'FULLY_PERIODIC' in english(result.infos)
    assert 'FULLY_PERIODIC' not in english(result.warnings)
    assert not p.vibrational.fully_periodic
    p.vibrational.fully_periodic = True
    node = validator.parse(generate_input(p)).tree['+vibrational_analysis']
    assert node['fully_periodic'] and 'tc_temperature' not in node


@pytest.mark.parametrize('setting', ['diagonalization', 'uks', 'smearing', 'added_mos'])
def test_raman_implemented_solver_subset(vib_project, setting):
    p = vib_project
    set_model_spectra(p.vibrational, 'RAMAN')
    if setting == 'diagonalization':
        p.dft.scf.method = 'DIAGONALIZATION'
    elif setting == 'uks':
        p.dft.uks = True
    elif setting == 'smearing':
        p.dft.scf.smearing = True
    else:
        p.dft.scf.added_mos = 1
    assert 'implemented workflow' in english(validate_project(p).errors)


def test_warnings_do_not_claim_geometry_or_scf_verified_and_constraints_are_isolated(vib_project):
    p = vib_project
    p.dft.scf.eps_scf = 1e-6
    p.structure.fixed_atoms = [FixedAtom(atom_id=1, components='Z')]
    result = validate_project(p)
    warnings = english(result.warnings)
    assert 'EPS_SCF' in warnings and 'fixed-atom' in warnings
    assert 'sufficiently optimized' in english(result.infos)
    text = generate_input(p)
    assert '&CONSTRAINT' not in text and '&MOTION' not in text
    p.global_settings.run_type = 'GEO_OPT'
    geometry = generate_input(p)
    assert '&FIXED_ATOMS' in geometry and 'LIST 1' in geometry
    assert '&VIBRATIONAL_ANALYSIS' not in geometry
    p.global_settings.run_type = 'VIBRATIONAL_ANALYSIS'
    assert generate_input(p) == text and p.structure.fixed_atoms[0].components == 'Z'


@pytest.mark.parametrize('task', ['ENERGY', 'GEO_OPT'])
def test_inactive_vibration_settings_do_not_change_existing_task_input(water, task):
    water.global_settings.run_type = task
    before = generate_input(water)
    set_model_spectra(water.vibrational, 'RAMAN')
    water.vibrational.nproc_rep = 1000  # Invalid resources for vibrations only.
    water.vibrational.dx = .004
    water.vibrational.fully_periodic = True
    water.vibrational.thermochemistry = True
    assert generate_input(water) == before


@pytest.mark.parametrize('mode', ['FREQUENCIES', 'IR', 'RAMAN'])
def test_project_preset_and_supported_inp_round_trip(vib_project, tmp_path, mode):
    p = vib_project
    set_model_spectra(p.vibrational, mode)
    p.vibrational.dx = .006
    p.vibrational.hessian = True
    p.structure.fixed_atoms = [FixedAtom(atom_id=2, components='XY')]
    path = tmp_path / 'vibrational.json'
    save_project(p, path)
    assert load_project(path) == p
    assert 'intensities' not in p.vibrational.model_dump()
    store = PresetStore(tmp_path / 'presets')
    preset = store.save(capture_preset(p, 'Vibrational test', category='custom'))
    assert 'vibrational' in preset.parameters and preset.coordinates is None
    target = p.model_copy(deep=True)
    target.vibrational = VibrationalConfig()
    restored = apply_preset(target, store.load(preset.id)).project
    assert restored.vibrational == p.vibrational and restored.structure == p.structure
    inp = tmp_path / 'vibration.inp'
    export_input(p, inp)
    imported, warnings = import_input(inp)
    assert imported.global_settings.run_type == 'VIBRATIONAL_ANALYSIS'
    assert imported.vibrational.spectra_label == mode and imported.vibrational.dx == .006
    assert imported.vibrational.hessian and generate_input(imported) == generate_input(p)


def test_old_projects_have_safe_defaults(water):
    data = water.model_dump()
    data.pop('vibrational')
    restored = Project.model_validate(data)
    assert restored.vibrational == VibrationalConfig()
    assert not restored.vibrational.intensities and not restored.vibrational.fully_periodic
    assert restored.global_settings == water.global_settings and restored.dft == water.dft


@pytest.mark.parametrize('mode', ['FREQUENCIES', 'IR', 'RAMAN'])
def test_comprehensive_check_and_portable_package(vib_project, validator, tmp_path, mode):
    p = vib_project
    set_model_spectra(p.vibrational, mode)
    p.vibrational.hessian = True
    p.run_environment.omp_threads = 2
    result = comprehensive_check(p)
    assert result.validation.ok, result.validation.errors
    assert all(stage.executed for stage in result.stages)
    assert result.stages[1].state == 'ready'
    assert result.stages[0].state == 'warning'  # No false minimum/convergence claim.
    folder = export_bundle(p, tmp_path / mode).parent
    assert {'input.inp', 'structure.xyz', 'run.sh', 'EXPORT_NOTES.txt', 'project.cp2kstudio.json'} <= {f.name for f in folder.iterdir()}
    text = (folder / 'input.inp').read_text()
    assert validator.parse(text, folder).ok
    assert 'COORD_FILE_NAME structure.xyz' in text and '&VIBRATIONAL_ANALYSIS' in text
    assert (folder / 'run.sh').read_text() == generate_run_script(p.run_environment)
    notes = (folder / 'EXPORT_NOTES.txt').read_text()
    assert 'bohr' in notes and 'per replica' in notes and 'output.out' in notes
    assert 'CP2K has not run' in notes and '未运行 CP2K' in notes
    assert not list(folder.glob('*.hess')) and not (folder / 'output.out').exists()
    assert load_project(folder / 'project.cp2kstudio.json').vibrational == p.vibrational
    archive = export_bundle(p, tmp_path / (mode + '.zip'), archive=True)
    with zipfile.ZipFile(archive) as zipped:
        assert any(name.endswith('run.sh') for name in zipped.namelist())


def test_import_rejects_intensities_without_required_properties(vib_project, tmp_path):
    text = generate_input(vib_project).replace('INTENSITIES FALSE', 'INTENSITIES TRUE')
    path = tmp_path / 'incomplete-spectrum.inp'
    path.write_text(text)
    with pytest.raises(ValueError):
        import_input(path)
