import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import zipfile

import pytest
from pydantic import ValidationError
from core.models import Project
from core.run_config import RunEnvironment
from core.run_script_generator import generate_run_script, run_command
from core.project_io import save_project, load_project, export_bundle
from core.input_export import export_input
from core.generator import generate_input
from core.presets import capture_preset, apply_preset


@pytest.mark.parametrize('mpi,omp,slots', [(16, 1, 16), (8, 2, 16), (8, 4, 32), (16, 4, 64), (32, 2, 64)])
def test_resources_and_modes(mpi, omp, slots):
    config = RunEnvironment(mpi_processes=mpi, omp_threads=omp)
    assert config.required_cpu_slots == slots
    assert config.execution_mode == ('Pure MPI' if omp == 1 else 'MPI + OpenMP')
    assert config.mode_label == ('纯 MPI' if omp == 1 else 'MPI + OpenMP 混合并行')


@pytest.mark.parametrize('field', ['mpi_processes', 'omp_threads'])
@pytest.mark.parametrize('value', [0, -1, 1.5, True, '8', 2**31])
def test_reject_invalid_parallel_settings(field, value):
    with pytest.raises(ValidationError):
        RunEnvironment(**{field: value})
    config = RunEnvironment()
    with pytest.raises(ValidationError):
        setattr(config, field, value)


def test_default_and_quoted_commands():
    assert run_command(RunEnvironment()) == ('export OMP_NUM_THREADS=1\n'
        'mpirun -np 16 cp2k.psmp -i input.inp -o output.out')
    name = "folder/input 'special'; $(echo unsafe).inp"
    command = run_command(RunEnvironment(mpi_processes=8, omp_threads=4), name)
    assert command.splitlines()[0] == 'export OMP_NUM_THREADS=4'
    assert shlex.split(command.splitlines()[1]) == ['mpirun', '-np', '8', 'cp2k.psmp', '-i', name, '-o', 'output.out']
    assert str(Path.cwd()) not in command


@pytest.mark.parametrize('name', ['/tmp/input.inp', '../input.inp', 'a/../../bad', 'x\ny', 'a\x00b', '', 'a\\b'])
def test_script_rejects_nonportable_or_escaping_names(name):
    with pytest.raises(ValueError):
        generate_run_script(RunEnvironment(), name)


@pytest.fixture
def bash_tools(tmp_path):
    bash = shutil.which('bash')
    if os.name != 'posix' or not bash:
        pytest.skip('Portable Bash integration requires a POSIX host and Bash')
    bin_dir = tmp_path / 'mock bin'
    bin_dir.mkdir()
    (bin_dir / 'dirname').symlink_to(shutil.which('dirname'))
    launcher = bin_dir / 'mpirun'
    launcher.write_text('''#!/bin/bash
printf '%s\n' "$@" > mpi-args.txt
shift 2
exec "$@"
''')
    cp2k = bin_dir / 'cp2k.psmp'
    cp2k.write_text('''#!/bin/bash
printf '%s\n' "$@" > cp2k-args.txt
printf '%s\n' "$OMP_NUM_THREADS" > omp.txt
printf 'mock output\n' > "$4"
exit "${MOCK_EXIT:-0}"
''')
    launcher.chmod(0o755)
    cp2k.chmod(0o755)
    return bash, bin_dir, dict(os.environ, PATH=str(bin_dir))


def run_script(bash_tools, script, cwd, **env):
    bash, _, environment = bash_tools
    return subprocess.run([bash, str(script)], cwd=cwd, env=dict(environment, **env),
                          capture_output=True, text=True, timeout=10)


@pytest.mark.parametrize('system', ['linux', 'macos', 'wsl2'])
def test_script_syntax_argument_safety_and_exit_status(tmp_path, bash_tools, system):
    package = tmp_path / "moved calculation ' $ folder"
    package.mkdir()
    name = "input '; $(touch pwned); &.inp"
    (package / name).write_text('mock input')
    script = package / 'run.sh'
    config = RunEnvironment(operating_system=system, mpi_processes=8, omp_threads=4)
    script.write_text(generate_run_script(config, name), newline='\n')
    syntax = subprocess.run([bash_tools[0], '-n', str(script)], capture_output=True, timeout=10)
    assert syntax.returncode == 0, syntax.stderr
    assert b'\r' not in script.read_bytes()
    assert str(tmp_path) not in script.read_text() and 'eval ' not in script.read_text()
    result = run_script(bash_tools, script, tmp_path, MOCK_EXIT='73')
    assert result.returncode == 73, result.stderr
    assert (package / 'mpi-args.txt').read_text().splitlines() == ['-np', '8', 'cp2k.psmp', '-i', name, '-o', 'output.out']
    assert (package / 'cp2k-args.txt').read_text().splitlines() == ['-i', name, '-o', 'output.out']
    assert (package / 'omp.txt').read_text().strip() == '4'
    assert (package / 'output.out').is_file()
    assert not list(tmp_path.rglob('pwned'))
    assert not (tmp_path / 'output.out').exists()


@pytest.mark.parametrize('missing,code,message', [('input.inp', 2, 'Input file not found'),
    ('cp2k.psmp', 127, 'cp2k.psmp: command not found'), ('mpirun', 127, 'mpirun: command not found')])
def test_script_preflight_errors(tmp_path, bash_tools, missing, code, message):
    package = tmp_path / 'package'
    package.mkdir()
    (package / 'input.inp').write_text('input')
    script = package / 'run.sh'
    script.write_text(generate_run_script(RunEnvironment()))
    target = package / missing if missing == 'input.inp' else bash_tools[1] / missing
    target.unlink()
    result = run_script(bash_tools, script, tmp_path)
    assert result.returncode == code and message in result.stderr
    assert not (package / 'mpi-args.txt').exists()


def test_project_roundtrip_defaults_and_no_scientific_preset_leak(water, tmp_path):
    original = generate_input(water)
    water.run_environment = RunEnvironment(operating_system='wsl2', mpi_processes=8, omp_threads=4)
    path = tmp_path / 'project.json'
    save_project(water, path)
    assert load_project(path) == water
    assert generate_input(water) == original
    preset = capture_preset(water, 'science only')
    assert 'run_environment' not in preset.parameters
    target = water.model_copy(deep=True)
    target.run_environment = RunEnvironment(operating_system='macos', mpi_processes=2, omp_threads=3)
    assert apply_preset(target, preset).project.run_environment == target.run_environment
    data = water.model_dump()
    data.pop('run_environment')
    path.write_text(json.dumps(data))
    old = load_project(path)
    assert old.run_environment == RunEnvironment() and not old._migration_warnings


@pytest.mark.parametrize('nested', [True, False])
@pytest.mark.parametrize('total,omp,expected', [(32, 4, (8, 4)), (15, 4, (16, 1)), (0, 1, (16, 1)),
    (16, 0, (16, 1)), ('32', 2, (16, 1)), (32, None, (16, 1))])
def test_legacy_migration(tmp_path, nested, total, omp, expected):
    legacy = {'total_cpu_cores': total, 'omp_threads': omp}
    data = {'run_environment': legacy} if nested else legacy
    path = tmp_path / 'old.json'
    path.write_text(json.dumps(data))
    project = load_project(path)
    assert (project.run_environment.mpi_processes, project.run_environment.omp_threads) == expected
    assert project._migration_warnings
    save_project(project, path)
    assert 'total_cpu_cores' not in path.read_text()
    assert load_project(path).run_environment == project.run_environment


def test_invalid_modern_run_configuration_is_reported(tmp_path):
    path = tmp_path / 'invalid.json'
    path.write_text(json.dumps({'run_environment': {'mpi_processes': 0}}))
    with pytest.raises(ValueError, match='mpi_processes'):
        load_project(path)


def test_bundle_script_notes_portability_and_single_input(water, tmp_path, bash_tools):
    water.run_environment = RunEnvironment(operating_system='macos', mpi_processes=8, omp_threads=2)
    package = tmp_path / 'original'
    export_bundle(water, package)
    moved = tmp_path / 'moved package'
    package.rename(moved)
    script = moved / 'run.sh'
    notes = (moved / 'EXPORT_NOTES.txt').read_text()
    assert run_command(water.run_environment) in script.read_text()
    assert run_command(water.run_environment) in notes
    assert 'Required Logical CPU Slots: 16' in notes and 'Execution Mode: MPI + OpenMP' in notes
    assert 'Operating System: macOS' in notes and 'bash run.sh' in notes
    assert 'not physical core' in notes and 'convergence' in notes
    for file in moved.rglob('*'):
        if file.is_file():
            assert file.relative_to(moved).as_posix() in notes
    assert load_project(moved / 'project.cp2kstudio.json').run_environment == water.run_environment
    result = run_script(bash_tools, script, tmp_path, MOCK_EXIT='0')
    assert result.returncode == 0, result.stderr
    assert (moved / 'output.out').exists()
    single = tmp_path / 'single'
    single.mkdir()
    result = export_input(water, single / 'custom name.inp')
    assert result.path.read_text() == generate_input(water)
    assert not (single / 'run.sh').exists() and not (single / 'EXPORT_NOTES.txt').exists()


def test_zip_contains_script_and_matches_notes(water, tmp_path):
    water.run_environment = RunEnvironment(operating_system='wsl2', mpi_processes=16, omp_threads=4)
    path = tmp_path / 'job.zip'
    assert export_bundle(water, path, archive=True) == path
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        assert {'input.inp', 'run.sh', 'EXPORT_NOTES.txt', 'structure.xyz', 'project.cp2kstudio.json'} <= set(names)
        assert all(not name.startswith('/') and '..' not in Path(name).parts for name in names)
        script, notes = archive.read('run.sh').decode(), archive.read('EXPORT_NOTES.txt').decode()
        assert run_command(water.run_environment) in script and run_command(water.run_environment) in notes
        assert 'Required Logical CPU Slots: 64' in notes and 'PowerShell' in notes
        assert all(name in notes for name in names)
    with pytest.raises(FileExistsError):
        export_bundle(water, path, archive=True)
    assert not list(tmp_path.glob('.cp2k-studio-*'))


def test_notes_explicitly_report_uncopied_dependencies(water, tmp_path):
    path = export_bundle(water, tmp_path / 'external', copy_resources=False)
    notes = (path.parent / 'EXPORT_NOTES.txt').read_text()
    assert 'NOT copied' in notes and 'not self-contained' in notes
    assert 'Selected basis/potential data and structure files are included' not in notes
    assert not (path.parent / 'data').exists()
