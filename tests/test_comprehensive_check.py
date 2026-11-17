"""Exercise real XML parsing and the actual temporary package, without CP2K."""
from pathlib import Path
import subprocess
import pytest
from core import comprehensive_check as checks
from core import generator, project_io
from core.database_resources import MERGED_POTENTIAL
from core.file_references import generated_file_references
from core.kind_validator import project_catalog
from core.models import DatabaseReference
from core.schema import BUNDLED_XML


def prepare_spy(monkeypatch, mutate=lambda directory: None):
    original = checks._write_bundle_files
    directories = []
    def write(*args, **kwargs):
        text = original(*args, **kwargs)
        directories.append(args[1])
        mutate(args[1])
        return text
    monkeypatch.setattr(checks, '_write_bundle_files', write)
    return directories


@pytest.mark.parametrize('mpi,omp', [(16, 1), (8, 4)])
def test_all_four_stages_inspect_real_files_without_running_programs(water, monkeypatch, mpi, omp):
    water.run_environment.mpi_processes = mpi
    water.run_environment.omp_threads = omp
    before = water.model_dump()
    originals = {path: Path(path).read_bytes() for path in checks.source_signatures(water, project_catalog(water))}
    def no_process(*args, **kwargs):
        pytest.fail('A static comprehensive check must not execute programs')
    monkeypatch.setattr(subprocess, 'Popen', no_process)
    observed = []
    def inspect(directory):
        script = (directory / 'run.sh').read_text()
        notes = (directory / 'EXPORT_NOTES.txt').read_text()
        command = f'mpirun -np {mpi} cp2k.psmp -i input.inp -o output.out'
        assert command in script and command in notes
        assert f'export OMP_NUM_THREADS={omp}' in script
        refs = list(generated_file_references((directory / 'input.inp').read_text()))
        assert all(not Path(ref.value).is_absolute() and (directory / ref.value).is_file() for ref in refs)
        observed.append(directory)
    directories = prepare_spy(monkeypatch, inspect)
    result = checks.comprehensive_check(water)
    assert [stage.state for stage in result.stages] == ['ready'] * 4
    assert not result.validation.errors and not result.validation.warnings
    assert f'所需逻辑核数: {mpi * omp}' in result.report()
    assert observed == directories and all(not path.exists() for path in directories)
    assert water.model_dump() == before
    assert all(Path(path).read_bytes() == content for path, content in originals.items())
    assert 'GEO_OPT' not in '\n'.join(result.validation.errors)  # ENERGY needs no extra optimizer input


@pytest.mark.parametrize('missing', ['charge', 'xc_functional', 'basis_set', 'potential'])
def test_incomplete_configuration_never_passes_skipped_xml(water, missing):
    if missing in ('charge', 'xc_functional'):
        setattr(water.dft, missing, None)
    else:
        setattr(water.kinds['O'], missing, '')
    result = checks.comprehensive_check(water)
    assert result.stages[0].errors and result.validation.errors
    assert all(stage.state == 'not_run' for stage in result.stages[1:])
    assert '未执行' in result.report() and '综合检查通过\n' not in result.report()


@pytest.mark.parametrize('field,value', [('mpi_processes', 0), ('omp_threads', -1), ('mpi_processes', 1.5)])
def test_invalid_run_draft_is_reported_without_crash(water, field, value):
    # Bypass assignment validation to simulate malformed imported state.
    water.run_environment.__dict__[field] = value
    result = checks.comprehensive_check(water)
    assert result.stages[0].errors
    assert all(not stage.executed for stage in result.stages[1:])


@pytest.mark.parametrize('invalid', ['section', 'keyword'])
def test_real_xml_service_rejects_illegal_generated_input(water, monkeypatch, invalid):
    original = generator.build_sections
    def build(*args, **kwargs):
        sections = original(*args, **kwargs)
        if invalid == 'section':
            sections.append(generator.Section('NOT_A_CP2K_SECTION'))
        else:
            sections[0].keywords.append(('NOT_A_CP2K_KEYWORD', 'bad'))
        return sections
    monkeypatch.setattr(generator, 'build_sections', build)
    result = checks.comprehensive_check(water)
    assert result.stages[0].state == 'ready'
    assert result.stages[1].state == 'error'
    assert 'NOT_A_CP2K_' in result.report()
    assert result.validation.errors


@pytest.mark.parametrize('xml_kind', ['missing', 'malformed', 'old'])
def test_unusable_xml_is_explicit_failure(water, tmp_path, xml_kind):
    xml = tmp_path / 'schema.xml'
    if xml_kind == 'malformed':
        xml.write_text('<broken')
    elif xml_kind == 'old':
        xml.write_text(BUNDLED_XML.read_text().replace('2026.1', '2025.1'))
    water.xml_spec = str(xml)
    result = checks.comprehensive_check(water)
    assert result.stages[1].state == 'error'
    assert str(xml) in result.report()
    assert all(stage.state == 'not_run' for stage in result.stages[2:])


@pytest.mark.parametrize('keyword', ['COORD_FILE_NAME', 'BASIS_SET_FILE_NAME', 'POTENTIAL_FILE_NAME'])
def test_missing_final_packaged_files_are_checked_from_run_directory(water, monkeypatch, keyword):
    def remove(directory):
        ref = next(ref for ref in generated_file_references((directory / 'input.inp').read_text()) if ref.keyword == keyword)
        (directory / ref.value).unlink()
    directories = prepare_spy(monkeypatch, remove)
    result = checks.comprehensive_check(water)
    assert result.stages[2].state == 'error'
    assert keyword in '\n'.join(result.stages[2].errors)
    assert not directories[0].exists()


@pytest.mark.parametrize('reference', ['/developer/missing/structure.xyz', '../structure.xyz', '"structure.xyz"'])
def test_final_disk_references_cannot_escape_or_use_shell_quotes(water, monkeypatch, reference):
    def corrupt(directory):
        inp = directory / 'input.inp'
        inp.write_text(inp.read_text().replace('COORD_FILE_NAME structure.xyz', f'COORD_FILE_NAME {reference}'))
    prepare_spy(monkeypatch, corrupt)
    result = checks.comprehensive_check(water)
    assert result.stages[2].state == 'error'
    assert 'COORD_FILE_NAME' in result.report()


@pytest.mark.parametrize('keyword', ['BASIS_SET_FILE_NAME', 'POTENTIAL_FILE_NAME'])
def test_existing_database_file_without_selected_entry_is_not_accepted(water, monkeypatch, keyword):
    def remove_entries(directory):
        ref = next(ref for ref in generated_file_references((directory / 'input.inp').read_text()) if ref.keyword == keyword)
        (directory / ref.value).write_text('# exists, but selected entries are absent\n')
    prepare_spy(monkeypatch, remove_entries)
    result = checks.comprehensive_check(water)
    assert result.stages[2].state == 'error'
    assert '条目' in result.report()


def test_multi_library_merged_potential_and_standalone_sidecar_are_checked(water, monkeypatch):
    catalog = project_catalog(water)
    for element, basis_source, potential_source, basis_name in [
            ('O', 'GTH_BASIS_SETS', 'POTENTIAL', 'DZVP-GTH'),
            ('H', 'BASIS_MOLOPT', 'GTH_POTENTIALS', 'DZVP-MOLOPT-GTH')]:
        kind = water.kinds[element]
        basis = next(e for e in catalog.find('basis', element, basis_name) if Path(e.path).name == basis_source)
        potential = next(e for e in catalog.find('potential', element, kind.potential) if Path(e.path).name == potential_source)
        kind.basis_set = basis_name
        kind.basis_ref = DatabaseReference(**basis.reference())
        kind.potential_ref = DatabaseReference(**potential.reference())
    inspected = []
    def inspect(directory):
        assert f'POTENTIAL_FILE_NAME {MERGED_POTENTIAL}' in (directory / 'input.inp').read_text()
        assert (directory / MERGED_POTENTIAL).is_file()
        inspected.append(directory)
    prepare_spy(monkeypatch, inspect)
    result = checks.comprehensive_check(water)
    assert all(stage.state == 'ready' for stage in result.stages), result.report()
    assert inspected


@pytest.mark.parametrize('filename,old,new', [
    ('run.sh', 'mpirun -np 16', 'mpirun -np 99'),
    ('run.sh', 'export OMP_NUM_THREADS=1', 'export OMP_NUM_THREADS=4'),
    ('run.sh', 'input_file=input.inp', 'input_file=missing.inp'),
    ('run.sh', '-o output.out', '-o wrong.out'),
    ('EXPORT_NOTES.txt', 'MPI Processes: 16', 'MPI Processes: 7'),
    ('EXPORT_NOTES.txt', 'mpirun -np 16', 'mpirun -np 2'),
])
def test_actual_scripts_and_notes_must_match_configuration(water, monkeypatch, filename, old, new):
    water.run_environment.mpi_processes = 16
    water.run_environment.omp_threads = 1
    def corrupt(directory):
        path = directory / filename
        text = path.read_text()
        assert old in text
        path.write_text(text.replace(old, new))
    prepare_spy(monkeypatch, corrupt)
    result = checks.comprehensive_check(water)
    assert result.stages[3].state == 'error'
    assert 'RUN_ENVIRONMENT' in result.report()


def test_recheck_parses_latest_input_and_uses_existing_xml_service(water, validator):
    inputs = []
    class Service:
        def parse(self, text, directory):
            inputs.append(text)
            return validator.parse(text, directory)
    factory_calls = []
    def factory(project):
        factory_calls.append(project.dft.cutoff)
        return Service()
    for cutoff in [400, 550]:
        water.dft.cutoff = cutoff
        result = checks.comprehensive_check(water, validator_factory=factory)
        assert not result.validation.errors
    assert factory_calls == [400, 550]
    assert len(inputs) == 4
    assert all('CUTOFF 400\n' in text for text in inputs[:2])
    assert all('CUTOFF 550\n' in text for text in inputs[2:])


def test_export_rechecks_final_disk_paths_and_scripts(water, monkeypatch, tmp_path):
    original = project_io._write_bundle_files
    def corrupt(*args, **kwargs):
        text = original(*args, **kwargs)
        path = args[1] / 'input.inp'
        path.write_text(text.replace('COORD_FILE_NAME structure.xyz', 'COORD_FILE_NAME absent.xyz'))
        return text
    monkeypatch.setattr(project_io, '_write_bundle_files', corrupt)
    with pytest.raises(generator.GenerationError, match='absent.xyz'):
        project_io.export_bundle(water, tmp_path / 'failed')
    assert not (tmp_path / 'failed').exists()
    assert not list(tmp_path.iterdir())
