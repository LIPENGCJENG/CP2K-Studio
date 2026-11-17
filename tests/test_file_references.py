"""Regress literal CP2K filenames, independently of XML quote normalization."""
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

import pytest
import numpy as np
from ase.io import write
from core.database_manager import BUNDLED_DATA
from core.file_references import (FileReferenceError, serialize_file_reference,
    generated_file_references, check_generated_dependencies, safe_resource_name)
from core.generator import generate_input, GenerationError, Section
from core.project_io import export_bundle, load_project, save_project
from core.input_export import export_input
from core.structure import load_structure, to_atoms
from ui.main_window import MainWindow


@pytest.mark.parametrize('keyword,path', [('COORD_FILE_NAME', 'structure.xyz'),
    ('BASIS_SET_FILE_NAME', 'data/BASIS_MOLOPT'), ('POTENTIAL_FILE_NAME', 'data/POTENTIAL')])
def test_plain_cp2k_file_values_are_not_quoted(keyword, path):
    assert serialize_file_reference(path, keyword) == path
    assert Section('TEST', keywords=[(keyword, serialize_file_reference(path, keyword))]).render()[1] == f'  {keyword} {path}'


def test_long_character_internal_spaces_are_literal_not_shell_escaped(validator):
    # These three CP2K 2026.1 keywords are whole-line long-character values.
    value = '/local/data directory/BASIS_MOLOPT'
    assert serialize_file_reference(value, 'BASIS_SET_FILE_NAME') == value
    parsed = validator.parse(f'&FORCE_EVAL\n &DFT\n BASIS_SET_FILE_NAME {value}\n &END\n&END\n')
    assert parsed.ok and parsed.tree['+force_eval'][0]['+dft']['basis_set_file_name'] == [value]


@pytest.mark.parametrize('name', ['"structure.xyz"', "'structure.xyz'", 'file#comment', 'file!comment',
    '$VARIABLE', '@INCLUDE', 'a\\b', 'two  spaces.xyz', ' leading.xyz', 'trailing.xyz ', 'x\ty', 'x\ny', 'x\x00y', '晶胞.xyz'])
def test_unsafe_direct_references_are_explicitly_rejected(name):
    with pytest.raises(FileReferenceError, match='导出完整计算包'):
        serialize_file_reference(name, 'COORD_FILE_NAME')


def test_other_strings_and_section_values_are_not_globally_changed():
    assert Section('TEST', keywords=[('UNCHANGED', '"legitimate quoted content"')]).render()[1] == '  UNCHANGED "legitimate quoted content"'
    with pytest.raises(FileReferenceError, match='未定义'):
        serialize_file_reference('name', 'UNKNOWN_FILE_KEYWORD')


def test_external_coordinate_reference_and_literal_checker(water, tmp_path, validator):
    text = generate_input(water, coordinate_file='structure.xyz')
    assert 'COORD_FILE_NAME structure.xyz\n' in text
    assert 'COORD_FILE_NAME "structure.xyz"' not in text
    assert "COORD_FILE_NAME 'structure.xyz'" not in text
    assert validator.parse(text).ok
    (tmp_path / 'structure.xyz').write_text('3\nexample\nO 0 0 0\nH 0 0 1\nH 0 1 0\n')
    assert not check_generated_dependencies(text, tmp_path)
    broken = text.replace('COORD_FILE_NAME structure.xyz', 'COORD_FILE_NAME "structure.xyz"')
    assert validator.parse(broken).ok  # The XML parser masks this runtime bug.
    assert any('COORD_FILE_NAME' in e for e in check_generated_dependencies(broken, tmp_path))
    (tmp_path / 'structure.xyz').unlink()
    assert any('structure.xyz' in e for e in check_generated_dependencies(text, tmp_path))


@pytest.mark.parametrize('extension', ['xyz', 'extxyz', 'cif'])
def test_structure_import_formats_with_special_source_names_export_safe_xyz(water, tmp_path, extension):
    original = tmp_path / f'structure with spaces # 中文.{extension}'
    write(original, to_atoms(water.structure), format=extension)
    content = original.read_bytes()
    imported = load_structure(original)
    if extension == 'xyz':
        imported.cell = water.structure.cell
        imported.periodic = water.structure.periodic
    water.structure = imported
    before = water.model_dump()
    path = export_bundle(water, tmp_path / f'package {extension}')
    assert original.read_bytes() == content and water.model_dump() == before
    assert 'COORD_FILE_FORMAT XYZ' in path.read_text()
    assert 'COORD_FILE_NAME structure.xyz' in path.read_text()
    assert not check_generated_dependencies(path.read_text(), path.parent, require_relative=True)
    assert np.allclose(load_structure(path.parent / 'structure.xyz').positions, imported.positions, rtol=0, atol=1e-12)
    assert {'input.inp', 'structure.xyz', 'run.sh', 'EXPORT_NOTES.txt'} <= {p.name for p in path.parent.iterdir()}


def special_databases(water, tmp_path):
    # Quote/question-mark filenames exist on POSIX, but cannot be created on
    # Windows. Use equally unsafe-for-INP characters there instead.
    second_name = 'same?library' if os.name == 'posix' else 'same#library'
    potential_name = 'potential "bad" # file' if os.name == 'posix' else 'potential @ # file'
    sources = [tmp_path / 'a' / 'same library', tmp_path / 'b' / second_name,
               tmp_path / 'c' / potential_name]
    for target, name in zip(sources, ['BASIS_MOLOPT', 'BASIS_MOLOPT', 'GTH_POTENTIALS']):
        target.parent.mkdir()
        target.write_bytes((BUNDLED_DATA / name).read_bytes())
    water.dft.basis_files = [str(p) for p in sources[:2]]
    water.dft.potential_file = str(sources[2])
    return sources


def test_special_database_names_normalized_without_collisions_or_source_mutation(water, tmp_path):
    sources = special_databases(water, tmp_path)
    assert safe_resource_name(sources[0].name) == safe_resource_name(sources[1].name)
    before = water.model_dump()
    original_bytes = [p.read_bytes() for p in sources]
    path = export_bundle(water, tmp_path / 'bundle')
    refs = list(generated_file_references(path.read_text()))
    assert len(refs) == 4
    assert all('"' not in r.value and "'" not in r.value and ' ' not in r.value for r in refs)
    assert len(set(r.value for r in refs)) == 4
    assert not check_generated_dependencies(path.read_text(), path.parent, require_relative=True)
    for ref in refs:
        assert (path.parent / ref.value).is_file()
    assert water.model_dump() == before and [p.read_bytes() for p in sources] == original_bytes
    reopened = load_project(path.parent / 'project.cp2kstudio.json')
    second = export_bundle(reopened, tmp_path / 'again')
    assert not check_generated_dependencies(second.read_text(), second.parent, require_relative=True)
    with pytest.raises(FileReferenceError, match='导出完整计算包'):
        export_input(water, tmp_path / 'standalone.inp')
    assert not (tmp_path / 'standalone.inp').exists()
    with pytest.raises(FileReferenceError):
        export_bundle(water, tmp_path / 'no_copy', copy_resources=False)
    assert not (tmp_path / 'no_copy').exists()


@pytest.mark.parametrize('missing', ['coordinate', 'basis', 'potential'])
def test_export_checks_actual_staged_files_and_cleans_failed_delivery(water, tmp_path, monkeypatch, missing):
    from core import project_io
    if missing == 'coordinate':
        original = project_io.write_structure
        def drop_coordinate(structure, path):
            original(structure, path)
            Path(path).unlink()
        monkeypatch.setattr(project_io, 'write_structure', drop_coordinate)
        expected = 'COORD_FILE_NAME'
    else:
        original = project_io.shutil.copy2
        filename = 'BASIS_MOLOPT' if missing == 'basis' else 'GTH_POTENTIALS'
        def drop_copy(source, target):
            result = original(source, target)
            if Path(source).name == filename:
                Path(target).unlink()
            return result
        monkeypatch.setattr(project_io.shutil, 'copy2', drop_copy)
        expected = 'BASIS_SET_FILE_NAME' if missing == 'basis' else 'POTENTIAL_FILE_NAME'
    with pytest.raises(GenerationError, match=expected):
        export_bundle(water, tmp_path / 'failed', archive=True)
    assert not (tmp_path / 'failed').exists() and not list(tmp_path.glob('.cp2k-studio-*'))


def test_final_dependency_checker_uses_run_directory_and_rejects_escape(water, tmp_path, monkeypatch):
    path = export_bundle(water, tmp_path / 'job')
    text = path.read_text()
    monkeypatch.chdir(tmp_path)
    assert not check_generated_dependencies(text, path.parent, require_relative=True)
    assert check_generated_dependencies(text, tmp_path, require_relative=True)
    outside = tmp_path / 'outside.xyz'
    outside.write_text('not a package coordinate file')
    escaped = text.replace('COORD_FILE_NAME structure.xyz', 'COORD_FILE_NAME ../outside.xyz')
    assert any('包内相对路径' in e for e in check_generated_dependencies(escaped, path.parent, require_relative=True))


def test_gui_preview_standalone_and_bundle_share_file_rules(app, water, tmp_path):
    window = MainWindow(preset_directory=tmp_path / 'presets')
    window.load_into_ui(water)
    expected = window.preview.toPlainText()
    single = export_input(window.project, tmp_path / 'single.inp').path
    bundle = export_bundle(window.project, tmp_path / 'bundle')
    assert single.read_text() == expected
    # Preview/standalone deliberately embed COORD; bundles reference the
    # canonical XYZ of exactly the same configured coordinates and KIND labels.
    assert 'COORD_FILE_NAME' not in expected and '&COORD' in expected
    assert 'COORD_FILE_NAME structure.xyz' in bundle.read_text()
    assert load_structure(bundle.parent / 'structure.xyz').positions == water.structure.positions
    for text in [expected, single.read_text(), bundle.read_text()]:
        assert all(not ref.value.startswith(('"', "'")) for ref in generated_file_references(text))
    project_file = tmp_path / 'project.json'
    save_project(window.project, project_file)
    window.load_into_ui(load_project(project_file))
    assert window.preview.toPlainText() == expected
    window.dirty = False
    window.close()


def test_unsafe_path_gui_allows_bundle_and_comprehensive_check_warns(app, water, tmp_path, monkeypatch):
    from tests.test_layout_workflow import wait_for_worker
    special_databases(water, tmp_path)
    window = MainWindow(preset_directory=tmp_path / 'presets')
    window.load_into_ui(water)
    assert '导出完整计算包' in window.preview.toPlainText()
    assert window.export_action.isEnabled() and window.ready_to_export()
    messages = []
    monkeypatch.setattr(window, '_error', lambda title, error: messages.append(str(error)))
    window.check_current_configuration()
    wait_for_worker(app, window)
    assert not messages
    assert not window._comprehensive_result.validation.errors
    assert window._step_states[7].state == 'warning'
    assert 'POTENTIAL_FILE_NAME' in window.report.toPlainText()
    assert '完整计算包' in window.report.toPlainText()
    path = export_bundle(window.project, tmp_path / 'safe_bundle')
    assert not check_generated_dependencies(path.read_text(), path.parent, require_relative=True)
    window.dirty = False
    window.close()


def test_moved_zipped_bundle_script_reads_literal_filenames(water, tmp_path):
    bash = shutil.which('bash')
    if os.name != 'posix' or not bash:
        pytest.skip('Bash integration requires a POSIX host and Bash')
    archive_path = export_bundle(water, tmp_path / 'job.zip', archive=True)
    moved = tmp_path / 'moved bundle with spaces'
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(moved)
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    launcher = bin_dir / 'mpirun'
    launcher.write_text('#!/bin/bash\nshift 2\nexec "$@"\n')
    cp2k = bin_dir / 'cp2k.psmp'
    cp2k.write_text('''#!/bin/bash
while read -r keyword value; do
    case "$keyword" in
        COORD_FILE_NAME|BASIS_SET_FILE_NAME|POTENTIAL_FILE_NAME)
            if [[ ! -r "$value" ]]; then
                printf 'Literal file not found: %s\n' "$value" >&2
                exit 91
            fi
            ;;
    esac
done < "$2"
printf 'coordinates and data opened\n' > "$4"
''')
    for command in [launcher, cp2k]:
        command.chmod(0o755)
    environment = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ['PATH'])
    def launch():
        return subprocess.run([bash, str(moved / 'run.sh')], cwd=tmp_path, env=environment,
                              capture_output=True, text=True, timeout=10)
    result = launch()
    assert result.returncode == 0, result.stderr
    assert (moved / 'output.out').read_text().strip() == 'coordinates and data opened'
    inp = moved / 'input.inp'
    inp.write_text(inp.read_text().replace('COORD_FILE_NAME structure.xyz', 'COORD_FILE_NAME "structure.xyz"'))
    broken = launch()
    assert broken.returncode == 91 and '"structure.xyz"' in broken.stderr
